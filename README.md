# 🌊 GrokFlow CLI - Ultimate Vibe Coding

**Command-line interface for reasoning-amplified development with Grok-4-fast**

## 🚀 Features

### Core Features
- **Interactive Chat Mode** - Natural conversation with Grok-4
- **Code Generation** - Generate code from descriptions
- **Smart Debugging** - Debug with reasoning insights
- **Code Optimization** - Optimize for performance
- **Multiple Vibe Modes** - Adaptive development styles
- **Stateful Sessions** - Persistent conversation context
- **Token Analytics** - Track reasoning efficiency
- **Beautiful CLI** - Rich terminal UI with syntax highlighting

### Codebase Management (NEW!)
- **Scan Codebase** - Analyze project structure and statistics
- **Read Files** - View files with syntax highlighting and analysis
- **Edit with AI** - Modify files with Grok-4's assistance
- **Run & Test** - Execute code and auto-debug errors
- **Search** - Find text across entire codebase
- **AI Analysis** - Get comprehensive codebase insights

### GrokFlow v2 - Smart Fix & GUKS (NEW!) 🚀

**The only AI coding assistant that learns from YOUR team's bugs**

- **Smart Fix CLI** - `./grokflow_v2.py fix` / `test` / `commit` / `status`
- **GUKS (GrokFlow Universal Knowledge System)** - Semantic search + analytics + insights
  - ✨ **Semantic bug search** - Finds similar bugs even with different wording (5ms queries)
  - 📊 **Recurring pattern detection** - Identifies bugs fixed 3+ times across projects
  - 🎯 **Auto-generated team policies** - Suggests linting rules based on your actual bugs
  - 🔍 **Cross-project learning** - Knowledge shared across all your projects
  - 💡 **Real-time suggestions** - Shows similar past fixes before AI analysis
- **Demo**: `guks_demo/` with failing pytest test for the test → fix → GUKS loop

## GrokFlow v2 Features

**New in v2:**
- **Universal Knowledge System (GUKS)**: System-wide learning from every bug fix across all projects
- **Dual-Model Architecture**: Two-phase approach with grok-beta (planning) + grok-4-fast (execution) for optimized speed and cost
- **Image Analysis with Vision AI**: Analyze screenshots and UI with grok-4-fast vision capabilities
- **Smart Fix**: AI-powered error analysis with context from past solutions
- **Streaming with Reasoning**: See AI's thought process in real-time during analysis
- **Enhanced CLI**: Tab completion, command history, and auto-suggest
- **Directory Recursive Add**: Add entire directories to context with one command
- **File Templates**: Create new files quickly with built-in templates
- **Binary File Detection**: Automatically skips binary files with helpful messages
- **Context Memory Display**: See what files the AI can access
- **Undo System**: Instant rollback of any fix with automatic undo points
- **Quick Test**: Intelligent test runner with failure tracking
- **Knowledge Commands**: Query, analyze, and learn from accumulated debugging experience

> Contributor note: See `AGENTS.md` for coding norms, style rules, and release expectations.

## 📦 Installation

```bash
cd grokflow-cli

# Preferred editable install with dev extras
pip install -e .[dev]

# Legacy fallback (without optional tooling)
pip install -r requirements.txt

# Make original CLI executable
chmod +x grokflow.py

# (Optional) Make v2 Smart Fix CLI executable
chmod +x grokflow_v2.py

# Optional: Add to PATH
ln -s $(pwd)/grokflow.py /usr/local/bin/grokflow

# Set API key
export XAI_API_KEY="your_key_here"

# Offline mode for tests / CI
export GROKFLOW_OFFLINE=1
```

## 🎮 Usage

### GrokFlow v2 Smart Fix CLI
```bash
# Interactive mode (recommended)
./grokflow_v2.py

# Quick commands
./grokflow_v2.py fix          # Smart fix (last error or modified file)
./grokflow_v2.py test         # Run relevant tests
./grokflow_v2.py commit       # Smart git commit
./grokflow_v2.py status       # Workspace and git context

# GUKS (GrokFlow Universal Knowledge System)
./grokflow_v2.py guks stats           # Show statistics and trends
./grokflow_v2.py guks patterns        # Show recurring bug patterns
./grokflow_v2.py guks constraints     # Show auto-generated linting rules
./grokflow_v2.py guks report          # Generate full analytics report

# Interactive mode (includes GUKS)
./grokflow_v2.py                      # Start interactive mode
> guks stats                          # Query GUKS interactively
> fix buggy_file.py                   # Get GUKS suggestions before AI fix
```

