# 🚀 GrokFlow - Quick Start Guide

## Installation

```bash
cd grokflow-cli
pip install -r requirements.txt
export XAI_API_KEY="your_xai_api_key"
```

## Basic Usage

### Interactive Mode (Recommended)
```bash
./grokflow_v2.py
```

### Quick Commands
```bash
# Fix errors (auto-detects context)
./grokflow_v2.py fix

# Run tests
./grokflow_v2.py test

# Smart commit
./grokflow_v2.py commit

# Check versions and health
./grokflow_v2.py status

# Undo last edit (or specific file)
./grokflow_v2.py undo [file]

# Show undo history
./grokflow_v2.py history

# Universal knowledge (stats, patterns, search)
./grokflow_v2.py knowledge stats
./grokflow_v2.py knowledge patterns
./grokflow_v2.py knowledge search "AttributeError: 'NoneType'"
```

## Key Features

### 1. Smart Fix
Automatically detects and fixes errors:
- Captures last error
- Checks for recurring patterns
- Applies known solutions
- Suggests permanent fixes

### 2. Learning System
Never solve the same problem twice:
- Tracks all errors
- Records successful fixes
- Shares knowledge across projects
- Gets smarter over time

### 3. Version Intelligence
Prevents issues before they happen:
- Checks Python version
- Monitors package versions
- Detects AI model staleness
- Warns about deprecated patterns

### 4. Context Awareness
Understands your workspace:
- Git integration
- Modified file detection
- Recent changes tracking
- Smart defaults

## Example Workflow

```bash
# 1. Start working
cd my-project
./grokflow_v2.py

# 2. Fix an error
> fix
🔎 Found 3 similar past issues in universal knowledge
💡 Suggested known fix (95% success rate)
✓ Applied fix

# 3. Run tests
> test
✓ All tests passed

# 4. Commit
> commit
🧠 Generated: "fix: add null check to user validation"
✓ Committed

# 5. Check health
> status
📁 Workspace: my-project
🌿 Git: ✓
⚠️ 2 warnings (run 'check' for details)
```

### End-to-End Fix + Learn Flow

1. Trigger or reproduce a failing test in your project.
2. Run `./grokflow_v2.py test` to capture the failure and record it in the universal knowledge base.
3. Run `./grokflow_v2.py fix` to:
   - See similar past issues from universal knowledge.
   - Watch Grok-4's reasoning process in real-time (displayed in cyan).
   - Get a Grok-4 fix proposal and optional diff to apply.
4. Re-run your tests, then answer the success/failure prompts so GUKS can learn which fixes worked.
5. Inspect what was learned with:
   - `./grokflow_v2.py knowledge stats`
   - `./grokflow_v2.py knowledge patterns`
   - `./grokflow_v2.py knowledge search "<error text>"`

For a ready-made example of this flow, see the `guks_demo/` project and the `GUKS_SMART_FIX_BLOG.md` page in this repo.

### Reasoning Display (NEW!)

When Grok-4 analyzes your code, you'll see its thought process in real-time:
- **Reasoning** (cyan, dim): AI's internal analysis and planning
- **Response** (white): Final fix proposal and explanation

This transparency helps you:
- Understand why the AI chose a particular fix
- Build trust in AI suggestions
- Learn debugging patterns from AI's reasoning
- Identify when AI might be on the wrong track

### Enhanced CLI with Tab Completion (NEW!)

GrokFlow v2 features an intelligent command-line interface with:
- **Tab Completion**: Auto-complete commands and file paths
- **Command History**: Navigate with ↑/↓ arrows
- **History Search**: Press Ctrl+R to search past commands
- **Auto-Suggest**: Ghost text from command history
- **Smart Completion**: Context-aware suggestions

**Try it:**
```bash
./grokflow_v2.py

> fi<Tab>          # Completes to "fix"
> fix bug<Tab>     # Completes to "fix buggy_module.py"
> <↑>              # Recalls previous command
> <Ctrl+R>test     # Searches history for "test"
```

