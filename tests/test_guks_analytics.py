"""
GUKS Analytics Tests

Validates analytics engine functionality:
  - Recurring bug detection
  - Constraint rule generation
  - Team insights dashboard
  - Pattern categorization
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from grokflow.guks.analytics import GUKSAnalytics


def generate_test_patterns_with_recurring() -> list:
    """Generate test patterns with known recurring bugs"""
    patterns = []

    # Recurring null pointer errors (5 instances)
    null_pointer_templates = [
        ('TypeError: Cannot read property "name" of undefined', 'Added null check: if (user) { user.name }'),
        ('TypeError: Cannot read property "email" of undefined', 'Added null check: if (user) { user.email }'),
        ('TypeError: Cannot read property "id" of undefined', 'Added null check: if (user) { user.id }'),
        ('NullPointerException in getUser', 'Added early return if user is null'),
        ('TypeError: Cannot read property "profile" of undefined', 'Added null check: if (user) { user.profile }'),
    ]

    for i, (error, fix) in enumerate(null_pointer_templates):
        patterns.append({
            'error': error,
            'fix': fix,
            'file': f'api_{i}.js',
            'project': f'project_{i % 3}',  # Spread across 3 projects
            'timestamp': (datetime.now() - timedelta(days=i)).isoformat()
        })

    # Recurring async errors (4 instances)
    async_templates = [
        ('UnhandledPromiseRejection in fetchData', 'Added try-catch around async function'),
        ('UnhandledPromiseRejection in saveData', 'Added try-catch around async function'),
        ('UnhandledPromiseRejection in loadData', 'Added try-catch around async function'),
        ('UnhandledPromiseRejection in updateData', 'Added try-catch around async function'),
    ]

    for i, (error, fix) in enumerate(async_templates):
        patterns.append({
            'error': error,
            'fix': fix,
            'file': f'api_{i}.ts',
            'project': f'project_{i % 2}',  # Spread across 2 projects
            'timestamp': (datetime.now() - timedelta(days=i + 10)).isoformat()
        })

    # Type errors (3 instances)
    type_templates = [
        ('TypeError: Expected string but got number', 'Added type validation'),
        ('TypeError: Expected object but got null', 'Added type guard'),
        ('TypeError: Cannot call method on undefined', 'Added type check'),
    ]

    for i, (error, fix) in enumerate(type_templates):
        patterns.append({
            'error': error,
            'fix': fix,
            'file': f'utils_{i}.ts',
            'project': 'project_1',
            'timestamp': (datetime.now() - timedelta(days=i + 20)).isoformat()
        })

    # API errors (3 instances)
    api_templates = [
        ('API Error: 404 Not Found', 'Added endpoint existence check'),
        ('API Error: 500 Internal Server Error', 'Added error handling middleware'),
        ('API Error: 401 Unauthorized', 'Added authentication check'),
    ]

    for i, (error, fix) in enumerate(api_templates):
        patterns.append({
            'error': error,
            'fix': fix,
            'file': f'routes_{i}.js',
            'project': 'project_2',
            'timestamp': (datetime.now() - timedelta(days=i + 5)).isoformat()
        })

    # Security issue (1 instance - should trigger recommendation)
    patterns.append({
        'error': 'XSS vulnerability in user input',
        'fix': 'Added input sanitization',
        'file': 'auth.js',
        'project': 'project_1',
        'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
    })

    return patterns


class TestGUKSAnalytics:
    """Analytics engine test suite"""

    def test_pattern_categorization(self):
        """Test that patterns are categorized correctly"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        # Check categories exist
        assert 'null_pointer' in analytics.categories
        assert 'async_error' in analytics.categories
        assert 'type_error' in analytics.categories
        assert 'api_error' in analytics.categories
        assert 'security' in analytics.categories

        # Check counts (some overlap is expected, e.g., "TypeError" matches both null_pointer and type_error)
        # Categories match first keyword, so some TypeErrors go to null_pointer if they mention "null"
        assert len(analytics.categories['null_pointer']) >= 5
        assert len(analytics.categories['async_error']) >= 4
        assert len(analytics.categories['type_error']) >= 1  # At least one pure type error
        assert len(analytics.categories['api_error']) >= 3
        assert len(analytics.categories['security']) >= 1

        print("\n✅ Pattern categorization working correctly")
        print(f"   - Null pointer: {len(analytics.categories['null_pointer'])}")
        print(f"   - Async errors: {len(analytics.categories['async_error'])}")
        print(f"   - Type errors: {len(analytics.categories['type_error'])}")
        print(f"   - API errors: {len(analytics.categories['api_error'])}")
        print(f"   - Security: {len(analytics.categories['security'])}")

    def test_recurring_bug_detection(self):
        """Test that recurring bugs are detected accurately"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        # Detect recurring bugs (min_count=3)
        recurring = analytics.detect_recurring_bugs(min_count=3)

        print(f"\n✅ Recurring bug detection working")
        print(f"   Found {len(recurring)} recurring patterns")

        # Should find at least 1 recurring pattern
        # (normalization may group similar errors together)
        assert len(recurring) >= 1, f"Expected >= 1 recurring pattern, got {len(recurring)}"

        # Check structure
        for bug in recurring:
            assert 'pattern' in bug
            assert 'count' in bug
            assert 'projects' in bug
            assert 'urgency' in bug
            assert 'suggested_action' in bug
            assert bug['count'] >= 3

            print(f"\n   Pattern: {bug['pattern'][:50]}...")
            print(f"     Count: {bug['count']}")
            print(f"     Projects: {len(bug['projects'])}")
            print(f"     Urgency: {bug['urgency']}")

        # Check urgency levels are assigned
        urgency_levels = {bug['urgency'] for bug in recurring}
        assert len(urgency_levels) > 0

    def test_constraint_rule_generation(self):
        """Test that constraint rules are generated appropriately"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        constraints = analytics.suggest_constraint_rules()

        print(f"\n✅ Constraint rule generation working")
        print(f"   Generated {len(constraints)} rules")

        # Should generate rules for categories with >= 3 patterns
        assert len(constraints) >= 3, f"Expected >= 3 constraint rules, got {len(constraints)}"

        # Check rule structure
        for rule in constraints:
            assert 'rule' in rule
            assert 'description' in rule
            assert 'reason' in rule
            assert 'severity' in rule
            assert 'pattern' in rule
            assert 'affected_files' in rule

            print(f"\n   Rule: {rule['rule']}")
            print(f"     Reason: {rule['reason']}")
            print(f"     Severity: {rule['severity']}")

        # Check specific rules exist
        rule_names = {r['rule'] for r in constraints}
        assert 'require-null-checks' in rule_names
        assert 'require-async-error-handling' in rule_names

    def test_team_insights_dashboard(self):
        """Test that team insights dashboard provides useful metrics"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        insights = analytics.get_team_insights(days=30)

        print(f"\n✅ Team insights dashboard working")

        # Check all expected keys exist
        required_keys = [
            'total_patterns',
            'recent_patterns',
            'category_distribution',
            'most_common_errors',
            'file_hotspots',
            'project_hotspots',
            'trend',
            'recommendations'
        ]

        for key in required_keys:
            assert key in insights, f"Missing key: {key}"

        # Check values are reasonable
        assert insights['total_patterns'] == len(patterns)
        assert insights['recent_patterns'] <= insights['total_patterns']
        assert insights['trend'] in ['improving', 'stable', 'worsening', 'insufficient_data']

        print(f"   Total patterns: {insights['total_patterns']}")
        print(f"   Recent patterns: {insights['recent_patterns']}")
        print(f"   Trend: {insights['trend']}")
        print(f"   Recommendations: {len(insights['recommendations'])}")

        # Check recommendations exist for high-frequency categories
        assert len(insights['recommendations']) > 0

        # Print top recommendations
        for i, rec in enumerate(insights['recommendations'][:3], 1):
            print(f"   {i}. {rec[:60]}...")

    def test_hotspot_detection(self):
        """Test that file and project hotspots are identified"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        insights = analytics.get_team_insights()

        # Check hotspots exist
        assert len(insights['file_hotspots']) > 0
        assert len(insights['project_hotspots']) > 0

        print(f"\n✅ Hotspot detection working")
        print(f"   File hotspots: {len(insights['file_hotspots'])}")
        print(f"   Project hotspots: {len(insights['project_hotspots'])}")

        # Check hotspot format (file, count) tuples
        for file, count in insights['file_hotspots'][:3]:
            assert isinstance(file, str)
            assert isinstance(count, int)
            assert count > 0
            print(f"   - {file}: {count} issues")

    def test_report_generation(self):
        """Test that full report can be generated"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        report = analytics.generate_report()

        print(f"\n✅ Report generation working")

        # Check report contains expected sections
        assert '# GUKS Analytics Report' in report
        assert '## Recurring Bugs' in report
        assert '## Suggested Constraint Rules' in report
        assert '## Team Insights' in report

        # Check report has content
        assert len(report) > 500, f"Report too short: {len(report)} chars"

        print(f"   Report length: {len(report)} characters")
        print(f"   Report preview:\n{report[:200]}...")

    def test_urgency_calculation(self):
        """Test that urgency levels are calculated correctly"""
        patterns = generate_test_patterns_with_recurring()
        analytics = GUKSAnalytics(patterns)

        recurring = analytics.detect_recurring_bugs(min_count=3)

        print(f"\n✅ Urgency calculation working")

        # Check urgency levels
        urgency_counts = {}
        for bug in recurring:
            urgency = bug['urgency']
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1

        print(f"   Urgency distribution:")
        for level in ['critical', 'high', 'medium', 'low']:
            count = urgency_counts.get(level, 0)
            if count > 0:
                print(f"     {level}: {count}")

        # High-count bugs should have high/critical urgency
        high_count_bugs = [b for b in recurring if b['count'] >= 4]
        if high_count_bugs:
            assert all(b['urgency'] in ['high', 'critical'] for b in high_count_bugs)

    def test_error_normalization(self):
        """Test that similar errors are normalized correctly"""
        patterns = [
            {
                'error': 'TypeError: Cannot read property "name" of undefined',
                'fix': 'Added null check',
                'file': 'a.js',
                'project': 'p1',
                'timestamp': datetime.now().isoformat()
            },
            {
                'error': 'TypeError: Cannot read property "email" of undefined',
                'fix': 'Added null check',
                'file': 'b.js',
                'project': 'p1',
                'timestamp': datetime.now().isoformat()
            },
            {
                'error': 'TypeError: Cannot read property "id" of undefined',
                'fix': 'Added null check',
                'file': 'c.js',
                'project': 'p1',
                'timestamp': datetime.now().isoformat()
            },
        ]

        analytics = GUKSAnalytics(patterns)

        # Should detect as recurring (same normalized form)
        recurring = analytics.detect_recurring_bugs(min_count=3)

        print(f"\n✅ Error normalization working")
        print(f"   Normalized 3 similar errors into {len(recurring)} pattern(s)")

        assert len(recurring) == 1, f"Expected 1 recurring pattern, got {len(recurring)}"
        assert recurring[0]['count'] == 3

    def test_empty_patterns(self):
        """Test analytics with empty patterns (graceful handling)"""
        analytics = GUKSAnalytics([])

        # Should not crash
        recurring = analytics.detect_recurring_bugs()
        constraints = analytics.suggest_constraint_rules()
        insights = analytics.get_team_insights()
        report = analytics.generate_report()

        print(f"\n✅ Empty patterns handled gracefully")
        print(f"   Recurring bugs: {len(recurring)}")
        print(f"   Constraints: {len(constraints)}")
        print(f"   Report length: {len(report)}")

        assert len(recurring) == 0
        assert len(constraints) == 0
        assert insights['total_patterns'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
