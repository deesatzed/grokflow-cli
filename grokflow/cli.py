"""
GrokFlow CLI Utilities

Enhanced command-line interface utilities:
- Progress indicators
- Colored output
- Interactive prompts
- Formatted tables
- Better error messages
- Command aliases

Features:
- Rich console output
- Progress bars
- Spinners
- Confirmations
- Input validation
"""

import sys
import time
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from pathlib import Path

from grokflow.logging_config import get_logger

logger = get_logger('grokflow.cli')


class Color(Enum):
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class Icon(Enum):
    """Unicode icons"""
    SUCCESS = '✓'
    ERROR = '✗'
    WARNING = '⚠'
    INFO = 'ℹ'
    ARROW = '→'
    BULLET = '•'
    SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']


class CLI:
    """
    Enhanced CLI utilities
    
    Features:
    - Colored output
    - Progress indicators
    - Interactive prompts
    - Formatted output
    
    Example:
        >>> cli = CLI()
        >>> cli.success("Operation completed!")
        >>> cli.error("Something went wrong")
        >>> if cli.confirm("Continue?"):
        ...     cli.info("Continuing...")
    """
    
    def __init__(self, use_colors: bool = True, verbose: bool = False):
        """
        Initialize CLI
        
        Args:
            use_colors: Enable colored output
            verbose: Enable verbose output
        """
        self.use_colors = use_colors and sys.stdout.isatty()
        self.verbose = verbose
        logger.debug(f"CLI initialized: colors={use_colors}, verbose={verbose}")
    
    def _colorize(self, text: str, color: Color) -> str:
        """
        Colorize text
        
        Args:
            text: Text to colorize
            color: Color to use
            
        Returns:
            Colorized text
        """
        if not self.use_colors:
            return text
        return f"{color.value}{text}{Color.RESET.value}"
    
    def print(self, message: str, color: Optional[Color] = None) -> None:
        """
        Print message
        
        Args:
            message: Message to print
            color: Optional color
        """
        if color:
            message = self._colorize(message, color)
        print(message)
    
    def success(self, message: str) -> None:
        """Print success message"""
        icon = self._colorize(Icon.SUCCESS.value, Color.GREEN)
        msg = self._colorize(message, Color.GREEN)
        print(f"{icon} {msg}")
    
    def error(self, message: str) -> None:
        """Print error message"""
        icon = self._colorize(Icon.ERROR.value, Color.RED)
        msg = self._colorize(message, Color.RED)
        print(f"{icon} {msg}", file=sys.stderr)
    
    def warning(self, message: str) -> None:
        """Print warning message"""
        icon = self._colorize(Icon.WARNING.value, Color.YELLOW)
        msg = self._colorize(message, Color.YELLOW)
        print(f"{icon} {msg}")
    
    def info(self, message: str) -> None:
        """Print info message"""
        icon = self._colorize(Icon.INFO.value, Color.CYAN)
        msg = self._colorize(message, Color.CYAN)
        print(f"{icon} {msg}")
    
    def debug(self, message: str) -> None:
        """Print debug message (only if verbose)"""
        if self.verbose:
            msg = self._colorize(message, Color.DIM)
            print(f"  {msg}")
    
    def header(self, title: str) -> None:
        """Print header"""
        bold_title = self._colorize(title, Color.BOLD)
        print(f"\n{bold_title}")
        print("=" * len(title))
    
    def subheader(self, title: str) -> None:
        """Print subheader"""
        bold_title = self._colorize(title, Color.BOLD)
        print(f"\n{bold_title}")
        print("-" * len(title))
    
    def bullet(self, message: str, indent: int = 0) -> None:
        """Print bullet point"""
        bullet = self._colorize(Icon.BULLET.value, Color.CYAN)
        print(f"{'  ' * indent}{bullet} {message}")
    
    def arrow(self, message: str) -> None:
        """Print arrow message"""
        arrow = self._colorize(Icon.ARROW.value, Color.BLUE)
        print(f"{arrow} {message}")
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Ask for confirmation
        
        Args:
            message: Confirmation message
            default: Default value
            
        Returns:
            True if confirmed
        """
        suffix = "[Y/n]" if default else "[y/N]"
        prompt = f"{message} {suffix}: "
        
        response = input(prompt).strip().lower()
        
        if not response:
            return default
        
        return response in ('y', 'yes')
    
    def prompt(self, message: str, default: Optional[str] = None) -> str:
        """
        Prompt for input
        
        Args:
            message: Prompt message
            default: Default value
            
        Returns:
            User input
        """
        if default:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "
        
        response = input(prompt).strip()
        
        if not response and default:
            return default
        
        return response
    
    def select(self, message: str, choices: List[str], default: int = 0) -> str:
        """
        Select from choices
        
        Args:
            message: Selection message
            choices: List of choices
            default: Default choice index
            
        Returns:
            Selected choice
        """
        print(f"\n{message}")
        for i, choice in enumerate(choices, 1):
            marker = ">" if i - 1 == default else " "
            print(f"{marker} {i}. {choice}")
        
        while True:
            try:
                response = input(f"\nSelect [1-{len(choices)}]: ").strip()
                if not response:
                    return choices[default]
                
                index = int(response) - 1
                if 0 <= index < len(choices):
                    return choices[index]
                else:
                    self.error(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                self.error("Please enter a valid number")
    
    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        """
        Print formatted table
        
        Args:
            headers: Table headers
            rows: Table rows
        """
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        
        # Print header
        header_row = " | ".join(
            h.ljust(w) for h, w in zip(headers, widths)
        )
        print(self._colorize(header_row, Color.BOLD))
        print("-" * len(header_row))
        
        # Print rows
        for row in rows:
            print(" | ".join(
                str(cell).ljust(w) for cell, w in zip(row, widths)
            ))
    
    def progress_bar(
        self,
        total: int,
        prefix: str = "",
        suffix: str = "",
        length: int = 50
    ) -> Callable[[int], None]:
        """
        Create progress bar
        
        Args:
            total: Total items
            prefix: Prefix text
            suffix: Suffix text
            length: Bar length
            
        Returns:
            Update function
        """
        def update(current: int) -> None:
            percent = current / total
            filled = int(length * percent)
            bar = '█' * filled + '-' * (length - filled)
            
            status = f"{prefix} |{bar}| {current}/{total} {suffix}"
            print(f"\r{status}", end='', flush=True)
            
            if current >= total:
                print()  # New line when complete
        
        return update
    
    def spinner(self, message: str = "Processing") -> 'Spinner':
        """
        Create spinner
        
        Args:
            message: Spinner message
            
        Returns:
            Spinner context manager
        """
        return Spinner(message, self.use_colors)


class Spinner:
    """
    Spinner context manager
    
    Example:
        >>> with cli.spinner("Loading"):
        ...     time.sleep(2)
    """
    
    def __init__(self, message: str, use_colors: bool = True):
        """
        Initialize spinner
        
        Args:
            message: Spinner message
            use_colors: Use colored output
        """
        self.message = message
        self.use_colors = use_colors
        self.frames = Icon.SPINNER.value
        self.running = False
        self.frame_index = 0
    
    def __enter__(self):
        """Start spinner"""
        self.running = True
        self._spin()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner"""
        self.running = False
        print("\r" + " " * (len(self.message) + 10) + "\r", end='', flush=True)
    
    def _spin(self) -> None:
        """Spin animation"""
        if not self.running:
            return
        
        frame = self.frames[self.frame_index % len(self.frames)]
        status = f"{frame} {self.message}..."
        print(f"\r{status}", end='', flush=True)
        
        self.frame_index += 1


