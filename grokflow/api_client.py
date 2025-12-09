"""
GrokFlow API Client

Centralized API client for x.ai Grok models with:
- Automatic retry with exponential backoff
- Rate limit handling
- Streaming support
- Error handling and logging
- Model validation
- Cost tracking integration
"""

import os
import time
from typing import Optional, Dict, List, Iterator, Any
from pathlib import Path

import httpx
from openai import OpenAI

from grokflow.exceptions import (
    APIError, RateLimitError, AuthenticationError,
    ModelNotAvailableError, APITimeoutError
)
from grokflow.logging_config import get_logger
from grokflow.rate_limiter import get_rate_limiter

logger = get_logger('grokflow.api_client')


class GrokAPIClient:
    """
    Centralized API client for x.ai Grok models
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Streaming support
    - Model validation
    - Cost tracking
    
    Example:
        >>> client = GrokAPIClient()
        >>> response = client.chat_completion(
        ...     model='grok-4-fast',
        ...     messages=[{'role': 'user', 'content': 'Hello'}]
        ... )
    """
    
    # Valid x.ai models (as of Nov 2024)
    VALID_MODELS = {
        'grok-4-fast',    # Fast, efficient (default executor)
        'grok-4',         # High-quality with reasoning (planner)
        'grok-beta',      # Beta model (planner alternative)
        'grok-3',         # Previous generation
        'grok-3-mini'     # Previous generation mini
    }
    
    # Default models for dual-model architecture
    DEFAULT_PLANNER = 'grok-beta'
    DEFAULT_EXECUTOR = 'grok-4-fast'
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 60.0
    
    # Timeout configuration
    DEFAULT_TIMEOUT = 120.0
    STREAMING_TIMEOUT = 300.0
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.x.ai/v1",
        timeout: Optional[float] = None,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize API client
        
        Args:
            api_key: x.ai API key (default: from XAI_API_KEY env var)
            base_url: API base URL
            timeout: Request timeout in seconds
            enable_rate_limiting: Enable rate limiting
        """
        # Get API key
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "No API key provided. Set XAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=timeout or self.DEFAULT_TIMEOUT,
            http_client=httpx.Client(
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10
                )
            )
        )
        
        # Rate limiting
        self.enable_rate_limiting = enable_rate_limiting
        if enable_rate_limiting:
            self.rate_limiter = get_rate_limiter()
        
        logger.info(f"GrokAPIClient initialized with base_url: {base_url}")
    
    def validate_model(self, model: str) -> None:
        """
        Validate model name
        
        Args:
            model: Model name to validate
            
        Raises:
            ModelNotAvailableError: If model is invalid
        """
        if model not in self.VALID_MODELS:
            logger.error(f"Invalid model: {model}")
            raise ModelNotAvailableError(
                f"Model '{model}' is not available. "
                f"Valid models: {', '.join(sorted(self.VALID_MODELS))}"
            )
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = DEFAULT_EXECUTOR,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        Create chat completion
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Enable streaming
            **kwargs: Additional API parameters
            
        Returns:
            Completion response or stream iterator
            
        Raises:
            APIError: If API call fails
            RateLimitError: If rate limit exceeded
            AuthenticationError: If authentication fails
        """
        # Validate model
        self.validate_model(model)
        
        # Check rate limit
        if self.enable_rate_limiting:
            operation = 'api_call_planner' if model in ['grok-4', 'grok-beta'] else 'api_call_executor'
            try:
                self.rate_limiter.check_and_record(operation)
            except RateLimitError as e:
                logger.warning(f"Rate limit hit: {e}")
                raise
        
        # Prepare request
        request_params = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'stream': stream,
            **kwargs
        }
        
        if max_tokens:
            request_params['max_tokens'] = max_tokens
        
        logger.debug(
            f"API request: model={model}, messages={len(messages)}, "
            f"stream={stream}, temp={temperature}"
        )
        
        # Execute with retry
        return self._execute_with_retry(request_params, stream=stream)
    
    def _execute_with_retry(
        self,
        request_params: Dict[str, Any],
        stream: bool = False
    ) -> Any:
        """
        Execute API request with exponential backoff retry
        
        Args:
            request_params: Request parameters
            stream: Whether this is a streaming request
            
        Returns:
            API response or stream iterator
            
        Raises:
            APIError: If all retries fail
        """
        last_error = None
        retry_delay = self.INITIAL_RETRY_DELAY
        
        for attempt in range(self.MAX_RETRIES):
            try:
                # Make API call
                response = self.client.chat.completions.create(**request_params)
                
                logger.debug(f"API call succeeded on attempt {attempt + 1}")
                return response
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                
                # Handle specific errors
                if 'rate_limit' in str(e).lower() or '429' in str(e):
                    logger.warning(f"Rate limit error (attempt {attempt + 1}): {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                        continue
                    raise RateLimitError(f"Rate limit exceeded: {e}") from e
                
                elif 'authentication' in str(e).lower() or '401' in str(e):
                    logger.error(f"Authentication error: {e}")
                    raise AuthenticationError(f"Authentication failed: {e}") from e
                
                elif 'timeout' in str(e).lower():
                    logger.warning(f"Timeout error (attempt {attempt + 1}): {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                        continue
                    raise APITimeoutError(f"Request timed out: {e}") from e
                
                else:
                    logger.error(f"API error (attempt {attempt + 1}): {error_type}: {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                        continue
                    raise APIError(f"API call failed: {e}") from e
        
        # All retries failed
        raise APIError(f"API call failed after {self.MAX_RETRIES} attempts: {last_error}")
    
    def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = DEFAULT_EXECUTOR,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream chat completion
        
        Args:
            messages: List of message dicts
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters
            
        Yields:
            Content chunks as they arrive
            
        Raises:
            APIError: If streaming fails
        """
        try:
            stream = self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            raise APIError(f"Streaming failed: {e}") from e
    
    def check_model_availability(self, model: str) -> bool:
        """
        Check if model is available
        
        Args:
            model: Model name to check
            
        Returns:
            True if model is available
        """
        try:
            self.validate_model(model)
            
            # Try a minimal request
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            logger.info(f"Model {model} is available")
            return True
            
        except Exception as e:
            logger.warning(f"Model {model} not available: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about available models
        
        Returns:
            Dictionary with model information
        """
        return {
            'valid_models': sorted(self.VALID_MODELS),
            'default_planner': self.DEFAULT_PLANNER,
            'default_executor': self.DEFAULT_EXECUTOR,
            'recommended_planner': ['grok-beta', 'grok-4'],
            'recommended_executor': ['grok-4-fast'],
            'deprecated_models': []
        }
    
    def close(self) -> None:
        """Close HTTP client connections"""
        try:
            self.client.close()
            logger.debug("API client closed")
        except Exception as e:
            logger.error(f"Error closing client: {e}")


# Global client instance
_global_client: Optional[GrokAPIClient] = None


def get_api_client(
    api_key: Optional[str] = None,
    force_new: bool = False
) -> GrokAPIClient:
    """
    Get global API client instance
    
    Args:
        api_key: Optional API key
        force_new: Force creation of new client
        
    Returns:
        GrokAPIClient instance
    """
    global _global_client
    
    if _global_client is None or force_new:
        _global_client = GrokAPIClient(api_key=api_key)
    
    return _global_client
