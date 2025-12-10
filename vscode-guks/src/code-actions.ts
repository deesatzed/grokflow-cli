/**
 * GUKS Code Actions Provider
 * Provides quick fix actions based on GUKS patterns
 */

import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSPattern, GUKSConfig } from './types';

export class GUKSCodeActions implements vscode.CodeActionProvider {
  private client: GUKSClient;
  private config: GUKSConfig;

  constructor(client: GUKSClient, config: GUKSConfig) {
    this.client = client;
    this.config = config;
  }

  async provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.CodeAction[]> {
    const actions: vscode.CodeAction[] = [];

    // Find GUKS diagnostics in context
    const guksDiagnostics = context.diagnostics.filter(d => d.source === 'GUKS');

    for (const diag of guksDiagnostics) {
      // Extract patterns from diagnostic
      const patterns: GUKSPattern[] = (diag as any).guks Patterns || [];

      // Create code action for each pattern
      for (const pattern of patterns) {
        const similarity = Math.round((pattern.similarity || 0) * 100);
        const action = new vscode.CodeAction(
          `$(lightbulb) ${pattern.fix} (${similarity}% match)`,
          vscode.CodeActionKind.QuickFix
        );
        action.diagnostics = [diag];
        action.command = {
          title: 'Apply GUKS Fix',
          command: 'guks.applyFix',
          arguments: [document, range, pattern]
        };

        // Mark high-confidence fixes as preferred
        action.isPreferred = (pattern.similarity || 0) > 0.9;

        actions.push(action);
      }
    }

    // If no GUKS diagnostics, try querying GUKS for the selection
    if (actions.length === 0 && !range.isEmpty) {
      const code = document.getText(range);
      const result = await this.client.query({
        code,
        context: {
          file_type: document.fileName.split('.').pop(),
          project: vscode.workspace.getWorkspaceFolder(document.uri)?.name,
          language: document.languageId
        },
        min_similarity: this.config.minSimilarity
      });

      for (const pattern of result.patterns) {
        const similarity = Math.round((pattern.similarity || 0) * 100);
        const action = new vscode.CodeAction(
          `$(database) GUKS: ${pattern.fix} (${similarity}% match)`,
          vscode.CodeActionKind.QuickFix
        );
        action.command = {
          title: 'Apply GUKS Suggestion',
          command: 'guks.applyFix',
          arguments: [document, range, pattern]
        };
        actions.push(action);
      }
    }

    return actions;
  }

  /**
   * Update configuration
   */
  updateConfig(config: GUKSConfig): void {
    this.config = config;
  }
}
