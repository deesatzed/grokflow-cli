# GUKS - Quick Start on New Computer

**Time**: 15-20 minutes to get running
**For**: Complete guide see `vscode-guks/INSTALLATION_AND_TESTING_GUIDE.md`

---

## Prerequisites (5 minutes)

**Install if missing**:
```bash
# Check versions
python3 --version  # Need 3.11+
node --version     # Need 18+
code --version     # Need VS Code

# macOS install (if needed)
brew install python@3.11 node

# Download VS Code: https://code.visualstudio.com/
```

---

## Setup GUKS (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/deesatzed/grokflow-cli.git
cd grokflow-cli

# 2. Install Python dependencies
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Test GUKS API
python -m grokflow.guks.api
# Should see: "✅ GUKS API started"
# Press Ctrl+C to stop
```

---

## Package Extension (5 minutes)

```bash
# 1. Install vsce
npm install -g @vscode/vsce

# 2. Build extension
cd vscode-guks
npm install
npm run compile
vsce package

# Result: vscode-guks-0.1.0.vsix created
```

---

## Install & Test (5 minutes)

```bash
# 1. Install extension
code --install-extension vscode-guks-0.1.0.vsix

# 2. Start GUKS API (keep running)
cd ..
source venv/bin/activate
python -m grokflow.guks.api

# 3. Open VS Code, check status bar
# Should see: "$(database) GUKS: 0 patterns"
```

---

## Quick Test (5 minutes)

**Create test file**: `test.ts`

```typescript
interface User {
  name: string;
}

function getUser(id: string): User | null {
  return null;  // Simulates not found
}

function display(id: string) {
  const user = getUser(id);
  console.log(user.name);  // ERROR: Object is possibly 'null'
}
```

**Save → See TypeScript error → Fix it**:
```typescript
function display(id: string) {
  const user = getUser(id);
  if (user) {  // FIX
    console.log(user.name);
  }
}
```

**Record fix**:
- `Cmd+Shift+P` → "GUKS: Record This Fix"
- Error: `Object is possibly 'null'`
- Fix: `Added null check`

**Create second file with same bug → GUKS suggests your fix!** ✅

---

## Troubleshooting

**"GUKS: Offline"** → GUKS API not running, start it:
```bash
python -m grokflow.guks.api
```

**"No module named 'sentence_transformers'"** → Install dependencies:
```bash
pip install -r requirements.txt
```

**"Extension not found"** → Check installation:
```bash
code --list-extensions | grep guks
```

---

## Full Documentation

- **Installation**: `vscode-guks/INSTALLATION_AND_TESTING_GUIDE.md` (23 KB, 60+ steps)
- **Testing**: `vscode-guks/TESTING_GUIDE.md` (15 KB, 18 test cases)
- **README**: `vscode-guks/README.md` (15 KB)
- **Summary**: `GUKS_COMPLETE_SUMMARY.md` (25 KB)

---

## Commands Cheatsheet

**Start GUKS API**:
```bash
cd grokflow-cli
source venv/bin/activate
python -m grokflow.guks.api
```

**VS Code Commands** (Cmd+Shift+P):
- `GUKS: Show Statistics` - View pattern count
- `GUKS: Record This Fix` - Save a fix
- `GUKS: Show Patterns` - See recurring bugs

**Package Extension**:
```bash
cd vscode-guks
vsce package
```

**Install Extension**:
```bash
code --install-extension vscode-guks-0.1.0.vsix
```

---

**Ready to test? Follow this guide, then see INSTALLATION_AND_TESTING_GUIDE.md for complete testing.**