**Keyboard Shortcuts:**
- `Tab` - Auto-complete
- `↑ / ↓` - Navigate history
- `Ctrl+R` - Search history
- `Ctrl+C` - Cancel input
- `Ctrl+D` - Exit

### Dual-Model Architecture (NEW!)

GrokFlow v2 uses a two-phase approach for optimal performance:
1. **Planner Model** (`grok-beta`): Analyzes issues and creates detailed fix plans with reasoning
2. **Executor Model** (`grok-4-fast`): Generates code based on the plan (optimized for speed)

**Benefits:**
- **Faster execution**: grok-4-fast is optimized for speed and efficiency
- **Cost reduction**: Lower API costs with grok-4-fast vs grok-beta
- **Better quality**: Planner focuses on analysis, executor on generation
- **Separation of concerns**: Planning vs. execution

**Performance Tracking:**
```bash
# View performance metrics
./grokflow_v2.py

> perf
┌──────────────────────────────────────────┐
│ Dual-Model Performance Metrics           │
├────────────────────┬─────────────────────┤
│ Planner Calls      │ 5                   │
│ Executor Calls     │ 5                   │
│ Planner Time       │ 12.3s               │
│ Executor Time      │ 8.7s                │
│ Total Time         │ 21.0s               │
│ Avg Plan Time      │ 2.5s                │
│ Avg Execute Time   │ 1.7s                │
└────────────────────┴─────────────────────┘
```

**✨ Active Now**: Dual-model is live! Using `grok-beta` for planning and `grok-4-fast` for execution.

### Binary File Detection (NEW!)

GrokFlow automatically detects and skips binary files:
- **Auto-detection**: Checks file content before analysis
- **Helpful messages**: Clear feedback when binary files are encountered
- **Prevents errors**: No crashes on images, compiled code, etc.

**Examples:**
```bash
./grokflow_v2.py fix image.png
⚠ Skipping binary file: image.png
Binary files (images, compiled code, etc.) cannot be analyzed

./grokflow_v2.py fix
Detected modified file: app.pyc
⚠ Skipping binary file: app.pyc
Specify a text file to analyze
```

### Directory Recursive Add (NEW!)

Quickly add entire directories to context for comprehensive analysis:
```bash
# Add a directory (auto-filters by file type)
./grokflow_v2.py add src/

# Or in interactive mode
> add src/

📂 Scanning directory: src/

✓ Added 15 files to context
Skipped 3 binary files
Skipped 47 excluded/non-matching files

Sample files added:
  • main.py
  • utils.py
  • config.py
  • models.py
  • handlers.py
  ... and 10 more

Use 'context' command to see all loaded files
```

**Smart Filtering**:
- **Auto-includes**: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.cpp`, `.go`, `.rs`, `.md`, `.json`, `.yaml`, etc.
- **Auto-excludes**: `__pycache__`, `.git`, `node_modules`, `.venv`, binary files, compiled code
- **Binary detection**: Automatically skips images, executables, etc.
- **Duplicate prevention**: Won't add files already in context

**Benefits**:
- **Fast context loading**: Add entire codebases in one command
- **Smart defaults**: Sensible include/exclude patterns
- **No manual file selection**: Just point at a directory
- **Safe**: Won't crash on binary files or large directories

### Image Analysis with Vision AI (NEW!)

Analyze screenshots, UI mockups, and visual bugs using grok-4-fast vision:
```bash
# Analyze a screenshot
./grokflow_v2.py image screenshot.png

📸 Analyzing image: screenshot.png
Using grok-4-fast vision model...

