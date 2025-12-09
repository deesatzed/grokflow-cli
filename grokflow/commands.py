"""
GrokFlow CLI Commands

Command-line interface for GrokFlow operations:
- Undo/redo management (single and batch)
- Session export/import
- Pattern alerts management
- Test suggestions

Usage:
    python -m grokflow.commands undo
    python -m grokflow.commands redo --batch 3
    python -m grokflow.commands session export output.json
    python -m grokflow.commands alerts list
    python -m grokflow.commands suggest-tests src/module.py
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import Optional, List

from grokflow.logging_config import get_logger
from grokflow.cli import CLI, get_cli, Color
from grokflow.undo_manager import get_undo_manager
from grokflow.session_manager import SessionManager
from grokflow.pattern_alerts import (
    PatternAlertManager, get_alert_manager,
    AlertSeverity, AlertStatus
)
from grokflow.test_suggester import TestSuggester, get_test_suggester
from grokflow.knowledge_base import get_knowledge_base

logger = get_logger('grokflow.commands')


class GrokFlowCommands:
    """
    Command handlers for GrokFlow CLI

    Provides command implementations for:
    - Undo/redo operations
    - Session management
    - Pattern alerts
    - Test suggestions
    """

    def __init__(self, workspace: Optional[Path] = None):
        """
        Initialize command handler

        Args:
            workspace: Workspace path (defaults to current directory)
        """
        self.workspace = workspace or Path.cwd()
        self.cli = get_cli()
        self._session_manager: Optional[SessionManager] = None
        self._alert_manager: Optional[PatternAlertManager] = None
        self._test_suggester: Optional[TestSuggester] = None

    @property
    def session_manager(self) -> SessionManager:
        """Get session manager (lazy initialization)"""
        if self._session_manager is None:
            session_file = self.workspace / '.grokflow' / 'session.json'
            self._session_manager = SessionManager(session_file)
        return self._session_manager

    @property
    def alert_manager(self) -> PatternAlertManager:
        """Get alert manager (lazy initialization)"""
        if self._alert_manager is None:
            kb = get_knowledge_base()
            self._alert_manager = get_alert_manager(knowledge_base=kb, force_new=True)
        return self._alert_manager

    @property
    def test_suggester(self) -> TestSuggester:
        """Get test suggester (lazy initialization)"""
        if self._test_suggester is None:
            self._test_suggester = get_test_suggester(self.workspace, force_new=True)
        return self._test_suggester

    # ==========================================================================
    # Undo/Redo Commands
    # ==========================================================================

    def cmd_undo(self, count: int = 1, all_: bool = False) -> int:
        """
        Undo command(s)

        Args:
            count: Number of commands to undo
            all_: Undo all commands

        Returns:
            Exit code (0 = success)
        """
        undo_manager = get_undo_manager()

        if not undo_manager.can_undo():
            self.cli.warning("Nothing to undo")
            return 1

        if all_:
            undone = undo_manager.undo_all()
            self.cli.success(f"Undid all {undone} command(s)")
        elif count > 1:
            undone = undo_manager.undo_batch(count)
            self.cli.success(f"Undid {undone} of {count} requested command(s)")
        else:
            undo_manager.undo()
            self.cli.success("Undid 1 command")

        # Show remaining history
        history = undo_manager.get_history_size()
        self.cli.info(
            f"History: {history['undo_stack']} undo, {history['redo_stack']} redo"
        )
        return 0

    def cmd_redo(self, count: int = 1, all_: bool = False) -> int:
        """
        Redo command(s)

        Args:
            count: Number of commands to redo
            all_: Redo all commands

        Returns:
            Exit code (0 = success)
        """
        undo_manager = get_undo_manager()

        if not undo_manager.can_redo():
            self.cli.warning("Nothing to redo")
            return 1

        if all_:
            redone = undo_manager.redo_all()
            self.cli.success(f"Redid all {redone} command(s)")
        elif count > 1:
            redone = undo_manager.redo_batch(count)
            self.cli.success(f"Redid {redone} of {count} requested command(s)")
        else:
            undo_manager.redo()
            self.cli.success("Redid 1 command")

        # Show remaining history
        history = undo_manager.get_history_size()
        self.cli.info(
            f"History: {history['undo_stack']} undo, {history['redo_stack']} redo"
        )
        return 0

    def cmd_history(self, limit: int = 10) -> int:
        """
        Show undo/redo history

        Args:
            limit: Maximum entries to show

        Returns:
            Exit code (0 = success)
        """
        undo_manager = get_undo_manager()

        undo_history = undo_manager.get_undo_history()
        redo_history = undo_manager.get_redo_history()

        if not undo_history and not redo_history:
            self.cli.info("No history available")
            return 0

        # Show undo history
        if undo_history:
            self.cli.header("Undo Stack (oldest first)")
            for i, desc in enumerate(undo_history[-limit:], 1):
                self.cli.bullet(f"{i}. {desc}")

        # Show redo history
        if redo_history:
            self.cli.header("Redo Stack (most recent first)")
            for i, desc in enumerate(reversed(redo_history[-limit:]), 1):
                self.cli.bullet(f"{i}. {desc}")

        return 0

    # ==========================================================================
    # Session Commands
    # ==========================================================================

    def cmd_session_export(
        self,
        output_path: str,
        no_conversation: bool = False,
        no_context: bool = False
    ) -> int:
        """
        Export session to file

        Args:
            output_path: Path for export file
            no_conversation: Exclude conversation history
            no_context: Exclude context files

        Returns:
            Exit code (0 = success)
        """
        try:
            result = self.session_manager.export_session(
                Path(output_path),
                include_conversation=not no_conversation,
                include_context=not no_context
            )
            self.cli.success(f"Session exported to {result['export_path']}")
            items = result['items_exported']
            self.cli.info(
                f"Exported: {items['conversation']} conversation items, "
                f"{items['context_files']} context files"
            )
            return 0
        except Exception as e:
            self.cli.error(f"Export failed: {e}")
            logger.error(f"Session export failed: {e}", exc_info=True)
            return 1

    def cmd_session_import(
        self,
        input_path: str,
        merge: bool = False,
        workspace: Optional[str] = None
    ) -> int:
        """
        Import session from file

        Args:
            input_path: Path to import file
            merge: Merge with existing session
            workspace: Override workspace path

        Returns:
            Exit code (0 = success)
        """
        try:
            workspace_path = Path(workspace) if workspace else None
            result = self.session_manager.import_session(
                Path(input_path),
                merge=merge,
                workspace_override=workspace_path
            )
            mode = "merged" if merge else "replaced"
            self.cli.success(f"Session {mode} from {result['import_path']}")
            items = result['items_imported']
            self.cli.info(
                f"Imported: {items['conversation']} conversation items, "
                f"{items['context_files']} context files"
            )
            return 0
        except Exception as e:
            self.cli.error(f"Import failed: {e}")
            logger.error(f"Session import failed: {e}", exc_info=True)
            return 1

    def cmd_session_info(self) -> int:
        """
        Show session information

        Returns:
            Exit code (0 = success)
        """
        try:
            info = self.session_manager.get_info()
            summary = self.session_manager.get_shareable_summary()

            self.cli.header("Session Information")
            self.cli.bullet(f"File: {info['session_file']}")
            self.cli.bullet(f"Exists: {info['exists']}")

            if info['exists']:
                self.cli.bullet(f"Size: {info.get('size_kb', 0):.2f} KB")
                self.cli.bullet(f"Modified: {info.get('modified', 'N/A')}")
                self.cli.bullet(f"Context files: {summary['context_file_count']}")
                self.cli.bullet(f"Conversation length: {summary['conversation_length']}")

            return 0
        except Exception as e:
            self.cli.error(f"Failed to get session info: {e}")
            return 1

    # ==========================================================================
    # Alert Commands
    # ==========================================================================

    def cmd_alerts_list(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        active_only: bool = False
    ) -> int:
        """
        List pattern alerts

        Args:
            status: Filter by status (new, acknowledged, resolved, dismissed)
            severity: Filter by severity (info, warning, high, critical)
            active_only: Show only active alerts

        Returns:
            Exit code (0 = success)
        """
        try:
            if active_only:
                alerts = self.alert_manager.get_active_alerts()
            else:
                filter_status = AlertStatus(status) if status else None
                filter_severity = AlertSeverity(severity) if severity else None
                alerts = self.alert_manager.get_alerts(
                    status=filter_status,
                    severity=filter_severity
                )

            if not alerts:
                self.cli.info("No alerts found")
                return 0

            self.cli.header(f"Pattern Alerts ({len(alerts)} found)")

            # Display as table
            headers = ['ID', 'Severity', 'Status', 'Pattern', 'Frequency']
            rows = []
            for alert in alerts:
                rows.append([
                    alert.id[:12] + '...',
                    alert.severity.value.upper(),
                    alert.status.value,
                    alert.pattern_type[:30],
                    str(alert.frequency)
                ])

            self.cli.table(headers, rows)
            return 0

        except ValueError as e:
            self.cli.error(f"Invalid filter value: {e}")
            return 1
        except Exception as e:
            self.cli.error(f"Failed to list alerts: {e}")
            logger.error(f"Alerts list failed: {e}", exc_info=True)
            return 1

    def cmd_alerts_check(self) -> int:
        """
        Check for new pattern alerts

        Returns:
            Exit code (0 = success)
        """
        try:
            new_alerts = self.alert_manager.check_for_alerts()

            if new_alerts:
                self.cli.success(f"Found {len(new_alerts)} new alert(s)")
                for alert in new_alerts:
                    severity_color = {
                        AlertSeverity.CRITICAL: Color.RED,
                        AlertSeverity.HIGH: Color.YELLOW,
                        AlertSeverity.WARNING: Color.YELLOW,
                        AlertSeverity.INFO: Color.CYAN
                    }.get(alert.severity, Color.WHITE)

                    self.cli.print(
                        f"[{alert.severity.value.upper()}] {alert.pattern_type}",
                        color=severity_color
                    )
                    if alert.recommended_action:
                        self.cli.bullet(f"Action: {alert.recommended_action}", indent=1)
            else:
                self.cli.info("No new alerts")

            return 0
        except Exception as e:
            self.cli.error(f"Alert check failed: {e}")
            logger.error(f"Alert check failed: {e}", exc_info=True)
            return 1

    def cmd_alerts_acknowledge(self, alert_id: str) -> int:
        """
        Acknowledge an alert

        Args:
            alert_id: Alert ID to acknowledge

        Returns:
            Exit code (0 = success)
        """
        if self.alert_manager.acknowledge_alert(alert_id):
            self.cli.success(f"Alert {alert_id} acknowledged")
            return 0
        else:
            self.cli.error(f"Alert not found: {alert_id}")
            return 1

    def cmd_alerts_resolve(self, alert_id: str) -> int:
        """
        Resolve an alert

        Args:
            alert_id: Alert ID to resolve

        Returns:
            Exit code (0 = success)
        """
        if self.alert_manager.resolve_alert(alert_id):
            self.cli.success(f"Alert {alert_id} resolved")
            return 0
        else:
            self.cli.error(f"Alert not found: {alert_id}")
            return 1

    def cmd_alerts_dismiss(self, alert_id: str) -> int:
        """
        Dismiss an alert

        Args:
            alert_id: Alert ID to dismiss

        Returns:
            Exit code (0 = success)
        """
        if self.alert_manager.dismiss_alert(alert_id):
            self.cli.success(f"Alert {alert_id} dismissed")
            return 0
        else:
            self.cli.error(f"Alert not found: {alert_id}")
            return 1

    def cmd_alerts_summary(self) -> int:
        """
        Show alert summary

        Returns:
            Exit code (0 = success)
        """
        try:
            summary = self.alert_manager.get_alert_summary()

            self.cli.header("Alert Summary")
            self.cli.bullet(f"Total alerts: {summary['total_alerts']}")
            self.cli.bullet(f"Active alerts: {summary['active_alerts']}")

            self.cli.subheader("By Severity")
            for sev, count in summary['by_severity'].items():
                if count > 0:
                    self.cli.bullet(f"{sev.upper()}: {count}")

            self.cli.subheader("By Status")
            for status, count in summary['by_status'].items():
                if count > 0:
                    self.cli.bullet(f"{status}: {count}")

            return 0
        except Exception as e:
            self.cli.error(f"Failed to get summary: {e}")
            return 1

    # ==========================================================================
    # Test Suggestion Commands
    # ==========================================================================

    def cmd_suggest_tests(
        self,
        files: Optional[List[str]] = None,
        from_git: bool = False,
        top: int = 5,
        include_integration: bool = True
    ) -> int:
        """
        Suggest tests to run

        Args:
            files: Specific files to analyze
            from_git: Use git diff to find modified files
            top: Number of top suggestions to show
            include_integration: Include integration tests

        Returns:
            Exit code (0 = success)
        """
        try:
            modified_files: List[str] = []

            if from_git:
                # Get modified files from git
                modified_files = self._get_git_modified_files()
                if not modified_files:
                    self.cli.info("No modified files detected by git")
                    return 0
            elif files:
                modified_files = files
            else:
                self.cli.error("Specify files or use --from-git")
                return 1

            self.cli.info(f"Analyzing {len(modified_files)} modified file(s)")

            analysis = self.test_suggester.suggest_tests(
                modified_files,
                include_integration=include_integration
            )

            if not analysis.suggestions:
                self.cli.warning("No test suggestions found")
                return 0

            top_suggestions = analysis.get_top_suggestions(top)

            self.cli.header(f"Top {len(top_suggestions)} Test Suggestions")

            headers = ['Test File', 'Reason', 'Confidence']
            rows = []
            for suggestion in top_suggestions:
                rows.append([
                    str(suggestion.test_path.name),
                    suggestion.reason.value.replace('_', ' '),
                    f"{suggestion.confidence:.0%}"
                ])

            self.cli.table(headers, rows)

            # Show command to run suggested tests
            test_paths = [str(s.test_path) for s in top_suggestions]
            self.cli.subheader("Run with pytest:")
            self.cli.print(f"pytest {' '.join(test_paths[:3])}")

            return 0

        except Exception as e:
            self.cli.error(f"Test suggestion failed: {e}")
            logger.error(f"Test suggestion failed: {e}", exc_info=True)
            return 1

    def cmd_suggest_coverage(self) -> int:
        """
        Show test coverage map

        Returns:
            Exit code (0 = success)
        """
        try:
            coverage_map = self.test_suggester.get_test_coverage_map()

            covered = sum(1 for tests in coverage_map.values() if tests)
            total = len(coverage_map)

            self.cli.header("Test Coverage Map")
            self.cli.info(f"{covered}/{total} source files have associated tests")

            # Show untested files
            untested = self.test_suggester.find_untested_files()
            if untested:
                self.cli.subheader(f"Untested Files ({len(untested)})")
                for path in untested[:10]:
                    self.cli.bullet(str(path.relative_to(self.workspace)))
                if len(untested) > 10:
                    self.cli.info(f"... and {len(untested) - 10} more")

            return 0
        except Exception as e:
            self.cli.error(f"Coverage map failed: {e}")
            return 1

    def _get_git_modified_files(self) -> List[str]:
        """
        Get list of modified files from git

        Returns:
            List of modified file paths
        """
        try:
            # Get uncommitted changes (staged + unstaged)
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.workspace
            )

            if result.returncode != 0:
                # Try without HEAD (for new repos)
                result = subprocess.run(
                    ['git', 'diff', '--name-only'],
                    capture_output=True,
                    text=True,
                    cwd=self.workspace
                )

            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

            # Filter to Python files
            py_files = [
                str(self.workspace / f) for f in files
                if f.endswith('.py') and not f.startswith('test_')
            ]

            return py_files

        except FileNotFoundError:
            logger.warning("git not found")
            return []
        except Exception as e:
            logger.error(f"Failed to get git modified files: {e}")
            return []


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='grokflow',
        description='GrokFlow CLI - AI-powered development environment'
    )
    parser.add_argument(
        '--workspace', '-w',
        type=str,
        help='Workspace path (defaults to current directory)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ==========================================================================
    # Undo/Redo Commands
    # ==========================================================================

    # undo
    undo_parser = subparsers.add_parser('undo', help='Undo command(s)')
    undo_parser.add_argument(
        '--batch', '-b',
        type=int,
        default=1,
        metavar='N',
        help='Number of commands to undo'
    )
    undo_parser.add_argument(
        '--all', '-a',
        action='store_true',
        dest='all_',
        help='Undo all commands'
    )

    # redo
    redo_parser = subparsers.add_parser('redo', help='Redo command(s)')
    redo_parser.add_argument(
        '--batch', '-b',
        type=int,
        default=1,
        metavar='N',
        help='Number of commands to redo'
    )
    redo_parser.add_argument(
        '--all', '-a',
        action='store_true',
        dest='all_',
        help='Redo all commands'
    )

    # history
    history_parser = subparsers.add_parser('history', help='Show undo/redo history')
    history_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Maximum entries to show'
    )

    # ==========================================================================
    # Session Commands
    # ==========================================================================

    session_parser = subparsers.add_parser('session', help='Session management')
    session_subparsers = session_parser.add_subparsers(dest='session_command')

    # session export
    export_parser = session_subparsers.add_parser('export', help='Export session')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument(
        '--no-conversation',
        action='store_true',
        help='Exclude conversation history'
    )
    export_parser.add_argument(
        '--no-context',
        action='store_true',
        help='Exclude context files'
    )

    # session import
    import_parser = session_subparsers.add_parser('import', help='Import session')
    import_parser.add_argument('input', help='Input file path')
    import_parser.add_argument(
        '--merge', '-m',
        action='store_true',
        help='Merge with existing session'
    )
    import_parser.add_argument(
        '--workspace',
        type=str,
        help='Override workspace path'
    )

    # session info
    session_subparsers.add_parser('info', help='Show session information')

    # ==========================================================================
    # Alert Commands
    # ==========================================================================

    alerts_parser = subparsers.add_parser('alerts', help='Pattern alerts management')
    alerts_subparsers = alerts_parser.add_subparsers(dest='alerts_command')

    # alerts list
    list_parser = alerts_subparsers.add_parser('list', help='List alerts')
    list_parser.add_argument(
        '--status', '-s',
        choices=['new', 'acknowledged', 'in_progress', 'resolved', 'dismissed'],
        help='Filter by status'
    )
    list_parser.add_argument(
        '--severity',
        choices=['info', 'warning', 'high', 'critical'],
        help='Filter by severity'
    )
    list_parser.add_argument(
        '--active', '-a',
        action='store_true',
        help='Show only active alerts'
    )

    # alerts check
    alerts_subparsers.add_parser('check', help='Check for new alerts')

    # alerts acknowledge
    ack_parser = alerts_subparsers.add_parser('acknowledge', help='Acknowledge alert')
    ack_parser.add_argument('alert_id', help='Alert ID')

    # alerts resolve
    resolve_parser = alerts_subparsers.add_parser('resolve', help='Resolve alert')
    resolve_parser.add_argument('alert_id', help='Alert ID')

    # alerts dismiss
    dismiss_parser = alerts_subparsers.add_parser('dismiss', help='Dismiss alert')
    dismiss_parser.add_argument('alert_id', help='Alert ID')

    # alerts summary
    alerts_subparsers.add_parser('summary', help='Show alert summary')

    # ==========================================================================
    # Test Suggestion Commands
    # ==========================================================================

    suggest_parser = subparsers.add_parser('suggest-tests', help='Suggest tests to run')
    suggest_parser.add_argument(
        'files',
        nargs='*',
        help='Files to analyze'
    )
    suggest_parser.add_argument(
        '--from-git', '-g',
        action='store_true',
        help='Use git diff to find modified files'
    )
    suggest_parser.add_argument(
        '--top', '-t',
        type=int,
        default=5,
        help='Number of top suggestions'
    )
    suggest_parser.add_argument(
        '--no-integration',
        action='store_true',
        help='Exclude integration tests'
    )

    # coverage
    subparsers.add_parser('coverage', help='Show test coverage map')

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Initialize commands handler
    workspace = Path(args.workspace) if args.workspace else None
    commands = GrokFlowCommands(workspace=workspace)

    # Route to appropriate command handler
    try:
        if args.command == 'undo':
            return commands.cmd_undo(count=args.batch, all_=args.all_)

        elif args.command == 'redo':
            return commands.cmd_redo(count=args.batch, all_=args.all_)

        elif args.command == 'history':
            return commands.cmd_history(limit=args.limit)

        elif args.command == 'session':
            if args.session_command == 'export':
                return commands.cmd_session_export(
                    args.output,
                    no_conversation=args.no_conversation,
                    no_context=args.no_context
                )
            elif args.session_command == 'import':
                return commands.cmd_session_import(
                    args.input,
                    merge=args.merge,
                    workspace=args.workspace
                )
            elif args.session_command == 'info':
                return commands.cmd_session_info()
            else:
                parser.parse_args(['session', '--help'])
                return 1

        elif args.command == 'alerts':
            if args.alerts_command == 'list':
                return commands.cmd_alerts_list(
                    status=args.status,
                    severity=args.severity,
                    active_only=args.active
                )
            elif args.alerts_command == 'check':
                return commands.cmd_alerts_check()
            elif args.alerts_command == 'acknowledge':
                return commands.cmd_alerts_acknowledge(args.alert_id)
            elif args.alerts_command == 'resolve':
                return commands.cmd_alerts_resolve(args.alert_id)
            elif args.alerts_command == 'dismiss':
                return commands.cmd_alerts_dismiss(args.alert_id)
            elif args.alerts_command == 'summary':
                return commands.cmd_alerts_summary()
            else:
                parser.parse_args(['alerts', '--help'])
                return 1

        elif args.command == 'suggest-tests':
            return commands.cmd_suggest_tests(
                files=args.files if args.files else None,
                from_git=args.from_git,
                top=args.top,
                include_integration=not args.no_integration
            )

        elif args.command == 'coverage':
            return commands.cmd_suggest_coverage()

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        commands.cli.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
