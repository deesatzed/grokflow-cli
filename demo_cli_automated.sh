#!/bin/bash
#
# GrokFlow CLI - Automated Demo Script
# Non-interactive version for CI/CD and quick validation
#
# Usage: ./demo_cli_automated.sh
#

set -e  # Exit on error

DEMO_DIR=$(mktemp -d -t grokflow_demo_XXXXXX)
CLI="python3 grokflow_constraint_cli.py --config-dir $DEMO_DIR"

echo "================================================================================"
echo "  GrokFlow CLI - Automated Demo"
echo "================================================================================"
echo ""
echo "Demo directory: $DEMO_DIR"
echo ""

# Section 1: Basic Operations
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SECTION 1: Basic Constraint Operations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ List constraints (empty)..."
$CLI list
echo ""

echo "→ Add constraint: Block mock data..."
$CLI add "Never use mock data" -k "mock,demo,fake" -a block -m "Use real data only!"
echo ""

echo "→ Add constraint: Warn about outdated models..."
$CLI add "Search for latest models" -k "gpt-3,claude-2" -a warn
echo ""

echo "→ List all constraints..."
$CLI list
echo ""

# Section 2: Advanced Constraints
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SECTION 2: Advanced Constraints (Phase 2)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ Add advanced constraint with regex patterns..."
$CLI add-v2 "Block placeholders" \
  -p "placeholder.*,todo.*,fixme.*" \
  -l OR \
  -c '{"query_type":["generate"]}' \
  -a warn
echo ""

echo "→ Add constraint with AND logic..."
$CLI add-v2 "Confirm database deletion" \
  -k "database,delete" \
  -l AND \
  -a require_action \
  -m "DANGER: Confirm database deletion!"
echo ""

# Section 3: Templates
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SECTION 3: Template Management"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ List available templates..."
$CLI templates
echo ""

echo "→ Import security-awareness template..."
$CLI templates --import security-awareness
echo ""

echo "→ List constraints after import..."
$CLI list
echo ""

# Section 4: Health & Analytics
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SECTION 4: Health Monitoring & Analytics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ View system statistics..."
$CLI stats
echo ""

echo "→ View health dashboard..."
$CLI health
echo ""

echo "→ Get improvement suggestions..."
$CLI suggestions
echo ""

# Section 5: Export
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SECTION 5: Export & Sharing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ Export constraints as template..."
EXPORT_PATH="$DEMO_DIR/team-constraints.json"
$CLI templates --export "$EXPORT_PATH"
echo ""

if [ -f "$EXPORT_PATH" ]; then
    echo "✓ Template exported successfully"
    echo ""
    echo "First 20 lines of exported template:"
    echo "────────────────────────────────────────────────────────────────────────────────"
    head -20 "$EXPORT_PATH"
    echo "────────────────────────────────────────────────────────────────────────────────"
fi
echo ""

# Final Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Demo Complete - Final Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

$CLI stats
echo ""

echo "✅ Demo completed successfully!"
echo ""
echo "📚 Features Demonstrated:"
echo "  • Basic constraints (keyword-based)"
echo "  • Advanced constraints (regex, context, AND/OR logic)"
echo "  • Template import/export"
echo "  • Health monitoring and analytics"
echo "  • System statistics"
echo ""
echo "🧹 Cleaning up demo directory..."
rm -rf "$DEMO_DIR"
echo "✓ Removed: $DEMO_DIR"
echo ""
echo "================================================================================"
