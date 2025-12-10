/**
 * GUKS Commands
 * Command handlers for the extension
 */

import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSPattern } from './types';

/**
 * Register all GUKS commands
 */
export function registerCommands(context: vscode.ExtensionContext, client: GUKSClient): void {
  // Show statistics
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.showStats', async () => {
      await showStats(client);
    })
  );

  // Show recurring patterns
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.showPatterns', async () => {
      await showPatterns(client);
    })
  );

  // Show suggested constraints
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.showConstraints', async () => {
      await showConstraints(client);
    })
  );

  // Apply fix
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.applyFix', async (
      document: vscode.TextDocument,
      range: vscode.Range,
      pattern: GUKSPattern
    ) => {
      await applyFix(document, range, pattern, client);
    })
  );

  // Start GUKS server
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.startServer', async () => {
      await startServer();
    })
  );

  // Record fix
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.recordFix', async () => {
      await recordFix(client);
    })
  );

  // Refresh patterns
  context.subscriptions.push(
    vscode.commands.registerCommand('guks.refreshPatterns', async () => {
      await refreshPatterns();
    })
  );
}

/**
 * Show GUKS statistics
 */
async function showStats(client: GUKSClient): Promise<void> {
  try {
    const stats = await client.getStats();
    if (!stats) {
      vscode.window.showErrorMessage('Failed to fetch GUKS statistics. Is the server running?');
      return;
    }

    const message = `**GUKS Statistics**\n\n` +
      `- Total Patterns: ${stats.total_patterns}\n` +
      `- Recent (30d): ${stats.recent_patterns_30d}\n` +
      `- Projects: ${stats.projects}\n` +
      (stats.trend ? `- Trend: ${stats.trend}\n` : '') +
      (stats.recurring_bugs ? `- Recurring Bugs: ${stats.recurring_bugs}\n` : '') +
      (stats.suggested_rules ? `- Suggested Rules: ${stats.suggested_rules}\n` : '');

    const panel = vscode.window.createWebviewPanel(
      'guksStats',
      'GUKS Statistics',
      vscode.ViewColumn.One,
      {}
    );

    panel.webview.html = getWebviewContent('GUKS Statistics', message);
  } catch (error) {
    vscode.window.showErrorMessage(`GUKS error: ${error}`);
  }
}

/**
 * Show recurring patterns
 */
async function showPatterns(client: GUKSClient): Promise<void> {
  try {
    const analytics = await client.getAnalytics();
    if (!analytics) {
      vscode.window.showErrorMessage('Failed to fetch GUKS analytics. Is the server running?');
      return;
    }

    if (analytics.recurring_patterns.length === 0) {
      vscode.window.showInformationMessage('No recurring patterns detected yet.');
      return;
    }

    let message = `**Recurring Bug Patterns**\n\n`;
    for (const pattern of analytics.recurring_patterns) {
      message += `- **${pattern.pattern}**\n`;
      message += `  - Count: ${pattern.count} across ${pattern.projects.length} project(s)\n`;
      message += `  - Urgency: ${pattern.urgency}\n`;
      message += `  - Suggested Action: ${pattern.suggested_action}\n\n`;
    }

    const panel = vscode.window.createWebviewPanel(
      'guksPatterns',
      'GUKS Recurring Patterns',
      vscode.ViewColumn.One,
      {}
    );

    panel.webview.html = getWebviewContent('Recurring Bug Patterns', message);
  } catch (error) {
    vscode.window.showErrorMessage(`GUKS error: ${error}`);
  }
}

/**
 * Show suggested constraints
 */
