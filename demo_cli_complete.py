#!/usr/bin/env python3
"""
GrokFlow CLI - Complete Interactive Demo

Demonstrates all CLI features with realistic scenarios:
- Basic and advanced constraint creation
- Health monitoring and analytics
- Template management
- Constraint refinement workflow

Version: 1.4.0
"""

import subprocess
import time
import tempfile
import shutil
from pathlib import Path
import re

class CLIDemo:
    """Interactive CLI demonstration."""

    def __init__(self):
        self.cli_path = Path(__file__).parent / "grokflow_constraint_cli.py"
        self.demo_dir = Path(tempfile.mkdtemp(prefix="grokflow_cli_demo_"))
        self.step_number = 0

    def print_header(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80 + "\n")

    def print_step(self, description):
        """Print step description."""
        self.step_number += 1
        print(f"\n{'─'*80}")
        print(f"Step {self.step_number}: {description}")
        print(f"{'─'*80}\n")

    def run_cli(self, args, show_command=True):
        """Run CLI command and display output."""
        cmd = ["python3", str(self.cli_path), "--config-dir", str(self.demo_dir)] + args

        if show_command:
            cmd_str = "grokflow-constraint " + " ".join(args)
            print(f"💻 Command: {cmd_str}\n")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout)

        if result.returncode != 0 and result.stderr:
            print(f"⚠️  Error: {result.stderr}")

        return result.stdout, result.returncode

    def pause(self, message="Press Enter to continue..."):
        """Pause for user interaction."""
        input(f"\n{message}")

    def extract_constraint_id(self, output):
        """Extract constraint ID from CLI output."""
        match = re.search(r'ID:\s*([a-f0-9]{8})', output)
        if match:
            return match.group(1)
        return None

    def cleanup(self):
        """Clean up demo directory."""
        if self.demo_dir.exists():
            shutil.rmtree(self.demo_dir)

    def run_demo(self):
        """Run complete CLI demonstration."""
        try:
            self.print_header("GrokFlow CLI - Interactive Demo")
            print("This demo shows all CLI features with realistic scenarios.")
            print(f"Demo directory: {self.demo_dir}")
            self.pause()

            # ========== SECTION 1: BASIC OPERATIONS ==========
            self.print_header("SECTION 1: Basic Constraint Operations")

            self.print_step("List constraints (empty system)")
            self.run_cli(["list"])
            self.pause()

            self.print_step("Add basic constraint: Block mock data")
            output, _ = self.run_cli([
                "add", "Never use mock data in production",
                "-k", "mock,demo,fake,placeholder",
                "-a", "block",
                "-m", "Use real data and APIs only!"
            ])
            mock_constraint_id = self.extract_constraint_id(output)
            self.pause()

            self.print_step("Add another constraint: Warn about outdated models")
            self.run_cli([
                "add", "Search for latest AI models",
                "-k", "gpt-3,gpt-4,claude-2",
                "-a", "warn",
                "-m", "Check for latest model versions!"
            ])
            self.pause()

            self.print_step("List all constraints")
            self.run_cli(["list"])
            self.pause()

            # ========== SECTION 2: ADVANCED CONSTRAINTS ==========
            self.print_header("SECTION 2: Advanced Constraints (Phase 2)")

            self.print_step("Add advanced constraint with regex patterns")
            output, _ = self.run_cli([
                "add-v2", "Block placeholder patterns in code generation",
                "-p", "placeholder.*,todo.*,fixme.*,xxx",
                "-l", "OR",
                "-c", '{"query_type":["generate"]}',
                "-a", "warn",
                "-m", "Avoid placeholder code - implement fully"
            ])
            placeholder_constraint_id = self.extract_constraint_id(output)
            self.pause()

            self.print_step("Add constraint with AND logic")
            self.run_cli([
                "add-v2", "Require confirmation for database deletion",
                "-k", "database,delete",
                "-l", "AND",
                "-a", "require_action",
                "-m", "DANGER: Confirm database deletion!"
            ])
            self.pause()

            self.print_step("List all constraints (basic + advanced)")
            self.run_cli(["list"])
            self.pause()

            # ========== SECTION 3: TEMPLATES ==========
            self.print_header("SECTION 3: Template Management")

            self.print_step("List available templates")
            self.run_cli(["templates"])
            self.pause()

            self.print_step("Import 'security-awareness' template")
            self.run_cli(["templates", "--import", "security-awareness"])
            self.pause()

            self.print_step("List constraints after template import")
            self.run_cli(["list"])
            self.pause()

            # ========== SECTION 4: HEALTH & ANALYTICS ==========
            self.print_header("SECTION 4: Health Monitoring & Analytics")

            self.print_step("View system statistics")
            self.run_cli(["stats"])
            self.pause()

            self.print_step("View health dashboard")
            self.run_cli(["health"])
            self.pause()

            if mock_constraint_id:
                self.print_step(f"View specific constraint health: {mock_constraint_id}")
                self.run_cli(["health", mock_constraint_id])
                self.pause()

            self.print_step("Get improvement suggestions")
            self.run_cli(["suggestions"])
            self.pause()

            # ========== SECTION 5: CONSTRAINT MANAGEMENT ==========
            self.print_header("SECTION 5: Constraint Management")

            if placeholder_constraint_id:
                self.print_step(f"Disable constraint: {placeholder_constraint_id}")
                self.run_cli(["disable", placeholder_constraint_id])
                self.pause()

                self.print_step("List enabled constraints only")
                self.run_cli(["list", "--enabled"])
                self.pause()

                self.print_step(f"Re-enable constraint: {placeholder_constraint_id}")
                self.run_cli(["enable", placeholder_constraint_id])
                self.pause()

            # ========== SECTION 6: REALISTIC WORKFLOW ==========
            self.print_header("SECTION 6: Realistic Team Workflow")

            self.print_step("Scenario: New team member joins")
            print("New developer needs constraints for Python best practices.\n")
            self.pause("Press Enter to import template...")

            self.run_cli(["templates", "--import", "best-practices-python"])
            self.pause()

            self.print_step("Scenario: Weekly health review")
            print("Team reviews constraint effectiveness every Monday.\n")
            self.pause("Press Enter to check health...")

            self.run_cli(["health"])
            self.pause()

            self.print_step("Scenario: Refine constraint after false positives")
            print("Team notices false positives and adjusts constraint.\n")
            print("(In production, you'd remove the old constraint and add a refined one)")
            self.pause()

            # ========== SECTION 7: EXPORT & SHARING ==========
            self.print_header("SECTION 7: Export & Team Sharing")

            self.print_step("Export constraints as custom template")
            export_path = self.demo_dir / "team-constraints.json"
            self.run_cli(["templates", "--export", str(export_path)])

            if export_path.exists():
                print(f"\n✅ Template exported to: {export_path}")
                print("\nTemplate contents (first 20 lines):")
                print("─" * 80)
                with open(export_path, 'r') as f:
                    for i, line in enumerate(f):
                        if i >= 20:
                            print("... (truncated)")
                            break
                        print(line.rstrip())
                print("─" * 80)

            self.pause()

            # ========== FINAL SUMMARY ==========
            self.print_header("Demo Complete - Summary")

            self.run_cli(["stats"])

            print("\n📚 What We Demonstrated:")
            print("  ✅ Basic constraints (keyword-based)")
            print("  ✅ Advanced constraints (regex, context, AND/OR logic)")
            print("  ✅ Template import/export")
            print("  ✅ Health monitoring and analytics")
            print("  ✅ Constraint enable/disable")
            print("  ✅ Improvement suggestions")
            print("  ✅ Realistic team workflows")
            print()
            print("🎯 Key Benefits:")
            print("  • No Python knowledge required")
            print("  • Beautiful terminal output (Rich library)")
            print("  • Easy team collaboration")
            print("  • Fast iteration on constraints")
            print("  • Production-ready with health monitoring")
            print()
            print("📖 For full documentation, see: CLI_USAGE_GUIDE.md")
            print()

        finally:
            print("\n" + "="*80)
            print("Cleaning up demo directory...")
            self.cleanup()
            print(f"✓ Removed: {self.demo_dir}")
            print("="*80 + "\n")


def main():
    """Main entry point."""
    demo = CLIDemo()

    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                    GrokFlow CLI - Complete Demo                           ║
║                                                                            ║
║  This interactive demo will show you all CLI features with realistic      ║
║  scenarios. The demo uses a temporary directory and cleans up after.      ║
║                                                                            ║
║  Duration: ~5-10 minutes (depending on your pace)                         ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)

    try:
        input("Press Enter to start the demo...")
        demo.run_demo()
        print("✅ Demo completed successfully!\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user.")
        demo.cleanup()
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        demo.cleanup()
        raise


if __name__ == "__main__":
    main()
