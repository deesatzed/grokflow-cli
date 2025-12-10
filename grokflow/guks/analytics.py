"""
GUKS Analytics Engine - Transform Knowledge into Intelligence

Analyzes GUKS patterns to extract actionable insights:
  - Detect recurring bugs (fixed 3+ times)
  - Auto-suggest constraint rules for teams
  - Identify problematic code patterns
  - Generate team insights dashboard
  - Pattern categorization and clustering

Use cases:
  - "Your team fixes null pointer errors frequently" → Suggest linting rules
  - "This pattern was fixed 5 times" → High-priority test case
  - "Similar bugs in auth code" → Suggest refactoring
"""

from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re
from pathlib import Path
import json


class GUKSAnalytics:
    """
    GUKS Analytics Engine

    Converts raw GUKS patterns into strategic insights about:
      - Code quality trends
      - Team knowledge gaps
      - Automation opportunities
      - Refactoring targets
    """

    def __init__(self, patterns: List[Dict]):
        """
        Initialize analytics engine

        Args:
            patterns: List of GUKS patterns from EnhancedGUKS
        """
        self.patterns = patterns
        self.categories = self._categorize_patterns()

    def _categorize_patterns(self) -> Dict[str, List[Dict]]:
        """
        Categorize patterns by error type

        Categories:
          - null_pointer: TypeError, NullPointerException, undefined
          - type_error: Type mismatches, coercion issues
          - async_error: Promise rejections, async/await issues
          - api_error: HTTP, REST, GraphQL issues
          - validation_error: Input validation, schema issues
          - import_error: Module not found, circular imports
          - state_error: Race conditions, stale state
          - security: Auth, XSS, injection issues

        Returns:
            Dict mapping category to patterns
        """
        categories = defaultdict(list)

        category_keywords = {
            'null_pointer': [
                'nullpointerexception', 'cannot read property', 'undefined',
                'null', 'none type', 'nullreferenceexception'
            ],
            'type_error': [
                'typeerror', 'type mismatch', 'expected', 'type error',
                'cannot convert', 'invalid type'
            ],
            'async_error': [
                'promise', 'async', 'await', 'unhandledpromiserejection',
                'timeout', 'async function', 'callback'
            ],
            'api_error': [
                'api', 'http', 'rest', 'graphql', 'fetch', 'request',
                'response', 'status code', '404', '500'
            ],
            'validation_error': [
                'validation', 'schema', 'invalid', 'required field',
                'missing parameter', 'constraint'
            ],
            'import_error': [
                'import', 'module not found', 'cannot find module',
                'circular import', 'dependency'
            ],
            'state_error': [
                'race condition', 'stale', 'state', 'concurrent',
                'lock', 'mutex'
            ],
            'security': [
                'auth', 'authentication', 'authorization', 'xss',
                'injection', 'sql injection', 'csrf', 'sanitize'
            ]
        }

        for pattern in self.patterns:
            error = pattern.get('error', '').lower()
            fix = pattern.get('fix', '').lower()
            text = f"{error} {fix}"

            # Match to categories
            matched = False
            for category, keywords in category_keywords.items():
                if any(kw in text for kw in keywords):
                    categories[category].append(pattern)
                    matched = True
                    break

            # Catch-all for unmatched
            if not matched:
                categories['other'].append(pattern)

        return dict(categories)

    def detect_recurring_bugs(
        self,
        min_count: int = 3,
        similarity_threshold: float = 0.8
    ) -> List[Dict]:
        """
        Detect bugs that keep happening across projects

        Args:
            min_count: Minimum occurrences to flag as recurring
            similarity_threshold: How similar errors must be (0-1)

        Returns:
            List of recurring bug patterns with metrics

        Example:
            >>> analytics.detect_recurring_bugs(min_count=3)
            [
                {
                    'pattern': 'TypeError: Cannot read property of undefined',
                    'count': 5,
                    'projects': ['api', 'frontend', 'admin'],
                    'fix': 'Added null check',
                    'urgency': 'high',
                    'suggested_action': 'Add linting rule: no-unsafe-member-access'
                }
            ]
        """
        # Group similar errors
        error_groups = defaultdict(list)

        for pattern in self.patterns:
            error = pattern.get('error', '')

            # Normalize error message
            normalized = self._normalize_error(error)

            error_groups[normalized].append(pattern)

        # Find recurring patterns
        recurring = []

        for normalized_error, instances in error_groups.items():
            if len(instances) >= min_count:
                # Analyze this recurring pattern
                projects = set(p.get('project', 'unknown') for p in instances)
                fixes = [p.get('fix', '') for p in instances]

                # Check if fixes are consistent
                fix_consensus = Counter(fixes).most_common(1)[0]
                fix_agreement = fix_consensus[1] / len(fixes)

                recurring.append({
                    'pattern': instances[0].get('error', ''),
                    'normalized': normalized_error,
                    'count': len(instances),
                    'projects': sorted(projects),
                    'fix': fix_consensus[0],
                    'fix_agreement': fix_agreement,
                    'urgency': self._calculate_urgency(len(instances), len(projects)),
                    'suggested_action': self._suggest_action(instances[0]),
                    'examples': instances[:3]  # Sample instances
                })

        # Sort by urgency and count
        recurring.sort(key=lambda x: (x['urgency'] == 'critical',
                                       x['urgency'] == 'high',
                                       x['count']),
                       reverse=True)

        return recurring

    def _normalize_error(self, error: str) -> str:
        """
        Normalize error message to group similar errors

        Removes:
          - Variable names
          - File paths
          - Line numbers
          - Specific values
        """
        # Remove quoted strings
        normalized = re.sub(r'["\'].*?["\']', '<string>', error)

        # Remove numbers
        normalized = re.sub(r'\d+', '<num>', normalized)

        # Remove file paths
        normalized = re.sub(r'/[\w/\.]+', '<path>', normalized)
        normalized = re.sub(r'\\[\w\\\.]+', '<path>', normalized)

        # Remove common variable patterns
        normalized = re.sub(r'\b[a-z_][a-z0-9_]*\b', '<var>', normalized)

        return normalized.strip()

    def _calculate_urgency(self, count: int, num_projects: int) -> str:
        """
        Calculate urgency level based on frequency and spread

        Returns:
            'critical', 'high', 'medium', or 'low'
        """
        if count >= 10 or num_projects >= 5:
            return 'critical'
        elif count >= 5 or num_projects >= 3:
            return 'high'
        elif count >= 3 or num_projects >= 2:
            return 'medium'
        else:
            return 'low'

    def _suggest_action(self, pattern: Dict) -> str:
        """
        Suggest remediation action based on pattern type

        Returns:
            Actionable suggestion (linting rule, test, refactor, etc.)
        """
        error = pattern.get('error', '').lower()
        fix = pattern.get('fix', '').lower()

        # Null pointer → Linting
        if 'null' in error or 'undefined' in error:
            return 'Add ESLint rule: @typescript-eslint/no-unsafe-member-access'

        # Type error → Type checking
        if 'type' in error:
            return 'Enable strict TypeScript mode in tsconfig.json'

        # Async error → Testing
        if 'promise' in error or 'async' in error:
            return 'Add async error handling tests + timeout guards'

        # API error → Validation
        if 'api' in error or 'http' in error:
            return 'Add request/response schema validation (Zod, ajv)'

        # Import error → Dependency management
        if 'import' in error or 'module' in error:
            return 'Run dependency audit + lockfile validation'

        # Generic
        if 'test' in fix:
            return 'Add regression test for this scenario'
        elif 'validation' in fix or 'check' in fix:
            return 'Add validation at system boundary'
        else:
            return 'Review code in affected files for similar issues'

    def suggest_constraint_rules(self) -> List[Dict]:
        """
        Auto-generate constraint rules based on GUKS patterns

        Returns:
            List of constraint rule suggestions for team policy

        Example:
            >>> analytics.suggest_constraint_rules()
            [
                {
                    'rule': 'require-null-checks',
                    'description': 'Require null checks before property access',
                    'reason': '8 bugs prevented by null checks',
                    'pattern': 'if (obj) { obj.property }',
                    'severity': 'error',
                    'affected_files': ['*.ts', '*.tsx']
                }
            ]
        """
        rules = []

        # Analyze categories for rule opportunities
        for category, category_patterns in self.categories.items():
            if len(category_patterns) < 3:
                continue  # Not enough data

            if category == 'null_pointer':
                rules.append({
                    'rule': 'require-null-checks',
                    'description': 'Require null/undefined checks before property access',
                    'reason': f'{len(category_patterns)} null pointer bugs prevented',
                    'pattern': 'if (obj && obj.property) { ... }',
                    'severity': 'error',
                    'affected_files': ['*.ts', '*.tsx', '*.js'],
                    'eslint_rule': '@typescript-eslint/no-unsafe-member-access'
                })

            elif category == 'type_error':
                rules.append({
                    'rule': 'strict-type-checking',
                    'description': 'Enforce strict type checking at compile time',
                    'reason': f'{len(category_patterns)} type errors caught',
                    'pattern': 'Enable strict: true in tsconfig.json',
                    'severity': 'error',
                    'affected_files': ['tsconfig.json'],
                    'config': {'strict': True, 'noImplicitAny': True}
                })

            elif category == 'async_error':
                rules.append({
                    'rule': 'require-async-error-handling',
                    'description': 'Require try-catch or .catch() for async operations',
                    'reason': f'{len(category_patterns)} unhandled promise rejections',
                    'pattern': 'try { await op() } catch (e) { handle(e) }',
                    'severity': 'warning',
                    'affected_files': ['*.ts', '*.tsx', '*.js'],
                    'eslint_rule': 'require-await-error-handling'
                })

            elif category == 'api_error':
                rules.append({
                    'rule': 'require-api-validation',
                    'description': 'Validate all API requests and responses',
                    'reason': f'{len(category_patterns)} API errors from invalid data',
                    'pattern': 'const validated = schema.parse(response)',
                    'severity': 'error',
                    'affected_files': ['**/api/**/*.ts', '**/routes/**/*.ts'],
                    'recommendation': 'Use Zod or ajv for runtime validation'
                })

        return rules

    def get_team_insights(self, days: int = 30) -> Dict:
        """
        Generate team insights dashboard data

        Args:
            days: Time window for analysis (default: 30 days)

        Returns:
            Dashboard metrics and insights

        Example:
            >>> analytics.get_team_insights()
            {
                'total_patterns': 150,
                'most_common_errors': [...],
                'trend': 'improving',
                'hotspots': ['auth/', 'api/'],
                'recommendations': [...]
            }
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Filter recent patterns
        recent_patterns = [
            p for p in self.patterns
            if datetime.fromisoformat(p.get('timestamp', '2000-01-01T00:00:00')) > cutoff_date
        ]

        # Category distribution
        category_counts = {
            cat: len(patterns)
            for cat, patterns in self.categories.items()
        }

        # File/module hotspots
        file_counter = Counter(p.get('file', 'unknown') for p in recent_patterns)
        project_counter = Counter(p.get('project', 'unknown') for p in recent_patterns)

        # Most common errors
        error_counter = Counter(p.get('error', '') for p in recent_patterns)

        # Trend analysis
        trend = self._analyze_trend(recent_patterns, days)

        return {
            'total_patterns': len(self.patterns),
            'recent_patterns': len(recent_patterns),
            'time_window_days': days,
            'category_distribution': category_counts,
            'most_common_errors': error_counter.most_common(10),
            'file_hotspots': file_counter.most_common(10),
            'project_hotspots': project_counter.most_common(5),
            'trend': trend,
            'recommendations': self._generate_recommendations(category_counts),
            'recurring_bugs': len(self.detect_recurring_bugs()),
            'constraint_rules_suggested': len(self.suggest_constraint_rules())
        }

    def _analyze_trend(self, patterns: List[Dict], days: int) -> str:
        """
        Analyze if bug rate is improving, stable, or worsening

        Returns:
            'improving', 'stable', or 'worsening'
        """
        if len(patterns) < 10:
            return 'insufficient_data'

        # Split into two halves
        mid = len(patterns) // 2
        first_half = patterns[:mid]
        second_half = patterns[mid:]

        # Compare bug rates
        first_rate = len(first_half) / (days / 2)
        second_rate = len(second_half) / (days / 2)

        if second_rate < first_rate * 0.8:
            return 'improving'
        elif second_rate > first_rate * 1.2:
            return 'worsening'
        else:
            return 'stable'

    def _generate_recommendations(self, category_counts: Dict[str, int]) -> List[str]:
        """
        Generate actionable recommendations based on category distribution

        Returns:
            List of recommendations
        """
        recommendations = []

        # Null pointer issues
        if category_counts.get('null_pointer', 0) > 5:
            recommendations.append(
                'High null pointer errors detected. Consider: '
                '(1) Enable strict null checks in TypeScript, '
                '(2) Use optional chaining (?.), '
                '(3) Add ESLint rule @typescript-eslint/no-unsafe-member-access'
            )

        # Type errors
        if category_counts.get('type_error', 0) > 5:
            recommendations.append(
                'Frequent type errors suggest weak type safety. '
                'Enable strict mode in tsconfig.json and run tsc --noEmit in CI'
            )

        # Async errors
        if category_counts.get('async_error', 0) > 5:
            recommendations.append(
                'Many unhandled promise rejections. '
                'Add global error handlers and use async/await with try-catch consistently'
            )

        # API errors
        if category_counts.get('api_error', 0) > 3:
            recommendations.append(
                'API integration issues detected. '
                'Implement schema validation (Zod/ajv) at API boundaries'
            )

        # Security
        if category_counts.get('security', 0) > 0:
            recommendations.append(
                'Security issues found. Run security audit (npm audit, Snyk) '
                'and review authentication/authorization patterns'
            )

        # Generic best practice
        if sum(category_counts.values()) > 20:
            recommendations.append(
                'Large number of patterns recorded. Great! '
                'Your team is building a valuable knowledge base. '
                'Consider sharing top patterns in weekly standup.'
            )

        return recommendations

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate comprehensive analytics report

        Args:
            output_file: Path to save report (optional)

        Returns:
            Report as markdown string
        """
        recurring = self.detect_recurring_bugs()
        constraints = self.suggest_constraint_rules()
        insights = self.get_team_insights()

        report_lines = [
            "# GUKS Analytics Report",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Total Patterns**: {insights['total_patterns']}",
            f"**Recent Patterns (30d)**: {insights['recent_patterns']}",
            f"**Trend**: {insights['trend'].title()}",
            "",
            "---",
            "",
            "## Recurring Bugs",
            "",
        ]

        if recurring:
            report_lines.append("| Pattern | Count | Projects | Urgency | Action |")
            report_lines.append("|---------|-------|----------|---------|--------|")
            for bug in recurring[:10]:
                report_lines.append(
                    f"| {bug['pattern'][:50]}... | {bug['count']} | "
                    f"{len(bug['projects'])} | {bug['urgency']} | "
                    f"{bug['suggested_action'][:40]}... |"
                )
        else:
            report_lines.append("*No recurring bugs detected*")

        report_lines.extend([
            "",
            "---",
            "",
            "## Suggested Constraint Rules",
            "",
        ])

        if constraints:
            for i, rule in enumerate(constraints, 1):
                report_lines.extend([
                    f"### {i}. {rule['rule']}",
                    "",
                    f"**Description**: {rule['description']}",
                    f"**Reason**: {rule['reason']}",
                    f"**Severity**: {rule['severity']}",
                    f"**Pattern**: `{rule['pattern']}`",
                    "",
                ])
        else:
            report_lines.append("*No constraint rules suggested yet (need more data)*")

        report_lines.extend([
            "",
            "---",
            "",
            "## Team Insights",
            "",
            "### Category Distribution",
            "",
        ])

        for category, count in sorted(
            insights['category_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            report_lines.append(f"- **{category.replace('_', ' ').title()}**: {count}")

        report_lines.extend([
            "",
            "### Hotspots",
            "",
        ])

        if insights['file_hotspots']:
            report_lines.append("**Files with most issues**:")
            for file, count in insights['file_hotspots'][:5]:
                report_lines.append(f"- `{file}`: {count} issues")

        report_lines.extend([
            "",
            "### Recommendations",
            "",
        ])

        for rec in insights['recommendations']:
            report_lines.append(f"- {rec}")

        report = "\n".join(report_lines)

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"Report saved to {output_path}")

        return report


if __name__ == "__main__":
    # Test with sample patterns
    print("Testing GUKS Analytics Engine...\n")

    # Load patterns (or create samples)
    from pathlib import Path
    import json

    patterns_file = Path.home() / ".grokflow" / "guks" / "patterns.json"

    if patterns_file.exists():
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
    else:
        # Create test patterns
        patterns = [
            {
                'error': 'TypeError: Cannot read property "name" of undefined',
                'fix': 'Added null check: if (user) { user.name }',
                'file': 'api.js',
                'project': 'user-service',
                'timestamp': '2025-11-15T10:30:00'
            },
            {
                'error': 'TypeError: Cannot read property "email" of undefined',
                'fix': 'Added null check: if (user) { user.email }',
                'file': 'auth.js',
                'project': 'user-service',
                'timestamp': '2025-11-20T14:20:00'
            },
            {
                'error': 'TypeError: Cannot read property "id" of undefined',
                'fix': 'Added null check: if (user) { user.id }',
                'file': 'profile.js',
                'project': 'frontend',
                'timestamp': '2025-12-01T09:15:00'
            },
            {
                'error': 'NullPointerException in getUserProfile',
                'fix': 'Added early return if user is null',
                'file': 'UserController.java',
                'project': 'auth-service',
                'timestamp': '2025-11-25T11:00:00'
            },
            {
                'error': 'UnhandledPromiseRejection in API call',
                'fix': 'Added try-catch around async function',
                'file': 'api.ts',
                'project': 'frontend',
                'timestamp': '2025-12-05T15:30:00'
            },
        ] * 3  # Create 15 patterns

    # Initialize analytics
    analytics = GUKSAnalytics(patterns)

    # Test 1: Detect recurring bugs
    print("=" * 60)
    print("TEST 1: Recurring Bug Detection")
    print("=" * 60)
    recurring = analytics.detect_recurring_bugs(min_count=2)
    print(f"\nFound {len(recurring)} recurring bug patterns:\n")

    for bug in recurring:
        print(f"Pattern: {bug['pattern']}")
        print(f"  Count: {bug['count']}")
        print(f"  Projects: {', '.join(bug['projects'])}")
        print(f"  Urgency: {bug['urgency']}")
        print(f"  Suggested Action: {bug['suggested_action']}")
        print()

    # Test 2: Constraint rules
    print("=" * 60)
    print("TEST 2: Constraint Rule Suggestions")
    print("=" * 60)
    constraints = analytics.suggest_constraint_rules()
    print(f"\nGenerated {len(constraints)} constraint rule suggestions:\n")

    for rule in constraints:
        print(f"Rule: {rule['rule']}")
        print(f"  Description: {rule['description']}")
        print(f"  Reason: {rule['reason']}")
        print(f"  Severity: {rule['severity']}")
        print()

    # Test 3: Team insights
    print("=" * 60)
    print("TEST 3: Team Insights Dashboard")
    print("=" * 60)
    insights = analytics.get_team_insights()
    print(f"\nTotal patterns: {insights['total_patterns']}")
    print(f"Trend: {insights['trend']}")
    print(f"\nCategory distribution:")
    for cat, count in sorted(insights['category_distribution'].items(),
                              key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    print(f"\nRecommendations:")
    for rec in insights['recommendations']:
        print(f"  - {rec}")

    # Test 4: Generate report
    print("\n" + "=" * 60)
    print("TEST 4: Generate Full Report")
    print("=" * 60)
    report = analytics.generate_report()
    print("\n" + report[:500] + "...\n")

    print("✅ All analytics tests completed successfully!")
