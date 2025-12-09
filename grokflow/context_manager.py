"""
GrokFlow Context Management

Modular context management for:
- Workspace context
- File context
- Directory context
- Context optimization
- Memory management
- Smart context building

Features:
- Efficient context building
- Binary file detection
- Size limits
- Context caching
- Relevance scoring
"""

import os
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from grokflow.exceptions import ContextError, PathValidationError
from grokflow.validators import InputValidator, PathSanitizer
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.context_manager')


@dataclass
class FileContext:
    """Context for a single file"""
    path: Path
    content: str
    size: int
    is_binary: bool = False
    encoding: str = 'utf-8'
    last_modified: Optional[str] = None
    relevance_score: float = 1.0
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"FileContext({self.path}, {self.size} bytes)"
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            'path': str(self.path),
            'content': self.content,
            'size': self.size,
            'is_binary': self.is_binary,
            'encoding': self.encoding,
            'last_modified': self.last_modified,
            'relevance_score': self.relevance_score,
            'metadata': self.metadata
        }


@dataclass
class WorkspaceContext:
    """Context for entire workspace"""
    workspace_path: Path
    files: List[FileContext] = field(default_factory=list)
    total_size: int = 0
    file_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def add_file(self, file_context: FileContext) -> None:
        """Add file to workspace context"""
        self.files.append(file_context)
        self.total_size += file_context.size
        self.file_count += 1
    
    def get_files_by_extension(self, extension: str) -> List[FileContext]:
        """Get files by extension"""
        return [f for f in self.files if f.path.suffix == extension]
    
    def get_total_content(self) -> str:
        """Get concatenated content of all files"""
        return "\n\n".join([
            f"=== {f.path} ===\n{f.content}"
            for f in self.files
            if not f.is_binary
        ])
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            'workspace_path': str(self.workspace_path),
            'files': [f.to_dict() for f in self.files],
            'total_size': self.total_size,
            'file_count': self.file_count,
            'created_at': self.created_at,
            'metadata': self.metadata
        }


