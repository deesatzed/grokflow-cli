# GUKS VS Code Extension - Design Document

**Date**: 2025-12-09
**Status**: Week 3 - Design Phase
**Goal**: Real-time GUKS suggestions as you code

---

## Overview

The GUKS VS Code extension brings cross-project learning directly into your editor. As you write code, GUKS analyzes errors and suggests fixes from your team's bug history in real-time.

**Key Features**:
1. **Inline diagnostics** - Show GUKS suggestions in Problems panel
2. **Quick fix actions** - Apply GUKS fixes with one click
3. **Hover tooltips** - Preview similar past fixes on hover
4. **Status bar integration** - Show GUKS stats (X patterns learned)
5. **Command palette** - Access GUKS analytics from editor

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  VS Code Extension (TypeScript)                     │
│  - Diagnostics Provider                             │
│  - Code Actions Provider                            │
│  - Hover Provider                                   │
│  - Status Bar Item                                  │
│  - Command Handlers                                 │
└────────────────┬────────────────────────────────────┘
                 │ HTTP
                 ▼
┌─────────────────────────────────────────────────────┐
│  GUKS API Server (FastAPI)                         │
│  - POST /api/guks/query                            │
│  - POST /api/guks/record                           │
│  - GET /api/guks/stats                             │
│  - POST /api/guks/complete                         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  Enhanced GUKS (Python)                            │
│  - Semantic search                                 │
│  - Pattern matching                                │
│  - Analytics engine                                │
└─────────────────────────────────────────────────────┘
```

---

## User Experience Flows

### Flow 1: Error Detection + GUKS Suggestion

**Trigger**: User saves file with error

**Steps**:
1. VS Code detects error (TypeScript compiler, ESLint, etc.)
2. Extension extracts: error message, code context, file type
3. Extension queries GUKS API: `POST /api/guks/query`
4. GUKS returns similar patterns (if any)
5. Extension adds diagnostic in Problems panel
6. User clicks "Quick Fix" → sees GUKS suggestions
7. User selects suggestion → code applied automatically
8. User confirms fix works → Extension records in GUKS

**Example**:
```typescript
// User writes:
function getUser(id: string) {
  const user = findUserById(id);
  return user.name; // <-- TypeScript error: Object is possibly 'null'
}

// Problems panel shows:
❌ Object is possibly 'null' (TypeScript)
💡 GUKS: Similar issue fixed 3 times - Add null check

// User clicks "Quick Fix" → sees:
1. Add null check (GUKS - 92% match)
   From: user-service/api.ts (fixed 2 weeks ago)
   Pattern: if (user) { return user.name }

2. Use optional chaining (GUKS - 87% match)
   From: auth-service/auth.ts (fixed 1 month ago)
   Pattern: return user?.name

