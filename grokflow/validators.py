"""
GrokFlow Input Validation

Centralized input validation to prevent:
- Path traversal attacks
- Command injection
- File size violations
- Invalid formats
- Malicious input

All user inputs should pass through these validators.
"""

import re
from pathlib import Path
from typing import Optional, List
from grokflow.exceptions import (
    ValidationError,
    PathValidationError,
    ImageValidationError,
    TemplateValidationError
)
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.validators')


class InputValidator:
    """Centralized input validation for all user inputs"""
    
    # Constants
    MAX_PATH_LENGTH = 4096
    MAX_PROMPT_LENGTH = 50000  # Increased for code context
    MAX_FILENAME_LENGTH = 255
    MAX_IMAGE_SIZE_MB = 20
    MAX_TEMPLATE_VAR_LENGTH = 100
    
    # Dangerous patterns to block (always)
    DANGEROUS_PATH_PATTERNS = [
        r'\.\.',           # Path traversal
        r'[\x00-\x1f]',    # Control characters
        r'[<>:"|?*]',      # Invalid filename chars (Windows)
    ]

    # Patterns to block only when NOT allowing outside workspace
    RESTRICTED_PATH_PATTERNS = [
        r'^/',             # Absolute paths (Unix)
        r'^[A-Z]:',        # Absolute paths (Windows)
        r'^~',             # Home directory expansion
    ]
    
    # Allowed file extensions for context
    ALLOWED_CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h',
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh',
        '.bash', '.zsh', '.fish', '.ps1', '.yaml', '.yml', '.json', '.xml',
        '.html', '.css', '.scss', '.sass', '.less', '.sql', '.md', '.txt',
        '.toml', '.ini', '.cfg', '.conf', '.env', '.gitignore', '.dockerignore'
    }
    
    # Image extensions
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    
    @staticmethod
    def validate_file_path(
        path_str: str,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        allow_outside_workspace: bool = False
    ) -> Path:
        """
        Validate file path for safety
        
        Args:
            path_str: Path string to validate
            must_exist: If True, path must exist
            must_be_file: If True, path must be a file
            must_be_dir: If True, path must be a directory
            allow_outside_workspace: If True, allow paths outside workspace
            
        Returns:
            Validated Path object
            
        Raises:
            PathValidationError: If path is invalid or unsafe
        """
        if not path_str or not path_str.strip():
            raise PathValidationError("Path cannot be empty")
        
        path_str = path_str.strip()
        
        # Check length
        if len(path_str) > InputValidator.MAX_PATH_LENGTH:
            raise PathValidationError(
                f"Path too long (max {InputValidator.MAX_PATH_LENGTH} characters)"
            )
        
        # Check for dangerous patterns (always blocked)
        for pattern in InputValidator.DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, path_str):
                logger.warning(f"Blocked dangerous path pattern: {path_str}")
                raise PathValidationError(
                    f"Invalid path: contains dangerous pattern '{pattern}'"
                )

        # Check for restricted patterns (blocked unless allow_outside_workspace)
        if not allow_outside_workspace:
            for pattern in InputValidator.RESTRICTED_PATH_PATTERNS:
                if re.search(pattern, path_str):
                    logger.warning(f"Blocked restricted path pattern: {path_str}")
                    raise PathValidationError(
                        f"Invalid path: contains restricted pattern '{pattern}'"
                    )
        
        # Convert to Path and resolve
        try:
            path = Path(path_str).resolve()
        except (ValueError, OSError) as e:
            raise PathValidationError(f"Invalid path: {e}")
        
        # Check if within workspace (unless explicitly allowed)
        if not allow_outside_workspace:
            workspace = Path.cwd().resolve()
            try:
                path.relative_to(workspace)
            except ValueError:
                logger.warning(f"Blocked path outside workspace: {path}")
                raise PathValidationError(
                    f"Path must be within workspace: {workspace}"
                )
        
        # Check existence
        if must_exist and not path.exists():
            raise PathValidationError(f"Path does not exist: {path}")
        
        # Check file type
        if must_be_file and path.exists() and not path.is_file():
            raise PathValidationError(f"Not a file: {path}")
        
        if must_be_dir and path.exists() and not path.is_dir():
            raise PathValidationError(f"Not a directory: {path}")
        
        logger.debug(f"Validated path: {path}")
        return path
    
    @staticmethod
    def validate_directory_path(
        path_str: str,
        must_exist: bool = True,
        allow_outside_workspace: bool = False
    ) -> Path:
        """
        Validate directory path
        
        Args:
            path_str: Directory path string
            must_exist: If True, directory must exist
            allow_outside_workspace: If True, allow outside workspace
            
        Returns:
            Validated Path object
            
        Raises:
            PathValidationError: If path is invalid
        """
        return InputValidator.validate_file_path(
            path_str,
            must_exist=must_exist,
            must_be_dir=True,
            allow_outside_workspace=allow_outside_workspace
        )
    
    @staticmethod
    def validate_code_file_path(path_str: str) -> Path:
        """
        Validate code file path
        
        Args:
            path_str: Code file path string
            
        Returns:
            Validated Path object
            
        Raises:
            PathValidationError: If path is invalid or not a code file
        """
        path = InputValidator.validate_file_path(
            path_str,
            must_exist=True,
            must_be_file=True
        )
        
        # Check extension
        if path.suffix.lower() not in InputValidator.ALLOWED_CODE_EXTENSIONS:
            logger.warning(f"Unsupported file extension: {path.suffix}")
            # Don't block, just warn - user might have custom extensions
            logger.info(f"Proceeding with non-standard extension: {path}")
        
        return path
    
    @staticmethod
    def validate_image_path(path_str: str, allow_outside_workspace: bool = False) -> Path:
        """
        Validate image file path

        Args:
            path_str: Image file path string
            allow_outside_workspace: If True, allow paths outside workspace

        Returns:
            Validated Path object

        Raises:
            ImageValidationError: If path is invalid or not a valid image
        """
        try:
            path = InputValidator.validate_file_path(
                path_str,
                must_exist=True,
                must_be_file=True,
                allow_outside_workspace=allow_outside_workspace
            )
        except PathValidationError as e:
            raise ImageValidationError(str(e))
        
        # Check extension
        if path.suffix.lower() not in InputValidator.ALLOWED_IMAGE_EXTENSIONS:
            raise ImageValidationError(
                f"Invalid image format: {path.suffix}. "
                f"Supported: {', '.join(InputValidator.ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Check size
        file_size = path.stat().st_size
        max_size = InputValidator.MAX_IMAGE_SIZE_MB * 1024 * 1024
        
        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            raise ImageValidationError(
                f"Image too large: {size_mb:.1f}MB "
                f"(max {InputValidator.MAX_IMAGE_SIZE_MB}MB)"
            )
        
        # Check if file is actually an image (basic check)
        try:
            with open(path, 'rb') as f:
                header = f.read(12)
                
                # Check magic numbers
                if path.suffix.lower() in ['.jpg', '.jpeg']:
                    if not header.startswith(b'\xff\xd8\xff'):
                        raise ImageValidationError("File is not a valid JPEG")
                elif path.suffix.lower() == '.png':
                    if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ImageValidationError("File is not a valid PNG")
        except OSError as e:
            raise ImageValidationError(f"Cannot read image file: {e}")
        
        logger.debug(f"Validated image: {path} ({file_size / 1024:.1f}KB)")
        return path
    
    @staticmethod
    def sanitize_prompt(prompt: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize user prompt
        
        Args:
            prompt: User prompt string
            max_length: Maximum length (default: MAX_PROMPT_LENGTH)
            
        Returns:
            Sanitized prompt string
        """
        if not prompt:
            return ""
        
        if max_length is None:
            max_length = InputValidator.MAX_PROMPT_LENGTH
        
        # Remove control characters (except newlines and tabs)
        prompt = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', prompt)
        
        # Limit length
        if len(prompt) > max_length:
            logger.warning(
                f"Prompt truncated from {len(prompt)} to {max_length} characters"
            )
            prompt = prompt[:max_length]
        
        return prompt.strip()
    
    @staticmethod
    def validate_template_name(name: str) -> str:
        """
        Validate template name
        
        Args:
            name: Template name string
            
        Returns:
            Validated template name
            
        Raises:
            TemplateValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise TemplateValidationError("Template name cannot be empty")
        
        name = name.strip()
        
        # Only alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-z0-9_-]+$', name):
            raise TemplateValidationError(
                "Template name must contain only lowercase letters, "
                "numbers, hyphens, and underscores"
            )
        
        if len(name) > 50:
            raise TemplateValidationError("Template name too long (max 50 characters)")
        
        return name
    
    @staticmethod
    def validate_template_variable(name: str, value: str) -> str:
        """
        Validate template variable
        
        Args:
            name: Variable name
            value: Variable value
            
        Returns:
            Validated value
            
        Raises:
            TemplateValidationError: If value is invalid
        """
        if not value or not value.strip():
            raise TemplateValidationError(f"Template variable '{name}' cannot be empty")
        
        value = value.strip()
        
        # Check length
        if len(value) > InputValidator.MAX_TEMPLATE_VAR_LENGTH:
            raise TemplateValidationError(
                f"Template variable '{name}' too long "
                f"(max {InputValidator.MAX_TEMPLATE_VAR_LENGTH} characters)"
            )
        
        # Remove control characters
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # Check for code injection attempts
        dangerous_patterns = [
            r'\$\{',           # Template injection
            r'\{\{',           # Template injection
            r'__import__',     # Python import
            r'eval\(',         # Eval
            r'exec\(',         # Exec
            r'subprocess',     # Subprocess
            r'os\.',           # OS module
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Blocked dangerous template variable: {value}")
                raise TemplateValidationError(
                    f"Template variable '{name}' contains dangerous pattern"
                )
        
        return value
    
    @staticmethod
    def validate_commit_message(message: str) -> str:
        """
        Validate git commit message
        
        Args:
            message: Commit message string
            
        Returns:
            Validated commit message
            
        Raises:
            ValidationError: If message is invalid
        """
        if not message or not message.strip():
            raise ValidationError("Commit message cannot be empty")
        
        message = message.strip()
        
        # Remove control characters
        message = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', message)
        
        # Check length (conventional: 50 char subject, 72 char body lines)
        if len(message) > 1000:
            raise ValidationError("Commit message too long (max 1000 characters)")
        
        return message
    
    @staticmethod
    def validate_file_pattern(pattern: str) -> str:
        """
        Validate file glob pattern
        
        Args:
            pattern: Glob pattern string
            
        Returns:
            Validated pattern
            
        Raises:
            ValidationError: If pattern is invalid
        """
        if not pattern or not pattern.strip():
            raise ValidationError("File pattern cannot be empty")
        
        pattern = pattern.strip()
        
        # Check for dangerous patterns
        if '..' in pattern:
            raise ValidationError("File pattern cannot contain '..'")
        
        if pattern.startswith('/'):
            raise ValidationError("File pattern cannot be absolute")
        
        # Basic validation - must be reasonable
        if len(pattern) > 200:
            raise ValidationError("File pattern too long (max 200 characters)")
        
        return pattern
    
    @staticmethod
    def validate_model_name(model: str) -> str:
        """
        Validate AI model name
        
        Args:
            model: Model name string
            
        Returns:
            Validated model name
            
        Raises:
            ValidationError: If model name is invalid
        """
        if not model or not model.strip():
            raise ValidationError("Model name cannot be empty")
        
        model = model.strip()
        
        # Valid model names (from grok_models.md)
        valid_models = {
            'grok-4-fast',
            'grok-4',
            'grok-beta',
            'grok-3',
            'grok-3-mini'
        }
        
        if model not in valid_models:
            logger.warning(f"Unknown model name: {model}")
            # Don't block - API will reject if invalid
            # Just log for monitoring
        
        return model


class PathSanitizer:
    """Helper class for path sanitization"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to be safe for filesystem
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
        
        # Limit length
        if len(filename) > InputValidator.MAX_FILENAME_LENGTH:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_len = InputValidator.MAX_FILENAME_LENGTH - len(ext) - 1
            filename = name[:max_name_len] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def get_safe_path(base_dir: Path, user_path: str) -> Path:
        """
        Get safe path within base directory
        
        Args:
            base_dir: Base directory
            user_path: User-provided path
            
        Returns:
            Safe path within base_dir
            
        Raises:
            PathValidationError: If path escapes base_dir
        """
        # Resolve both paths
        base = base_dir.resolve()
        target = (base / user_path).resolve()
        
        # Ensure target is within base
        try:
            target.relative_to(base)
        except ValueError:
            raise PathValidationError(
                f"Path escapes base directory: {user_path}"
            )
        
        return target
