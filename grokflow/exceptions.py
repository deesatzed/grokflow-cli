"""
GrokFlow Custom Exception Hierarchy

Provides specific exception types for better error handling and debugging.
All exceptions inherit from GrokFlowError for easy catching.
"""


class GrokFlowError(Exception):
    """Base exception for all GrokFlow errors"""
    pass


# API-related exceptions
class APIError(GrokFlowError):
    """Base class for API-related errors"""
    pass


class RateLimitError(GrokFlowError):
    """Rate limit exceeded"""
    pass


class KnowledgeBaseError(GrokFlowError):
    """Knowledge base operation failed"""
    pass


class ContextError(GrokFlowError):
    """Context building or management failed"""
    pass


class UndoError(GrokFlowError):
    """Undo/redo operation failed"""
    pass


class AuthenticationError(APIError):
    """API authentication failed (invalid API key)"""
    pass


class ModelNotAvailableError(APIError):
    """Requested model is not available"""
    pass


class APITimeoutError(APIError):
    """API request timed out"""
    pass


# File operation exceptions
class FileOperationError(GrokFlowError):
    """Base class for file operation errors"""
    pass


class BinaryFileError(FileOperationError):
    """Attempted to process a binary file as text"""
    pass


class FileNotFoundError(FileOperationError):
    """File not found in workspace"""
    pass


class FileReadError(FileOperationError):
    """Failed to read file"""
    pass


class FileWriteError(FileOperationError):
    """Failed to write file"""
    pass


# Session management exceptions
class SessionError(GrokFlowError):
    """Base class for session-related errors"""
    pass


class SessionCorruptedError(SessionError):
    """Session file is corrupted"""
    pass


class SessionLockError(SessionError):
    """Failed to acquire session lock"""
    pass


# Validation exceptions
class ValidationError(GrokFlowError):
    """Input validation failed"""
    pass


class PathValidationError(ValidationError):
    """Path validation failed (traversal, outside workspace, etc.)"""
    pass


class ImageValidationError(ValidationError):
    """Image validation failed (size, format, etc.)"""
    pass


class TemplateValidationError(ValidationError):
    """Template validation failed"""
    pass


# Git operation exceptions
class GitError(GrokFlowError):
    """Base class for git-related errors"""
    pass


class GitNotFoundError(GitError):
    """Git executable not found"""
    pass


class GitCommandError(GitError):
    """Git command execution failed"""
    pass


class NotInGitRepoError(GitError):
    """Current directory is not in a git repository"""
    pass


# Knowledge base exceptions
class KnowledgeBaseError(GrokFlowError):
    """Base class for knowledge base errors"""
    pass


class KnowledgeBaseNotAvailableError(KnowledgeBaseError):
    """Knowledge base system not available"""
    pass


class KnowledgeBaseInitError(KnowledgeBaseError):
    """Failed to initialize knowledge base"""
    pass


# Template system exceptions
class TemplateError(GrokFlowError):
    """Base class for template-related errors"""
    pass


class TemplateNotFoundError(TemplateError):
    """Requested template not found"""
    pass


class TemplateRenderError(TemplateError):
    """Failed to render template"""
    pass


# Undo system exceptions
class UndoError(GrokFlowError):
    """Base class for undo-related errors"""
    pass


class NoUndoHistoryError(UndoError):
    """No undo history available"""
    pass


class UndoRestoreError(UndoError):
    """Failed to restore from undo point"""
    pass