3. TypeScript: Add '!' assertion (built-in)
```

### Flow 2: Proactive Suggestions (No Error)

**Trigger**: User types code that matches GUKS pattern

**Steps**:
1. User types code (debounced, e.g., 500ms after last keystroke)
2. Extension extracts code context (current function, imports)
3. Extension queries GUKS: "Have we fixed similar code before?"
4. GUKS returns patterns if code is risky
5. Extension shows subtle hint (hover or CodeLens)

**Example**:
```typescript
// User types:
function updateProfile(userId: string, data: any) {
  const user = getUser(userId);
  user.profile = data; // <-- GUKS detects pattern

// Hover shows:
💡 GUKS: Similar pattern caused 5 bugs in the past
Suggestion: Check if user exists before updating
```

### Flow 3: Team Analytics

**Trigger**: User opens Command Palette → "GUKS: Show Team Insights"

**Steps**:
1. Extension queries GUKS API: `GET /api/guks/stats`
2. GUKS returns analytics (recurring bugs, suggested rules)
3. Extension shows webview panel with:
   - Recurring bug patterns
   - Suggested linting rules
   - Team metrics (X patterns learned, Y bugs prevented)
   - Hotspot files (most bugs)

**Example**:
```
┌─────────────────────────────────────────────┐
│  GUKS Team Insights                         │
├─────────────────────────────────────────────┤
│ Total Patterns: 150                         │
│ Recent (30d): 47                            │
│ Trend: ↓ 12% (Improving)                    │
│                                             │
│ Recurring Bugs:                             │
│ • TypeError: Cannot read property (8)       │
│ • UnhandledPromiseRejection (5)             │
│                                             │
│ Suggested Linting Rules:                    │
│ • require-null-checks (8 bugs prevented)    │
│ • strict-promise-handling (5 bugs)          │
│                                             │
│ [Apply Rules to .eslintrc]                  │
└─────────────────────────────────────────────┘
```

---

## Technical Implementation

### Extension Structure

```
vscode-guks/
├── package.json              # Extension manifest
├── tsconfig.json             # TypeScript config
├── src/
│   ├── extension.ts          # Entry point, activation
│   ├── guks-client.ts        # GUKS API client
│   ├── diagnostics.ts        # Diagnostics provider
│   ├── code-actions.ts       # Quick fix provider
│   ├── hover.ts              # Hover provider
│   ├── status-bar.ts         # Status bar item
│   ├── commands.ts           # Command handlers
│   ├── webview.ts            # Analytics webview
│   └── types.ts              # TypeScript interfaces
├── media/
│   └── guks-icon.svg         # Extension icon
├── test/
│   └── extension.test.ts     # Extension tests
└── README.md                 # Extension docs
```

### Core Components

#### 1. GUKS Client (`guks-client.ts`)

```typescript
import axios from 'axios';

export interface GUKSPattern {
  error: string;
  fix: string;
  file: string;
  project: string;
  similarity: number;
}

export interface GUKSQueryResult {
  patterns: GUKSPattern[];
  total: number;
}

export class GUKSClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://127.0.0.1:8765') {
    this.baseUrl = baseUrl;
  }

  async query(code: string, error?: string, context?: any): Promise<GUKSQueryResult> {
    const response = await axios.post(`${this.baseUrl}/api/guks/query`, {
      code,
      error,
      context
    });
    return response.data;
  }

  async recordFix(pattern: GUKSPattern): Promise<void> {
    await axios.post(`${this.baseUrl}/api/guks/record`, pattern);
  }

  async getStats(): Promise<any> {
    const response = await axios.get(`${this.baseUrl}/api/guks/stats`);
    return response.data;
  }

  async checkHealth(): Promise<boolean> {
    try {
      await axios.get(`${this.baseUrl}/health`, { timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }
}
```

#### 2. Diagnostics Provider (`diagnostics.ts`)

```typescript
import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';

export class GUKSDiagnostics {
  private diagnostics: vscode.DiagnosticCollection;
  private client: GUKSClient;

  constructor(client: GUKSClient) {
    this.client = client;
    this.diagnostics = vscode.languages.createDiagnosticCollection('guks');
  }

  async analyzeDiagnostics(document: vscode.TextDocument, diagnostics: vscode.Diagnostic[]): Promise<void> {
    const guksDiagnostics: vscode.Diagnostic[] = [];

    for (const diag of diagnostics) {
      // Extract error context
      const error = diag.message;
      const range = diag.range;
      const code = document.getText(range);

      // Query GUKS for similar patterns
      const result = await this.client.query(code, error, {
        file_type: this.getFileExtension(document),
        project: this.getProjectName(document)
      });

      if (result.patterns.length > 0) {
        // Add GUKS suggestion as info diagnostic
        const topPattern = result.patterns[0];
        const guksDiag = new vscode.Diagnostic(
          range,
          `GUKS: Similar issue fixed ${result.patterns.length} time(s) - ${topPattern.fix}`,
          vscode.DiagnosticSeverity.Information
        );
        guksDiag.source = 'GUKS';
        guksDiag.code = { value: 'guks-suggestion', target: vscode.Uri.parse('command:guks.showPatterns') };
        guksDiagnostics.push(guksDiag);
      }
    }

    this.diagnostics.set(document.uri, guksDiagnostics);
  }

  private getFileExtension(document: vscode.TextDocument): string {
    return document.fileName.split('.').pop() || 'unknown';
  }

  private getProjectName(document: vscode.TextDocument): string {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
    return workspaceFolder?.name || 'unknown';
  }
}
```

#### 3. Code Actions Provider (`code-actions.ts`)

```typescript
import * as vscode from 'vscode';
import { GUKSClient, GUKSPattern } from './guks-client';

export class GUKSCodeActions implements vscode.CodeActionProvider {
  private client: GUKSClient;

  constructor(client: GUKSClient) {
    this.client = client;
  }

  async provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range,
    context: vscode.CodeActionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.CodeAction[]> {
    const actions: vscode.CodeAction[] = [];

    // Find GUKS diagnostics in context
    const guksDiagnostics = context.diagnostics.filter(d => d.source === 'GUKS');

    for (const diag of guksDiagnostics) {
      // Extract error and code
      const error = diag.message;
      const code = document.getText(range);

      // Query GUKS for patterns
      const result = await this.client.query(code, error);

      // Create code action for each pattern
      for (const pattern of result.patterns) {
        const action = new vscode.CodeAction(
          `GUKS: ${pattern.fix} (${Math.round(pattern.similarity * 100)}% match)`,
          vscode.CodeActionKind.QuickFix
        );
        action.diagnostics = [diag];
        action.command = {
          title: 'Apply GUKS Fix',
          command: 'guks.applyFix',
          arguments: [document, range, pattern]
        };
        action.isPreferred = pattern.similarity > 0.9; // Mark high-confidence fixes as preferred
        actions.push(action);
      }
    }

    return actions;
  }
}
```

#### 4. Hover Provider (`hover.ts`)

```typescript
import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';

export class GUKSHoverProvider implements vscode.HoverProvider {
  private client: GUKSClient;

  constructor(client: GUKSClient) {
    this.client = client;
  }

  async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken
  ): Promise<vscode.Hover | undefined> {
    // Get word/range at position
    const range = document.getWordRangeAtPosition(position);
    if (!range) return;

    const code = document.getText(range);

    // Query GUKS for similar patterns
    const result = await this.client.query(code, undefined, {
      file_type: document.languageId,
      project: vscode.workspace.getWorkspaceFolder(document.uri)?.name
    });

    if (result.patterns.length === 0) return;

    // Build hover content
    const markdown = new vscode.MarkdownString();
    markdown.appendMarkdown(`**GUKS:** Found ${result.patterns.length} similar pattern(s)\n\n`);

    const topPattern = result.patterns[0];
    markdown.appendMarkdown(`**Top Match** (${Math.round(topPattern.similarity * 100)}% similar):\n`);
    markdown.appendMarkdown(`- **Error:** ${topPattern.error}\n`);
    markdown.appendMarkdown(`- **Fix:** ${topPattern.fix}\n`);
    markdown.appendMarkdown(`- **From:** ${topPattern.project}/${topPattern.file}\n`);

    return new vscode.Hover(markdown, range);
  }
}
```

#### 5. Status Bar (`status-bar.ts`)

```typescript
import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';

export class GUKSStatusBar {
  private statusBarItem: vscode.StatusBarItem;
  private client: GUKSClient;

  constructor(client: GUKSClient) {
    this.client = client;
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.statusBarItem.command = 'guks.showStats';
  }

  async update(): Promise<void> {
    try {
      const stats = await this.client.getStats();
      this.statusBarItem.text = `$(database) GUKS: ${stats.total_patterns} patterns`;
      this.statusBarItem.tooltip = `GUKS: ${stats.total_patterns} patterns learned\nClick for details`;
      this.statusBarItem.show();
    } catch (error) {
      this.statusBarItem.text = '$(warning) GUKS: Offline';
      this.statusBarItem.tooltip = 'GUKS API not available. Start server with: python -m grokflow.guks.api';
      this.statusBarItem.show();
    }
  }

  dispose(): void {
    this.statusBarItem.dispose();
  }
}
```

#### 6. Extension Entry Point (`extension.ts`)

```typescript
import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSDiagnostics } from './diagnostics';
import { GUKSCodeActions } from './code-actions';
import { GUKSHoverProvider } from './hover';
import { GUKSStatusBar } from './status-bar';
import { registerCommands } from './commands';