┌──────────────────────────────────────────┐
│ Image Analysis: screenshot.png           │
├──────────────────────────────────────────┤
│ ## Layout Analysis                       │
│                                          │
│ The screenshot shows a web application  │
│ with a navigation bar at the top...     │
│                                          │
│ ## Visual Issues Detected                │
│ 1. Button alignment is off by 2px       │
│ 2. Color contrast ratio is 3.5:1        │
│    (should be 4.5:1 for WCAG AA)        │
│                                          │
│ ## Suggestions                           │
│ - Adjust button padding to 12px         │
│ - Increase text color to #333333        │
│ - Add focus indicators for keyboard nav │
└──────────────────────────────────────────┘

# Custom prompt for specific analysis
./grokflow_v2.py image ui_mockup.png "Check if this follows our design system"

# In interactive mode
> image error_screenshot.png "What's causing this visual bug?"
```

**Supported Formats**:
- **Image types**: JPG, JPEG, PNG
- **Max size**: 20MB per image
- **Resolution**: Any (automatically handled)

**Use Cases**:
- **UI debugging**: Find visual bugs and layout issues
- **Design review**: Check mockups against design system
- **Accessibility**: Identify contrast and usability issues
- **Error screenshots**: Analyze error states and edge cases
- **Documentation**: Review diagrams and flowcharts

**Benefits**:
- **Visual debugging**: No more describing screenshots in text
- **Fast feedback**: Instant analysis of UI issues
- **Accessibility checks**: Automatic WCAG compliance review
- **Design validation**: Compare against design system
- **Session memory**: Analysis saved for context

### File Templates (NEW!)

Create new files quickly with built-in templates:
```bash
# List available templates
./grokflow_v2.py templates

┌──────────────────────────────────────────┐
│ Available File Templates                 │
├───────────────┬──────────────┬───────────┤
│ Template      │ Description  │ Example   │
├───────────────┼──────────────┼───────────┤
│ python        │ Python script│ new python│
│ python-class  │ Python class │ new python│
│ python-test   │ Python test  │ new python│
│ javascript    │ JS module    │ new javasc│
│ typescript    │ TS module    │ new typesc│
│ markdown      │ Markdown doc │ new markdo│
│ readme        │ README file  │ new readme│
│ config-json   │ JSON config  │ new config│
│ config-yaml   │ YAML config  │ new config│
└───────────────┴──────────────┴───────────┘

# Create a new Python script
./grokflow_v2.py new python my_script.py

✓ Created my_script.py from template 'python'

Preview (first 10 lines):
#!/usr/bin/env python3
"""
my_script module
"""

def main():
    """Main entry point"""
    pass

# Create a Python class
./grokflow_v2.py new python-class database.py

✓ Created database.py from template 'python-class'

# Create a test file
./grokflow_v2.py new python-test test_auth.py

✓ Created test_auth.py from template 'python-test'
```

**Smart Features**:
- **Auto-naming**: Converts filenames to proper class names (e.g., `user_model.py` → `UserModel`)
- **Auto-descriptions**: Generates sensible default descriptions
- **Project context**: Uses project name in templates
- **Overwrite protection**: Asks before overwriting existing files
- **Preview**: Shows first lines of created file

**Benefits**:
- **Fast file creation**: No more copying from old files
- **Consistent structure**: All files follow best practices
- **Less typing**: Templates include boilerplate
- **Professional**: Proper docstrings, imports, structure

### Context Memory Display (NEW!)

See what files and data are loaded in GrokFlow's context:
```bash
# Quick view in status
./grokflow_v2.py status
Context Memory: 3 file(s) loaded
Use 'context' command to see details

# Detailed view
./grokflow_v2.py

> context
┌──────────────────────────────────────────┐
│ Context Memory                           │
├────────────────┬──────┬───────┬──────────┤
│ File           │ Size │ Lines │ Loaded   │
├────────────────┼──────┼───────┼──────────┤
│ buggy_module.py│ 2.3KB│   87  │ 14:23:45 │
│ test_module.py │ 1.8KB│   65  │ 14:24:12 │
│ utils.py       │ 3.1KB│  124  │ 14:24:30 │
└────────────────┴──────┴───────┴──────────┘

