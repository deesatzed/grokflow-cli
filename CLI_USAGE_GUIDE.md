# GrokFlow Constraint CLI - Usage Guide

**Version**: 1.4.0
**Date**: 2025-12-09
**Status**: Production Ready

---

## Quick Start (60 seconds)

```bash
# 1. List all constraints
python3 grokflow_constraint_cli.py list

# 2. Add a basic constraint
python3 grokflow_constraint_cli.py add "Never use mock data" -k "mock,demo,fake" -a block

# 3. View system health
python3 grokflow_constraint_cli.py health

# 4. Show statistics
python3 grokflow_constraint_cli.py stats
```

---

## Installation

### Method 1: Add to PATH (Recommended)

```bash
# Create symlink in your PATH
sudo ln -s /path/to/grokflow_constraint_cli.py /usr/local/bin/grokflow-constraint

# Now use from anywhere
grokflow-constraint list
grokflow-constraint health
```

### Method 2: Direct Execution

```bash
# Make executable
chmod +x grokflow_constraint_cli.py

# Run with full path
python3 /path/to/grokflow_constraint_cli.py list
```

---

## All Commands

### 1. `list` - List Constraints

**Show all constraints:**
```bash
grokflow-constraint list
```

**Show only enabled constraints:**
```bash
grokflow-constraint list --enabled
```

**Example Output:**
```
                             Constraints (5 total)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID       ┃ Description           ┃ Keywords/Patt ┃ Action ┃ Triggers ┃ Status     ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━┩
│ fca454b5 │ Never use mock data   │ Keywords: mo… │ block  │ 12       │ ✅ Enabled │
│ a0963a32 │ Block placeholders    │ Patterns: pl… │ warn   │ 5        │ ✅ Enabled │
└──────────┴───────────────────────┴───────────────┴────────┴──────────┴────────────┘
```

---

### 2. `add` - Add Basic Constraint (Phase 1)

**Simple keyword-based constraint:**

```bash
grokflow-constraint add "Never use mock data" \
  -k "mock,demo,fake" \
  -a block \
  -m "Use real data and APIs only!"
```

**Parameters:**
- `description` - Human-readable description (required)
- `-k, --keywords` - Comma-separated trigger keywords (required)
- `-a, --action` - Enforcement action: `warn`, `block`, `require_action` (default: `warn`)
- `-m, --message` - Custom enforcement message (optional)

**Examples:**

```bash
# Block mock data usage
grokflow-constraint add "No mock data" -k "mock,demo" -a block

# Warn about outdated models
grokflow-constraint add "Search for latest AI models" \
  -k "gpt,llm,model" \
  -a warn

# Require confirmation for destructive actions
grokflow-constraint add "Confirm deletions" \
  -k "delete,remove,drop" \
  -a require_action \
  -m "DANGER: This will delete data!"
```

---

### 3. `add-v2` - Add Advanced Constraint (Phase 2)

**Regex patterns, AND/OR/NOT logic, context-aware:**

```bash
grokflow-constraint add-v2 "Block placeholders in code generation" \
  -p "placeholder.*,todo.*,fixme.*" \
  -l OR \
  -c '{"query_type":["generate"]}' \
  -a warn
```

**Parameters:**
- `description` - Human-readable description (required)
- `-p, --patterns` - Comma-separated regex patterns (optional)
- `-k, --keywords` - Comma-separated keywords (optional)
- `-l, --logic` - Trigger logic: `OR`, `AND`, `NOT` (default: `OR`)
- `-c, --context` - Context filters as JSON (optional)
- `-a, --action` - Enforcement action (default: `warn`)
- `-m, --message` - Custom message (optional)

**Examples:**

```bash
# Regex pattern matching
grokflow-constraint add-v2 "No mock patterns" \
  -p "mock.*,demo.*" \
  -a block

# AND logic (all keywords must match)
grokflow-constraint add-v2 "Database deletion safety" \
  -k "database,delete" \
  -l AND \
  -a require_action

# Context-aware (only trigger in generate mode)
grokflow-constraint add-v2 "No placeholders in code" \
  -p "placeholder.*" \
  -c '{"query_type":["generate"]}' \
  -a warn

# NOT logic (none should match)
grokflow-constraint add-v2 "Ensure production ready" \
  -k "test,mock,debug" \
  -l NOT \
  -a block

# Hardcoded credentials (regex)
grokflow-constraint add-v2 "No hardcoded credentials" \
  -p "password\s*=\s*['\"],api_key\s*=\s*['\"]" \
  -a block \
  -m "Use environment variables for credentials"
```

---

### 4. `remove` - Remove Constraint

```bash
# Remove by ID (full or partial, min 4 chars)
grokflow-constraint remove fca454b5
grokflow-constraint remove fca4
```

---

### 5. `enable` - Enable Constraint

```bash
grokflow-constraint enable fca454b5
```