class ErrorFormatter:
    """
    Enhanced error message formatting
    
    Features:
    - Contextual error messages
    - Suggestions
    - Stack trace formatting
    - Error categorization
    """
    
    @staticmethod
    def format_error(
        error: Exception,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> str:
        """
        Format error message
        
        Args:
            error: Exception
            context: Error context
            suggestion: Suggested fix
            
        Returns:
            Formatted error message
        """
        lines = []
        
        # Error type and message
        lines.append(f"Error: {type(error).__name__}")
        lines.append(f"Message: {str(error)}")
        
        # Context
        if context:
            lines.append(f"Context: {context}")
        
        # Suggestion
        if suggestion:
            lines.append(f"Suggestion: {suggestion}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_validation_error(field: str, value: Any, reason: str) -> str:
        """Format validation error"""
        return f"Validation failed for '{field}': {reason}\nValue: {value}"
    
    @staticmethod
    def format_api_error(status_code: int, message: str) -> str:
        """Format API error"""
        return f"API Error ({status_code}): {message}"


# Global CLI instance
_global_cli: Optional[CLI] = None


def get_cli(use_colors: bool = True, verbose: bool = False) -> CLI:
    """
    Get global CLI instance
    
    Args:
        use_colors: Enable colored output
        verbose: Enable verbose output
        
    Returns:
        CLI instance
    """
    global _global_cli
    
    if _global_cli is None:
        _global_cli = CLI(use_colors=use_colors, verbose=verbose)
    
    return _global_cli