let client: GUKSClient;
let statusBar: GUKSStatusBar;

export async function activate(context: vscode.ExtensionContext) {
  console.log('GUKS extension activating...');

  // Initialize GUKS client
  const config = vscode.workspace.getConfiguration('guks');
  const apiUrl = config.get<string>('apiUrl', 'http://127.0.0.1:8765');
  client = new GUKSClient(apiUrl);

  // Check if GUKS API is available
  const isAvailable = await client.checkHealth();
  if (!isAvailable) {
    vscode.window.showWarningMessage(
      'GUKS API not available. Start with: python -m grokflow.guks.api',
      'Start Server',
      'Dismiss'
    ).then(selection => {
      if (selection === 'Start Server') {
        vscode.commands.executeCommand('guks.startServer');
      }
    });
  }

  // Register diagnostics provider
  const diagnostics = new GUKSDiagnostics(client);
  vscode.workspace.onDidChangeTextDocument(async (event) => {
    const diags = vscode.languages.getDiagnostics(event.document.uri);
    await diagnostics.analyzeDiagnostics(event.document, diags);
  });

  // Register code actions provider
  const codeActions = new GUKSCodeActions(client);
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { scheme: 'file' },
      codeActions,
      { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
    )
  );

  // Register hover provider
  const hoverProvider = new GUKSHoverProvider(client);
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(
      { scheme: 'file' },
      hoverProvider
    )
  );

  // Create status bar item
  statusBar = new GUKSStatusBar(client);
  await statusBar.update();
  context.subscriptions.push(statusBar);

  // Update status bar every 30 seconds
  const statusInterval = setInterval(() => statusBar.update(), 30000);
  context.subscriptions.push({ dispose: () => clearInterval(statusInterval) });

  // Register commands
  registerCommands(context, client);

  console.log('GUKS extension activated');
}

