"""
GrokFlow Test Suggester

Context-aware test suggestion system that analyzes the codebase and suggests
relevant tests based on:
- Modified files
- Code patterns
- Test coverage gaps
- Related test files

Features:
- Analyze modified files and suggest related tests
- Detect test file naming conventions
- Find tests that import modified modules
- Suggest tests based on code changes
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from grokflow.logging_config import get_logger

logger = get_logger('grokflow.test_suggester')


class SuggestionReason(Enum):
    """Reason for suggesting a test"""
    MODIFIED_SOURCE = "modified_source"  # Test file for modified source
    IMPORTS_MODIFIED = "imports_modified"  # Test imports modified module
    NAMING_CONVENTION = "naming_convention"  # Test follows naming convention
    SAME_DIRECTORY = "same_directory"  # Test in same directory
    PATTERN_MATCH = "pattern_match"  # Test name matches pattern
    INTEGRATION_TEST = "integration_test"  # Integration test for feature
    RELATED_FEATURE = "related_feature"  # Tests related functionality


@dataclass
class TestSuggestion:
    """A suggested test with metadata"""
    test_path: Path
    reason: SuggestionReason
    confidence: float  # 0.0 to 1.0
    related_file: Optional[Path] = None
    description: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'test_path': str(self.test_path),
            'reason': self.reason.value,
            'confidence': self.confidence,
            'related_file': str(self.related_file) if self.related_file else None,
            'description': self.description
        }


@dataclass
class TestAnalysis:
    """Analysis result for test suggestions"""
    suggestions: List[TestSuggestion] = field(default_factory=list)
    modified_files: List[Path] = field(default_factory=list)
    test_files_found: int = 0
    total_confidence: float = 0.0

    def add_suggestion(self, suggestion: TestSuggestion) -> None:
        """Add a suggestion to the analysis"""
        self.suggestions.append(suggestion)
        self.total_confidence += suggestion.confidence

    def get_top_suggestions(self, n: int = 5) -> List[TestSuggestion]:
        """Get top N suggestions by confidence"""
        sorted_suggestions = sorted(
            self.suggestions,
            key=lambda s: s.confidence,
            reverse=True
        )
        return sorted_suggestions[:n]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'suggestions': [s.to_dict() for s in self.suggestions],
            'modified_files': [str(f) for f in self.modified_files],
            'test_files_found': self.test_files_found,
            'total_confidence': self.total_confidence
        }


class TestSuggester:
    """
    Context-aware test suggestion engine

    Analyzes modified files and suggests relevant tests to run.

    Example:
        >>> suggester = TestSuggester(workspace_path)
        >>> analysis = suggester.suggest_tests(['src/module.py'])
        >>> for suggestion in analysis.get_top_suggestions():
        ...     print(f"{suggestion.test_path}: {suggestion.reason.value}")
    """

    # Common test file patterns
    TEST_FILE_PATTERNS = [
        r'^test_.*\.py$',
        r'^.*_test\.py$',
        r'^tests?\.py$',
    ]

    # Test directory names
    TEST_DIRECTORIES = ['tests', 'test', 'testing', 'spec']

    # Import patterns to detect
    IMPORT_PATTERNS = [
        r'^from\s+(\S+)\s+import',
        r'^import\s+(\S+)',
    ]

    def __init__(
        self,
        workspace_path: Path,
        test_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ):
        """
        Initialize test suggester

        Args:
            workspace_path: Root path of the workspace
            test_patterns: Additional test file patterns
            exclude_patterns: Patterns to exclude from suggestions
        """
        self.workspace_path = Path(workspace_path)
        self.test_patterns = test_patterns or []
        self.exclude_patterns = exclude_patterns or [
            r'__pycache__',
            r'\.pyc$',
            r'\.git',
            r'\.venv',
            r'node_modules',
        ]

        # Compile patterns
        self._test_patterns = [
            re.compile(p) for p in self.TEST_FILE_PATTERNS + self.test_patterns
        ]
        self._exclude_patterns = [
            re.compile(p) for p in self.exclude_patterns
        ]
        self._import_patterns = [
            re.compile(p) for p in self.IMPORT_PATTERNS
        ]

        logger.info(f"TestSuggester initialized for: {workspace_path}")

    def suggest_tests(
        self,
        modified_files: List[str],
        include_integration: bool = True
    ) -> TestAnalysis:
        """
        Suggest tests based on modified files

        Args:
            modified_files: List of modified file paths
            include_integration: Include integration tests

        Returns:
            TestAnalysis with suggestions
        """
        analysis = TestAnalysis()
        analysis.modified_files = [Path(f) for f in modified_files]

        # Find all test files
        test_files = self._find_test_files()
        analysis.test_files_found = len(test_files)

        seen_tests: Set[Path] = set()

        for modified_file in analysis.modified_files:
            modified_path = Path(modified_file)

            # Strategy 1: Find test file by naming convention
            suggestions = self._find_by_naming_convention(modified_path, test_files)
            for suggestion in suggestions:
                if suggestion.test_path not in seen_tests:
                    analysis.add_suggestion(suggestion)
                    seen_tests.add(suggestion.test_path)

            # Strategy 2: Find tests that import this module
            suggestions = self._find_by_imports(modified_path, test_files)
            for suggestion in suggestions:
                if suggestion.test_path not in seen_tests:
                    analysis.add_suggestion(suggestion)
                    seen_tests.add(suggestion.test_path)

            # Strategy 3: Find tests in same directory
            suggestions = self._find_in_same_directory(modified_path, test_files)
            for suggestion in suggestions:
                if suggestion.test_path not in seen_tests:
                    analysis.add_suggestion(suggestion)
                    seen_tests.add(suggestion.test_path)

        # Strategy 4: Add integration tests if requested
        if include_integration:
            integration_tests = self._find_integration_tests(test_files)
            for test_path in integration_tests:
                if test_path not in seen_tests:
                    analysis.add_suggestion(TestSuggestion(
                        test_path=test_path,
                        reason=SuggestionReason.INTEGRATION_TEST,
                        confidence=0.5,
                        description="Integration test that may cover modified code"
                    ))
                    seen_tests.add(test_path)

        logger.info(f"Generated {len(analysis.suggestions)} test suggestions")
        return analysis

    def _find_test_files(self) -> List[Path]:
        """Find all test files in workspace"""
        test_files = []

        for pattern in self._test_patterns:
            for file_path in self.workspace_path.rglob('*.py'):
                if self._is_excluded(file_path):
                    continue
                if pattern.match(file_path.name):
                    test_files.append(file_path)

        # Remove duplicates
        return list(set(test_files))

    def _is_excluded(self, path: Path) -> bool:
        """Check if path should be excluded"""
        path_str = str(path)
        for pattern in self._exclude_patterns:
            if pattern.search(path_str):
                return True
        return False

    def _find_by_naming_convention(
        self,
        modified_file: Path,
        test_files: List[Path]
    ) -> List[TestSuggestion]:
        """Find tests by naming convention"""
        suggestions = []

        # Get base name without extension
        base_name = modified_file.stem

        # Common test file name patterns
        possible_names = [
            f'test_{base_name}.py',
            f'{base_name}_test.py',
            f'test_{base_name}s.py',  # plural
            f'tests_{base_name}.py',
        ]

        for test_path in test_files:
            if test_path.name in possible_names:
                suggestions.append(TestSuggestion(
                    test_path=test_path,
                    reason=SuggestionReason.NAMING_CONVENTION,
                    confidence=0.9,
                    related_file=modified_file,
                    description=f"Test file naming matches {modified_file.name}"
                ))

        return suggestions

    def _find_by_imports(
        self,
        modified_file: Path,
        test_files: List[Path]
    ) -> List[TestSuggestion]:
        """Find tests that import the modified module"""
        suggestions = []

        # Get module name from file path
        module_name = self._path_to_module_name(modified_file)
        if not module_name:
            return suggestions

        for test_path in test_files:
            try:
                content = test_path.read_text()
                imports = self._extract_imports(content)

                for imp in imports:
                    if module_name in imp or modified_file.stem in imp:
                        suggestions.append(TestSuggestion(
                            test_path=test_path,
                            reason=SuggestionReason.IMPORTS_MODIFIED,
                            confidence=0.85,
                            related_file=modified_file,
                            description=f"Test imports {module_name}"
                        ))
                        break
            except Exception as e:
                logger.debug(f"Could not read test file {test_path}: {e}")

        return suggestions

    def _find_in_same_directory(
        self,
        modified_file: Path,
        test_files: List[Path]
    ) -> List[TestSuggestion]:
        """Find tests in the same directory"""
        suggestions = []

        modified_dir = modified_file.parent

        for test_path in test_files:
            # Check if test is in same directory or in a tests subdirectory
            if test_path.parent == modified_dir:
                suggestions.append(TestSuggestion(
                    test_path=test_path,
                    reason=SuggestionReason.SAME_DIRECTORY,
                    confidence=0.6,
                    related_file=modified_file,
                    description=f"Test in same directory as {modified_file.name}"
                ))
            elif test_path.parent.name in self.TEST_DIRECTORIES:
                if test_path.parent.parent == modified_dir.parent:
                    suggestions.append(TestSuggestion(
                        test_path=test_path,
                        reason=SuggestionReason.SAME_DIRECTORY,
                        confidence=0.5,
                        related_file=modified_file,
                        description=f"Test in tests/ directory near {modified_file.name}"
                    ))

        return suggestions

    def _find_integration_tests(self, test_files: List[Path]) -> List[Path]:
        """Find integration test files"""
        integration_tests = []

        for test_path in test_files:
            # Check directory name
            if 'integration' in test_path.parent.name.lower():
                integration_tests.append(test_path)
            # Check file name
            elif 'integration' in test_path.name.lower():
                integration_tests.append(test_path)
            elif 'e2e' in test_path.name.lower():
                integration_tests.append(test_path)

        return integration_tests

    def _path_to_module_name(self, file_path: Path) -> Optional[str]:
        """Convert file path to Python module name"""
        try:
            # Get relative path from workspace
            rel_path = file_path.relative_to(self.workspace_path)

            # Convert path to module name
            parts = list(rel_path.parts)
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]  # Remove .py

            return '.'.join(parts)
        except ValueError:
            return file_path.stem

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Python code"""
        imports = []

        for line in content.split('\n'):
            line = line.strip()
            for pattern in self._import_patterns:
                match = pattern.match(line)
                if match:
                    imports.append(match.group(1))
                    break

        return imports

    def get_test_coverage_map(self) -> Dict[str, List[Path]]:
        """
        Build a map of source files to their test files

        Returns:
            Dictionary mapping source file names to test file paths
        """
        coverage_map: Dict[str, List[Path]] = {}
        test_files = self._find_test_files()

        # Find all Python source files (non-test)
        source_files = []
        for file_path in self.workspace_path.rglob('*.py'):
            if self._is_excluded(file_path):
                continue
            if file_path not in test_files:
                source_files.append(file_path)

        for source_file in source_files:
            source_key = str(source_file.relative_to(self.workspace_path))

            # Find tests for this source file
            analysis = self.suggest_tests([str(source_file)], include_integration=False)

            if analysis.suggestions:
                coverage_map[source_key] = [s.test_path for s in analysis.suggestions]
            else:
                coverage_map[source_key] = []

        return coverage_map

    def find_untested_files(self) -> List[Path]:
        """
        Find source files without any associated tests

        Returns:
            List of source file paths without tests
        """
        coverage_map = self.get_test_coverage_map()

        untested = []
        for source_file, tests in coverage_map.items():
            if not tests:
                untested.append(self.workspace_path / source_file)

        return untested


# Global instance
_global_suggester: Optional[TestSuggester] = None


def get_test_suggester(
    workspace_path: Optional[Path] = None,
    force_new: bool = False
) -> TestSuggester:
    """
    Get global test suggester instance

    Args:
        workspace_path: Workspace path (defaults to current directory)
        force_new: Force new instance

    Returns:
        TestSuggester instance
    """
    global _global_suggester

    if _global_suggester is None or force_new:
        path = workspace_path or Path.cwd()
        _global_suggester = TestSuggester(path)

    return _global_suggester
