/**
 * GUKS Hover Provider
 * Shows similar patterns on hover
 */

import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSConfig, GUKSPattern } from './types';

export class GUKSHoverProvider implements vscode.HoverProvider {
  private client: GUKSClient;
  private config: GUKSConfig;
  private cache: Map<string, { patterns: GUKSPattern[]; timestamp: number }> = new Map();
  private cacheTimeout = 5 * 60 * 1000; // 5 minutes

  constructor(client: GUKSClient, config: GUKSConfig) {
    this.client = client;
    this.config = config;
  }

  async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken
  ): Promise<vscode.Hover | undefined> {
    if (!this.config.enableHover) {
      return undefined;
    }

    // Get word/range at position
    const range = document.getWordRangeAtPosition(position) ||
                  new vscode.Range(position, position);

    if (range.isEmpty) {
      return undefined;
    }

    const code = document.getText(range);
    if (!code || code.length < 3) {
      return undefined; // Too short to be meaningful
    }

    // Check cache
    const cacheKey = `${document.uri.toString()}:${range.start.line}:${range.start.character}`;
    const cached = this.cache.get(cacheKey);
    if (cached && (Date.now() - cached.timestamp < this.cacheTimeout)) {
      return this.buildHover(cached.patterns, range);
    }

    try {
      // Query GUKS for similar patterns
      const result = await this.client.query({
        code,
        context: {
          file_type: document.fileName.split('.').pop(),
          project: vscode.workspace.getWorkspaceFolder(document.uri)?.name,
          language: document.languageId
        },
        min_similarity: this.config.minSimilarity,
        limit: 3 // Only show top 3 in hover
      });

      if (result.patterns.length === 0) {
        return undefined;
      }

      // Cache result
      this.cache.set(cacheKey, {
        patterns: result.patterns,
        timestamp: Date.now()
      });

      return this.buildHover(result.patterns, range);
    } catch (error) {
      console.error('[GUKS Hover] Query failed:', error);
      return undefined;
    }
  }

  /**
   * Build hover content from patterns
   */
  private buildHover(patterns: GUKSPattern[], range: vscode.Range): vscode.Hover {
    const markdown = new vscode.MarkdownString();
    markdown.isTrusted = true;

    markdown.appendMarkdown(`$(database) **GUKS:** Found ${patterns.length} similar pattern(s)\n\n`);

    for (let i = 0; i < Math.min(patterns.length, 3); i++) {
      const pattern = patterns[i];
      const similarity = Math.round((pattern.similarity || 0) * 100);

      if (i > 0) {
        markdown.appendMarkdown('\n---\n\n');
      }

      markdown.appendMarkdown(`**Match ${i + 1}** (${similarity}% similar)\n\n`);
      markdown.appendMarkdown(`- **Error:** ${this.truncate(pattern.error, 100)}\n`);
      markdown.appendMarkdown(`- **Fix:** ${this.truncate(pattern.fix, 100)}\n`);
      markdown.appendMarkdown(`- **From:** ${pattern.project}/${pattern.file}\n`);
    }

    if (patterns.length > 3) {
      markdown.appendMarkdown(`\n\n*...and ${patterns.length - 3} more. Click for details.*\n`);
    }

    markdown.appendMarkdown('\n\n[Show All Patterns](command:guks.showPatterns)');

    return new vscode.Hover(markdown, range);
  }

  /**
   * Truncate text with ellipsis
   */
  private truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength - 3) + '...';
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Update configuration
   */
  updateConfig(config: GUKSConfig): void {
    this.config = config;
  }
}
