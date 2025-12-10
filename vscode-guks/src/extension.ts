/**
 * GUKS VS Code Extension - Entry Point
 */

import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSDiagnostics } from './diagnostics';
import { GUKSCodeActions } from './code-actions';
import { GUKSHoverProvider } from './hover';
import { GUKSStatusBar } from './status-bar';
import { registerCommands } from './commands';
import { GUKSConfig } from './types';

let client: GUKSClient;
let diagnostics: GUKSDiagnostics;
let codeActions: GUKSCodeActions;
let hoverProvider: GUKSHoverProvider;
let statusBar: GUKSStatusBar;

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext) {
  console.log('[GUKS] Extension activating...');

  // Load configuration
  const config = loadConfig();

  // Initialize GUKS client
  client = new GUKSClient(config.apiUrl);

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
  } else {
    console.log('[GUKS] API is healthy');
  }

  // Initialize diagnostics provider
  diagnostics = new GUKSDiagnostics(client, config);

  // Watch for diagnostic changes
  context.subscriptions.push(
    vscode.languages.onDidChangeDiagnostics(async (event) => {
      for (const uri of event.uris) {
        const document = await vscode.workspace.openTextDocument(uri);
        const diags = vscode.languages.getDiagnostics(uri);
        await diagnostics.analyzeDiagnostics(document, diags);
      }
    })
  );

  // Watch for document saves (trigger diagnostics)
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      const diags = vscode.languages.getDiagnostics(document.uri);
      await diagnostics.analyzeDiagnostics(document, diags);
    })
  );

  // Initialize code actions provider
  codeActions = new GUKSCodeActions(client, config);
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { scheme: 'file' },
      codeActions,
      {
        providedCodeActionKinds: [vscode.CodeActionKind.QuickFix]
      }
    )
  );

  // Initialize hover provider
  hoverProvider = new GUKSHoverProvider(client, config);
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(
      { scheme: 'file' },
      hoverProvider
    )
  );

  // Create status bar item
  if (config.showStatusBar) {
    statusBar = new GUKSStatusBar(client);
    await statusBar.start();
    context.subscriptions.push(statusBar);
  }

  // Register commands
  registerCommands(context, client);

  // Watch for configuration changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(event => {
      if (event.affectsConfiguration('guks')) {
        const newConfig = loadConfig();
        client.updateBaseUrl(newConfig.apiUrl);
        diagnostics.updateConfig(newConfig);
        codeActions.updateConfig(newConfig);
        hoverProvider.updateConfig(newConfig);

        // Restart status bar if show/hide setting changed
        if (newConfig.showStatusBar && !statusBar) {
          statusBar = new GUKSStatusBar(client);
          statusBar.start();
          context.subscriptions.push(statusBar);
        } else if (!newConfig.showStatusBar && statusBar) {
          statusBar.dispose();
        }
      }
    })
  );

  console.log('[GUKS] Extension activated successfully');
}

/**
 * Extension deactivation
 */
export function deactivate() {
  console.log('[GUKS] Extension deactivating...');

  // Cleanup
  if (diagnostics) {
    diagnostics.dispose();
  }
  if (hoverProvider) {
    hoverProvider.clearCache();
  }
  if (statusBar) {
    statusBar.dispose();
  }

  console.log('[GUKS] Extension deactivated');
}

/**
 * Load configuration from VS Code settings
 */
function loadConfig(): GUKSConfig {
  const config = vscode.workspace.getConfiguration('guks');

  return {
    apiUrl: config.get<string>('apiUrl', 'http://127.0.0.1:8765'),
    enableDiagnostics: config.get<boolean>('enableDiagnostics', true),
    enableHover: config.get<boolean>('enableHover', true),
    minSimilarity: config.get<number>('minSimilarity', 0.7),
    debounceMs: config.get<number>('debounceMs', 500),
    showStatusBar: config.get<boolean>('showStatusBar', true)
  };
}
