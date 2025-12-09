"""
GrokFlow Dual-Model System

Orchestrates the dual-model architecture:
- Planner: grok-beta/grok-4 for reasoning and planning
- Executor: grok-4-fast for fast code generation

Features:
- Automatic model selection
- Conversation flow management
- Context optimization
- Fallback handling
- Performance tracking
"""

from typing import List, Dict, Optional, Any, Iterator
from dataclasses import dataclass
from enum import Enum

from grokflow.api_client import GrokAPIClient, get_api_client
from grokflow.exceptions import APIError, ModelNotAvailableError
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.dual_model')


class ModelRole(Enum):
    """Model role in dual-model architecture"""
    PLANNER = "planner"
    EXECUTOR = "executor"


@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    role: ModelRole
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    def __str__(self):
        return f"{self.name} ({self.role.value})"


class DualModelOrchestrator:
    """
    Orchestrates dual-model architecture
    
    Architecture:
    - Planner (grok-beta/grok-4): Analyzes problem, creates plan
    - Executor (grok-4-fast): Implements plan, generates code
    
    Flow:
    1. User provides prompt + context
    2. Planner analyzes and creates execution plan
    3. Executor implements plan with fast generation
    4. Results returned to user
    
    Example:
        >>> orchestrator = DualModelOrchestrator()
        >>> result = orchestrator.process_request(
        ...     user_prompt="Fix the bug in main.py",
        ...     context="<file contents>"
        ... )
    """
    
    # Default model configurations
    DEFAULT_PLANNER_CONFIG = ModelConfig(
        name='grok-beta',
        role=ModelRole.PLANNER,
        temperature=0.7,
        max_tokens=4000
    )
    
    DEFAULT_EXECUTOR_CONFIG = ModelConfig(
        name='grok-4-fast',
        role=ModelRole.EXECUTOR,
        temperature=0.5,
        max_tokens=8000
    )
    
    # Fallback models
    PLANNER_FALLBACKS = ['grok-beta', 'grok-4']
    EXECUTOR_FALLBACKS = ['grok-4-fast', 'grok-4']
    
    def __init__(
        self,
        api_client: Optional[GrokAPIClient] = None,
        planner_config: Optional[ModelConfig] = None,
        executor_config: Optional[ModelConfig] = None,
        enable_planner: bool = True
    ):
        """
        Initialize dual-model orchestrator
        
        Args:
            api_client: API client instance
            planner_config: Planner model configuration
            executor_config: Executor model configuration
            enable_planner: Enable planner model (if False, executor only)
        """
        self.client = api_client or get_api_client()
        self.planner_config = planner_config or self.DEFAULT_PLANNER_CONFIG
        self.executor_config = executor_config or self.DEFAULT_EXECUTOR_CONFIG
        self.enable_planner = enable_planner
        
        # Verify models are available
        self._verify_models()
        
        logger.info(
            f"DualModelOrchestrator initialized: "
            f"planner={self.planner_config.name}, "
            f"executor={self.executor_config.name}, "
            f"planner_enabled={enable_planner}"
        )
    
    def _verify_models(self) -> None:
        """Verify configured models are available"""
        try:
            if self.enable_planner:
                self.client.validate_model(self.planner_config.name)
            self.client.validate_model(self.executor_config.name)
        except ModelNotAvailableError as e:
            logger.error(f"Model validation failed: {e}")
            raise
    
    def process_request(
        self,
        user_prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False
    ) -> Any:
        """
        Process user request through dual-model architecture
        
        Args:
            user_prompt: User's request/prompt
            context: Optional context (code, files, etc.)
            conversation_history: Previous conversation messages
            stream: Enable streaming response
            
        Returns:
            Response from executor model
        """
        logger.info(f"Processing request: {user_prompt[:100]}...")
        
        # Build messages
        messages = self._build_messages(
            user_prompt=user_prompt,
            context=context,
            conversation_history=conversation_history
        )
        
        # If planner disabled, go straight to executor
        if not self.enable_planner:
            logger.debug("Planner disabled, using executor only")
            return self._execute_with_model(
                messages=messages,
                config=self.executor_config,
                stream=stream
            )
        
        # Step 1: Planner analyzes and creates plan
        try:
            plan = self._create_plan(messages)
            logger.debug(f"Plan created: {plan[:200]}...")
        except Exception as e:
            logger.warning(f"Planner failed, falling back to executor: {e}")
            # Fallback to executor only
            return self._execute_with_model(
                messages=messages,
                config=self.executor_config,
                stream=stream
            )
        
        # Step 2: Executor implements plan
        executor_messages = self._build_executor_messages(
            original_messages=messages,
            plan=plan
        )
        
        return self._execute_with_model(
            messages=executor_messages,
            config=self.executor_config,
            stream=stream
        )
    
    def _build_messages(
        self,
        user_prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Build message list for API
        
        Args:
            user_prompt: User's prompt
            context: Optional context
            conversation_history: Previous messages
            
        Returns:
            List of message dicts
        """
        messages = []
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Build user message with context
        user_message = user_prompt
        if context:
            user_message = f"Context:\n{context}\n\nRequest:\n{user_prompt}"
        
        messages.append({
            'role': 'user',
            'content': user_message
        })
        
        return messages
    
    def _create_plan(self, messages: List[Dict[str, str]]) -> str:
        """
        Use planner model to create execution plan
        
        Args:
            messages: Message list
            
        Returns:
            Plan as string
        """
        # Add planning instruction
        planning_messages = messages.copy()
        planning_messages[-1]['content'] = (
            f"{planning_messages[-1]['content']}\n\n"
            "Analyze this request and create a detailed execution plan. "
            "Break down the task into clear steps."
        )
        
        logger.debug(f"Calling planner: {self.planner_config.name}")
        
        response = self.client.chat_completion(
            messages=planning_messages,
            model=self.planner_config.name,
            temperature=self.planner_config.temperature,
            max_tokens=self.planner_config.max_tokens
        )
        
        plan = response.choices[0].message.content
        logger.info(f"Plan created by {self.planner_config.name}")
        
        return plan
    
    def _build_executor_messages(
        self,
        original_messages: List[Dict[str, str]],
        plan: str
    ) -> List[Dict[str, str]]:
        """
        Build messages for executor with plan
        
        Args:
            original_messages: Original user messages
            plan: Plan from planner
            
        Returns:
            Messages for executor
        """
        executor_messages = original_messages.copy()
        
        # Add plan as assistant message
        executor_messages.append({
            'role': 'assistant',
            'content': f"Plan:\n{plan}"
        })
        
        # Add execution instruction
        executor_messages.append({
            'role': 'user',
            'content': "Now implement this plan. Provide the complete solution."
        })
        
        return executor_messages
    
    def _execute_with_model(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        stream: bool = False
    ) -> Any:
        """
        Execute with specified model
        
        Args:
            messages: Message list
            config: Model configuration
            stream: Enable streaming
            
        Returns:
            API response or stream iterator
        """
        logger.debug(f"Executing with {config}")
        
        if stream:
            return self.client.stream_completion(
                messages=messages,
                model=config.name,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        else:
            response = self.client.chat_completion(
                messages=messages,
                model=config.name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=False
            )
            return response.choices[0].message.content
    
    def stream_request(
        self,
        user_prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Iterator[str]:
        """
        Stream response for user request
        
        Args:
            user_prompt: User's request
            context: Optional context
            conversation_history: Previous messages
            
        Yields:
            Response chunks
        """
        result = self.process_request(
            user_prompt=user_prompt,
            context=context,
            conversation_history=conversation_history,
            stream=True
        )
        
        # Result is already an iterator from stream_completion
        yield from result
    
    def switch_planner(self, model_name: str) -> None:
        """
        Switch planner model
        
        Args:
            model_name: New planner model name
        """
        self.client.validate_model(model_name)
        self.planner_config.name = model_name
        logger.info(f"Switched planner to: {model_name}")
    
    def switch_executor(self, model_name: str) -> None:
        """
        Switch executor model
        
        Args:
            model_name: New executor model name
        """
        self.client.validate_model(model_name)
        self.executor_config.name = model_name
        logger.info(f"Switched executor to: {model_name}")
    
    def disable_planner(self) -> None:
        """Disable planner (executor only mode)"""
        self.enable_planner = False
        logger.info("Planner disabled, using executor only")
    
    def enable_planner_mode(self) -> None:
        """Enable planner mode"""
        self.enable_planner = True
        logger.info("Planner enabled")
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        Get current configuration
        
        Returns:
            Configuration dictionary
        """
        return {
            'planner': {
                'model': self.planner_config.name,
                'enabled': self.enable_planner,
                'temperature': self.planner_config.temperature,
                'max_tokens': self.planner_config.max_tokens
            },
            'executor': {
                'model': self.executor_config.name,
                'temperature': self.executor_config.temperature,
                'max_tokens': self.executor_config.max_tokens
            }
        }


class SimpleExecutor:
    """
    Simple single-model executor (no planner)
    
    For simple requests that don't need planning.
    """
    
    def __init__(
        self,
        api_client: Optional[GrokAPIClient] = None,
        model: str = 'grok-4-fast',
        temperature: float = 0.7
    ):
        """
        Initialize simple executor
        
        Args:
            api_client: API client
            model: Model to use
            temperature: Sampling temperature
        """
        self.client = api_client or get_api_client()
        self.model = model
        self.temperature = temperature
        
        self.client.validate_model(model)
        logger.info(f"SimpleExecutor initialized: model={model}")
    
    def execute(
        self,
        prompt: str,
        context: Optional[str] = None,
        stream: bool = False
    ) -> Any:
        """
        Execute simple request
        
        Args:
            prompt: User prompt
            context: Optional context
            stream: Enable streaming
            
        Returns:
            Response or stream iterator
        """
        messages = [{'role': 'user', 'content': prompt}]
        
        if context:
            messages[0]['content'] = f"Context:\n{context}\n\nRequest:\n{prompt}"
        
        if stream:
            return self.client.stream_completion(
                messages=messages,
                model=self.model,
                temperature=self.temperature
            )
        else:
            response = self.client.chat_completion(
                messages=messages,
                model=self.model,
                temperature=self.temperature
            )
            return response.choices[0].message.content


# Global orchestrator instance
_global_orchestrator: Optional[DualModelOrchestrator] = None


def get_orchestrator(
    planner_model: Optional[str] = None,
    executor_model: Optional[str] = None,
    enable_planner: bool = True,
    force_new: bool = False
) -> DualModelOrchestrator:
    """
    Get global orchestrator instance
    
    Args:
        planner_model: Optional planner model name
        executor_model: Optional executor model name
        enable_planner: Enable planner
        force_new: Force new instance
        
    Returns:
        DualModelOrchestrator instance
    """
    global _global_orchestrator
    
    if _global_orchestrator is None or force_new:
        planner_config = None
        if planner_model:
            planner_config = ModelConfig(
                name=planner_model,
                role=ModelRole.PLANNER
            )
        
        executor_config = None
        if executor_model:
            executor_config = ModelConfig(
                name=executor_model,
                role=ModelRole.EXECUTOR
            )
        
        _global_orchestrator = DualModelOrchestrator(
            planner_config=planner_config,
            executor_config=executor_config,
            enable_planner=enable_planner
        )
    
    return _global_orchestrator
