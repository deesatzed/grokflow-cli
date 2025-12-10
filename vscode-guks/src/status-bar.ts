/**
 * GUKS Status Bar Item
 * Shows GUKS statistics in the VS Code status bar
 */

import * as vscode from 'vscode';
import { GUKSClient } from './guks-client';
import { GUKSStats } from './types';

export class GUKSStatusBar {
  private statusBarItem: vscode.StatusBarItem;
  private client: GUKSClient;
  private updateInterval?: NodeJS.Timeout;
  private isHealthy: boolean = false;

  constructor(client: GUKSClient) {
    this.client = client;
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.statusBarItem.command = 'guks.showStats';
  }

  /**
   * Start the status bar (show and begin updates)
   */
  async start(): Promise<void> {
    await this.update();
    this.statusBarItem.show();

    // Update every 30 seconds
    this.updateInterval = setInterval(() => this.update(), 30000);
  }

  /**
   * Stop the status bar (hide and stop updates)
   */
  stop(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = undefined;
    }
    this.statusBarItem.hide();
  }

  /**
   * Update status bar content
   */
  async update(): Promise<void> {
    try {
      // Check health first
      const healthy = await this.client.checkHealth();
      this.isHealthy = healthy;

      if (!healthy) {
        this.showOffline();
        return;
      }

      // Get stats
      const stats = await this.client.getStats();
      if (stats) {
        this.showStats(stats);
      } else {
        this.showOffline();
      }
    } catch (error) {
      console.error('[GUKS StatusBar] Update failed:', error);
      this.showOffline();
    }
  }

  /**
   * Show stats in status bar
   */
  private showStats(stats: GUKSStats): void {
    const icon = this.getTrendIcon(stats.trend);
    this.statusBarItem.text = `$(database) GUKS: ${stats.total_patterns}${icon}`;

    const tooltip = new vscode.MarkdownString();
    tooltip.appendMarkdown(`**GUKS Statistics**\n\n`);
    tooltip.appendMarkdown(`- Total Patterns: ${stats.total_patterns}\n`);
    tooltip.appendMarkdown(`- Recent (30d): ${stats.recent_patterns_30d}\n`);
    tooltip.appendMarkdown(`- Projects: ${stats.projects}\n`);
    if (stats.trend) {
      tooltip.appendMarkdown(`- Trend: ${stats.trend}\n`);
    }
    if (stats.recurring_bugs && stats.recurring_bugs > 0) {
      tooltip.appendMarkdown(`- Recurring Bugs: ${stats.recurring_bugs}\n`);
    }
    if (stats.suggested_rules && stats.suggested_rules > 0) {
      tooltip.appendMarkdown(`- Suggested Rules: ${stats.suggested_rules}\n`);
    }
    tooltip.appendMarkdown(`\n*Click for details*`);

    this.statusBarItem.tooltip = tooltip;
    this.statusBarItem.backgroundColor = undefined;
  }

  /**
   * Show offline status
   */
  private showOffline(): void {
    this.statusBarItem.text = '$(warning) GUKS: Offline';
    this.statusBarItem.tooltip = new vscode.MarkdownString(
      '**GUKS API not available**\n\n' +
      'Start server with:\n' +
      '```bash\n' +
      'python -m grokflow.guks.api\n' +
      '```\n' +
      'Or click to start server.'
    );
    this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
  }

  /**
   * Get icon for trend
   */
  private getTrendIcon(trend?: string): string {
    if (!trend) {
      return '';
    }
    const lowerTrend = trend.toLowerCase();
    if (lowerTrend.includes('improving') || lowerTrend.includes('decreasing')) {
      return ' $(arrow-down)'; // Fewer bugs = good
    } else if (lowerTrend.includes('worsening') || lowerTrend.includes('increasing')) {
      return ' $(arrow-up)'; // More bugs = bad
    } else if (lowerTrend.includes('stable')) {
      return ' $(dash)';
    }
    return '';
  }

  /**
   * Check if GUKS is healthy
   */
  isGUKSHealthy(): boolean {
    return this.isHealthy;
  }

  /**
   * Dispose of the status bar item
   */
  dispose(): void {
    this.stop();
    this.statusBarItem.dispose();
  }
}