### Interactive Chat
```bash
grokflow chat
```

Start an interactive chat session with Grok-4. Type naturally, get reasoning-backed responses.

**In-chat commands:**
- `exit` - Exit chat
- `clear` - Clear screen
- `/vibe <mode>` - Change vibe mode
- `/stats` - Show statistics
- `/help` - Show help

### Generate Code
```bash
# From prompt
grokflow generate "Create a REST API with FastAPI"

# From file
grokflow generate -f prompt.txt -o api.py

# Interactive
grokflow generate
```

### Debug Code
```bash
# Debug file
grokflow debug -f mycode.py

# With error message
grokflow debug -f mycode.py -e "IndexError: list index out of range"

# From stdin
grokflow debug < mycode.py
```

### Optimize Code
```bash
# Optimize file
grokflow optimize -f mycode.py

# From stdin
grokflow optimize < mycode.py
```

### Vibe Modes
```bash
# Show available modes
grokflow vibe

# Set mode
grokflow vibe creative   # Maximum innovation
grokflow vibe focused    # Task-oriented
grokflow vibe analytical # Deep reasoning
grokflow vibe rapid      # Speed-first
```

### Project Context
```bash
# Set context
grokflow context "Building a React dashboard with TypeScript"

# View context
grokflow context
```

### Statistics
```bash
# Show session stats
grokflow stats
```

### History
```bash
# Show last 10 entries
grokflow history

# Show last 20
grokflow history -n 20
```

### Clear Session
```bash
grokflow clear
```

### Scan Codebase
```bash
# Basic scan
grokflow scan

# With tree view
grokflow scan --tree

# Custom depth
grokflow scan --depth 5 --tree
```

### Read Files
```bash
# Read file
grokflow read src/app.py

# Read with analysis (Python)
grokflow read src/app.py --analyze
```

### Edit Files
```bash
# Edit with instructions
grokflow edit src/app.py -i "Add error handling"

# Create new file
grokflow edit src/new.py --create -i "Create user model"

# Interactive mode
grokflow edit src/app.py
```

### Run Code
```bash
# Run file
grokflow run src/app.py

# Run with arguments
grokflow run src/script.py --args "arg1 arg2"

# Run with auto-debug
grokflow run src/app.py --debug
```

### Search Codebase
```bash
# Search for text
grokflow search "function authenticate"

# Search specific files
grokflow search "TODO" --pattern "*.py"

# Limit results
grokflow search "import" --limit 10
```

### Analyze Codebase
```bash
# AI-powered analysis
grokflow analyze
```

### Constraint System (NEW in v1.4.0!) 🎯

**Never repeat the same mistake twice!** The constraint system learns from your patterns and enforces best practices automatically.

#### Quick Start
```bash
# Use the new CLI interface (v1.4.0)
grokflow-constraint list

# Add basic constraint
grokflow-constraint add "Never use mock data" \
  -k "mock,demo,fake" \
  -a block \
  -m "Use real data and APIs only!"

# Import security best practices
grokflow-constraint templates --import security-awareness

# Check system health
grokflow-constraint health
```

#### What's New in v1.4.0 🚀

**CLI Interface**:
- ✅ **10 commands** with beautiful Rich terminal output
- ✅ **Advanced constraints** (regex patterns, AND/OR logic, context filters)
- ✅ **Template system** (4 built-in templates, import/export)
- ✅ **Health monitoring** (precision tracking, drift detection)
- ✅ **AI-powered suggestions** (automatic improvement recommendations)
- ✅ **100% E2E tested** (13/13 tests passing)

**Performance Optimizations** (v1.3.1):
- ✅ **9x faster** at 100+ constraints (O(1) keyword indexing)
- ✅ **10x faster** regex matching (pattern caching)
- ✅ **Schema migration** framework for future upgrades

#### All Commands

