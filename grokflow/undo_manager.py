"""
GrokFlow Undo/Redo System

Command pattern-based undo/redo system for:
- File operations
- Context changes
- Session modifications
- Atomic operations
- State snapshots

Features:
- Command pattern
- Undo/redo stacks
- State snapshots
- Atomic operations
- History management
- Persistence
"""

import json
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum

from grokflow.exceptions import UndoError
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.undo_manager')


class CommandType(Enum):
    """Type of command"""
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    FILE_RENAME = "file_rename"
    CONTEXT_ADD = "context_add"
    CONTEXT_REMOVE = "context_remove"
    SESSION_UPDATE = "session_update"
    BATCH = "batch"
    CUSTOM = "custom"


@dataclass
class CommandMetadata:
    """Metadata for a command"""
    command_type: CommandType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    user_initiated: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['command_type'] = self.command_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandMetadata':
        """Create from dictionary"""
        data = data.copy()
        data['command_type'] = CommandType(data['command_type'])
        return cls(**data)


class Command(ABC):
    """
    Abstract base class for commands
    
    Implements the Command pattern for undo/redo functionality.
    """
    
    def __init__(self, metadata: Optional[CommandMetadata] = None):
        """
        Initialize command
        
        Args:
            metadata: Command metadata
        """
        self.metadata = metadata or CommandMetadata(
            command_type=CommandType.CUSTOM,
            description="Custom command"
        )
        self.executed = False
    
    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the command
        
        Returns:
            Result of execution
        """
        pass
    
    @abstractmethod
    def undo(self) -> None:
        """Undo the command"""
        pass
    
    def can_undo(self) -> bool:
        """Check if command can be undone"""
        return self.executed
    
    def get_description(self) -> str:
        """Get command description"""
        return self.metadata.description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            'metadata': self.metadata.to_dict(),
            'executed': self.executed
        }


class FileWriteCommand(Command):
    """Command for writing to a file"""
    
    def __init__(
        self,
        file_path: Path,
        content: str,
        backup_content: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Initialize file write command
        
        Args:
            file_path: Path to file
            content: Content to write
            backup_content: Previous content (for undo)
            description: Command description
        """
        super().__init__(CommandMetadata(
            command_type=CommandType.FILE_WRITE,
            description=description or f"Write to {file_path.name}"
        ))
        self.file_path = file_path
        self.content = content
        self.backup_content = backup_content
        
        # Save current content if file exists
        if self.backup_content is None and file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    self.backup_content = f.read()
            except Exception as e:
                logger.warning(f"Could not backup file content: {e}")
    
    def execute(self) -> None:
        """Write content to file"""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w') as f:
                f.write(self.content)
            self.executed = True
            logger.info(f"Wrote to file: {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to write file: {e}", exc_info=True)
            raise UndoError(f"Failed to write file: {e}") from e
    
    def undo(self) -> None:
        """Restore previous content"""
        if not self.can_undo():
            raise UndoError("Command not executed, cannot undo")
        
        try:
            if self.backup_content is not None:
                with open(self.file_path, 'w') as f:
                    f.write(self.backup_content)
                logger.info(f"Restored file: {self.file_path}")
            else:
                # No backup, delete file
                if self.file_path.exists():
                    self.file_path.unlink()
                logger.info(f"Deleted file (no backup): {self.file_path}")
            
            self.executed = False
        except Exception as e:
            logger.error(f"Failed to undo file write: {e}", exc_info=True)
            raise UndoError(f"Failed to undo file write: {e}") from e