Total: 3 files, 7.2KB, 276 lines
This is what the AI can see when analyzing your code
```

**Benefits:**
- **Transparency**: Know what the AI can see
- **Context awareness**: Understand AI's knowledge scope
- **Memory management**: Track loaded files

### Undo System (NEW!)

Every fix applied by GrokFlow creates an automatic undo point:
```bash
# Undo the most recent edit
./grokflow_v2.py undo

# Undo a specific file
./grokflow_v2.py undo buggy_module.py

# View undo history
./grokflow_v2.py history
```

**Benefits:**
- **Safety**: Instantly revert bad fixes without git
- **Confidence**: Try AI suggestions knowing you can undo
- **GUKS Integration**: Prevents false positives in knowledge base
- **Fast Recovery**: No need to manually restore files

**In Interactive Mode:**
```
> fix
✓ Fix applied to file
💾 Undo point saved (use 'undo buggy_module.py' to revert)

> history
┌─────────────────┬─────────────────────┬──────────────────┐
│ File            │ Timestamp           │ Error ID         │
├─────────────────┼─────────────────────┼──────────────────┤
│ buggy_module.py │ 2025-11-14 07:45:23 │ abc123def456...  │
└─────────────────┴─────────────────────┴──────────────────┘

> undo
✓ Undid edit to buggy_module.py
```

## Advanced Features

### Universal Knowledge (System-wide Learning)
```bash
# Stats about learned errors and fixes
./grokflow_v2.py knowledge stats

# Recurring patterns across projects
./grokflow_v2.py knowledge patterns

# Semantic search for similar errors
./grokflow_v2.py knowledge search "AttributeError: 'NoneType' object has no attribute 'upper'"
```

- Uses `universal_knowledge.py` (GrokFlow Universal Knowledge System)
- Learns from failing tests and past fixes
- Shares solutions across all projects on this machine

## Files Overview

| File | Purpose |
|------|---------|
| `grokflow_v2.py` | Main CLI (recommended) |
| `universal_knowledge.py` | Universal knowledge system (GUKS) |
| `grokflow.py` | Original CLI with codebase tools |
| `codebase_manager.py` | File operations |
| `demo_codebase.py` | Demo of features |

## Documentation

- **README.md** - Overview and installation
- **UX_DESIGN.md** - UX philosophy and design
- **LEARNING_SYSTEM.md** - How learning works
- **UNIVERSAL_LEARNING_SYSTEM.md** - System-wide experiential learning design
- **BREAKTHROUGH_SUMMARY.md** - Executive summary of Universal Knowledge System
- **BETTER_THAN_CURSOR.md** - Comparison with competitors
- **COMPLETE_SOLUTION.md** - Full feature matrix
- **FEATURES.md** - Detailed feature list
- **CODEBASE_FEATURES.md** - Codebase management

## Tips

1. **Run in interactive mode** for best experience
2. **Let it learn** - the more you use it, the smarter it gets
3. **Check versions regularly** - `./grokflow_v2.py check`
4. **Share knowledge** with your team
5. **Review stats** to see time saved

## Troubleshooting

### No API Key
```bash
export XAI_API_KEY="your_key"
```

### Permission Denied
```bash
chmod +x grokflow_v2.py
```

### Import Errors
```bash
pip install -r requirements.txt
```

## What Makes It Special

✅ **Learns from mistakes** - Never repeat errors
✅ **20x faster** than Cursor/Windsurf
✅ **Zero copy-paste** - Everything automated
✅ **Git-native** - Smart commits built-in
✅ **Version-aware** - Prevents compatibility issues
✅ **Team-friendly** - Share knowledge easily

## Next Steps

1. Try the interactive mode
2. Fix an error and see it learn
3. Check your stats after a week
4. Share knowledge with your team
5. Watch productivity soar 🚀

---

**Questions? Check the full documentation in the repo.**

*Learn once. Fix forever. Ship faster.* 🌊