---

### 6. `disable` - Disable Constraint

```bash
# Temporarily disable without deleting
grokflow-constraint disable fca454b5
```

---

### 7. `health` - Health Dashboard

**Show overall system health:**
```bash
grokflow-constraint health
```

**Example Output:**
```
╭────────────────────────── System Health Dashboard ───────────────────────────╮
│ Overall Status: ACCEPTABLE                                                   │
│ Average Precision: 0.634                                                     │
│ Total Constraints: 6                                                         │
│                                                                              │
│ ✅ Healthy: 2                                                                │
│ ⚠️  Needs Review: 3                                                           │
│ ❌ Unhealthy: 1                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

                          ⚠️  Constraints Needing Review
┏━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┓
┃ ID       ┃ Precision ┃ Drift ┃
┡━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━┩
│ fca454b5 │ 0.600     │ 0.000 │
│ a0963a32 │ 0.667     │ 0.000 │
└──────────┴───────────┴───────┘
```

**Show specific constraint health:**
```bash
grokflow-constraint health fca454b5
```

**Example Output:**
```
╭─────────────────────────── Health: fca454b5 ──────────────────────────────╮
│ Status: NEEDS_REVIEW                                                       │
│                                                                            │
│ Precision: 0.600                                                           │
│ FP Rate: 0.400                                                             │
│ Effectiveness: 0.030                                                       │
│ Drift Score: 0.000                                                         │
│                                                                            │
│ Total Triggers: 5                                                          │
│ True Positives: 3                                                          │
│ False Positives: 2                                                         │
│                                                                            │
│ Recommendations:                                                           │
│   • Low precision - Consider narrowing trigger patterns or adding context  │
│   • High false positive rate - Review recent false positives               │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

### 8. `suggestions` - Improvement Suggestions

**Get AI-powered suggestions to improve constraints:**

```bash
grokflow-constraint suggestions
```

**Example Output:**
```
                    Suggestions for fca454b5: Never use mock data
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Type             ┃ Suggestion                                     ┃ Confidence ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ narrow_pattern   │ Consider narrowing to r'\bmock\b' (word bound… │ 0.75       │
│ add_context_filt │ Consider restricting to 'generate' mode only   │ 0.65       │
└──────────────────┴────────────────────────────────────────────────┴────────────┘
```

---

### 9. `templates` - Manage Templates

**List available templates:**
```bash
grokflow-constraint templates
```

**Example Output:**
```
                         Available Templates (4 total)
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Name                  ┃ Description            ┃ Constraints ┃ Author        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ no-mock-data          │ Block all mock, demo,  │ 2           │ GrokFlow Team │
│ best-practices-python │ Python coding best pr… │ 2           │ GrokFlow Team │
│ security-awareness    │ Security-sensitive pa… │ 2           │ GrokFlow Team │
│ destructive-actions   │ Require confirmation … │ 2           │ GrokFlow Team │
└───────────────────────┴────────────────────────┴─────────────┴───────────────┘
```

**Import template:**
```bash
grokflow-constraint templates --import no-mock-data
# ✅ Imported 2 constraints from 'no-mock-data'
```

**Export constraints to template:**
```bash
grokflow-constraint templates --export my-team-rules.json
# ✅ Exported constraints to 'my-team-rules.json'
```

---

### 10. `stats` - System Statistics

```bash
grokflow-constraint stats
```

**Example Output:**
```
╭──────────────────────── Constraint System Statistics ────────────────────────╮
│ Total Constraints: 5                                                         │
│ Enabled Constraints: 4                                                       │
│ Total Triggers: 42                                                           │
│                                                                              │
│ Most Triggered Constraint:                                                   │
│   ID: fca454b5                                                               │
│   Description: Never use mock data                                           │
│   Triggers: 25                                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## Common Workflows

### Workflow 1: Team Setup (First Time)

```bash
# 1. Import team rules template
grokflow-constraint templates --import no-mock-data

# 2. Add custom constraints
grokflow-constraint add "Use TypeScript strict mode" \
  -k "typescript,noImplicitAny:false" \
  -a warn

# 3. Verify constraints
grokflow-constraint list

# 4. Export for team sharing
grokflow-constraint templates --export team-rules-v1.json
```

### Workflow 2: Monitor Health (Weekly)

```bash
# 1. Check overall health
grokflow-constraint health

# 2. Get improvement suggestions
grokflow-constraint suggestions

# 3. Review unhealthy constraints
grokflow-constraint health <constraint_id>

# 4. Disable low-performing constraints
grokflow-constraint disable <constraint_id>
```

### Workflow 3: Add Security Constraints

```bash
# Import security template
grokflow-constraint templates --import security-awareness

# Add custom security rules
grokflow-constraint add-v2 "No eval usage" \
  -p "eval\s*\(" \
  -a block \
  -m "Never use eval() - security risk!"

grokflow-constraint add-v2 "Require HTTPS" \
  -p "http://[^s]" \
  -a warn \
  -m "Use HTTPS instead of HTTP"
```

### Workflow 4: Manage False Positives

```bash
# 1. Check constraint health
grokflow-constraint health fca454b5

# 2. If high false positive rate, get suggestions
grokflow-constraint suggestions

# 3. Narrow the pattern based on suggestions
grokflow-constraint add-v2 "Improved mock constraint" \
  -p "\\bmock\\b" \
  -c '{"query_type":["generate"]}' \
  -a block

# 4. Disable old constraint
grokflow-constraint disable fca454b5
```

---

## Built-in Templates

### 1. `no-mock-data` (2 constraints)
- Block mock, demo, placeholder, fake data usage
- Warn about dummy/sample data

### 2. `best-practices-python` (2 constraints)
- Warn about global variables
- Encourage type hints in function signatures

### 3. `security-awareness` (2 constraints)
- Block hardcoded credentials (password, api_key, secret)
- Warn about SQL string concatenation

### 4. `destructive-actions` (2 constraints)
- Require confirmation for database deletions
- Require confirmation for file system deletions

---

## Advanced Usage

### Regex Pattern Tips

```bash
# Word boundary (exact match)
-p "\\bmock\\b"  # Matches "mock" but not "mocking"

# Multiple patterns (OR logic)
-p "mock.*,demo.*,fake.*"

# Case-sensitive pattern
-p "TODO"  # Note: All patterns are case-insensitive by default

# Complex patterns
-p "password\s*=\s*['\"][^'\"]*['\"]"  # Hardcoded password detection
```

### Context Filter Examples

```bash
# Only in generate mode
-c '{"query_type":["generate"]}'

# Only in focused vibe
-c '{"vibe_mode":["focused"]}'

# Multiple contexts (AND logic)
-c '{"query_type":["generate"],"vibe_mode":["focused"]}'
```

### AND/OR/NOT Logic

```bash
# OR (any match) - default
grokflow-constraint add-v2 "Avoid test keywords" \
  -k "test,mock,debug" \
  -l OR

# AND (all must match)
grokflow-constraint add-v2 "Database deletion safety" \
  -k "database,delete" \
  -l AND

# NOT (none should match)
grokflow-constraint add-v2 "Production ready" \
  -k "test,debug,mock" \
  -l NOT
```

---

## Troubleshooting

### Issue: Constraint not triggering

**Solution**:
```bash
# 1. Check if enabled
grokflow-constraint list

# 2. Verify keywords/patterns
grokflow-constraint list  # Look at Keywords/Patterns column

# 3. Check context filters (might be too restrictive)
grokflow-constraint list  # Review constraint details
```

### Issue: Too many false positives

**Solution**:
```bash
# 1. Check health
grokflow-constraint health <constraint_id>

# 2. Get suggestions
grokflow-constraint suggestions

# 3. Narrow pattern or add context filter
grokflow-constraint add-v2 "Narrowed constraint" \
  -p "\\bmock\\b" \
  -c '{"query_type":["generate"]}'

# 4. Disable old constraint
grokflow-constraint disable <old_id>
```

### Issue: Can't find constraint ID

**Solution**:
```bash
# List all constraints and copy the ID
grokflow-constraint list

# Use partial ID (min 4 chars)
grokflow-constraint remove fca4  # Instead of full fca454b5
```

---

## Performance

- **List command**: <5ms (all constraints)
- **Health dashboard**: <20ms (all constraints with analytics)
- **Add constraint**: <10ms (including index rebuild)
- **Suggestions**: <50ms (per constraint)

---

## Integration with GrokFlow

```python
# Pre-generation hook
from grokflow_constraints import ConstraintManager

manager = ConstraintManager(Path("~/.grokflow"))

# Before generating code
query = "Create mock API endpoint"
triggered = manager.check_constraints_v2(query, {"query_type": "generate"})

if any(c["enforcement_action"] == "block" for c in triggered):
    print("❌ Generation blocked by constraint")
    for c in triggered:
        print(f"  {c['enforcement_message']}")
    return

# Generate code...
```

---

## What's Next?

### Short-Term (1-2 Months)
- Anonymous telemetry for constraint effectiveness
- Machine learning-based pattern suggestions
- Visual health dashboard (web interface)

### Long-Term (3-6 Months)
- Team collaboration features
- Constraint marketplace (share templates publicly)
- IDE integration (VSCode extension)

---

## Help & Support

```bash
# Get help for any command
grokflow-constraint --help
grokflow-constraint add --help
grokflow-constraint add-v2 --help
```

**File Issues**: https://github.com/yourusername/grokflow-cli/issues

---

**Built with ❤️ by the GrokFlow Team**
**Version**: 1.4.0 | **Date**: 2025-12-09