```bash
# List constraints
grokflow-constraint list                    # All constraints
grokflow-constraint list --enabled          # Enabled only

# Add constraints
grokflow-constraint add "Description" \
  -k "keywords" \
  -a warn|block|require_action \
  -m "Custom message"

# Advanced constraints (Phase 2)
grokflow-constraint add-v2 "Block placeholders" \
  -p "placeholder.*,todo.*,fixme.*" \      # Regex patterns
  -l OR|AND|NOT \                           # Logic
  -c '{"query_type":["generate"]}' \        # Context filters (JSON)
  -a warn

# Manage constraints
grokflow-constraint remove <id>             # Remove permanently
grokflow-constraint enable <id>             # Enable constraint
grokflow-constraint disable <id>            # Disable temporarily

# Health & Analytics
grokflow-constraint health                  # System dashboard
grokflow-constraint health <id>             # Specific constraint
grokflow-constraint suggestions             # AI recommendations
grokflow-constraint stats                   # System statistics

# Templates
grokflow-constraint templates               # List built-in templates
grokflow-constraint templates --import <name>     # Import template
grokflow-constraint templates --export <path>     # Export to file
```

#### Built-in Templates

| Template | Description | Constraints |
|----------|-------------|-------------|
| `no-mock-data` | Block mock/demo/placeholder data | 2 |
| `security-awareness` | Security patterns (SQL injection, hardcoded credentials) | 2 |
| `best-practices-python` | Python coding standards | 2 |
| `destructive-actions` | Confirm dangerous operations | 2 |

#### Advanced Features

**Regex Patterns**:
```bash
# Match "mockapi", "mock_api", "mock-api"
-p "mock.*api"

# Match "password = 'xxx'" (security)
-p "password\s*=\s*['\"]"
```

**AND/OR/NOT Logic**:
```bash
# AND: Require BOTH keywords
-k "database,delete" -l AND

# OR: Any keyword matches (default)
-k "mock,demo,fake" -l OR

# NOT: Block if NONE present
-k "real,production" -l NOT
```

**Context Filters**:
```bash
# Only in code generation
-c '{"query_type":["generate"]}'

# Only in creative mode
-c '{"vibe_mode":["creative"]}'
```

**Example Workflows**:

**Team Onboarding**:
```bash
# Import security constraints
grokflow-constraint templates --import security-awareness

# Add team-specific rules
grokflow-constraint add "Require code review for prod deployments" \
  -p "deploy.*production" \
  -a require_action
```

**Health Monitoring**:
```bash
# Weekly review
grokflow-constraint health

# Check specific constraint
grokflow-constraint health abc12345

# Get improvement suggestions
grokflow-constraint suggestions
```

**Constraint Refinement**:
```bash
# Review false positives
grokflow-constraint health abc12345

# Disable problematic constraint
grokflow-constraint disable abc12345

# Export for sharing
grokflow-constraint templates --export team-rules.json
```

#### Performance

| Constraints | Check Time | Memory |
|-------------|------------|--------|
| 10 | 0.18ms | ~4KB |
| 100 | 2ms | ~40KB |
| 1000 | 20ms | ~400KB |

**Scalability**: Handles 1000+ constraints with <20ms overhead

#### Documentation

- **CLI_USAGE_GUIDE.md** - Complete CLI documentation (600+ lines)
- **CLI_E2E_TEST_RESULTS.md** - Test results and validation
- **CHANGELOG.md** - Version history (v1.0.0 → v1.4.0)

**Demos**:
- `demo_cli_complete.py` - Interactive walkthrough
- `demo_cli_automated.sh` - Automated validation

## 🎨 Vibe Modes

| Mode | Temperature | Best For |
|------|-------------|----------|
| **Creative** 🎨 | 0.7 | New projects, brainstorming, innovation |
| **Focused** 🎯 | 0.3 | Bug fixes, specific tasks, refactoring |
| **Analytical** 🧠 | 0.3 | Complex algorithms, system design |
| **Rapid** ⚡ | 0.5 | Prototypes, MVPs, quick iterations |

## 🧠 GUKS - Universal Knowledge System

**What makes GrokFlow different?** Most AI assistants forget your fixes. **GUKS remembers everything**.

### How GUKS Works

```mermaid
graph LR
    A[Fix Bug] --> B[GUKS Records]
    B --> C[Semantic Index]
    C --> D[Similar Bug Later]
    D --> E[GUKS Suggests Fix]
    E --> F[Faster Resolution]
```

