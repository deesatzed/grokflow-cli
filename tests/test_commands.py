"""Tests for GrokFlow CLI commands"""

import pytest
import json
from pathlib import Path
from grokflow.commands import GrokFlowCommands, create_parser, main
from grokflow.undo_manager import (
    get_undo_manager, FileWriteCommand, UndoManager
)
from grokflow.session_manager import SessionManager
from grokflow.pattern_alerts import PatternAlertManager, AlertSeverity


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / '.grokflow').mkdir()
    return workspace


@pytest.fixture
def commands(temp_workspace):
    """Create commands handler with temp workspace"""
    return GrokFlowCommands(workspace=temp_workspace)


@pytest.fixture
def undo_manager():
    """Create fresh undo manager for each test"""
    return get_undo_manager(force_new=True)


class TestUndoCommands:
    """Tests for undo/redo commands"""

    def test_undo_empty_stack(self, commands):
        """Should return 1 when nothing to undo"""
        # Force new empty manager
        get_undo_manager(force_new=True)
        result = commands.cmd_undo()
        assert result == 1

    def test_undo_single(self, commands, temp_workspace):
        """Should undo single command"""
        manager = get_undo_manager(force_new=True)

        # Execute a command
        test_file = temp_workspace / "test.txt"
        cmd = FileWriteCommand(test_file, "content")
        manager.execute(cmd)

        assert test_file.exists()

        result = commands.cmd_undo()
        assert result == 0
        assert not test_file.exists()

    def test_undo_batch(self, commands, temp_workspace):
        """Should undo multiple commands"""
        manager = get_undo_manager(force_new=True)

        # Execute multiple commands
        for i in range(5):
            cmd = FileWriteCommand(
                temp_workspace / f"file{i}.txt",
                f"content{i}"
            )
            manager.execute(cmd)

        result = commands.cmd_undo(count=3)
        assert result == 0

        # Check 3 files removed, 2 remain
        assert not (temp_workspace / "file4.txt").exists()
        assert not (temp_workspace / "file3.txt").exists()
        assert not (temp_workspace / "file2.txt").exists()
        assert (temp_workspace / "file1.txt").exists()
        assert (temp_workspace / "file0.txt").exists()

    def test_undo_all(self, commands, temp_workspace):
        """Should undo all commands"""
        manager = get_undo_manager(force_new=True)

        for i in range(3):
            cmd = FileWriteCommand(
                temp_workspace / f"file{i}.txt",
                f"content{i}"
            )
            manager.execute(cmd)

        result = commands.cmd_undo(all_=True)
        assert result == 0

        # All files should be removed
        for i in range(3):
            assert not (temp_workspace / f"file{i}.txt").exists()

    def test_redo_empty_stack(self, commands):
        """Should return 1 when nothing to redo"""
        get_undo_manager(force_new=True)
        result = commands.cmd_redo()
        assert result == 1

    def test_redo_single(self, commands, temp_workspace):
        """Should redo single command"""
        manager = get_undo_manager(force_new=True)

        test_file = temp_workspace / "test.txt"
        cmd = FileWriteCommand(test_file, "content")
        manager.execute(cmd)
        manager.undo()

        assert not test_file.exists()

        result = commands.cmd_redo()
        assert result == 0
        assert test_file.exists()


class TestHistoryCommand:
    """Tests for history command"""

    def test_history_empty(self, commands):
        """Should show no history when empty"""
        get_undo_manager(force_new=True)
        result = commands.cmd_history()
        assert result == 0

    def test_history_with_commands(self, commands, temp_workspace):
        """Should show history with commands"""
        manager = get_undo_manager(force_new=True)

        for i in range(3):
            cmd = FileWriteCommand(
                temp_workspace / f"file{i}.txt",
                f"content{i}"
            )
            manager.execute(cmd)

        result = commands.cmd_history()
        assert result == 0


class TestSessionCommands:
    """Tests for session export/import commands"""

    def test_session_export(self, commands, temp_workspace):
        """Should export session to file"""
        # Create a session first
        session_file = temp_workspace / '.grokflow' / 'session.json'
        manager = SessionManager(session_file)
        session = manager.load()
        session['context_files'] = ['file1.py', 'file2.py']
        manager.save(session)

        export_path = temp_workspace / "exported.json"
        result = commands.cmd_session_export(str(export_path))

        assert result == 0
        assert export_path.exists()

        # Verify export content
        with open(export_path) as f:
            data = json.load(f)
        assert 'export_version' in data
        assert 'context_files' in data

    def test_session_import(self, commands, temp_workspace):
        """Should import session from file"""
        # Create export file
        export_data = {
            'export_version': '1.0',
            'exported_at': '2024-01-01T00:00:00',
            'source_workspace': str(temp_workspace),
            'conversation': [{'role': 'user', 'content': 'test'}],
            'context_files': [
                {'path': 'src/main.py', 'is_relative': True}
            ]
        }

        import_path = temp_workspace / "import.json"
        with open(import_path, 'w') as f:
            json.dump(export_data, f)

        result = commands.cmd_session_import(str(import_path))

        assert result == 0

    def test_session_import_merge(self, commands, temp_workspace):
        """Should merge imported session"""
        # Create existing session
        session_file = temp_workspace / '.grokflow' / 'session.json'
        manager = SessionManager(session_file)
        session = manager.load()
        session['context_files'] = ['existing.py']
        session['conversation'] = [{'role': 'user', 'content': 'existing'}]
        manager.save(session)

        # Create export file
        export_data = {
            'export_version': '1.0',
            'exported_at': '2024-01-01T00:00:00',
            'source_workspace': str(temp_workspace),
            'conversation': [{'role': 'user', 'content': 'imported'}],
            'context_files': [
                {'path': 'new.py', 'is_relative': True}
            ]
        }

        import_path = temp_workspace / "import.json"
        with open(import_path, 'w') as f:
            json.dump(export_data, f)

        result = commands.cmd_session_import(str(import_path), merge=True)

        assert result == 0

        # Verify merge
        session = manager.load()
        assert len(session['conversation']) == 2
        assert 'existing.py' in session['context_files']

    def test_session_info(self, commands, temp_workspace):
        """Should show session info"""
        result = commands.cmd_session_info()
        assert result == 0


