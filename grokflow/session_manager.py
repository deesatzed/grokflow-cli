"""
GrokFlow Session Manager

Thread-safe, atomic session management with:
- Atomic writes (no corruption on crash)
- File locking (no race conditions)
- Backup/restore functionality
- Validation and recovery
- Transaction support

All session operations are safe for concurrent access and crash-resistant.
"""

import json
import tempfile
import shutil
import fcntl
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from contextlib import contextmanager

from grokflow.exceptions import SessionCorruptedError, SessionLockError
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.session')


class SessionManager:
    """
    Thread-safe, atomic session management
    
    Features:
    - Atomic writes prevent corruption
    - File locking prevents race conditions
    - Automatic backup/restore
    - Validation on load
    - Transaction support
    
    Example:
        >>> manager = SessionManager(Path("~/.grokflow/session.json"))
        >>> session = manager.load()
        >>> session['key'] = 'value'
        >>> manager.save(session)
    """
    
    def __init__(self, session_file: Path):
        """
        Initialize session manager
        
        Args:
            session_file: Path to session file
        """
        self.session_file = session_file.expanduser().resolve()
        self.backup_file = self.session_file.with_suffix('.backup')
        self.lock_file = self.session_file.with_suffix('.lock')
        
        # Ensure parent directory exists
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"SessionManager initialized: {self.session_file}")
    
    @contextmanager
    def _acquire_lock(self, timeout: int = 5):
        """
        Acquire exclusive lock on session file
        
        Args:
            timeout: Maximum seconds to wait for lock
            
        Raises:
            SessionLockError: If lock cannot be acquired
        """
        lock_fd = None
        try:
            # Create lock file
            lock_fd = open(self.lock_file, 'w')
            
            # Try to acquire lock with timeout
            import time
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logger.debug(f"Acquired lock: {self.lock_file}")
                    break
                except BlockingIOError:
                    if time.time() - start_time > timeout:
                        raise SessionLockError(
                            f"Could not acquire session lock after {timeout}s. "
                            "Another GrokFlow instance may be running."
                        )
                    time.sleep(0.1)
            
            yield
            
        finally:
            if lock_fd:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                    self.lock_file.unlink(missing_ok=True)
                    logger.debug(f"Released lock: {self.lock_file}")
                except Exception as e:
                    logger.error(f"Error releasing lock: {e}")
    
    def load(self) -> Dict:
        """
        Load session with validation and recovery
        
        Returns:
            Session dictionary
            
        Raises:
            SessionCorruptedError: If session cannot be recovered
        """
        with self._acquire_lock():
            # Try main file
            if self.session_file.exists():
                try:
                    session = self._load_and_validate(self.session_file)
                    logger.info(f"Loaded session from {self.session_file}")
                    return session
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Session file corrupted: {e}")
                    
                    # Try backup
                    if self.backup_file.exists():
                        logger.info("Attempting to restore from backup")
                        try:
                            session = self._load_and_validate(self.backup_file)
                            logger.info("Successfully restored from backup")
                            
                            # Save restored session as main file
                            self._atomic_write(self.session_file, session)
                            logger.info("Restored session saved as main file")
                            
                            return session
                        except Exception as backup_error:
                            logger.error(f"Backup also corrupted: {backup_error}")
                            raise SessionCorruptedError(
                                "Both session file and backup are corrupted. "
                                "Creating new session."
                            )
                    else:
                        logger.warning("No backup file available")
                        raise SessionCorruptedError(
                            "Session file corrupted and no backup available. "
                            "Creating new session."
                        )
            
            # No session file exists - create default
            logger.info("No session file found, creating new session")
            return self._default_session()
    
    def _load_and_validate(self, file_path: Path) -> Dict:
        """
        Load and validate session file
        
        Args:
            file_path: Path to session file
            
        Returns:
            Validated session dictionary
            
        Raises:
            ValueError: If session structure is invalid
            json.JSONDecodeError: If JSON is malformed
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            session = json.load(f)
        
        # Validate structure
        required_keys = ['workspace', 'context_files', 'conversation']
        for key in required_keys:
            if key not in session:
                raise ValueError(f"Missing required key: {key}")
        
        # Validate types
        if not isinstance(session['context_files'], list):
            raise ValueError("context_files must be a list")
        
        if not isinstance(session['conversation'], list):
            raise ValueError("conversation must be a list")
        
        logger.debug(f"Session validated: {len(session['context_files'])} context files")
        return session
    
    def save(self, session: Dict) -> None:
        """
        Atomically save session with backup

        Args:
            session: Session dictionary to save

        Raises:
            SessionCorruptedError: If save fails
        """
        with self._acquire_lock():
            try:
                # Create backup of current file (before overwriting)
                if self.session_file.exists():
                    shutil.copy2(self.session_file, self.backup_file)
                    logger.debug(f"Created backup: {self.backup_file}")

                # Atomic write to main file
                self._atomic_write(self.session_file, session)
                logger.info(f"Session saved: {self.session_file}")

                # If no backup existed before, create one now (for first-save case)
                if not self.backup_file.exists() and self.session_file.exists():
                    shutil.copy2(self.session_file, self.backup_file)
                    logger.debug(f"Created initial backup: {self.backup_file}")
                
            except Exception as e:
                logger.error(f"Failed to save session: {e}", exc_info=True)
                raise SessionCorruptedError(f"Failed to save session: {e}") from e
    
    def _atomic_write(self, target_file: Path, session: Dict) -> None:
        """
        Atomically write session to file
        
        Uses temp file + atomic rename to prevent corruption
        
        Args:
            target_file: Target file path
            session: Session dictionary
            
        Raises:
            OSError: If write fails
        """
        # Write to temporary file in same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=target_file.parent,
            prefix='.session_',
            suffix='.tmp',
            text=True
        )
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic rename
            shutil.move(temp_path, target_file)
            logger.debug(f"Atomic write completed: {target_file}")
            
        except Exception as e:
            # Cleanup temp file on error
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup temp file: {cleanup_error}")
            raise
    
    def _default_session(self) -> Dict:
        """
        Return default session structure
        
        Returns:
            Default session dictionary
        """
        return {
            'workspace': str(Path.cwd()),
            'context_files': [],
            'conversation': [],
            'undo_stack': [],
            'image_analyses': [],
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'version': '2.0'
        }
    
    def backup(self) -> Optional[Path]:
        """
        Create manual backup of current session
        
        Returns:
            Path to backup file, or None if no session exists
        """
        with self._acquire_lock():
            if not self.session_file.exists():
                logger.warning("No session file to backup")
                return None
            
            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.session_file.with_suffix(f'.backup_{timestamp}')
            
            shutil.copy2(self.session_file, backup_path)
            logger.info(f"Manual backup created: {backup_path}")
            
            return backup_path
    
    def restore_from_backup(self, backup_path: Optional[Path] = None) -> Dict:
        """
        Restore session from backup
        
        Args:
            backup_path: Path to backup file (default: use latest .backup file)
            
        Returns:
            Restored session dictionary
            
        Raises:
            SessionCorruptedError: If restore fails
        """
        with self._acquire_lock():
            if backup_path is None:
                backup_path = self.backup_file
            
            if not backup_path.exists():
                raise SessionCorruptedError(f"Backup file not found: {backup_path}")
            
            try:
                session = self._load_and_validate(backup_path)
                logger.info(f"Restored session from {backup_path}")
                
                # Save as main file
                self._atomic_write(self.session_file, session)
                logger.info("Restored session saved as main file")
                
                return session
                
            except Exception as e:
                logger.error(f"Failed to restore from backup: {e}", exc_info=True)
                raise SessionCorruptedError(f"Failed to restore from backup: {e}") from e
    
    def clear(self) -> None:
        """
        Clear session (create new default session)
        """
        with self._acquire_lock():
            session = self._default_session()
            self._atomic_write(self.session_file, session)
            logger.info("Session cleared")
    
    def get_info(self) -> Dict:
        """
        Get session file information

        Returns:
            Dictionary with session file info
        """
        info = {
            'session_file': str(self.session_file),
            'exists': self.session_file.exists(),
            'backup_exists': self.backup_file.exists(),
        }

        if self.session_file.exists():
            stat = self.session_file.stat()
            info.update({
                'size_bytes': stat.st_size,
                'size_kb': stat.st_size / 1024,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        return info

    def export_session(
        self,
        export_path: Path,
        include_conversation: bool = True,
        include_context: bool = True,
        include_metadata: bool = True
    ) -> Dict:
        """
        Export session to a portable format for sharing

        Args:
            export_path: Path to export file
            include_conversation: Include conversation history
            include_context: Include context file paths
            include_metadata: Include session metadata

        Returns:
            Dictionary with export info

        Example:
            >>> manager.export_session(Path("~/shared_session.json"))
            {'exported_at': '2024-01-01T00:00:00', 'items_exported': 5}
        """
        # Load session first (this acquires its own lock)
        session = self.load()

        export_data = {
            'export_version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'source_workspace': session.get('workspace', ''),
        }

        if include_conversation:
            export_data['conversation'] = session.get('conversation', [])

        if include_context:
            # Export context files as relative paths where possible
            context_files = session.get('context_files', [])
            workspace = Path(session.get('workspace', ''))
            export_data['context_files'] = []
            for file_path in context_files:
                try:
                    rel_path = Path(file_path).relative_to(workspace)
                    export_data['context_files'].append({
                        'path': str(rel_path),
                        'is_relative': True
                    })
                except ValueError:
                    export_data['context_files'].append({
                        'path': file_path,
                        'is_relative': False
                    })

        if include_metadata:
            export_data['metadata'] = {
                'created_at': session.get('created_at'),
                'last_modified': session.get('last_modified'),
                'version': session.get('version'),
                'undo_stack_size': len(session.get('undo_stack', [])),
                'image_analyses_count': len(session.get('image_analyses', []))
            }

        # Write export file
        export_path = Path(export_path).expanduser().resolve()
        export_path.parent.mkdir(parents=True, exist_ok=True)

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Session exported to {export_path}")

        return {
            'exported_at': export_data['exported_at'],
            'export_path': str(export_path),
            'items_exported': {
                'conversation': len(export_data.get('conversation', [])),
                'context_files': len(export_data.get('context_files', []))
            }
        }

    def import_session(
        self,
        import_path: Path,
        merge: bool = False,
        workspace_override: Optional[Path] = None
    ) -> Dict:
        """
        Import session from an exported file

        Args:
            import_path: Path to import file
            merge: If True, merge with current session; if False, replace
            workspace_override: Override workspace path for imported session

        Returns:
            Dictionary with import info

        Raises:
            SessionCorruptedError: If import file is invalid

        Example:
            >>> manager.import_session(Path("~/shared_session.json"), merge=True)
            {'imported_at': '2024-01-01T00:00:00', 'items_imported': 5}
        """
        import_path = Path(import_path).expanduser().resolve()

        if not import_path.exists():
            raise SessionCorruptedError(f"Import file not found: {import_path}")

        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
        except json.JSONDecodeError as e:
            raise SessionCorruptedError(f"Invalid import file format: {e}") from e

        # Validate export version
        export_version = import_data.get('export_version', '0')
        if not export_version.startswith('1.'):
            raise SessionCorruptedError(
                f"Unsupported export version: {export_version}"
            )

        # Load or create session (load() acquires its own lock)
        if merge:
            current_session = self.load()
        else:
            current_session = self._default_session()

        # Determine workspace
        workspace = str(workspace_override) if workspace_override else \
                    import_data.get('source_workspace', str(Path.cwd()))
        current_session['workspace'] = workspace

        # Import conversation
        imported_conversation = import_data.get('conversation', [])
        if merge and imported_conversation:
            # Append imported conversation
            current_session['conversation'].extend(imported_conversation)
        elif imported_conversation:
            current_session['conversation'] = imported_conversation

        # Import context files
        imported_context = import_data.get('context_files', [])
        imported_file_count = 0
        workspace_path = Path(workspace)

        for ctx_file in imported_context:
            if isinstance(ctx_file, dict):
                file_path = ctx_file.get('path', '')
                is_relative = ctx_file.get('is_relative', False)

                if is_relative:
                    # Resolve relative to new workspace
                    full_path = str(workspace_path / file_path)
                else:
                    full_path = file_path
            else:
                # Legacy format - just a string path
                full_path = ctx_file

            if merge:
                if full_path not in current_session['context_files']:
                    current_session['context_files'].append(full_path)
                    imported_file_count += 1
            else:
                current_session['context_files'].append(full_path)
                imported_file_count += 1

        # Update metadata
        current_session['last_modified'] = datetime.now().isoformat()
        current_session['imported_from'] = str(import_path)
        current_session['imported_at'] = datetime.now().isoformat()

        # Save imported session (save() acquires its own lock)
        self.save(current_session)

        logger.info(f"Session imported from {import_path}")

        return {
            'imported_at': current_session['imported_at'],
            'import_path': str(import_path),
            'merge_mode': merge,
            'items_imported': {
                'conversation': len(imported_conversation),
                'context_files': imported_file_count
            }
        }

    def get_shareable_summary(self) -> Dict:
        """
        Get a summary of the session suitable for sharing

        Returns:
            Dictionary with shareable session summary
        """
        # load() acquires its own lock
        session = self.load()

        return {
            'workspace': session.get('workspace', ''),
            'context_file_count': len(session.get('context_files', [])),
            'conversation_length': len(session.get('conversation', [])),
            'created_at': session.get('created_at'),
            'last_modified': session.get('last_modified'),
            'version': session.get('version'),
            'can_export': True
        }


@contextmanager
def transactional_session(manager: SessionManager):
    """
    Context manager for transactional session operations
    
    Automatically saves on success, rolls back on failure
    
    Example:
        >>> with transactional_session(manager) as session:
        ...     session['key'] = 'value'
        ...     # Automatically saved on exit
    
    Args:
        manager: SessionManager instance
        
    Yields:
        Session dictionary
    """
    # Load session
    session = manager.load()
    
    # Create backup before modifications
    backup_data = json.dumps(session)
    
    try:
        yield session
        
        # Success - save changes
        manager.save(session)
        logger.debug("Transaction committed")
        
    except Exception as e:
        # Failure - rollback
        logger.error(f"Transaction failed, rolling back: {e}")
        
        # Restore from backup data
        restored_session = json.loads(backup_data)
        manager.save(restored_session)
        logger.info("Transaction rolled back")
        
        raise
