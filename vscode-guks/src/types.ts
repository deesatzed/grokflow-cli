/**
 * GUKS VS Code Extension - Type Definitions
 */

export interface GUKSPattern {
  error: string;
  fix: string;
  file: string;
  project: string;
  similarity?: number;
  context?: Record<string, any>;
  timestamp?: string;
}

export interface GUKSQueryRequest {
  code?: string;
  error?: string;
  context?: {
    file_type?: string;
    project?: string;
    language?: string;
  };
  limit?: number;
  min_similarity?: number;
}

export interface GUKSQueryResult {
  patterns: GUKSPattern[];
  total: number;
  query_time_ms?: number;
}

export interface GUKSRecordRequest {
  error: string;
  fix: string;
  file: string;
  project: string;
  context?: Record<string, any>;
  success?: boolean;
}

export interface GUKSStats {
  total_patterns: number;
  recent_patterns_30d: number;
  projects: number;
  categories: Record<string, number>;
  trend?: string;
  recurring_bugs?: number;
  suggested_rules?: number;
}

export interface GUKSRecurringPattern {
  pattern: string;
  normalized_error: string;
  count: number;
  projects: string[];
  urgency: 'critical' | 'high' | 'medium' | 'low';
  suggested_action: string;
}

export interface GUKSConstraintRule {
  rule: string;
  description: string;
  reason: string;
  severity: 'error' | 'warning';
  pattern?: string;
  eslint_rule?: string;
}

export interface GUKSAnalytics {
  recurring_patterns: GUKSRecurringPattern[];
  constraint_rules: GUKSConstraintRule[];
  insights: {
    total_patterns: number;
    recent_patterns: number;
    trend: string;
    top_categories: Array<{ category: string; count: number }>;
    top_files: Array<{ file: string; count: number }>;
  };
}

export interface GUKSHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  guks_available: boolean;
  num_patterns: number;
  version?: string;
}

export interface GUKSConfig {
  apiUrl: string;
  enableDiagnostics: boolean;
  enableHover: boolean;
  minSimilarity: number;
  debounceMs: number;
  showStatusBar: boolean;
}