class FileDeleteCommand(Command):
    """Command for deleting a file"""
    
    def __init__(
        self,
        file_path: Path,
        description: Optional[str] = None
    ):
        """
        Initialize file delete command
        
        Args:
            file_path: Path to file
            description: Command description
        """
        super().__init__(CommandMetadata(
            command_type=CommandType.FILE_DELETE,
            description=description or f"Delete {file_path.name}"
        ))
        self.file_path = file_path
        self.backup_content: Optional[str] = None
        
        # Backup content before deletion
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    self.backup_content = f.read()
            except Exception as e:
                logger.warning(f"Could not backup file for deletion: {e}")
    
    def execute(self) -> None:
        """Delete the file"""
        try:
            if self.file_path.exists():
                self.file_path.unlink()
                self.executed = True
                logger.info(f"Deleted file: {self.file_path}")
            else:
                logger.warning(f"File not found for deletion: {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file: {e}", exc_info=True)
            raise UndoError(f"Failed to delete file: {e}") from e
    
    def undo(self) -> None:
        """Restore deleted file"""
        if not self.can_undo():
            raise UndoError("Command not executed, cannot undo")
        
        try:
            if self.backup_content is not None:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.file_path, 'w') as f:
                    f.write(self.backup_content)
                logger.info(f"Restored deleted file: {self.file_path}")
            else:
                logger.warning(f"No backup content to restore: {self.file_path}")
            
            self.executed = False
        except Exception as e:
            logger.error(f"Failed to undo file deletion: {e}", exc_info=True)
            raise UndoError(f"Failed to undo file deletion: {e}") from e


class FileRenameCommand(Command):
    """Command for renaming a file"""
    
    def __init__(
        self,
        old_path: Path,
        new_path: Path,
        description: Optional[str] = None
    ):
        """
        Initialize file rename command
        
        Args:
            old_path: Original file path
            new_path: New file path
            description: Command description
        """
        super().__init__(CommandMetadata(
            command_type=CommandType.FILE_RENAME,
            description=description or f"Rename {old_path.name} to {new_path.name}"
        ))
        self.old_path = old_path
        self.new_path = new_path
    
    def execute(self) -> None:
        """Rename the file"""
        try:
            if self.old_path.exists():
                self.new_path.parent.mkdir(parents=True, exist_ok=True)
                self.old_path.rename(self.new_path)
                self.executed = True
                logger.info(f"Renamed file: {self.old_path} → {self.new_path}")
            else:
                raise UndoError(f"File not found: {self.old_path}")
        except Exception as e:
            logger.error(f"Failed to rename file: {e}", exc_info=True)
            raise UndoError(f"Failed to rename file: {e}") from e
    
    def undo(self) -> None:
        """Restore original file name"""
        if not self.can_undo():
            raise UndoError("Command not executed, cannot undo")
        
        try:
            if self.new_path.exists():
                self.new_path.rename(self.old_path)
                logger.info(f"Restored file name: {self.new_path} → {self.old_path}")
            else:
                logger.warning(f"File not found for undo: {self.new_path}")
            
            self.executed = False
        except Exception as e:
            logger.error(f"Failed to undo file rename: {e}", exc_info=True)
            raise UndoError(f"Failed to undo file rename: {e}") from e


class CustomCommand(Command):
    """Custom command with user-defined execute and undo functions"""

    def __init__(
        self,
        execute_fn: Callable[[], Any],
        undo_fn: Callable[[], None],
        description: str = "Custom command"
    ):
        """
        Initialize custom command

        Args:
            execute_fn: Function to execute
            undo_fn: Function to undo
            description: Command description
        """
        super().__init__(CommandMetadata(
            command_type=CommandType.CUSTOM,
            description=description
        ))
        self.execute_fn = execute_fn
        self.undo_fn = undo_fn
        self.result: Any = None

    def execute(self) -> Any:
        """Execute custom function"""
        try:
            self.result = self.execute_fn()
            self.executed = True
            logger.info(f"Executed custom command: {self.metadata.description}")
            return self.result
        except Exception as e:
            logger.error(f"Failed to execute custom command: {e}", exc_info=True)
            raise UndoError(f"Failed to execute custom command: {e}") from e

    def undo(self) -> None:
        """Undo custom function"""
        if not self.can_undo():
            raise UndoError("Command not executed, cannot undo")

        try:
            self.undo_fn()
            self.executed = False
            logger.info(f"Undid custom command: {self.metadata.description}")
        except Exception as e:
            logger.error(f"Failed to undo custom command: {e}", exc_info=True)
            raise UndoError(f"Failed to undo custom command: {e}") from e


