#!/usr/bin/env python3
"""
GrokFlow Constraint CLI
Command-line interface for constraint system management

Usage:
    grokflow-constraint list [--enabled]
    grokflow-constraint add <description> -k <keywords> [-a <action>] [-m <message>]
    grokflow-constraint add-v2 <description> [-p <patterns>] [-k <keywords>] [-l <logic>] [-c <context>] [-a <action>]
    grokflow-constraint remove <constraint_id>
    grokflow-constraint enable <constraint_id>
    grokflow-constraint disable <constraint_id>
    grokflow-constraint health [<constraint_id>]
    grokflow-constraint suggestions
    grokflow-constraint templates [--import <name>] [--export <path>]
    grokflow-constraint stats

Author: Claude Code (CLI Implementation)
Date: 2025-12-09
Version: 1.4.0 (CLI Interface)
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Import constraint system
from grokflow_constraints import ConstraintManager, ConstraintSupervisor


class ConstraintCLI:
    """Command-line interface for GrokFlow constraint system."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize CLI.

        Args:
            config_dir: Configuration directory (default: ~/.grokflow)
        """
        self.config_dir = config_dir or Path.home() / ".grokflow"
        self.manager = ConstraintManager(self.config_dir)
        self.supervisor = ConstraintSupervisor(self.config_dir)
        self.console = Console()

    def list_constraints(self, enabled_only: bool = False):
        """List all constraints."""
        constraints = self.manager.list_constraints(enabled_only=enabled_only)

        if not constraints:
            self.console.print("[yellow]No constraints found.[/yellow]")
            return

        table = Table(title=f"Constraints ({len(constraints)} total)")
        table.add_column("ID", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Keywords/Patterns", style="green")
        table.add_column("Action", style="yellow")
        table.add_column("Triggers", style="magenta")
        table.add_column("Status", style="blue")

        for c in constraints:
            cid = c.get("constraint_id", "")[:8]
            desc = c.get("description", "")[:50]

            # Get keywords or patterns
            keywords = c.get("trigger_keywords", [])
            patterns = c.get("trigger_patterns", [])
            if patterns:
                kp_text = f"Patterns: {', '.join(patterns[:2])}"
            elif keywords:
                kp_text = f"Keywords: {', '.join(keywords[:3])}"
            else:
                kp_text = "None"

            action = c.get("enforcement_action", "warn")
            triggers = str(c.get("triggered_count", 0))
            status = "✅ Enabled" if c.get("enabled", True) else "❌ Disabled"

            table.add_row(cid, desc, kp_text, action, triggers, status)

        self.console.print(table)

    def add_constraint(
        self,
        description: str,
        keywords: List[str],
        action: str = "warn",
        message: Optional[str] = None
    ):
        """Add Phase 1 constraint."""
        constraint_id = self.manager.add_constraint(
            description=description,
            trigger_keywords=keywords,
            enforcement_action=action,
            enforcement_message=message
        )

        self.console.print(Panel(
            f"[green]✅ Constraint created successfully![/green]\n\n"
            f"ID: {constraint_id}\n"
            f"Description: {description}\n"
            f"Keywords: {', '.join(keywords)}\n"
            f"Action: {action}",
            title="Constraint Added"
        ))

    def add_constraint_v2(
        self,
        description: str,
        patterns: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        logic: str = "OR",
        context: Optional[str] = None,
        action: str = "warn",
        message: Optional[str] = None
    ):
        """Add Phase 2 constraint with advanced features."""
        # Parse context JSON if provided
        context_filters = None
        if context:
            try:
                context_filters = json.loads(context)
            except json.JSONDecodeError:
                self.console.print("[red]Error: Invalid context JSON[/red]")
                return

        constraint_id = self.manager.add_constraint_v2(
            description=description,
            trigger_patterns=patterns,
            trigger_keywords=keywords,
            trigger_logic=logic,
            context_filters=context_filters,
            enforcement_action=action,
            enforcement_message=message
        )

        self.console.print(Panel(
            f"[green]✅ Advanced constraint created successfully![/green]\n\n"
            f"ID: {constraint_id}\n"
            f"Description: {description}\n"
            f"Patterns: {patterns or 'None'}\n"
            f"Keywords: {keywords or 'None'}\n"
            f"Logic: {logic}\n"
            f"Context: {context_filters or 'None'}\n"
            f"Action: {action}",
            title="Phase 2 Constraint Added"
        ))

    def remove_constraint(self, constraint_id: str):
        """Remove a constraint."""
        if self.manager.remove_constraint(constraint_id):
            self.console.print(f"[green]✅ Constraint {constraint_id} removed[/green]")
        else:
            self.console.print(f"[red]❌ Constraint {constraint_id} not found[/red]")

    def enable_constraint(self, constraint_id: str):
        """Enable a constraint."""
        if self.manager.enable_constraint(constraint_id):
            self.console.print(f"[green]✅ Constraint {constraint_id} enabled[/green]")
        else:
            self.console.print(f"[red]❌ Constraint {constraint_id} not found[/red]")

    def disable_constraint(self, constraint_id: str):
        """Disable a constraint."""
        if self.manager.disable_constraint(constraint_id):
            self.console.print(f"[yellow]⚠️  Constraint {constraint_id} disabled[/yellow]")
        else:
            self.console.print(f"[red]❌ Constraint {constraint_id} not found[/red]")

    def show_health(self, constraint_id: Optional[str] = None):
        """Show constraint health dashboard."""
        if constraint_id:
            # Show single constraint health
            health = self.supervisor.analyze_constraint_health(constraint_id)

            if health.get("status") == "no_data":
                self.console.print(f"[red]No analytics data for constraint {constraint_id}[/red]")
                return

            # Color-code status
            status_colors = {
                "healthy": "green",
                "acceptable": "yellow",
                "needs_review": "orange",
                "unhealthy": "red"
            }
            status_color = status_colors.get(health.get("status", ""), "white")

            panel_content = (
                f"[{status_color}]Status: {health.get('status', 'unknown').upper()}[/{status_color}]\n\n"
                f"Precision: {health.get('precision', 0):.3f}\n"
                f"FP Rate: {health.get('fp_rate', 0):.3f}\n"
                f"Effectiveness: {health.get('effectiveness_score', 0):.3f}\n"
                f"Drift Score: {health.get('drift_score', 0):.3f}\n\n"
                f"Total Triggers: {health.get('total_triggers', 0)}\n"
                f"True Positives: {health.get('true_positives', 0)}\n"
                f"False Positives: {health.get('false_positives', 0)}\n\n"
                f"Recommendations:\n"
            )

            for rec in health.get("recommendations", []):
                panel_content += f"  • {rec}\n"

            self.console.print(Panel(panel_content, title=f"Health: {constraint_id[:8]}"))

        else:
            # Show dashboard
            dashboard = self.supervisor.get_dashboard_data()
            overall = dashboard["overall_health"]

            # Overall health panel
            status_colors = {
                "healthy": "green",
                "acceptable": "yellow",
                "needs_attention": "red"
            }
            status_color = status_colors.get(overall.get("status", ""), "white")

            self.console.print(Panel(
                f"[{status_color}]Overall Status: {overall.get('status', 'unknown').upper()}[/{status_color}]\n"
                f"Average Precision: {overall.get('average_precision', 0):.3f}\n"
                f"Total Constraints: {overall.get('total_constraints', 0)}\n\n"
                f"✅ Healthy: {overall.get('healthy_count', 0)}\n"
                f"⚠️  Needs Review: {overall.get('needs_review_count', 0)}\n"
                f"❌ Unhealthy: {overall.get('unhealthy_count', 0)}",
                title="System Health Dashboard"
            ))

            # Show constraints by category
            if dashboard.get("needs_review"):
                table = Table(title="⚠️  Constraints Needing Review")
                table.add_column("ID", style="cyan")
                table.add_column("Precision", style="yellow")
                table.add_column("Drift", style="red")

                for c in dashboard["needs_review"]:
                    table.add_row(
                        c.get("constraint_id", "")[:8],
                        f"{c.get('precision', 0):.3f}",
                        f"{c.get('drift_score', 0):.3f}"
                    )

                self.console.print(table)

            if dashboard.get("unhealthy"):
                table = Table(title="❌ Unhealthy Constraints")
                table.add_column("ID", style="cyan")
                table.add_column("Precision", style="red")
                table.add_column("Recommendations", style="yellow")

                for c in dashboard["unhealthy"]:
                    recs = "\n".join(c.get("recommendations", [])[:2])
                    table.add_row(
                        c.get("constraint_id", "")[:8],
                        f"{c.get('precision', 0):.3f}",
                        recs
                    )

                self.console.print(table)

    def show_suggestions(self):
        """Show constraint improvement suggestions."""
        # Get all constraints with analytics
        constraints_with_analytics = []
        for c in self.manager.list_constraints():
            cid = c.get("constraint_id")
            suggestions = self.supervisor.suggest_improvements(cid)
            if suggestions:
                constraints_with_analytics.append((cid, c.get("description", ""), suggestions))

        if not constraints_with_analytics:
            self.console.print("[yellow]No improvement suggestions available.[/yellow]")
            return

        for cid, desc, suggestions in constraints_with_analytics:
            table = Table(title=f"Suggestions for {cid[:8]}: {desc[:50]}")
            table.add_column("Type", style="cyan")
            table.add_column("Suggestion", style="white")
            table.add_column("Confidence", style="green")

            for s in suggestions:
                table.add_row(
                    s.get("type", ""),
                    s.get("suggestion", "")[:80],
                    f"{s.get('confidence', 0):.2f}"
                )

            self.console.print(table)

    def show_templates(self, import_name: Optional[str] = None, export_path: Optional[str] = None):
        """Show, import, or export templates."""
        if import_name:
            # Import template
            count = self.manager.import_template(import_name)
            if count > 0:
                self.console.print(f"[green]✅ Imported {count} constraints from '{import_name}'[/green]")
            else:
                self.console.print(f"[red]❌ Template '{import_name}' not found[/red]")

        elif export_path:
            # Export constraints
            if self.manager.export_constraints(export_path):
                self.console.print(f"[green]✅ Exported constraints to '{export_path}'[/green]")
            else:
                self.console.print(f"[red]❌ Failed to export constraints[/red]")

        else:
            # List templates
            templates = self.manager.list_templates()

            if not templates:
                self.console.print("[yellow]No templates found.[/yellow]")
                return

            table = Table(title=f"Available Templates ({len(templates)} total)")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Constraints", style="green")
            table.add_column("Author", style="yellow")

            for t in templates:
                table.add_row(
                    t.get("template_name", ""),
                    t.get("description", "")[:60],
                    str(t.get("constraint_count", 0)),
                    t.get("author", "")
                )

            self.console.print(table)

    def show_stats(self):
        """Show system statistics."""
        stats = self.manager.get_stats()

        panel_content = (
            f"Total Constraints: {stats.get('total_constraints', 0)}\n"
            f"Enabled Constraints: {stats.get('enabled_constraints', 0)}\n"
            f"Total Triggers: {stats.get('total_triggers', 0)}\n\n"
        )

        most_triggered = stats.get("most_triggered")
        if most_triggered:
            panel_content += (
                f"Most Triggered Constraint:\n"
                f"  ID: {most_triggered.get('constraint_id', '')[:8]}\n"
                f"  Description: {most_triggered.get('description', '')[:50]}\n"
                f"  Triggers: {most_triggered.get('triggered_count', 0)}"
            )
        else:
            panel_content += "No constraints have been triggered yet."

        self.console.print(Panel(panel_content, title="Constraint System Statistics"))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GrokFlow Constraint System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global arguments
    parser.add_argument("--config-dir", type=str, default=None,
                       help="Configuration directory (default: ~/.grokflow)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List constraints")
    list_parser.add_argument("--enabled", action="store_true", help="Show only enabled constraints")

    # Add command (Phase 1)
    add_parser = subparsers.add_parser("add", help="Add basic constraint")
    add_parser.add_argument("description", help="Constraint description")
    add_parser.add_argument("-k", "--keywords", required=True, help="Trigger keywords (comma-separated)")
    add_parser.add_argument("-a", "--action", default="warn", choices=["warn", "block", "require_action"],
                           help="Enforcement action")
    add_parser.add_argument("-m", "--message", help="Custom enforcement message")

    # Add-v2 command (Phase 2)
    add_v2_parser = subparsers.add_parser("add-v2", help="Add advanced constraint (Phase 2)")
    add_v2_parser.add_argument("description", help="Constraint description")
    add_v2_parser.add_argument("-p", "--patterns", help="Regex patterns (comma-separated)")
    add_v2_parser.add_argument("-k", "--keywords", help="Trigger keywords (comma-separated)")
    add_v2_parser.add_argument("-l", "--logic", default="OR", choices=["OR", "AND", "NOT"],
                              help="Trigger logic")
    add_v2_parser.add_argument("-c", "--context", help="Context filters (JSON)")
    add_v2_parser.add_argument("-a", "--action", default="warn", choices=["warn", "block", "require_action"],
                              help="Enforcement action")
    add_v2_parser.add_argument("-m", "--message", help="Custom enforcement message")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove constraint")
    remove_parser.add_argument("constraint_id", help="Constraint ID (full or partial)")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable constraint")
    enable_parser.add_argument("constraint_id", help="Constraint ID (full or partial)")

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable constraint")
    disable_parser.add_argument("constraint_id", help="Constraint ID (full or partial)")

    # Health command
    health_parser = subparsers.add_parser("health", help="Show health dashboard")
    health_parser.add_argument("constraint_id", nargs="?", help="Constraint ID (optional)")

    # Suggestions command
    subparsers.add_parser("suggestions", help="Show improvement suggestions")

    # Templates command
    templates_parser = subparsers.add_parser("templates", help="Manage templates")
    templates_parser.add_argument("--import", dest="import_name", help="Import template by name")
    templates_parser.add_argument("--export", dest="export_path", help="Export constraints to file")

    # Stats command
    subparsers.add_parser("stats", help="Show system statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Use custom config directory if provided
    config_dir = Path(args.config_dir) if args.config_dir else None
    cli = ConstraintCLI(config_dir=config_dir)

    try:
        if args.command == "list":
            cli.list_constraints(enabled_only=args.enabled)

        elif args.command == "add":
            keywords = [k.strip() for k in args.keywords.split(",")]
            cli.add_constraint(args.description, keywords, args.action, args.message)

        elif args.command == "add-v2":
            patterns = [p.strip() for p in args.patterns.split(",")] if args.patterns else None
            keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
            cli.add_constraint_v2(args.description, patterns, keywords, args.logic,
                                args.context, args.action, args.message)

        elif args.command == "remove":
            cli.remove_constraint(args.constraint_id)

        elif args.command == "enable":
            cli.enable_constraint(args.constraint_id)

        elif args.command == "disable":
            cli.disable_constraint(args.constraint_id)

        elif args.command == "health":
            cli.show_health(args.constraint_id)

        elif args.command == "suggestions":
            cli.show_suggestions()

        elif args.command == "templates":
            cli.show_templates(args.import_name, args.export_path)

        elif args.command == "stats":
            cli.show_stats()

    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