### Key Features

**1. Semantic Search** (30x faster than target)
- Query: "TypeError: Cannot read property"
- GUKS finds: "NullPointerException in getUser" (87% match)
- **Why**: Understands both are null pointer issues, different wording

**2. Recurring Pattern Detection**
```bash
$ grokflow guks patterns

Recurring Bug Patterns
Pattern                          Count  Projects  Urgency  Action
TypeError: Cannot read prop...     8       3      high     Add ESLint rule
UnhandledPromiseRejection...       5       2      medium   Add try-catch
```

**3. Auto-Generated Team Policies**
```bash
$ grokflow guks constraints

Suggested Constraint Rules
Rule                  Description                    Reason
require-null-checks   Require null checks...         8 bugs prevented
strict-type-checking  Enable strict mode...          5 type errors caught
```

**4. Cross-Project Learning**
- Fix bug in `project-A` → Knowledge shared
- Work on `project-B` → GUKS suggests: "Similar issue in project-A"
- **Result**: No repeated work across projects

### GUKS Commands

```bash
# Show overall statistics
grokflow guks stats

# Find recurring patterns (fixed 3+ times)
grokflow guks patterns

# Get suggested linting rules
grokflow guks constraints

# Generate full analytics report
grokflow guks report
```

### Example Output

**GUKS in Action** (during `fix` command):
```
📚 Querying GUKS...

🔍 GUKS found similar patterns:
  #  Similarity  Error                          Fix
  1  92%         TypeError: Cannot read prop... Added null check: if (user)...
  2  78%         NullPointerException in get... Added early return...

💡 Top suggestion (92% match):
Error: TypeError: Cannot read property "email" of undefined
Fix: Added null check: if (user) { user.email }
```

### What Competitors Don't Have

| Feature | GrokFlow GUKS | Copilot | Cursor | Aider |
|---------|---------------|---------|--------|-------|
| Cross-project learning | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Semantic bug search | ✅ Yes (5ms) | ❌ No | ❌ No | ❌ No |
| Auto linting rules | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Pattern detection | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Team insights | ✅ Yes | ❌ No | ❌ No | ❌ No |

### Performance

- **Query latency**: 5ms mean (target: <150ms) → **30x faster**
- **Index build**: 0.59s for 1000 patterns
- **Precision**: 100% on test queries
- **Memory**: ~50MB for typical usage

---

## 💡 Examples

### Real-World Example: Fixing Podcast Briefing AI 🎙️

**Project**: React + TypeScript + Google Gemini AI podcast generation app
**Result**: **11 critical bugs fixed in 2 minutes**

```bash
cd podcast-briefing-ai
export XAI_API_KEY=xai-***

# Analyze API integration issues
python grokflow_v2.py fix services/geminiService.ts
# ⏱️  53 seconds | 🐛 8 bugs found | ✅ Production fixes suggested

# Analyze UX issues
python grokflow_v2.py fix App.tsx
# ⏱️  50 seconds | 🐛 3 bugs found | ✅ UX improvements suggested
```

**Issues Found**:
- ❌ Wrong API request format → ✅ Fixed to Gemini SDK spec
- ❌ Undefined response parsing → ✅ Added safe extraction helpers
- ❌ JSON mode not working → ✅ Corrected config key
- ❌ Missing error handling → ✅ Added try-catch blocks
- ❌ Search input creating duplicates → ✅ Added trim + validation

**Impact**: Non-functional application → Production-ready in 27 minutes
**Time Saved**: ~2 hours of manual debugging

[**📖 Read full example →**](./examples/REAL_WORLD_EXAMPLE_PODCAST_AI.md)

---

### Example 1: Generate API
```bash
$ grokflow generate "Create a FastAPI endpoint for user authentication"

🧠 Grok-4 is thinking...

Generated Code:

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
...
```

### Example 2: Debug with Context
```bash
$ grokflow context "Python web scraper using BeautifulSoup"
$ grokflow debug -f scraper.py -e "AttributeError: 'NoneType' object has no attribute 'find'"

Debug Analysis:

The error occurs because the HTML element you're trying to find doesn't exist...
```