export function deactivate() {
  console.log('GUKS extension deactivated');
}
```

---

## Configuration

### package.json (Extension Manifest)

```json
{
  "name": "vscode-guks",
  "displayName": "GUKS - Cross-Project Learning",
  "description": "AI coding assistant that learns from your team's bug history",
  "version": "0.1.0",
  "publisher": "grokflow",
  "engines": {
    "vscode": "^1.80.0"
  },
  "categories": ["Linters", "Other"],
  "keywords": ["guks", "grokflow", "ai", "bug-fixing", "learning"],
  "activationEvents": ["onStartupFinished"],
  "main": "./out/extension.js",
  "contributes": {
    "configuration": {
      "title": "GUKS",
      "properties": {
        "guks.apiUrl": {
          "type": "string",
          "default": "http://127.0.0.1:8765",
          "description": "GUKS API server URL"
        },
        "guks.enableDiagnostics": {
          "type": "boolean",
          "default": true,
          "description": "Enable GUKS diagnostic suggestions"
        },
        "guks.enableHover": {
          "type": "boolean",
          "default": true,
          "description": "Enable GUKS hover tooltips"
        },
        "guks.minSimilarity": {
          "type": "number",
          "default": 0.7,
          "description": "Minimum similarity threshold (0.0-1.0)"
        }
      }
    },
    "commands": [
      {
        "command": "guks.showStats",
        "title": "GUKS: Show Statistics"
      },
      {
        "command": "guks.showPatterns",
        "title": "GUKS: Show Recurring Patterns"
      },
      {
        "command": "guks.showConstraints",
        "title": "GUKS: Show Suggested Linting Rules"
      },
      {
        "command": "guks.applyFix",
        "title": "GUKS: Apply Fix"
      },
      {
        "command": "guks.startServer",
        "title": "GUKS: Start API Server"
      },
      {
        "command": "guks.recordFix",
        "title": "GUKS: Record This Fix"
      }
    ]
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "test": "node ./out/test/runTest.js"
  },
  "devDependencies": {
    "@types/vscode": "^1.80.0",
    "@types/node": "^18.0.0",
    "typescript": "^5.0.0",
    "@vscode/test-electron": "^2.3.0"
  },
  "dependencies": {
    "axios": "^1.6.0"
  }
}
```

---

## Development Workflow

### Setup

```bash
# Create extension directory
mkdir vscode-guks
cd vscode-guks

