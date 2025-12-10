# GrokFlow CLI

**AI-powered coding assistant with cross-project learning**

GrokFlow is a command-line tool that helps you fix bugs, write code, and learn from your team's bug history using Grok AI models.

---

## Quick Start

```bash
# Install
git clone https://github.com/deesatzed/grokflow-cli.git
cd grokflow-cli
pip install -r requirements.txt

# Set API key
export XAI_API_KEY="your_key_here"

# Run interactive mode
./grokflow_v2.py
```

---

## What Can I Do?

### Fix Bugs
```bash
# Interactive mode - just type what you want
./grokflow_v2.py

> fix myfile.py              # Fix errors in a file
> test                       # Run tests
> commit                     # Create smart commit
```

### Common Tasks

**Fix a specific file**:
```bash
./grokflow_v2.py fix path/to/file.py
```

**Run tests**:
```bash
./grokflow_v2.py test
```

**Create a commit**:
```bash
./grokflow_v2.py commit
```

**Check workspace status**:
```bash
./grokflow_v2.py status
```

---

## Features

### Smart Fix
- AI analyzes errors in your code
- Suggests fixes with explanations
- Shows similar fixes from past work (GUKS)
- Auto-creates undo points

### GUKS (Knowledge System)
- Remembers every bug you fix
- Finds similar bugs across all your projects
- Suggests fixes based on your team's history
- Detects recurring patterns

**View GUKS stats**:
```bash
./grokflow_v2.py guks stats
```

**See recurring bugs**:
```bash
./grokflow_v2.py guks patterns
```

---

## Installation

