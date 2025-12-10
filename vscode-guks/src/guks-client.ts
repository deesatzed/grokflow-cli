/**
 * GUKS API Client
 * Handles all communication with the GUKS backend API
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  GUKSPattern,
  GUKSQueryRequest,
  GUKSQueryResult,
  GUKSRecordRequest,
  GUKSStats,
  GUKSAnalytics,
  GUKSHealthResponse
} from './types';

export class GUKSClient {
  private client: AxiosInstance;
  private baseUrl: string;

  constructor(baseUrl: string = 'http://127.0.0.1:8765') {
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  /**
   * Query GUKS for similar patterns
   */
  async query(request: GUKSQueryRequest): Promise<GUKSQueryResult> {
    try {
      const response = await this.client.post<GUKSQueryResult>('/api/guks/query', request);
      return response.data;
    } catch (error) {
      this.handleError('query', error);
      return { patterns: [], total: 0 };
    }
  }

  /**
   * Record a successful fix in GUKS
   */
  async recordFix(request: GUKSRecordRequest): Promise<void> {
    try {
      await this.client.post('/api/guks/record', request);
    } catch (error) {
      this.handleError('recordFix', error);
    }
  }

  /**
   * Get GUKS statistics
   */
  async getStats(): Promise<GUKSStats | null> {
    try {
      const response = await this.client.get<GUKSStats>('/api/guks/stats');
      return response.data;
    } catch (error) {
      this.handleError('getStats', error);
      return null;
    }
  }

  /**
   * Get analytics (recurring patterns, suggested rules)
   */
  async getAnalytics(): Promise<GUKSAnalytics | null> {
    try {
      const response = await this.client.get<GUKSAnalytics>('/api/guks/analytics');
      return response.data;
    } catch (error) {
      this.handleError('getAnalytics', error);
      return null;
    }
  }

  /**
   * Check if GUKS API is healthy
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get<GUKSHealthResponse>('/health', {
        timeout: 1000
      });
      return response.data.status === 'healthy' && response.data.guks_available;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get list of all patterns with pagination
   */
  async getPatterns(limit: number = 100, offset: number = 0): Promise<GUKSPattern[]> {
    try {
      const response = await this.client.get<{ patterns: GUKSPattern[] }>('/api/guks/patterns', {
        params: { limit, offset }
      });
      return response.data.patterns;
    } catch (error) {
      this.handleError('getPatterns', error);
      return [];
    }
  }

  /**
   * Update API URL
   */
  updateBaseUrl(url: string): void {
    this.baseUrl = url;
    this.client.defaults.baseURL = url;
  }

  /**
   * Handle API errors gracefully
   */
  private handleError(method: string, error: unknown): void {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;
      if (axiosError.code === 'ECONNREFUSED') {
        console.warn(`[GUKS] API not available at ${this.baseUrl}. Start with: python -m grokflow.guks.api`);
      } else if (axiosError.response) {
        console.error(`[GUKS] ${method} failed: ${axiosError.response.status} - ${axiosError.response.statusText}`);
      } else {
        console.error(`[GUKS] ${method} failed:`, axiosError.message);
      }
    } else {
      console.error(`[GUKS] ${method} failed:`, error);
    }
  }
}