### Example 3: Interactive Chat
```bash
$ grokflow chat

🌊 GrokFlow Interactive Chat
Vibe Mode: creative 🎨 Maximum innovation

You: Create a binary search tree in Python
🧠 Grok-4 is thinking...

Response:
Here's a clean implementation of a binary search tree...
```

## 📊 Session Management

GrokFlow automatically saves your session to `~/.grokflow/`:
- `session.json` - Current conversation state
- `history.json` - Command history (last 100)

Sessions persist across runs, maintaining context for up to 30 days via Grok-4's Responses API.

## 🧠 Reasoning Insights

Every response includes reasoning metrics:

```
┌─────────────────┬─────────┐
│ Metric          │ Value   │
├─────────────────┼─────────┤
│ Reasoning Tokens│ 1,234   │
│ Completion Tokens│ 567    │
│ Total Tokens    │ 1,801   │
│ Reasoning Ratio │ 68.5%   │
└─────────────────┴─────────┘
```

## 🔧 Advanced Usage

### Pipe Code Through GrokFlow
```bash
# Optimize code from git diff
git diff | grokflow optimize

# Debug failing tests
pytest --tb=short | grokflow debug
```

### Chain Commands
```bash
# Generate, then optimize
grokflow generate "quicksort algorithm" -o sort.py && \
grokflow optimize -f sort.py
```

### Use in Scripts
```python
import subprocess

result = subprocess.run(
    ['grokflow', 'generate', 'fibonacci function'],
    capture_output=True,
    text=True
)

code = result.stdout
```

## 🎯 Tips for Best Results

1. **Set Project Context** - Helps Grok-4 understand your codebase
2. **Choose Right Vibe** - Match mode to task type
3. **Use Streaming** - See reasoning in real-time
4. **Review Metrics** - Optimize token usage
5. **Maintain Sessions** - Build on previous context

## 🔐 Security

- API keys stored in environment variables only
- Session data stored locally in `~/.grokflow/`
- No data sent to third parties
- Encrypted reasoning content support

## 🚀 Performance

- **Streaming responses** - See output as it's generated
- **Session caching** - Reduced token usage
- **Async operations** - Non-blocking I/O
- **Smart context** - Only sends relevant history

## 🐛 Troubleshooting

### API Key Not Found
```bash
export XAI_API_KEY="your_key_here"
# Or add to ~/.bashrc or ~/.zshrc
```

### Permission Denied
```bash
chmod +x grokflow.py
```

### Module Not Found
```bash
pip install -r requirements.txt
```

## 📚 Documentation

### Command Reference

| Command | Description | Options |
|---------|-------------|---------|
| `chat` | Interactive chat | - |
| `generate` | Generate code | `-f`, `-o` |
| `debug` | Debug code | `-f`, `-e` |
| `optimize` | Optimize code | `-f` |
| `vibe` | Set vibe mode | `mode` |
| `context` | Set context | `text` |
| `stats` | Show stats | - |
| `history` | Show history | `-n` |
| `clear` | Clear session | - |
| `constraint` | Manage constraints | `add`, `list`, `show`, `remove`, `disable`, `enable`, `stats` |

### Additional Docs

- `QUICK_START.md` - Getting started with `grokflow_v2.py` Smart Fix CLI
- `UNIVERSAL_LEARNING_SYSTEM.md` - System-wide experiential learning architecture
- `BREAKTHROUGH_SUMMARY.md` - Executive summary of the Universal Knowledge System (GUKS)
 - `GUKS_SMART_FIX_BLOG.md` - Blog-style walkthrough of GUKS + Smart Fix, including the `guks_demo` project

### Environment Variables

- `XAI_API_KEY` - Your XAI API key (required)
- `GROKFLOW_CONFIG_DIR` - Config directory (default: `~/.grokflow`)

## 🔮 Future Features

- [ ] Multi-file project support
- [ ] Git integration
- [ ] Code review mode
- [ ] Test generation
- [ ] Documentation generation
- [ ] Diff-based optimization
- [ ] Team collaboration
- [ ] Custom vibe modes

## 🤝 Contributing

This is a demonstration project. Feel free to fork and customize!

## 📝 License

MIT License - Build amazing things!

---

**Built with ❤️ using Grok-4-fast and XAI API**

*Vibe fast, reason deep, ship smart* 🌊
