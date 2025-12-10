/**
 * GUKS Diagnostics Provider
 * Provides inline diagnostic suggestions based on GUKS patterns
 */

import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSConfig } from './types';

export class GUKSDiagnostics {
  private diagnostics: vscode.DiagnosticCollection;
  private client: GUKSClient;
  private config: GUKSConfig;

  constructor(client: GUKSClient, config: GUKSConfig) {
    this.client = client;
    this.config = config;
    this.diagnostics = vscode.languages.createDiagnosticCollection('guks');
  }

  /**
   * Analyze diagnostics and add GUKS suggestions
   */
  async analyzeDiagnostics(
    document: vscode.TextDocument,
    existingDiagnostics: readonly vscode.Diagnostic[]
  ): Promise<void> {
    if (!this.config.enableDiagnostics) {
      return;
    }

    const guksDiagnostics: vscode.Diagnostic[] = [];

    for (const diag of existingDiagnostics) {
      // Extract error context
      const error = diag.message;
      const range = diag.range;
      const code = document.getText(range);

      try {
        // Query GUKS for similar patterns
        const result = await this.client.query({
          code,
          error,
          context: {
            file_type: this.getFileExtension(document),
            project: this.getProjectName(document),
            language: document.languageId
          },
          min_similarity: this.config.minSimilarity
        });

        if (result.patterns.length > 0) {
          // Add GUKS suggestion as info diagnostic
          const topPattern = result.patterns[0];
          const similarity = Math.round((topPattern.similarity || 0) * 100);

          const guksDiag = new vscode.Diagnostic(
            range,
            `GUKS: Similar issue fixed ${result.patterns.length} time(s) - ${topPattern.fix} (${similarity}% match)`,
            vscode.DiagnosticSeverity.Information
          );
          guksDiag.source = 'GUKS';
          guksDiag.code = {
            value: 'guks-suggestion',
            target: vscode.Uri.parse('command:guks.showPatterns')
          };

          // Store patterns in diagnostic for quick fix provider
          (guksDiag as any).guksPatterns = result.patterns;

          guksDiagnostics.push(guksDiag);
        }
      } catch (error) {
        console.error('[GUKS Diagnostics] Query failed:', error);
      }
    }

    this.diagnostics.set(document.uri, guksDiagnostics);
  }

  /**
   * Clear diagnostics for a document
   */
  clear(document: vscode.TextDocument): void {
    this.diagnostics.delete(document.uri);
  }

  /**
   * Clear all diagnostics
   */
  clearAll(): void {
    this.diagnostics.clear();
  }

  /**
   * Get file extension without dot
   */
  private getFileExtension(document: vscode.TextDocument): string {
    const parts = document.fileName.split('.');
    return parts.length > 1 ? parts[parts.length - 1] : 'unknown';
  }

  /**
   * Get project name from workspace
   */
  private getProjectName(document: vscode.TextDocument): string {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
    return workspaceFolder?.name || 'unknown';
  }

  /**
   * Update configuration
   */
  updateConfig(config: GUKSConfig): void {
    this.config = config;
  }

  /**
   * Dispose of diagnostics collection
   */
  dispose(): void {
    this.diagnostics.dispose();
  }
}