class BatchCommand(Command):
    """
    Command that groups multiple commands into a single atomic operation.

    All commands in the batch are executed together, and undo/redo
    operations affect all commands as a single unit.

    Example:
        >>> batch = BatchCommand([
        ...     FileWriteCommand(path1, content1),
        ...     FileWriteCommand(path2, content2),
        ... ], description="Update config files")
        >>> manager.execute(batch)  # Executes both writes
        >>> manager.undo()  # Undoes both writes atomically
    """

    def __init__(
        self,
        commands: List[Command],
        description: Optional[str] = None
    ):
        """
        Initialize batch command

        Args:
            commands: List of commands to execute as a batch
            description: Optional description for the batch
        """
        super().__init__(CommandMetadata(
            command_type=CommandType.BATCH,
            description=description or f"Batch of {len(commands)} commands"
        ))
        self.commands = commands
        self.executed_commands: List[Command] = []

    def execute(self) -> List[Any]:
        """
        Execute all commands in the batch

        Returns:
            List of results from each command

        Raises:
            UndoError: If any command fails (rolls back executed commands)
        """
        results = []
        self.executed_commands = []

        try:
            for cmd in self.commands:
                result = cmd.execute()
                results.append(result)
                self.executed_commands.append(cmd)

            self.executed = True
            logger.info(f"Executed batch: {self.metadata.description} ({len(self.commands)} commands)")
            return results

        except Exception as e:
            # Rollback executed commands in reverse order
            logger.warning(f"Batch failed, rolling back {len(self.executed_commands)} commands")
            for cmd in reversed(self.executed_commands):
                try:
                    cmd.undo()
                except Exception as rollback_error:
                    logger.error(f"Rollback failed for {cmd.get_description()}: {rollback_error}")

            self.executed_commands = []
            raise UndoError(f"Batch execution failed: {e}") from e

    def undo(self) -> None:
        """
        Undo all commands in the batch (in reverse order)

        Raises:
            UndoError: If command not executed or undo fails
        """
        if not self.can_undo():
            raise UndoError("Batch not executed, cannot undo")

        errors = []
        for cmd in reversed(self.executed_commands):
            try:
                cmd.undo()
            except Exception as e:
                errors.append(f"{cmd.get_description()}: {e}")
                logger.error(f"Failed to undo command in batch: {e}")

        if errors:
            raise UndoError(f"Batch undo partially failed: {'; '.join(errors)}")

        self.executed = False
        logger.info(f"Undid batch: {self.metadata.description}")

    def get_commands(self) -> List[Command]:
        """Get list of commands in the batch"""
        return self.commands.copy()

    def get_command_count(self) -> int:
        """Get number of commands in the batch"""
        return len(self.commands)