### Prerequisites
- Python 3.11+
- XAI API key ([get one here](https://x.ai/api))

### Install
```bash
git clone https://github.com/deesatzed/grokflow-cli.git
cd grokflow-cli
pip install -r requirements.txt
export XAI_API_KEY="your_key_here"
```

### Optional: VS Code Extension
For real-time suggestions in VS Code, see [vscode-guks/](./vscode-guks/)

---

## Interactive Mode

Start interactive mode:
```bash
./grokflow_v2.py
```

Available commands:
- `architect` - Generate architectural plan (app blueprints)
- `fix` - Fix errors in code
- `test` - Run relevant tests
- `commit` - Create smart commit
- `guks` - View knowledge stats
- `status` - Show workspace context
- `undo` / `redo` - Undo/redo changes
- `exit` - Quit

**Example session**:
```
> fix src/app.py
🧠 Analyzing src/app.py...
Found 3 errors:
  1. TypeError on line 42: ...
  2. Missing import on line 5
  3. Undefined variable on line 67

Apply fixes? (y/n): y
✅ Fixed all 3 errors

> test
Running tests...
✅ All tests passed

> commit
📝 Suggested commit message:
"Fix TypeError and missing imports in app.py"

Commit? (y/n): y
✅ Committed
```

---

## Configuration

### API Key
Set your XAI API key:
```bash
export XAI_API_KEY="your_key_here"

# Or add to ~/.bashrc or ~/.zshrc for permanence
echo 'export XAI_API_KEY="your_key_here"' >> ~/.bashrc
```

### Models
GrokFlow uses `grok-4-1-fast` by default. You can configure models with environment variables:
```bash
export GROKFLOW_PLANNER_MODEL="grok-beta"
export GROKFLOW_EXECUTOR_MODEL="grok-4-1-fast"
```

---

## Examples

### Example 1: Fix a Bug

**File**: `app.py`
```python
def get_user(id):
    user = database.find(id)
    return user.name  # Error: user might be None
```

**Run**:
```bash
./grokflow_v2.py fix app.py
```

**Output**:
```
🧠 Analyzing app.py...

Found error on line 3:
  TypeError: 'NoneType' object has no attribute 'name'

📚 GUKS: Similar issue fixed 2 times before
  Suggestion: Add null check (92% match)

Suggested fix:
  def get_user(id):
      user = database.find(id)
      if user:
          return user.name
      return None

Apply fix? (y/n): y
✅ Fixed app.py
```

### Example 2: Build a New Feature

**Task**: Create a REST API endpoint

**Run**:
```bash
./grokflow_v2.py
```

**Type**:
```
> I need to create a FastAPI endpoint for user login
```

**Output**:
```
🧠 Generating code...

Here's a FastAPI login endpoint:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    # Add your authentication logic here
    if authenticate(request.username, request.password):
        return {"token": generate_token(request.username)}
    raise HTTPException(status_code=401, detail="Invalid credentials")
```

Save to file? (y/n): y
Enter filename: api.py
✅ Saved to api.py
```

### Example 3: Generate Architectural Plan

**Task**: Plan a new application

**Run**:
```bash
./grokflow_v2.py architect "Build a REST API for inventory management with:
- CRUD operations for products
- PostgreSQL database
- User authentication with JWT
- Search and filtering
- Docker deployment"
```

**Output**:
```
🏗️  Generating comprehensive architectural plan...
This may take 30-60 seconds for detailed analysis...

================================================================================

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🏗️  Architectural Plan ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                        ┃
┃  # Summary Integration                                                                 ┃
┃                                                                                        ┃
┃  Building a REST API for inventory management with PostgreSQL...                      ┃
┃                                                                                        ┃
┃  # 1. Comprehensive Build Roadmap                                                      ┃
┃                                                                                        ┃
┃  | Phase | Objective | Inputs | Outputs | Risks/Unknowns |                           ┃
┃  |-------|-----------|--------|---------|----------------|                           ┃
┃  | 1     | Database Schema | Requirements | Schema DDL | Performance at scale |      ┃
┃  | 2     | API Endpoints | Schema | REST API | Auth complexity |                     ┃
┃  | 3     | Authentication | Security reqs | JWT system | Token management |          ┃
┃  ...                                                                                   ┃
┃                                                                                        ┃
┃  # 2. Step-by-Step Implementation Plan                                                 ┃
┃  # 3. Testing & Validation Plan                                                        ┃
┃  # 4. Scope Guardrails                                                                 ┃
┃  # 5. Expected Outcomes                                                                ┃
┃  # 6. UX Bible                                                                         ┃
┃                                                                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

================================================================================

💾 Save architectural plan to file? (Y/n): y
Filename [ARCHITECTURE.md]:
✅ Plan saved to ARCHITECTURE.md
```

The `architect` command uses a professional architecture prompt that generates:
- Phased build roadmap (no unrealistic timelines)
- Step-by-step implementation plan with risks
- Testing & validation strategy
- Drift protection guardrails
- UX-driven design principles
- Realistic outcome scenarios

### Example 4: Understand GUKS Stats

```bash
./grokflow_v2.py guks stats
```

**Output**:
```
GUKS Statistics

Total Patterns: 47
Recent (30d): 12
Projects: 8
Trend: Improving ↓

Top Categories:
  • Null Pointer: 15
  • Type Errors: 10
  • Async Errors: 8

Suggested Actions:
  • Consider adding ESLint rule for null checks (15 patterns)
```

---

## GUKS (Knowledge System)

GUKS learns from every bug you fix and suggests solutions when you encounter similar issues.

### How It Works

1. **You fix a bug** → GUKS records it
2. **Similar bug appears** → GUKS suggests your previous fix
3. **Pattern emerges** → GUKS recommends team policy (e.g., linting rule)

### Commands

```bash
# View statistics
./grokflow_v2.py guks stats

# See recurring bugs (fixed 3+ times)
./grokflow_v2.py guks patterns

# Get suggested linting rules
./grokflow_v2.py guks constraints

# Generate full report
./grokflow_v2.py guks report
```

### Example: Recurring Pattern

After fixing null pointer errors 8 times:

```bash
$ ./grokflow_v2.py guks patterns

Recurring Bug Patterns

Pattern: TypeError: Cannot read property 'name' of undefined
Count: 8 across 3 projects
Urgency: high
Suggested Action: Add ESLint rule @typescript-eslint/no-unsafe-member-access

$ ./grokflow_v2.py guks constraints

Suggested Linting Rules

Rule: require-null-checks
Description: Require null/undefined checks before property access
Reason: 8 null pointer bugs prevented
ESLint: @typescript-eslint/no-unsafe-member-access
```

**Add the rule** → Future bugs prevented automatically ✅

---

## Troubleshooting

### API Key Not Found
```bash
# Check if set
echo $XAI_API_KEY

# Set it
export XAI_API_KEY="your_key_here"
```

### Permission Denied
```bash
chmod +x grokflow_v2.py
```

### Module Not Found
```bash
pip install -r requirements.txt
```

### GUKS Not Working
GUKS requires additional dependencies:
```bash
pip install sentence-transformers faiss-cpu fastapi uvicorn
```

Start GUKS server:
```bash
python -m grokflow.guks.api
```

---

## Documentation

- **[VS Code Extension](./vscode-guks/README.md)** - Real-time suggestions in your editor
- **[Installation Guide](./vscode-guks/INSTALLATION_AND_TESTING_GUIDE.md)** - Complete setup for VS Code extension
- **[Testing Guide](./vscode-guks/TESTING_GUIDE.md)** - How to test all features
- **[Quick Start](./QUICK_START_NEW_COMPUTER.md)** - Fast setup on new computer
- **[Complete Summary](./GUKS_COMPLETE_SUMMARY.md)** - Full project overview

---

## FAQ

**Q: What AI models does it use?**
A: GrokFlow uses Grok models from XAI (grok-beta, grok-4-1-fast)

**Q: Does it work offline?**
A: No, it requires API access to XAI. Set `GROKFLOW_OFFLINE=1` for tests.

**Q: How much does it cost?**
A: Depends on XAI pricing. Uses fast models to minimize cost.

**Q: Can my team share GUKS knowledge?**
A: Yes, run the GUKS API server and point all team members to it.

**Q: Is my code sent to third parties?**
A: Only to XAI's API for processing. Not stored or shared otherwise.

**Q: How is this different from Copilot?**
A: GUKS learns from YOUR bugs, not GitHub's public code. Gets smarter over time.

---

## License

MIT License - See [LICENSE](./LICENSE) for details

---

## Get Help

- **Issues**: https://github.com/deesatzed/grokflow-cli/issues
- **Discussions**: https://github.com/deesatzed/grokflow-cli/discussions

---

**Built with Grok AI** • [XAI API](https://x.ai/api)