# Initialize npm project
npm init -y

# Install dependencies
npm install --save axios
npm install --save-dev @types/vscode @types/node typescript @vscode/test-electron

# Create tsconfig.json
cat > tsconfig.json <<EOF
{
  "compilerOptions": {
    "module": "commonjs",
    "target": "ES2020",
    "outDir": "out",
    "lib": ["ES2020"],
    "sourceMap": true,
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true
  },
  "exclude": ["node_modules", ".vscode-test"]
}
EOF

# Create src directory
mkdir src
```

### Testing

```bash
# Compile TypeScript
npm run compile

# Run in Extension Development Host
# Press F5 in VS Code (opens new window with extension loaded)

# Run tests
npm test
```

### Debugging

```bash
# .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Extension",
      "type": "extensionHost",
      "request": "launch",
      "args": ["--extensionDevelopmentPath=${workspaceFolder}"],
      "outFiles": ["${workspaceFolder}/out/**/*.js"],
      "preLaunchTask": "npm: compile"
    }
  ]
}
```

---

## Testing Strategy

### Unit Tests

Test each component in isolation:
- GUKSClient API calls
- Diagnostics extraction
- Code action generation
- Hover content formatting

### Integration Tests

Test VS Code API integration:
- Extension activation
- Diagnostic collection
- Quick fix application
- Command execution

### Manual Testing Checklist

- [ ] Extension activates without errors
- [ ] Status bar shows GUKS stats
- [ ] Diagnostics appear in Problems panel
- [ ] Quick fixes work (apply GUKS suggestions)
- [ ] Hover tooltips show similar patterns
- [ ] Commands execute (showStats, showPatterns, etc.)
- [ ] Configuration changes take effect
- [ ] Graceful degradation if API is offline

---

## Performance Considerations

**Debouncing**: Avoid querying GUKS on every keystroke
- Use 500ms debounce for proactive suggestions
- Only query on save for diagnostics

**Caching**: Cache GUKS responses
- Cache patterns for 5 minutes
- Invalidate on file save

**Background Processing**: Run GUKS queries async
- Don't block editor UI
- Use cancellation tokens

**Rate Limiting**: Limit API calls
- Max 10 queries per second
- Queue requests if needed

---

## Deployment

### Publishing to VS Code Marketplace

```bash
# Install vsce (VS Code Extension Manager)
npm install -g @vscode/vsce

# Package extension
vsce package

# Output: vscode-guks-0.1.0.vsix

# Publish (requires publisher account)
vsce publish
```

### Manual Installation

```bash
# Install .vsix file
code --install-extension vscode-guks-0.1.0.vsix
```

---

## Success Metrics

**Adoption**:
- [ ] 100+ installs in first month
- [ ] 10+ GitHub stars on extension repo

**Usage**:
- [ ] 50+ GUKS queries per user per day
- [ ] 10+ quick fixes applied per user per day

**Quality**:
- [ ] 90%+ user satisfaction (5-star reviews)
- [ ] <1% crash rate

**Performance**:
- [ ] <100ms to show diagnostics
- [ ] <50ms to show hover tooltip

---

## Next Steps

**Week 3 Tasks**:
1. ✅ Design architecture (this document)
2. Create extension scaffolding
3. Implement GUKS client
4. Add inline diagnostics
5. Add quick fix actions
6. Add hover tooltips
7. Add status bar integration
8. Write tests
9. Document extension

**Week 4 (Optional)**:
- Real-time pattern matching (CodeLens)
- Webview for analytics dashboard
- Auto-apply high-confidence fixes
- Team sync configuration

---

## Questions?

**Ready to implement**:
1. Extension structure is designed
2. All components specified
3. Testing strategy defined
4. Deployment process documented

**Proceed with implementation?**