class ContextManager:
    """
    Manages context for workspace and files
    
    Features:
    - Build file context
    - Build workspace context
    - Binary file detection
    - Size limits
    - Context optimization
    - Caching
    
    Example:
        >>> cm = ContextManager()
        >>> file_ctx = cm.build_file_context(Path('main.py'))
        >>> workspace_ctx = cm.build_workspace_context(Path('.'))
    """
    
    # Binary file extensions
    BINARY_EXTENSIONS = {
        '.pyc', '.pyo', '.so', '.dll', '.dylib',
        '.exe', '.bin', '.dat', '.db', '.sqlite',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
        '.pdf', '.zip', '.tar', '.gz', '.bz2',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.ttf', '.otf', '.woff', '.woff2'
    }
    
    # Text file extensions (always try to read)
    TEXT_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.java', '.c', '.cpp', '.h', '.hpp',
        '.go', '.rs', '.rb', '.php',
        '.html', '.css', '.scss', '.sass',
        '.json', '.xml', '.yaml', '.yml',
        '.md', '.txt', '.rst', '.toml',
        '.sh', '.bash', '.zsh', '.fish',
        '.sql', '.graphql', '.proto'
    }
    
    # Default limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_CONTEXT_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_FILES = 1000
    
    def __init__(
        self,
        max_file_size: int = MAX_FILE_SIZE,
        max_context_size: int = MAX_CONTEXT_SIZE,
        max_files: int = MAX_FILES
    ):
        """
        Initialize context manager
        
        Args:
            max_file_size: Maximum size for single file
            max_context_size: Maximum total context size
            max_files: Maximum number of files
        """
        self.max_file_size = max_file_size
        self.max_context_size = max_context_size
        self.max_files = max_files
        
        # Cache for file contexts
        self._cache: Dict[str, FileContext] = {}
        
        logger.info(
            f"ContextManager initialized: "
            f"max_file={max_file_size}, max_context={max_context_size}, max_files={max_files}"
        )
    
    def is_binary_file(self, file_path: Path) -> bool:
        """
        Check if file is binary
        
        Args:
            file_path: Path to file
            
        Returns:
            True if binary
        """
        # Check extension first
        if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
            return True
        
        if file_path.suffix.lower() in self.TEXT_EXTENSIONS:
            return False
        
        # Check file content (read first 8KB)
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
            
            # Check for null bytes
            if b'\x00' in chunk:
                return True
            
            # Try to decode as text
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
                
        except Exception as e:
            logger.warning(f"Error checking if binary: {file_path}: {e}")
            return True
    
    def build_file_context(
        self,
        file_path: Path,
        validate: bool = True,
        use_cache: bool = True
    ) -> FileContext:
        """
        Build context for single file
        
        Args:
            file_path: Path to file
            validate: Validate file path
            use_cache: Use cached context if available
            
        Returns:
            FileContext object
            
        Raises:
            ContextError: If context building fails
        """
        # Validate path
        if validate:
            try:
                # Allow outside workspace since context can include files from anywhere
                file_path = InputValidator.validate_file_path(
                    str(file_path), allow_outside_workspace=True
                )
            except PathValidationError as e:
                raise ContextError(f"Invalid file path: {e}") from e
        
        file_path = Path(file_path)
        
        # Check cache
        cache_key = str(file_path.absolute())
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached context: {file_path}")
            return self._cache[cache_key]
        
        # Check if file exists
        if not file_path.exists():
            raise ContextError(f"File not found: {file_path}")
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            logger.warning(f"File too large: {file_path} ({file_size} bytes)")
            raise ContextError(
                f"File too large: {file_path} ({file_size} bytes, max {self.max_file_size})"
            )
        
        # Check if binary
        is_binary = self.is_binary_file(file_path)
        
        # Read content
        content = ""
        encoding = "utf-8"
        
        if not is_binary:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try different encodings
                for enc in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            content = f.read()
                        encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Give up, treat as binary
                    is_binary = True
                    content = f"<binary file: {file_path.name}>"
            except Exception as e:
                logger.error(f"Error reading file: {file_path}: {e}")
                raise ContextError(f"Failed to read file: {e}") from e
        else:
            content = f"<binary file: {file_path.name}>"
        
        # Get last modified time
        last_modified = datetime.fromtimestamp(
            file_path.stat().st_mtime
        ).isoformat()
        
        # Create context
        file_context = FileContext(
            path=file_path,
            content=content,
            size=file_size,
            is_binary=is_binary,
            encoding=encoding,
            last_modified=last_modified,
            metadata={
                'extension': file_path.suffix,
                'name': file_path.name
            }
        )
        
        # Cache it
        if use_cache:
            self._cache[cache_key] = file_context
        
        logger.debug(f"Built file context: {file_path} ({file_size} bytes)")
        return file_context
    
    def build_directory_context(
        self,
        directory_path: Path,
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None
    ) -> WorkspaceContext:
        """
        Build context for directory
        
        Args:
            directory_path: Path to directory
            recursive: Include subdirectories
            exclude_patterns: Patterns to exclude (glob)
            include_patterns: Patterns to include (glob)
            
        Returns:
            WorkspaceContext object
            
        Raises:
            ContextError: If context building fails
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise ContextError(f"Directory not found: {directory_path}")
        
        if not directory_path.is_dir():
            raise ContextError(f"Not a directory: {directory_path}")
        
        # Default excludes
        if exclude_patterns is None:
            exclude_patterns = [
                '*.pyc', '__pycache__', '.git', '.svn', '.hg',
                'node_modules', 'venv', 'env', '.venv',
                '*.egg-info', 'dist', 'build', '.pytest_cache',
                '.mypy_cache', '.tox', 'htmlcov', '.coverage'
            ]
        
        workspace_ctx = WorkspaceContext(workspace_path=directory_path)
        
        # Get all files
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        files_to_process = []
        for file_path in directory_path.glob(pattern):
            if not file_path.is_file():
                continue
            
            # Check exclude patterns
            if any(file_path.match(pat) for pat in exclude_patterns):
                continue
            
            # Check include patterns
            if include_patterns and not any(file_path.match(pat) for pat in include_patterns):
                continue
            
            files_to_process.append(file_path)
        
        # Check file count limit
        if len(files_to_process) > self.max_files:
            logger.warning(
                f"Too many files: {len(files_to_process)} (max {self.max_files})"
            )
            files_to_process = files_to_process[:self.max_files]
        
        # Build context for each file
        for file_path in files_to_process:
            try:
                file_ctx = self.build_file_context(file_path, validate=False)
                workspace_ctx.add_file(file_ctx)
                
                # Check total size limit
                if workspace_ctx.total_size > self.max_context_size:
                    logger.warning(
                        f"Context size limit reached: {workspace_ctx.total_size} bytes"
                    )
                    break
                    
            except ContextError as e:
                logger.warning(f"Skipping file {file_path}: {e}")
                continue
        
        logger.info(
            f"Built directory context: {directory_path} "
            f"({workspace_ctx.file_count} files, {workspace_ctx.total_size} bytes)"
        )
        
        return workspace_ctx
    
    def build_workspace_context(
        self,
        workspace_path: Path,
        file_patterns: Optional[List[str]] = None
    ) -> WorkspaceContext:
        """
        Build context for workspace
        
        Args:
            workspace_path: Path to workspace
            file_patterns: File patterns to include
            
        Returns:
            WorkspaceContext object
        """
        return self.build_directory_context(
            directory_path=workspace_path,
            recursive=True,
            include_patterns=file_patterns
        )
    
    def build_context_from_files(
        self,
        file_paths: List[Path]
    ) -> WorkspaceContext:
        """
        Build context from list of files
        
        Args:
            file_paths: List of file paths
            
        Returns:
            WorkspaceContext object
        """
        if not file_paths:
            raise ContextError("No files provided")
        
        # Use first file's parent as workspace
        workspace_path = file_paths[0].parent
        workspace_ctx = WorkspaceContext(workspace_path=workspace_path)
        
        for file_path in file_paths:
            try:
                file_ctx = self.build_file_context(file_path)
                workspace_ctx.add_file(file_ctx)
                
                # Check limits
                if workspace_ctx.file_count >= self.max_files:
                    logger.warning(f"Max files reached: {self.max_files}")
                    break
                
                if workspace_ctx.total_size >= self.max_context_size:
                    logger.warning(f"Max context size reached: {self.max_context_size}")
                    break
                    
            except ContextError as e:
                logger.warning(f"Skipping file {file_path}: {e}")
                continue
        
        return workspace_ctx
    
    def optimize_context(
        self,
        workspace_ctx: WorkspaceContext,
        max_size: Optional[int] = None,
        relevance_threshold: float = 0.5
    ) -> WorkspaceContext:
        """
        Optimize context by removing low-relevance files
        
        Args:
            workspace_ctx: Workspace context to optimize
            max_size: Maximum size (bytes)
            relevance_threshold: Minimum relevance score
            
        Returns:
            Optimized workspace context
        """
        max_size = max_size or self.max_context_size
        
        # Filter by relevance
        relevant_files = [
            f for f in workspace_ctx.files
            if f.relevance_score >= relevance_threshold
        ]
        
        # Sort by relevance (descending)
        relevant_files.sort(key=lambda f: f.relevance_score, reverse=True)
        
        # Build optimized context
        optimized = WorkspaceContext(workspace_path=workspace_ctx.workspace_path)
        
        for file_ctx in relevant_files:
            if optimized.total_size + file_ctx.size > max_size:
                break
            optimized.add_file(file_ctx)
        
        logger.info(
            f"Optimized context: {workspace_ctx.file_count} → {optimized.file_count} files, "
            f"{workspace_ctx.total_size} → {optimized.total_size} bytes"
        )
        
        return optimized
    
    def clear_cache(self) -> None:
        """Clear file context cache"""
        self._cache.clear()
        logger.debug("Context cache cleared")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics
        """
        return {
            'cached_files': len(self._cache),
            'cache_size': sum(ctx.size for ctx in self._cache.values())
        }


# Global context manager instance
_global_context_manager: Optional[ContextManager] = None


def get_context_manager(
    max_file_size: Optional[int] = None,
    max_context_size: Optional[int] = None,
    force_new: bool = False
) -> ContextManager:
    """
    Get global context manager instance
    
    Args:
        max_file_size: Maximum file size
        max_context_size: Maximum context size
        force_new: Force new instance
        
    Returns:
        ContextManager instance
    """
    global _global_context_manager
    
    if _global_context_manager is None or force_new:
        kwargs = {}
        if max_file_size:
            kwargs['max_file_size'] = max_file_size
        if max_context_size:
            kwargs['max_context_size'] = max_context_size
        
        _global_context_manager = ContextManager(**kwargs)
    
    return _global_context_manager