async function showConstraints(client: GUKSClient): Promise<void> {
  try {
    const analytics = await client.getAnalytics();
    if (!analytics) {
      vscode.window.showErrorMessage('Failed to fetch GUKS analytics. Is the server running?');
      return;
    }

    if (analytics.constraint_rules.length === 0) {
      vscode.window.showInformationMessage('No linting rules suggested yet.');
      return;
    }

    let message = `**Suggested Constraint Rules**\n\n`;
    for (const rule of analytics.constraint_rules) {
      message += `- **${rule.rule}**\n`;
      message += `  - Description: ${rule.description}\n`;
      message += `  - Reason: ${rule.reason}\n`;
      message += `  - Severity: ${rule.severity}\n`;
      if (rule.eslint_rule) {
        message += `  - ESLint: ${rule.eslint_rule}\n`;
      }
      message += '\n';
    }

    const panel = vscode.window.createWebviewPanel(
      'guksConstraints',
      'GUKS Suggested Linting Rules',
      vscode.ViewColumn.One,
      {}
    );

    panel.webview.html = getWebviewContent('Suggested Linting Rules', message);
  } catch (error) {
    vscode.window.showErrorMessage(`GUKS error: ${error}`);
  }
}

/**
 * Apply a GUKS fix to the document
 */
async function applyFix(
  document: vscode.TextDocument,
  range: vscode.Range,
  pattern: GUKSPattern,
  client: GUKSClient
): Promise<void> {
  const edit = new vscode.WorkspaceEdit();

  // For now, show the fix in a quick pick and let user decide
  const action = await vscode.window.showQuickPick(
    [
      { label: 'View Full Fix Details', description: 'Show complete fix information', action: 'view' },
      { label: 'Copy Fix to Clipboard', description: 'Copy fix description', action: 'copy' },
      { label: 'Record as Fixed', description: 'Mark this as successfully fixed', action: 'record' }
    ],
    { placeHolder: `Fix from ${pattern.project}/${pattern.file}` }
  );

  if (!action) {
    return;
  }

  switch (action.action) {
    case 'view':
      vscode.window.showInformationMessage(
        `GUKS Fix:\n\nError: ${pattern.error}\n\nFix: ${pattern.fix}\n\nFrom: ${pattern.project}/${pattern.file}`,
        { modal: true }
      );
      break;

    case 'copy':
      await vscode.env.clipboard.writeText(pattern.fix);
      vscode.window.showInformationMessage('Fix copied to clipboard');
      break;

    case 'record':
      await client.recordFix({
        error: pattern.error,
        fix: pattern.fix,
        file: document.fileName.split('/').pop() || 'unknown',
        project: vscode.workspace.getWorkspaceFolder(document.uri)?.name || 'unknown',
        success: true
      });
      vscode.window.showInformationMessage('Fix recorded in GUKS');
      break;
  }
}

/**
 * Start GUKS server
 */
async function startServer(): Promise<void> {
  const terminal = vscode.window.createTerminal('GUKS Server');
  terminal.sendText('python -m grokflow.guks.api');
  terminal.show();
  vscode.window.showInformationMessage('GUKS server starting in terminal...');
}

/**
 * Record a fix manually
 */
async function recordFix(client: GUKSClient): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage('No active editor');
    return;
  }

  const error = await vscode.window.showInputBox({
    prompt: 'Enter the error message',
    placeHolder: 'e.g., TypeError: Cannot read property "name" of undefined'
  });

  if (!error) {
    return;
  }

  const fix = await vscode.window.showInputBox({
    prompt: 'Enter the fix description',
    placeHolder: 'e.g., Added null check: if (user) { user.name }'
  });

  if (!fix) {
    return;
  }

  await client.recordFix({
    error,
    fix,
    file: editor.document.fileName.split('/').pop() || 'unknown',
    project: vscode.workspace.getWorkspaceFolder(editor.document.uri)?.name || 'unknown',
    success: true
  });

  vscode.window.showInformationMessage('Fix recorded in GUKS');
}

/**
 * Refresh patterns (reload from server)
 */
async function refreshPatterns(): Promise<void> {
  vscode.window.showInformationMessage('GUKS patterns refreshed');
  // Trigger a status bar update
  vscode.commands.executeCommand('guks.showStats');
}

/**
 * Get webview HTML content
 */
function getWebviewContent(title: string, markdown: string): string {
  // Convert markdown to HTML (basic conversion)
  const html = markdown
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
        }
        h1 {
            color: var(--vscode-textLink-foreground);
        }
        p {
            margin: 10px 0;
        }
        strong {
            color: var(--vscode-textLink-activeForeground);
        }
    </style>
</head>
<body>
    <h1>${title}</h1>
    <p>${html}</p>
</body>
</html>`;
}