class TestAlertCommands:
    """Tests for alert commands"""

    def test_alerts_list_empty(self, commands):
        """Should handle empty alerts list"""
        result = commands.cmd_alerts_list()
        assert result == 0

    def test_alerts_check(self, commands):
        """Should check for new alerts"""
        result = commands.cmd_alerts_check()
        assert result == 0

    def test_alerts_summary(self, commands):
        """Should show alert summary"""
        result = commands.cmd_alerts_summary()
        assert result == 0

    def test_alerts_acknowledge_nonexistent(self, commands):
        """Should return 1 for nonexistent alert"""
        result = commands.cmd_alerts_acknowledge("nonexistent_id")
        assert result == 1

    def test_alerts_resolve_nonexistent(self, commands):
        """Should return 1 for nonexistent alert"""
        result = commands.cmd_alerts_resolve("nonexistent_id")
        assert result == 1

    def test_alerts_dismiss_nonexistent(self, commands):
        """Should return 1 for nonexistent alert"""
        result = commands.cmd_alerts_dismiss("nonexistent_id")
        assert result == 1


class TestSuggestTestsCommand:
    """Tests for test suggestion commands"""

    def test_suggest_tests_no_args(self, commands):
        """Should return 1 when no files specified"""
        result = commands.cmd_suggest_tests()
        assert result == 1

    def test_suggest_tests_with_files(self, commands, temp_workspace):
        """Should suggest tests for given files"""
        # Create source file
        src_file = temp_workspace / "module.py"
        src_file.write_text("def foo(): pass")

        # Create matching test
        test_file = temp_workspace / "test_module.py"
        test_file.write_text("def test_foo(): pass")

        result = commands.cmd_suggest_tests(files=[str(src_file)])
        assert result == 0

    def test_suggest_coverage(self, commands, temp_workspace):
        """Should show coverage map"""
        # Create source file
        (temp_workspace / "module.py").write_text("def foo(): pass")

        result = commands.cmd_suggest_coverage()
        assert result == 0


class TestArgumentParser:
    """Tests for argument parser"""

    def test_parser_creation(self):
        """Should create parser"""
        parser = create_parser()
        assert parser is not None

    def test_undo_args(self):
        """Should parse undo arguments"""
        parser = create_parser()
        args = parser.parse_args(['undo', '--batch', '3'])
        assert args.command == 'undo'
        assert args.batch == 3

    def test_undo_all_args(self):
        """Should parse undo --all"""
        parser = create_parser()
        args = parser.parse_args(['undo', '--all'])
        assert args.command == 'undo'
        assert args.all_ is True

    def test_redo_args(self):
        """Should parse redo arguments"""
        parser = create_parser()
        args = parser.parse_args(['redo', '--batch', '5'])
        assert args.command == 'redo'
        assert args.batch == 5

    def test_session_export_args(self):
        """Should parse session export arguments"""
        parser = create_parser()
        args = parser.parse_args(['session', 'export', 'output.json'])
        assert args.command == 'session'
        assert args.session_command == 'export'
        assert args.output == 'output.json'

    def test_session_import_args(self):
        """Should parse session import arguments"""
        parser = create_parser()
        args = parser.parse_args([
            'session', 'import', 'input.json', '--merge'
        ])
        assert args.command == 'session'
        assert args.session_command == 'import'
        assert args.input == 'input.json'
        assert args.merge is True

    def test_alerts_list_args(self):
        """Should parse alerts list arguments"""
        parser = create_parser()
        args = parser.parse_args([
            'alerts', 'list', '--status', 'new', '--severity', 'high'
        ])
        assert args.command == 'alerts'
        assert args.alerts_command == 'list'
        assert args.status == 'new'
        assert args.severity == 'high'

    def test_suggest_tests_args(self):
        """Should parse suggest-tests arguments"""
        parser = create_parser()
        args = parser.parse_args([
            'suggest-tests', 'file1.py', 'file2.py', '--top', '10'
        ])
        assert args.command == 'suggest-tests'
        assert args.files == ['file1.py', 'file2.py']
        assert args.top == 10

    def test_suggest_tests_from_git(self):
        """Should parse suggest-tests --from-git"""
        parser = create_parser()
        args = parser.parse_args(['suggest-tests', '--from-git'])
        assert args.from_git is True


class TestMainFunction:
    """Tests for main entry point"""

    def test_main_no_args(self):
        """Should show help with no arguments"""
        result = main([])
        assert result == 0

    def test_main_history(self):
        """Should run history command"""
        get_undo_manager(force_new=True)
        result = main(['history'])
        assert result == 0
