"""
Tests for session management system
"""

import pytest
import json
import time
from pathlib import Path
from grokflow.session_manager import SessionManager, transactional_session
from grokflow.exceptions import SessionCorruptedError, SessionLockError


class TestSessionManager:
    """Test session manager"""
    
    def test_init_creates_directory(self, temp_dir):
        """Test initialization creates parent directory"""
        session_file = temp_dir / "subdir" / "session.json"
        manager = SessionManager(session_file)
        assert session_file.parent.exists()
    
    def test_load_creates_default_session(self, temp_dir):
        """Test loading non-existent session creates default"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        session = manager.load()
        
        assert 'workspace' in session
        assert 'context_files' in session
        assert 'conversation' in session
        assert session['version'] == '2.0'
    
    def test_save_and_load(self, temp_dir, mock_session):
        """Test save and load cycle"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Save
        manager.save(mock_session)
        assert session_file.exists()
        
        # Load
        loaded = manager.load()
        assert loaded['workspace'] == mock_session['workspace']
        assert loaded['version'] == mock_session['version']
    
    def test_atomic_write_creates_backup(self, temp_dir, mock_session):
        """Test atomic write creates backup"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # First save
        manager.save(mock_session)
        
        # Second save should create backup
        mock_session['workspace'] = '/new/workspace'
        manager.save(mock_session)
        
        assert manager.backup_file.exists()
    
    def test_load_corrupted_restores_from_backup(self, temp_dir, mock_session):
        """Test recovery from corrupted session"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Save valid session
        manager.save(mock_session)
        
        # Corrupt main file
        session_file.write_text("corrupted json{{{")
        
        # Load should restore from backup
        loaded = manager.load()
        assert loaded['workspace'] == mock_session['workspace']
    
    def test_load_both_corrupted_creates_new(self, temp_dir):
        """Test creating new session when both corrupted"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Create corrupted files
        session_file.write_text("corrupted")
        manager.backup_file.write_text("also corrupted")
        
        # Should raise but we can catch and create new
        with pytest.raises(SessionCorruptedError):
            manager.load()
    
    def test_validation_missing_key(self, temp_dir):
        """Test validation catches missing keys"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Save invalid session
        invalid_session = {'workspace': '/test'}
        session_file.write_text(json.dumps(invalid_session))
        
        with pytest.raises(SessionCorruptedError):
            manager.load()
    
    def test_validation_wrong_type(self, temp_dir):
        """Test validation catches wrong types"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Save session with wrong type
        invalid_session = {
            'workspace': '/test',
            'context_files': 'not a list',  # Should be list
            'conversation': []
        }
        session_file.write_text(json.dumps(invalid_session))
        
        with pytest.raises(SessionCorruptedError):
            manager.load()
    
    def test_backup_creates_timestamped_file(self, temp_dir, mock_session):
        """Test manual backup creates timestamped file"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        manager.save(mock_session)
        backup_path = manager.backup()
        
        assert backup_path is not None
        assert backup_path.exists()
        assert 'backup_' in backup_path.name
    
    def test_restore_from_backup(self, temp_dir, mock_session):
        """Test restore from backup"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Save and backup
        manager.save(mock_session)
        backup_path = manager.backup()
        
        # Modify and save
        mock_session['workspace'] = '/modified'
        manager.save(mock_session)
        
        # Restore from backup
        restored = manager.restore_from_backup(backup_path)
        assert restored['workspace'] == '/test/workspace'
    
    def test_clear_creates_default_session(self, temp_dir, mock_session):
        """Test clear creates default session"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Save custom session
        manager.save(mock_session)
        
        # Clear
        manager.clear()
        
        # Load should have default values
        loaded = manager.load()
        assert loaded['context_files'] == []
        assert loaded['conversation'] == []
    
    def test_get_info(self, temp_dir, mock_session):
        """Test get_info returns metadata"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        manager.save(mock_session)
        info = manager.get_info()
        
        assert info['exists'] is True
        assert info['size_bytes'] > 0
        assert 'modified' in info


class TestTransactionalSession:
    """Test transactional session context manager"""
    
    def test_transaction_commits_on_success(self, temp_dir, mock_session):
        """Test transaction commits changes on success"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        manager.save(mock_session)
        
        with transactional_session(manager) as session:
            session['workspace'] = '/modified'
        
        # Changes should be saved
        loaded = manager.load()
        assert loaded['workspace'] == '/modified'
    
    def test_transaction_rolls_back_on_error(self, temp_dir, mock_session):
        """Test transaction rolls back on exception"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        manager.save(mock_session)
        
        original_workspace = mock_session['workspace']
        
        try:
            with transactional_session(manager) as session:
                session['workspace'] = '/modified'
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Changes should be rolled back
        loaded = manager.load()
        assert loaded['workspace'] == original_workspace


class TestFileLocking:
    """Test file locking mechanism"""
    
    def test_lock_prevents_concurrent_access(self, temp_dir, mock_session):
        """Test file locking prevents concurrent access"""
        session_file = temp_dir / "session.json"
        manager1 = SessionManager(session_file)
        manager2 = SessionManager(session_file)
        
        # First manager acquires lock
        with manager1._acquire_lock():
            # Second manager should timeout
            with pytest.raises(SessionLockError, match="Could not acquire"):
                with manager2._acquire_lock(timeout=1):
                    pass
    
    def test_lock_released_after_operation(self, temp_dir, mock_session):
        """Test lock is released after operation"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)
        
        # Acquire and release lock
        with manager._acquire_lock():
            pass
        
        # Should be able to acquire again
        with manager._acquire_lock():
            pass
    
    def test_lock_file_cleaned_up(self, temp_dir):
        """Test lock file is cleaned up"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)

        with manager._acquire_lock():
            assert manager.lock_file.exists()

        # Lock file should be removed
        assert not manager.lock_file.exists()


class TestSessionExportImport:
    """Test session export and import functionality"""

    def test_export_session_basic(self, temp_dir, mock_session):
        """Test basic session export"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        manager.save(mock_session)
        result = manager.export_session(export_file)

        assert export_file.exists()
        assert 'exported_at' in result
        assert 'items_exported' in result

    def test_export_includes_conversation(self, temp_dir, mock_session):
        """Test export includes conversation history"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        mock_session['conversation'] = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there'}
        ]
        manager.save(mock_session)
        manager.export_session(export_file)

        with open(export_file, 'r') as f:
            exported = json.load(f)

        assert 'conversation' in exported
        assert len(exported['conversation']) == 2

    def test_export_includes_context_files(self, temp_dir, mock_session):
        """Test export includes context files"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        mock_session['context_files'] = [
            str(temp_dir / "file1.py"),
            str(temp_dir / "file2.py")
        ]
        manager.save(mock_session)
        manager.export_session(export_file)

        with open(export_file, 'r') as f:
            exported = json.load(f)

        assert 'context_files' in exported
        assert len(exported['context_files']) == 2

    def test_export_without_conversation(self, temp_dir, mock_session):
        """Test export can exclude conversation"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        mock_session['conversation'] = [{'role': 'user', 'content': 'test'}]
        manager.save(mock_session)
        manager.export_session(export_file, include_conversation=False)

        with open(export_file, 'r') as f:
            exported = json.load(f)

        assert 'conversation' not in exported

    def test_export_without_context(self, temp_dir, mock_session):
        """Test export can exclude context files"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        mock_session['context_files'] = ['file1.py', 'file2.py']
        manager.save(mock_session)
        manager.export_session(export_file, include_context=False)

        with open(export_file, 'r') as f:
            exported = json.load(f)

        assert 'context_files' not in exported

    def test_export_includes_metadata(self, temp_dir, mock_session):
        """Test export includes metadata by default"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        manager.save(mock_session)
        manager.export_session(export_file)

        with open(export_file, 'r') as f:
            exported = json.load(f)

        assert 'metadata' in exported
        assert 'version' in exported['metadata']

    def test_import_session_replace(self, temp_dir, mock_session):
        """Test importing session in replace mode"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        # Create and export session
        mock_session['conversation'] = [{'role': 'user', 'content': 'original'}]
        manager.save(mock_session)
        manager.export_session(export_file)

        # Modify current session
        new_session = manager.load()
        new_session['conversation'] = [{'role': 'user', 'content': 'modified'}]
        manager.save(new_session)

        # Import (replace mode)
        result = manager.import_session(export_file, merge=False)

        assert result['merge_mode'] is False
        loaded = manager.load()
        assert loaded['conversation'][0]['content'] == 'original'

    def test_import_session_merge(self, temp_dir, mock_session):
        """Test importing session in merge mode"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        # Create and export session with one message
        mock_session['conversation'] = [{'role': 'user', 'content': 'exported'}]
        manager.save(mock_session)
        manager.export_session(export_file)

        # Modify current session with different message
        new_session = manager.load()
        new_session['conversation'] = [{'role': 'user', 'content': 'current'}]
        manager.save(new_session)

        # Import (merge mode)
        result = manager.import_session(export_file, merge=True)

        assert result['merge_mode'] is True
        loaded = manager.load()
        # Should have both messages
        assert len(loaded['conversation']) == 2

    def test_import_session_workspace_override(self, temp_dir, mock_session):
        """Test importing with workspace override"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        manager.save(mock_session)
        manager.export_session(export_file)

        # Import with workspace override
        new_workspace = temp_dir / "new_workspace"
        manager.import_session(export_file, workspace_override=new_workspace)

        loaded = manager.load()
        assert loaded['workspace'] == str(new_workspace)

    def test_import_nonexistent_file_raises_error(self, temp_dir):
        """Test importing nonexistent file raises error"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)

        with pytest.raises(SessionCorruptedError, match="not found"):
            manager.import_session(temp_dir / "nonexistent.json")

    def test_import_invalid_json_raises_error(self, temp_dir):
        """Test importing invalid JSON raises error"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "invalid.json"
        manager = SessionManager(session_file)

        export_file.write_text("not valid json {{{")

        with pytest.raises(SessionCorruptedError, match="Invalid import file"):
            manager.import_session(export_file)

    def test_import_unsupported_version_raises_error(self, temp_dir):
        """Test importing unsupported export version raises error"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "old_export.json"
        manager = SessionManager(session_file)

        export_file.write_text(json.dumps({
            'export_version': '0.5',
            'conversation': []
        }))

        with pytest.raises(SessionCorruptedError, match="Unsupported export version"):
            manager.import_session(export_file)

    def test_import_sets_metadata(self, temp_dir, mock_session):
        """Test import updates session metadata"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        manager.save(mock_session)
        manager.export_session(export_file)
        manager.import_session(export_file)

        loaded = manager.load()
        assert 'imported_from' in loaded
        assert 'imported_at' in loaded

    def test_get_shareable_summary(self, temp_dir, mock_session):
        """Test getting shareable summary"""
        session_file = temp_dir / "session.json"
        manager = SessionManager(session_file)

        mock_session['conversation'] = [{'role': 'user', 'content': 'test'}]
        mock_session['context_files'] = ['file1.py', 'file2.py']
        manager.save(mock_session)

        summary = manager.get_shareable_summary()

        assert summary['context_file_count'] == 2
        assert summary['conversation_length'] == 1
        assert summary['can_export'] is True

    def test_context_files_exported_as_relative(self, temp_dir, mock_session):
        """Test context files within workspace exported as relative paths"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        # Set workspace and add context file within workspace
        workspace = temp_dir / "workspace"
        workspace.mkdir()
        mock_session['workspace'] = str(workspace)
        mock_session['context_files'] = [
            str(workspace / "src" / "module.py"),  # Within workspace
            "/outside/workspace/file.py"  # Outside workspace
        ]
        manager.save(mock_session)
        manager.export_session(export_file)

        with open(export_file, 'r') as f:
            exported = json.load(f)

        # File within workspace should be relative
        ctx_files = exported['context_files']
        relative_file = [f for f in ctx_files if f['is_relative']][0]
        assert relative_file['path'] == "src/module.py"

        # File outside workspace should be absolute
        absolute_file = [f for f in ctx_files if not f['is_relative']][0]
        assert absolute_file['path'] == "/outside/workspace/file.py"

    def test_import_resolves_relative_paths(self, temp_dir, mock_session):
        """Test import resolves relative paths to new workspace"""
        session_file = temp_dir / "session.json"
        export_file = temp_dir / "export.json"
        manager = SessionManager(session_file)

        # Export with relative path
        old_workspace = temp_dir / "old_workspace"
        old_workspace.mkdir()
        mock_session['workspace'] = str(old_workspace)
        mock_session['context_files'] = [str(old_workspace / "src" / "module.py")]
        manager.save(mock_session)
        manager.export_session(export_file)

        # Import to new workspace
        new_workspace = temp_dir / "new_workspace"
        new_workspace.mkdir()
        manager.import_session(export_file, workspace_override=new_workspace)

        loaded = manager.load()
        # Relative path should be resolved to new workspace
        assert str(new_workspace / "src" / "module.py") in loaded['context_files']