class UndoManager:
    """
    Manages undo/redo operations
    
    Features:
    - Command execution with undo support
    - Undo/redo stacks
    - History management
    - Persistence
    - Atomic operations
    
    Example:
        >>> manager = UndoManager()
        >>> cmd = FileWriteCommand(Path('test.txt'), 'content')
        >>> manager.execute(cmd)
        >>> manager.undo()
        >>> manager.redo()
    """
    
    def __init__(
        self,
        max_history: int = 100,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize undo manager
        
        Args:
            max_history: Maximum history size
            storage_path: Path for persistence
        """
        self.max_history = max_history
        self.storage_path = storage_path or Path.home() / '.grokflow' / 'undo_history.json'
        
        # Undo/redo stacks
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        
        logger.info(f"UndoManager initialized: max_history={max_history}")
    
    def execute(self, command: Command) -> Any:
        """
        Execute command and add to undo stack
        
        Args:
            command: Command to execute
            
        Returns:
            Result of command execution
        """
        result = command.execute()
        
        # Add to undo stack
        self.undo_stack.append(command)
        
        # Clear redo stack (new action invalidates redo)
        self.redo_stack.clear()
        
        # Limit history size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        logger.debug(f"Executed command: {command.get_description()}")
        return result
    
    def undo(self) -> bool:
        """
        Undo last command
        
        Returns:
            True if undo successful, False if nothing to undo
        """
        if not self.can_undo():
            logger.warning("Nothing to undo")
            return False
        
        command = self.undo_stack.pop()
        
        try:
            command.undo()
            self.redo_stack.append(command)
            logger.info(f"Undid command: {command.get_description()}")
            return True
        except Exception as e:
            # Put command back on undo stack if undo fails
            self.undo_stack.append(command)
            logger.error(f"Undo failed: {e}", exc_info=True)
            raise
    
    def redo(self) -> bool:
        """
        Redo last undone command
        
        Returns:
            True if redo successful, False if nothing to redo
        """
        if not self.can_redo():
            logger.warning("Nothing to redo")
            return False
        
        command = self.redo_stack.pop()
        
        try:
            command.execute()
            self.undo_stack.append(command)
            logger.info(f"Redid command: {command.get_description()}")
            return True
        except Exception as e:
            # Put command back on redo stack if redo fails
            self.redo_stack.append(command)
            logger.error(f"Redo failed: {e}", exc_info=True)
            raise
    
    def undo_batch(self, count: int = 1) -> int:
        """
        Undo multiple commands at once

        Args:
            count: Number of commands to undo (default 1)

        Returns:
            Number of commands actually undone

        Example:
            >>> manager.undo_batch(3)  # Undo last 3 commands
            3
        """
        if count < 1:
            logger.warning("undo_batch called with count < 1")
            return 0

        undone = 0
        errors = []

        for _ in range(count):
            if not self.can_undo():
                break
            try:
                self.undo()
                undone += 1
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Batch undo stopped at command {undone + 1}: {e}")
                break

        if errors:
            logger.warning(f"Batch undo completed with errors: {errors}")

        logger.info(f"Batch undo completed: {undone}/{count} commands undone")
        return undone

    def redo_batch(self, count: int = 1) -> int:
        """
        Redo multiple commands at once

        Args:
            count: Number of commands to redo (default 1)

        Returns:
            Number of commands actually redone

        Example:
            >>> manager.redo_batch(3)  # Redo last 3 undone commands
            3
        """
        if count < 1:
            logger.warning("redo_batch called with count < 1")
            return 0

        redone = 0
        errors = []

        for _ in range(count):
            if not self.can_redo():
                break
            try:
                self.redo()
                redone += 1
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Batch redo stopped at command {redone + 1}: {e}")
                break

        if errors:
            logger.warning(f"Batch redo completed with errors: {errors}")

        logger.info(f"Batch redo completed: {redone}/{count} commands redone")
        return redone

    def undo_all(self) -> int:
        """
        Undo all commands in the undo stack

        Returns:
            Number of commands undone
        """
        return self.undo_batch(len(self.undo_stack))

    def redo_all(self) -> int:
        """
        Redo all commands in the redo stack

        Returns:
            Number of commands redone
        """
        return self.redo_batch(len(self.redo_stack))

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self.redo_stack) > 0

    def get_undo_history(self) -> List[str]:
        """
        Get undo history descriptions
        
        Returns:
            List of command descriptions
        """
        return [cmd.get_description() for cmd in self.undo_stack]
    
    def get_redo_history(self) -> List[str]:
        """
        Get redo history descriptions
        
        Returns:
            List of command descriptions
        """
        return [cmd.get_description() for cmd in self.redo_stack]
    
    def clear_history(self) -> None:
        """Clear all history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        logger.info("Cleared undo/redo history")
    
    def get_history_size(self) -> Dict[str, int]:
        """
        Get history sizes
        
        Returns:
            Dictionary with undo and redo stack sizes
        """
        return {
            'undo_stack': len(self.undo_stack),
            'redo_stack': len(self.redo_stack)
        }


# Global undo manager instance
_global_undo_manager: Optional[UndoManager] = None


def get_undo_manager(
    max_history: Optional[int] = None,
    force_new: bool = False
) -> UndoManager:
    """
    Get global undo manager instance
    
    Args:
        max_history: Maximum history size
        force_new: Force new instance
        
    Returns:
        UndoManager instance
    """
    global _global_undo_manager
    
    if _global_undo_manager is None or force_new:
        kwargs = {}
        if max_history:
            kwargs['max_history'] = max_history
        
        _global_undo_manager = UndoManager(**kwargs)
    
    return _global_undo_manager
