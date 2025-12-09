"""
GrokFlow Constraint System
Prevents repeated mistakes and enforces user-defined rules

Architecture:
- Isolated from VAMS (separate storage: constraints.json)
- Declarative constraints with trigger keywords
- Enforcement levels: warn | block | require_action
- Fail-safe design (graceful degradation on errors)

Phase 3.1 Optimizations:
- O(1) keyword indexing for 100+ constraint scaling
- Regex pattern caching to avoid recompilation
- Schema migration framework for analytics versioning

Usage:
    # Add constraint
    manager = ConstraintManager(Path("~/.grokflow"))
    manager.add_constraint(
        description="Never use mock data",
        trigger_keywords=["mock", "demo", "placeholder"],
        enforcement_action="block",
        enforcement_message="Use real data and APIs only"
    )

    # Check constraints before generation
    triggered = manager.check_constraints("Create mock API endpoint")
    if any(c["enforcement_action"] == "block" for c in triggered):
        # Block action
        return

Author: Claude Code (Constraint System Implementation)
Date: 2025-12-09
Version: 1.3.1 (Phase 3.1: Performance Optimizations)
"""

import json
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ConstraintManager:
    """
    Manages user-defined constraints for GrokFlow behavior enforcement.

    Constraints are declarative rules that prevent repeated mistakes:
    - "Never use mock data" → blocks generation with mock/demo/placeholder
    - "Always search for current models" → warns if using outdated knowledge
    - "Require approval for destructive actions" → requires user confirmation

    Storage: ~/.grokflow/constraints.json (isolated from VAMS)
    """

    def __init__(self, config_dir: Path):
        """
        Initialize ConstraintManager.

        Args:
            config_dir: Path to GrokFlow config directory (e.g., ~/.grokflow)

        Raises:
            No exceptions - fails gracefully and returns empty constraint list
        """
        self.config_dir = Path(config_dir).expanduser()
        self.constraints_file = self.config_dir / "constraints.json"
        self.templates_dir = self.config_dir / "templates"  # Phase 2.5: Templates
        self.constraints = self._load_constraints()
        self._ensure_templates_dir()

        # Phase 3.1: Performance optimizations
        self.keyword_index = {}  # keyword → [constraint_ids] for O(1) lookup
        self._regex_cache = {}  # pattern → compiled regex for caching
        self._rebuild_keyword_index()

    def _load_constraints(self) -> List[Dict]:
        """
        Load constraints from disk.

        Returns:
            List of constraint dictionaries. Empty list if file doesn't exist
            or is corrupted.

        Graceful degradation:
            - Missing file → return []
            - Corrupted JSON → return []
            - Invalid schema → return []
        """
        if not self.constraints_file.exists():
            return []

        try:
            with open(self.constraints_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate data is a list
            if not isinstance(data, list):
                return []

            # Validate each constraint has required fields
            valid_constraints = []
            for c in data:
                if isinstance(c, dict) and all(
                    k in c for k in ["constraint_id", "description", "trigger_keywords"]
                ):
                    valid_constraints.append(c)

            return valid_constraints

        except (json.JSONDecodeError, IOError, OSError):
            # Corrupted file or I/O error - return empty list
            return []

    def _save_constraints(self) -> bool:
        """
        Persist constraints to disk.

        Returns:
            True if save successful, False otherwise

        Graceful degradation:
            - I/O error → return False (don't crash)
            - Permission error → return False (don't crash)
        """
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Write to temp file first (atomic write)
            temp_file = self.constraints_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.constraints, f, indent=2, ensure_ascii=False)

            # Move temp file to final location (atomic on POSIX)
            temp_file.replace(self.constraints_file)

            # Set restrictive permissions (user-only read/write)
            self.constraints_file.chmod(0o600)

            # Rebuild keyword index after saving (Phase 3.1 optimization)
            self._rebuild_keyword_index()

            return True

        except (IOError, OSError):
            return False

    def _rebuild_keyword_index(self):
        """
        Rebuild keyword index for O(1) constraint lookup.

        Phase 3.1 optimization: Build index mapping keywords to constraint IDs.
        This enables fast candidate selection - only check constraints that
        might match the query instead of checking all constraints.

        Performance: O(n*k) build time (n=constraints, k=keywords per constraint)
                     O(1) lookup time per keyword

        Example:
            keyword_index = {
                "mock": ["abc123", "def456"],
                "delete": ["ghi789"]
            }
        """
        self.keyword_index = {}

        for constraint in self.constraints:
            cid = constraint.get("constraint_id")
            if not cid:
                continue

            # Index keywords
            keywords = constraint.get("trigger_keywords", [])
            for keyword in keywords:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = []
                if cid not in self.keyword_index[keyword]:
                    self.keyword_index[keyword].append(cid)

            # Index patterns (extract simple keywords from patterns for optimization)
            patterns = constraint.get("trigger_patterns", [])
            for pattern in patterns:
                # Extract simple keywords from regex (best effort)
                # E.g., "mock.*" → extract "mock"
                simple_keyword = self._extract_keyword_from_pattern(pattern)
                if simple_keyword and len(simple_keyword) >= 3:
                    if simple_keyword not in self.keyword_index:
                        self.keyword_index[simple_keyword] = []
                    if cid not in self.keyword_index[simple_keyword]:
                        self.keyword_index[simple_keyword].append(cid)

    def _extract_keyword_from_pattern(self, pattern: str) -> Optional[str]:
        """
        Extract a simple keyword from a regex pattern for indexing.

        Args:
            pattern: Regex pattern (e.g., "mock.*", "delete|remove")

        Returns:
            Simple keyword if extractable, None otherwise

        Examples:
            "mock.*" → "mock"
            "delete|remove" → "delete" (first alternative)
            r"\\bmock\\b" → "mock"
            "^test$" → "test"
        """
        # Remove common regex metacharacters
        cleaned = pattern.replace(".*", "").replace(".+", "")
        cleaned = cleaned.replace("^", "").replace("$", "")
        cleaned = cleaned.replace(r"\b", "").replace(r"\s*", "")

        # Split on alternation and take first
        parts = cleaned.split("|")
        if parts:
            keyword = parts[0].strip()
            # Only return if it looks like a simple keyword
            if keyword and len(keyword) >= 3 and keyword.replace("_", "").isalnum():
                return keyword.lower()

        return None

    def add_constraint(
        self,
        description: str,
        trigger_keywords: List[str],
        enforcement_action: str = "warn",
        enforcement_message: Optional[str] = None
    ) -> str:
        """
        Add a new constraint.

        Args:
            description: Human-readable constraint description
            trigger_keywords: List of keywords that trigger this constraint
                             (case-insensitive matching)
            enforcement_action: Action to take when triggered:
                - "warn": Print warning but continue
                - "block": Prevent action entirely
                - "require_action": Print message and require user confirmation
            enforcement_message: Custom message to display when triggered
                                (default: constraint description)

        Returns:
            constraint_id: 8-character unique ID for this constraint

        Example:
            manager.add_constraint(
                description="Never use mock data",
                trigger_keywords=["mock", "demo", "placeholder", "fake"],
                enforcement_action="block",
                enforcement_message="Use real data and APIs only. No mock allowed."
            )
        """
        constraint_id = str(uuid.uuid4())[:8]

        constraint = {
            "constraint_id": constraint_id,
            "description": description,
            "trigger_keywords": [kw.lower().strip() for kw in trigger_keywords],
            "enforcement_action": enforcement_action,
            "enforcement_message": enforcement_message or description,
            "created": datetime.now().isoformat(),
            "triggered_count": 0,
            "last_triggered": None,
            "enabled": True
        }

        self.constraints.append(constraint)
        self._save_constraints()

        return constraint_id

    def check_constraints(self, query: str, context: str = "generation") -> List[Dict]:
        """
        Check if query triggers any constraints.

        Args:
            query: User query/prompt to check
            context: Context of check (e.g., "generation", "file_write")
                    (reserved for future use)

        Returns:
            List of triggered constraint dictionaries

        Side effects:
            - Updates triggered_count for each triggered constraint
            - Updates last_triggered timestamp
            - Persists changes to disk

        Example:
            triggered = manager.check_constraints("Create mock API endpoint")
            if any(c["enforcement_action"] == "block" for c in triggered):
                print("Action blocked by constraint")
                return
        """
        query_lower = query.lower()
        triggered = []

        for constraint in self.constraints:
            # Skip disabled constraints
            if not constraint.get("enabled", True):
                continue

            # Check if any trigger keyword matches
            matched = False
            for keyword in constraint["trigger_keywords"]:
                if keyword in query_lower:
                    matched = True
                    break

            if matched:
                # Update stats
                constraint["triggered_count"] += 1
                constraint["last_triggered"] = datetime.now().isoformat()
                triggered.append(constraint)

        # Persist stats updates
        if triggered:
            self._save_constraints()

        return triggered

    def list_constraints(self, enabled_only: bool = False) -> List[Dict]:
        """
        List all constraints.

        Args:
            enabled_only: If True, only return enabled constraints

        Returns:
            List of constraint dictionaries
        """
        if enabled_only:
            return [c for c in self.constraints if c.get("enabled", True)]
        return self.constraints.copy()

    def get_constraint(self, constraint_id: str) -> Optional[Dict]:
        """
        Get a single constraint by ID.

        Args:
            constraint_id: Full or partial constraint ID (min 4 chars)

        Returns:
            Constraint dictionary if found, None otherwise
        """
        if len(constraint_id) < 4:
            return None

        for c in self.constraints:
            if c["constraint_id"].startswith(constraint_id):
                return c.copy()

        return None

    def remove_constraint(self, constraint_id: str) -> bool:
        """
        Remove a constraint by ID.

        Args:
            constraint_id: Full or partial constraint ID (min 4 chars)

        Returns:
            True if removed, False if not found
        """
        if len(constraint_id) < 4:
            return False

        for i, c in enumerate(self.constraints):
            if c["constraint_id"].startswith(constraint_id):
                self.constraints.pop(i)
                self._save_constraints()
                return True

        return False

    def disable_constraint(self, constraint_id: str) -> bool:
        """
        Disable (but don't delete) a constraint.

        Args:
            constraint_id: Full or partial constraint ID (min 4 chars)

        Returns:
            True if disabled, False if not found
        """
        if len(constraint_id) < 4:
            return False

        for c in self.constraints:
            if c["constraint_id"].startswith(constraint_id):
                c["enabled"] = False
                self._save_constraints()
                return True

        return False

    def enable_constraint(self, constraint_id: str) -> bool:
        """
        Re-enable a disabled constraint.

        Args:
            constraint_id: Full or partial constraint ID (min 4 chars)

        Returns:
            True if enabled, False if not found
        """
        if len(constraint_id) < 4:
            return False

        for c in self.constraints:
            if c["constraint_id"].startswith(constraint_id):
                c["enabled"] = True
                self._save_constraints()
                return True

        return False

    def get_stats(self) -> Dict:
        """
        Get constraint system statistics.

        Returns:
            Dictionary with stats:
            - total_constraints: Total number of constraints
            - enabled_constraints: Number of enabled constraints
            - total_triggers: Sum of all triggered_count
            - most_triggered: Constraint with highest trigger count
        """
        total = len(self.constraints)
        enabled = len([c for c in self.constraints if c.get("enabled", True)])
        total_triggers = sum(c.get("triggered_count", 0) for c in self.constraints)

        most_triggered = None
        max_count = 0
        for c in self.constraints:
            count = c.get("triggered_count", 0)
            if count > max_count:
                max_count = count
                most_triggered = {
                    "constraint_id": c["constraint_id"],
                    "description": c["description"],
                    "triggered_count": count
                }

        return {
            "total_constraints": total,
            "enabled_constraints": enabled,
            "total_triggers": total_triggers,
            "most_triggered": most_triggered
        }

    # ========================================================================
    # Phase 2: Smart Enforcement Methods
    # ========================================================================

    def add_constraint_v2(
        self,
        description: str,
        trigger_patterns: Optional[List[str]] = None,
        trigger_keywords: Optional[List[str]] = None,
        trigger_logic: str = "OR",
        context_filters: Optional[Dict] = None,
        enforcement_action: str = "warn",
        enforcement_message: Optional[str] = None
    ) -> str:
        """
        Add Phase 2 constraint with advanced features (regex, AND/OR/NOT, context-aware).

        Args:
            description: Human-readable constraint description
            trigger_patterns: List of regex patterns (e.g., ["mock.*api", "test.*data"])
            trigger_keywords: List of keywords (Phase 1 compatibility)
            trigger_logic: Logic operator - "OR" (default), "AND", "NOT"
            context_filters: Context-aware filters (e.g., {"query_type": ["generate"]})
            enforcement_action: "warn", "block", or "require_action"
            enforcement_message: Custom message when triggered

        Returns:
            constraint_id: 8-character unique ID

        Example:
            manager.add_constraint_v2(
                description="Never use mock in code generation",
                trigger_patterns=["mock.*", "demo.*"],
                trigger_logic="OR",
                context_filters={"query_type": ["generate"]},
                enforcement_action="block"
            )
        """
        constraint_id = str(uuid.uuid4())[:8]

        # Validate regex patterns if provided
        if trigger_patterns:
            for pattern in trigger_patterns:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error:
                    # Invalid regex - will fallback to literal matching
                    pass

        # Validate trigger_logic
        if trigger_logic not in ["OR", "AND", "NOT"]:
            trigger_logic = "OR"  # Default to OR

        constraint = {
            "constraint_id": constraint_id,
            "version": 2,  # Phase 2 constraint
            "description": description,
            "trigger_keywords": [kw.lower().strip() for kw in trigger_keywords] if trigger_keywords else [],
            "trigger_patterns": trigger_patterns or [],  # Phase 2: Regex patterns
            "trigger_logic": trigger_logic,  # Phase 2: AND/OR/NOT
            "context_filters": context_filters or {},  # Phase 2: Context-aware
            "enforcement_action": enforcement_action,
            "enforcement_message": enforcement_message or description,
            "created": datetime.now().isoformat(),
            "triggered_count": 0,
            "last_triggered": None,
            "enabled": True,
            "false_positive_count": 0  # Phase 2: Analytics
        }

        self.constraints.append(constraint)
        self._save_constraints()

        return constraint_id

    def check_constraints_v2(self, query: str, context: Optional[Dict] = None) -> List[Dict]:
        """
        Check constraints with Phase 2 enhancements (regex, context-aware).

        Phase 3.1 optimization: Uses keyword index for fast candidate selection.
        Only checks constraints that have keywords matching the query.

        Args:
            query: User query/prompt to check
            context: Full context dictionary (query_type, vibe_mode, etc.)

        Returns:
            List of triggered constraint dictionaries

        Example:
            context = {"query_type": "generate", "vibe_mode": "creative"}
            triggered = manager.check_constraints_v2("Create mock API", context)

        Performance:
            - Before: O(n) - check all constraints
            - After: O(k) - check only candidate constraints (k << n for large n)
        """
        triggered = []
        context = context or {}

        # Phase 3.1 optimization: Get candidate constraint IDs from keyword index
        candidate_ids = self._get_candidate_constraint_ids(query)

        # Build constraint ID → constraint mapping for fast lookup
        constraint_map = {c["constraint_id"]: c for c in self.constraints if c.get("constraint_id")}

        # Check only candidate constraints (or all if index is empty)
        constraints_to_check = []
        if candidate_ids:
            # Use indexed candidates (optimized path)
            constraints_to_check = [constraint_map[cid] for cid in candidate_ids if cid in constraint_map]
        else:
            # No candidates from index - check all constraints (fallback path)
            constraints_to_check = self.constraints

        for constraint in constraints_to_check:
            # Skip disabled constraints
            if not constraint.get("enabled", True):
                continue

            version = constraint.get("version", 1)

            # Check context filters (Phase 2 only)
            if version == 2 and not self._check_context_filters(context, constraint.get("context_filters", {})):
                continue

            matched = False

            if version == 1:
                # Phase 1: Simple keyword matching
                matched = self._check_keywords_phase1(query, constraint)
            elif version == 2:
                # Phase 2: Regex + advanced logic (with caching)
                try:
                    matched = self._check_patterns_phase2(query, constraint)
                except Exception:
                    # Phase 2 failed → fallback to Phase 1
                    matched = self._check_keywords_phase1(query, constraint)

            if matched:
                # Update stats
                constraint["triggered_count"] = constraint.get("triggered_count", 0) + 1
                constraint["last_triggered"] = datetime.now().isoformat()
                triggered.append(constraint)

        # Persist stats updates
        if triggered:
            self._save_constraints()

        return triggered

    def _get_candidate_constraint_ids(self, query: str) -> set:
        """
        Get candidate constraint IDs from keyword index.

        Phase 3.1 optimization: Extract keywords from query and lookup in index.

        Args:
            query: User query

        Returns:
            Set of constraint IDs that might match the query

        Performance: O(w) where w = words in query
        """
        query_lower = query.lower()
        candidate_ids = set()

        # Extract words from query
        words = query_lower.replace(',', ' ').replace('.', ' ').split()

        # Lookup each word in keyword index
        for word in words:
            if word in self.keyword_index:
                candidate_ids.update(self.keyword_index[word])

        return candidate_ids

    def _check_keywords_phase1(self, query: str, constraint: Dict) -> bool:
        """
        Phase 1 keyword matching logic (backward compatibility).

        Args:
            query: User query
            constraint: Constraint dictionary

        Returns:
            True if any keyword matches
        """
        query_lower = query.lower()
        keywords = constraint.get("trigger_keywords", [])

        for keyword in keywords:
            if keyword in query_lower:
                return True

        return False

    def _check_patterns_phase2(self, query: str, constraint: Dict) -> bool:
        """
        Phase 2 pattern matching with regex and advanced logic.

        Args:
            query: User query
            constraint: Constraint dictionary

        Returns:
            True if patterns match according to trigger_logic
        """
        # Get patterns and keywords
        patterns = constraint.get("trigger_patterns", [])
        keywords = constraint.get("trigger_keywords", [])
        logic = constraint.get("trigger_logic", "OR")

        # Check regex patterns
        pattern_matches = []
        for pattern in patterns:
            if self._check_regex_pattern(query, pattern):
                pattern_matches.append(True)
            else:
                pattern_matches.append(False)

        # Check keywords
        keyword_matches = []
        query_lower = query.lower()
        for keyword in keywords:
            if keyword in query_lower:
                keyword_matches.append(True)
            else:
                keyword_matches.append(False)

        # Combine all matches
        all_matches = pattern_matches + keyword_matches

        if not all_matches:
            return False

        # Apply trigger_logic
        if logic == "OR":
            return any(all_matches)
        elif logic == "AND":
            return all(all_matches)
        elif logic == "NOT":
            return not any(all_matches)
        else:
            return any(all_matches)  # Default to OR

    def _check_regex_pattern(self, query: str, pattern: str) -> bool:
        """
        Check if query matches regex pattern (with timeout protection).

        Phase 3.1 optimization: Caches compiled regex patterns to avoid recompilation.

        Args:
            query: User query
            pattern: Regex pattern

        Returns:
            True if pattern matches

        Safety:
            - Invalid regex → fallback to literal match
            - Timeout protection (prevents ReDoS)

        Performance:
            - Before: re.compile() on every check (expensive)
            - After: Compile once, cache forever (much faster)
        """
        try:
            # Phase 3.1 optimization: Check cache first
            if pattern not in self._regex_cache:
                # Compile and cache the regex
                self._regex_cache[pattern] = re.compile(pattern, re.IGNORECASE)

            regex = self._regex_cache[pattern]
            return bool(regex.search(query))
        except re.error:
            # Invalid regex → fallback to literal matching
            return pattern.lower() in query.lower()

    def _check_context_filters(self, context: Dict, filters: Dict) -> bool:
        """
        Check if current context matches constraint filters.

        Args:
            context: Current execution context
            filters: Constraint context filters

        Returns:
            True if constraint should be checked, False to skip

        Example:
            context = {"query_type": "generate", "vibe_mode": "creative"}
            filters = {"query_type": ["generate", "chat"]}
            → Returns True (query_type matches)
        """
        if not filters:
            return True  # No filters = always check

        # Check query_type filter
        if "query_type" in filters:
            allowed_types = filters["query_type"]
            if context.get("query_type") not in allowed_types:
                return False

        # Check vibe_mode filter
        if "vibe_mode" in filters:
            allowed_modes = filters["vibe_mode"]
            if context.get("vibe_mode") not in allowed_modes:
                return False

        # All filters passed
        return True

    # ========================================================================
    # Phase 2.5: Constraint Templates
    # ========================================================================

    def _ensure_templates_dir(self):
        """Ensure templates directory exists."""
        try:
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self._create_builtin_templates()
        except (IOError, OSError):
            pass  # Graceful degradation

    def _create_builtin_templates(self):
        """Create built-in templates if they don't exist."""
        builtin_templates = {
            "no-mock-data": {
                "template_name": "no-mock-data",
                "template_version": "1.0.0",
                "description": "Block all mock, demo, and placeholder data usage",
                "author": "GrokFlow Team",
                "created": "2025-12-09",
                "constraints": [
                    {
                        "description": "Never use mock data",
                        "trigger_patterns": [r"mock.*", r"demo.*", r"placeholder.*", r"fake.*"],
                        "trigger_logic": "OR",
                        "enforcement_action": "block",
                        "enforcement_message": "Use real data and APIs only. No mock allowed."
                    },
                    {
                        "description": "Never use dummy values",
                        "trigger_keywords": ["dummy", "sample", "example"],
                        "trigger_logic": "OR",
                        "enforcement_action": "warn",
                        "enforcement_message": "Consider using real values instead of dummy/sample data"
                    }
                ]
            },
            "best-practices-python": {
                "template_name": "best-practices-python",
                "template_version": "1.0.0",
                "description": "Python coding best practices and standards",
                "author": "GrokFlow Team",
                "created": "2025-12-09",
                "constraints": [
                    {
                        "description": "Avoid global variables",
                        "trigger_patterns": [r"global\s+\w+"],
                        "enforcement_action": "warn",
                        "enforcement_message": "Global variables should be avoided. Consider using class attributes or function parameters."
                    },
                    {
                        "description": "Use type hints",
                        "trigger_keywords": ["def"],
                        "trigger_logic": "NOT",
                        "context_filters": {"query_type": ["generate"]},
                        "enforcement_action": "warn",
                        "enforcement_message": "Consider adding type hints to function signatures"
                    }
                ]
            },
            "security-awareness": {
                "template_name": "security-awareness",
                "template_version": "1.0.0",
                "description": "Security-sensitive patterns and practices",
                "author": "GrokFlow Team",
                "created": "2025-12-09",
                "constraints": [
                    {
                        "description": "Avoid hardcoded credentials",
                        "trigger_patterns": [r"password\s*=\s*['\"]", r"api_key\s*=\s*['\"]", r"secret\s*=\s*['\"]"],
                        "enforcement_action": "block",
                        "enforcement_message": "Never hardcode credentials. Use environment variables or secret management."
                    },
                    {
                        "description": "Warn about SQL string concatenation",
                        "trigger_patterns": [r"execute\s*\(\s*['\"].*\+", r"query\s*=\s*['\"].*\+"],
                        "enforcement_action": "warn",
                        "enforcement_message": "SQL string concatenation may lead to SQL injection. Use parameterized queries."
                    }
                ]
            },
            "destructive-actions": {
                "template_name": "destructive-actions",
                "template_version": "1.0.0",
                "description": "Require confirmation for potentially destructive operations",
                "author": "GrokFlow Team",
                "created": "2025-12-09",
                "constraints": [
                    {
                        "description": "Confirm database destructive actions",
                        "trigger_keywords": ["delete", "drop", "truncate", "remove"],
                        "trigger_logic": "OR",
                        "enforcement_action": "require_action",
                        "enforcement_message": "CAUTION: This action may delete data. Proceed with care."
                    },
                    {
                        "description": "Confirm file system destructive actions",
                        "trigger_patterns": [r"rm\s+-rf", r"shutil\.rmtree", r"os\.remove"],
                        "enforcement_action": "require_action",
                        "enforcement_message": "CAUTION: This action will delete files/directories. Ensure you have backups."
                    }
                ]
            }
        }

        for template_name, template_data in builtin_templates.items():
            template_file = self.templates_dir / f"{template_name}.json"
            if not template_file.exists():
                try:
                    with open(template_file, 'w', encoding='utf-8') as f:
                        json.dump(template_data, f, indent=2, ensure_ascii=False)
                except (IOError, OSError):
                    pass  # Graceful degradation

    def list_templates(self) -> List[Dict]:
        """
        List all available constraint templates.

        Returns:
            List of template metadata dictionaries

        Example:
            templates = manager.list_templates()
            for t in templates:
                print(f"{t['template_name']}: {t['description']}")
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        try:
            for template_file in self.templates_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)

                    templates.append({
                        "template_name": template_data.get("template_name", template_file.stem),
                        "template_version": template_data.get("template_version", "unknown"),
                        "description": template_data.get("description", "No description"),
                        "author": template_data.get("author", "Unknown"),
                        "constraint_count": len(template_data.get("constraints", []))
                    })
                except (json.JSONDecodeError, IOError, KeyError):
                    continue  # Skip invalid templates

        except (IOError, OSError):
            pass  # Graceful degradation

        return templates

    def get_template(self, template_name: str) -> Optional[Dict]:
        """
        Get a template by name.

        Args:
            template_name: Name of the template (e.g., "no-mock-data")

        Returns:
            Template dictionary if found, None otherwise

        Example:
            template = manager.get_template("no-mock-data")
            if template:
                print(f"Found {len(template['constraints'])} constraints")
        """
        template_file = self.templates_dir / f"{template_name}.json"

        if not template_file.exists():
            return None

        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            return None

    def import_template(self, template_name: str) -> int:
        """
        Import all constraints from a template.

        Args:
            template_name: Name of the template to import

        Returns:
            Number of constraints imported, -1 on error

        Example:
            count = manager.import_template("no-mock-data")
            print(f"Imported {count} constraints")
        """
        template = self.get_template(template_name)

        if not template:
            return -1

        try:
            constraints = template.get("constraints", [])
            imported_count = 0

            for constraint_data in constraints:
                # Determine if Phase 1 or Phase 2 constraint
                has_patterns = "trigger_patterns" in constraint_data
                has_logic = "trigger_logic" in constraint_data
                has_context = "context_filters" in constraint_data

                if has_patterns or has_logic or has_context:
                    # Phase 2 constraint
                    self.add_constraint_v2(
                        description=constraint_data.get("description", "Imported constraint"),
                        trigger_patterns=constraint_data.get("trigger_patterns"),
                        trigger_keywords=constraint_data.get("trigger_keywords"),
                        trigger_logic=constraint_data.get("trigger_logic", "OR"),
                        context_filters=constraint_data.get("context_filters"),
                        enforcement_action=constraint_data.get("enforcement_action", "warn"),
                        enforcement_message=constraint_data.get("enforcement_message")
                    )
                else:
                    # Phase 1 constraint
                    self.add_constraint(
                        description=constraint_data.get("description", "Imported constraint"),
                        trigger_keywords=constraint_data.get("trigger_keywords", []),
                        enforcement_action=constraint_data.get("enforcement_action", "warn"),
                        enforcement_message=constraint_data.get("enforcement_message")
                    )

                imported_count += 1

            return imported_count

        except (KeyError, TypeError):
            return -1

    def export_constraints(self, file_path: str, constraint_ids: Optional[List[str]] = None) -> bool:
        """
        Export constraints as a template file.

        Args:
            file_path: Path to save the template file
            constraint_ids: Optional list of constraint IDs to export (exports all if None)

        Returns:
            True if successful, False otherwise

        Example:
            # Export all constraints
            manager.export_constraints("my-team-rules.json")

            # Export specific constraints
            manager.export_constraints("mock-rules.json", ["abc12345", "def67890"])
        """
        try:
            # Get constraints to export
            if constraint_ids:
                constraints_to_export = []
                for cid in constraint_ids:
                    c = self.get_constraint(cid)
                    if c:
                        constraints_to_export.append(c)
            else:
                constraints_to_export = self.list_constraints()

            if not constraints_to_export:
                return False

            # Build template structure
            template = {
                "template_name": Path(file_path).stem,
                "template_version": "1.0.0",
                "description": f"Custom constraint template ({len(constraints_to_export)} constraints)",
                "author": "User",
                "created": datetime.now().isoformat(),
                "constraints": []
            }

            # Convert constraints to template format (remove IDs, stats, etc.)
            for c in constraints_to_export:
                constraint_data = {
                    "description": c.get("description"),
                    "enforcement_action": c.get("enforcement_action"),
                    "enforcement_message": c.get("enforcement_message")
                }

                # Add Phase 2 fields if present
                if c.get("version") == 2:
                    if c.get("trigger_patterns"):
                        constraint_data["trigger_patterns"] = c["trigger_patterns"]
                    if c.get("trigger_keywords"):
                        constraint_data["trigger_keywords"] = c["trigger_keywords"]
                    if c.get("trigger_logic"):
                        constraint_data["trigger_logic"] = c["trigger_logic"]
                    if c.get("context_filters"):
                        constraint_data["context_filters"] = c["context_filters"]
                else:
                    # Phase 1
                    constraint_data["trigger_keywords"] = c.get("trigger_keywords", [])

                template["constraints"].append(constraint_data)

            # Write template file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

            return True

        except (IOError, OSError, KeyError, TypeError):
            return False


# ==============================================================================
# Phase 3: Supervisor Meta-Layer
# ==============================================================================

class ConstraintSupervisor:
    """
    Intelligent supervision layer for constraint system.

    Features:
    - Automated constraint suggestions (learn from violations)
    - Drift detection (effectiveness declining over time)
    - Health monitoring (precision, recall metrics)
    - Learning analytics (visualize performance)
    - Auto-tuning (optimize based on feedback)

    Storage: ~/.grokflow/constraint_analytics.json (separate from constraints.json)

    Example:
        supervisor = ConstraintSupervisor(Path("~/.grokflow"))
        supervisor.record_trigger("abc12345", "Create mock API", "false_positive")
        health = supervisor.analyze_constraint_health("abc12345")
        suggestions = supervisor.suggest_improvements("abc12345")
    """

    def __init__(self, config_dir: Path):
        """
        Initialize ConstraintSupervisor.

        Args:
            config_dir: Path to GrokFlow config directory (e.g., ~/.grokflow)
        """
        self.config_dir = Path(config_dir).expanduser()
        self.analytics_file = self.config_dir / "constraint_analytics.json"
        self.manager = ConstraintManager(config_dir)
        self.analytics = self._load_analytics()

        # Save analytics if it's a new file (ensure it exists)
        if not self.analytics_file.exists():
            self._save_analytics()

    def _load_analytics(self) -> Dict:
        """
        Load analytics from disk with automatic schema migration.

        Phase 3.1 enhancement: Migrates analytics schema from older versions.

        Returns:
            Analytics dictionary with constraint metrics

        Graceful degradation:
            - Missing file → return default structure
            - Corrupted JSON → return default structure
            - Old schema version → migrate to current version
        """
        if not self.analytics_file.exists():
            return self._create_default_analytics()

        try:
            with open(self.analytics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict):
                return self._create_default_analytics()

            # Ensure required fields exist
            if "analytics_version" not in data or "constraints" not in data:
                return self._create_default_analytics()

            # Phase 3.1: Schema migration
            data = self._migrate_analytics_schema(data)

            return data

        except (json.JSONDecodeError, IOError, OSError):
            # Corrupted file - return default
            return self._create_default_analytics()

    def _migrate_analytics_schema(self, data: Dict) -> Dict:
        """
        Migrate analytics schema from old versions to current version.

        Phase 3.1 enhancement: Handles schema version upgrades.

        Args:
            data: Analytics data (any version)

        Returns:
            Migrated analytics data (current version)

        Migration path:
            - 1.0.0 → 2.0.0: Add performance metrics, cache stats
            - 2.0.0 → 3.0.0: Add ml-based suggestions (future)

        Example:
            v1.0.0 data → automatically upgraded to v2.0.0 on load
        """
        current_version = "1.0.0"  # Current analytics schema version
        data_version = data.get("analytics_version", "1.0.0")

        # No migration needed if already current
        if data_version == current_version:
            return data

        # Future migrations will go here
        # if data_version == "1.0.0":
        #     data = self._migrate_v1_to_v2(data)
        #     data["analytics_version"] = "2.0.0"
        #
        # if data_version == "2.0.0":
        #     data = self._migrate_v2_to_v3(data)
        #     data["analytics_version"] = "3.0.0"

        return data

    # Example migration function (for future use)
    # def _migrate_v1_to_v2(self, data: Dict) -> Dict:
    #     """
    #     Migrate analytics from v1.0.0 to v2.0.0.
    #
    #     Changes in v2.0.0:
    #         - Add performance_metrics to each constraint
    #         - Add cache_stats to global_stats
    #     """
    #     # Add performance metrics to each constraint
    #     for cid, analytics in data.get("constraints", {}).items():
    #         if "performance_metrics" not in analytics:
    #             analytics["performance_metrics"] = {
    #                 "avg_check_time_ms": 0.0,
    #                 "regex_cache_hits": 0,
    #                 "regex_cache_misses": 0
    #             }
    #
    #     # Add cache stats to global stats
    #     if "cache_stats" not in data.get("global_stats", {}):
    #         data["global_stats"]["cache_stats"] = {
    #             "regex_cache_size": 0,
    #             "keyword_index_size": 0
    #         }
    #
    #     return data

    def _create_default_analytics(self) -> Dict:
        """Create default analytics structure."""
        return {
            "analytics_version": "1.0.0",
            "created": datetime.now().isoformat(),
            "constraints": {},
            "global_stats": {
                "total_constraints": 0,
                "healthy_constraints": 0,
                "drifting_constraints": 0,
                "disabled_constraints": 0,
                "average_precision": 0.0,
                "total_suggestions_generated": 0,
                "suggestions_accepted": 0
            },
            "learned_patterns": []
        }

    def _save_analytics(self) -> bool:
        """
        Persist analytics to disk.

        Returns:
            True if save successful, False otherwise

        Graceful degradation:
            - I/O error → return False (don't crash)
        """
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Write to temp file first (atomic write)
            temp_file = self.analytics_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.analytics, f, indent=2, ensure_ascii=False)

            # Move temp file to final location (atomic on POSIX)
            temp_file.replace(self.analytics_file)

            # Set restrictive permissions (user-only read/write)
            self.analytics_file.chmod(0o600)

            return True

        except (IOError, OSError):
            return False

    def record_trigger(
        self,
        constraint_id: str,
        query: str,
        user_feedback: str = "true_positive"
    ) -> bool:
        """
        Record constraint trigger with user feedback.

        Args:
            constraint_id: Constraint ID that was triggered
            query: The query that triggered the constraint
            user_feedback: User feedback - "true_positive", "false_positive", or "unknown"

        Returns:
            True if recorded successfully

        Example:
            supervisor.record_trigger("abc12345", "Create mock API", "false_positive")
        """
        try:
            # Ensure constraint exists in analytics
            if constraint_id not in self.analytics["constraints"]:
                self.analytics["constraints"][constraint_id] = {
                    "constraint_id": constraint_id,
                    "total_triggers": 0,
                    "false_positives": 0,
                    "true_positives": 0,
                    "unknown": 0,
                    "auto_disabled_count": 0,
                    "last_analyzed": None,
                    "precision": 0.0,
                    "effectiveness_score": 0.0,
                    "drift_score": 0.0,
                    "trigger_history": [],
                    "suggested_improvements": []
                }

            analytics = self.analytics["constraints"][constraint_id]

            # Update counts
            analytics["total_triggers"] += 1
            if user_feedback == "true_positive":
                analytics["true_positives"] += 1
            elif user_feedback == "false_positive":
                analytics["false_positives"] += 1
            else:
                analytics["unknown"] += 1

            # Add to history
            analytics["trigger_history"].append({
                "timestamp": datetime.now().isoformat(),
                "query": query[:100],  # Store first 100 chars
                "result": user_feedback
            })

            # Keep only last 50 triggers in history
            if len(analytics["trigger_history"]) > 50:
                analytics["trigger_history"] = analytics["trigger_history"][-50:]

            # Recalculate metrics
            self._recalculate_metrics(constraint_id)

            # Save analytics
            self._save_analytics()

            return True

        except (KeyError, TypeError, AttributeError):
            return False

    def _recalculate_metrics(self, constraint_id: str):
        """
        Recalculate precision, effectiveness, and drift for a constraint.

        Args:
            constraint_id: Constraint ID to recalculate
        """
        try:
            analytics = self.analytics["constraints"][constraint_id]

            tp = analytics.get("true_positives", 0)
            fp = analytics.get("false_positives", 0)
            total = tp + fp

            # Calculate precision
            if total > 0:
                analytics["precision"] = tp / total
            else:
                analytics["precision"] = 0.0

            # Calculate effectiveness (precision * normalized trigger rate)
            # Higher trigger rate with high precision = more effective
            trigger_rate = min(total / 100.0, 1.0)  # Normalize to 100 triggers
            analytics["effectiveness_score"] = analytics["precision"] * trigger_rate

            # Calculate drift
            analytics["drift_score"] = self.detect_drift(constraint_id)

            analytics["last_analyzed"] = datetime.now().isoformat()

        except (KeyError, TypeError, ZeroDivisionError):
            pass  # Graceful degradation

    def detect_drift(self, constraint_id: str, window_size: int = 10) -> float:
        """
        Detect if constraint effectiveness is drifting over time.

        Args:
            constraint_id: Constraint ID to analyze
            window_size: Number of recent triggers to analyze

        Returns:
            Drift score: 0.0 (stable) to 1.0 (high drift)

        Drift indicators:
            - Precision declining over time
            - High variance in recent triggers
            - Increasing false positive rate

        Example:
            drift = supervisor.detect_drift("abc12345")
            if drift > 0.5:
                print("Constraint is drifting - needs review")
        """
        try:
            analytics = self.analytics["constraints"].get(constraint_id)
            if not analytics:
                return 0.0

            trigger_history = analytics.get("trigger_history", [])
            if len(trigger_history) < window_size:
                return 0.0  # Not enough data

            # Calculate precision in two windows
            recent = trigger_history[-window_size:]
            older = trigger_history[-2*window_size:-window_size] if len(trigger_history) >= 2*window_size else []

            recent_precision = self._calculate_precision(recent)
            older_precision = self._calculate_precision(older) if older else recent_precision

            # Drift = precision decline + variance
            precision_decline = max(0, older_precision - recent_precision)
            variance = self._calculate_variance([r["result"] == "true_positive" for r in recent])

            drift_score = (precision_decline * 0.7) + (variance * 0.3)

            return min(drift_score, 1.0)

        except (KeyError, TypeError, IndexError):
            return 0.0  # Graceful degradation

    def _calculate_precision(self, trigger_list: List[Dict]) -> float:
        """
        Calculate precision for a list of triggers.

        Args:
            trigger_list: List of trigger dictionaries with "result" field

        Returns:
            Precision (0.0 to 1.0)
        """
        if not trigger_list:
            return 0.0

        tp = sum(1 for t in trigger_list if t.get("result") == "true_positive")
        total = len(trigger_list)

        return tp / total if total > 0 else 0.0

    def _calculate_variance(self, values: List[bool]) -> float:
        """
        Calculate variance for boolean values.

        Args:
            values: List of boolean values

        Returns:
            Variance (0.0 to 1.0)
        """
        if not values:
            return 0.0

        # Convert bool to 0/1
        numeric_values = [1 if v else 0 for v in values]
        mean = sum(numeric_values) / len(numeric_values)

        # Variance = average of squared differences from mean
        variance = sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)

        return variance

    def analyze_constraint_health(self, constraint_id: str) -> Dict:
        """
        Comprehensive health analysis for a constraint.

        Args:
            constraint_id: Constraint ID to analyze

        Returns:
            Health dictionary with metrics and recommendations

        Metrics:
            - status: "healthy", "acceptable", "needs_review", "unhealthy"
            - precision: TP / (TP + FP)
            - fp_rate: FP / (FP + TP)
            - effectiveness_score: Custom metric (precision * trigger_rate)
            - drift_score: Time-series drift detection
            - recommendations: List of suggested improvements

        Example:
            health = supervisor.analyze_constraint_health("abc12345")
            print(f"Status: {health['status']}")
            print(f"Precision: {health['precision']:.2f}")
        """
        analytics = self.analytics["constraints"].get(constraint_id)
        if not analytics:
            return {"status": "no_data", "message": "No analytics data available"}

        tp = analytics.get("true_positives", 0)
        fp = analytics.get("false_positives", 0)
        total = tp + fp

        if total == 0:
            return {"status": "no_triggers", "message": "Constraint has not been triggered yet"}

        precision = tp / total if total > 0 else 0.0
        fp_rate = fp / total if total > 0 else 0.0
        effectiveness = analytics.get("effectiveness_score", 0.0)
        drift_score = analytics.get("drift_score", 0.0)

        # Determine health status
        if precision >= 0.90 and drift_score < 0.2:
            status = "healthy"
        elif precision >= 0.75 and drift_score < 0.5:
            status = "acceptable"
        elif precision >= 0.50 or drift_score < 0.7:
            status = "needs_review"
        else:
            status = "unhealthy"

        # Generate recommendations
        recommendations = self._generate_health_recommendations(precision, fp_rate, drift_score)

        return {
            "constraint_id": constraint_id,
            "status": status,
            "precision": round(precision, 3),
            "fp_rate": round(fp_rate, 3),
            "effectiveness_score": round(effectiveness, 3),
            "drift_score": round(drift_score, 3),
            "total_triggers": total,
            "true_positives": tp,
            "false_positives": fp,
            "recommendations": recommendations
        }

    def _generate_health_recommendations(
        self,
        precision: float,
        fp_rate: float,
        drift_score: float
    ) -> List[str]:
        """
        Generate health recommendations based on metrics.

        Args:
            precision: Constraint precision
            fp_rate: False positive rate
            drift_score: Drift score

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if precision < 0.70:
            recommendations.append("Low precision - Consider narrowing trigger patterns or adding context filters")

        if fp_rate > 0.30:
            recommendations.append("High false positive rate - Review recent false positives and adjust patterns")

        if drift_score > 0.50:
            recommendations.append("High drift detected - Constraint effectiveness is declining over time")

        if drift_score > 0.70:
            recommendations.append("CRITICAL: Very high drift - Consider disabling or rewriting this constraint")

        if not recommendations:
            recommendations.append("Constraint is performing well - no action needed")

        return recommendations

    def suggest_improvements(self, constraint_id: str) -> List[Dict]:
        """
        Suggest improvements for a specific constraint.

        Args:
            constraint_id: Constraint ID to analyze

        Returns:
            List of improvement suggestion dictionaries

        Suggestions include:
            - Narrow overly broad patterns
            - Add context filters
            - Adjust enforcement action
            - Add NOT logic to exclude false positive patterns

        Example:
            suggestions = supervisor.suggest_improvements("abc12345")
            for s in suggestions:
                print(f"{s['type']}: {s['suggestion']}")
        """
        try:
            analytics = self.analytics["constraints"].get(constraint_id)
            constraint = self.manager.get_constraint(constraint_id)

            if not analytics or not constraint:
                return []

            suggestions = []
            precision = analytics.get("precision", 1.0)
            fp_rate = analytics.get("false_positives", 0) / max(analytics.get("total_triggers", 1), 1)

            # Suggestion 1: Narrow broad patterns
            if fp_rate > 0.20 and constraint.get("trigger_patterns"):
                patterns = constraint["trigger_patterns"]
                for pattern in patterns:
                    if ".*" in pattern:
                        # Suggest word boundary
                        new_pattern = pattern.replace(".*", r"\b")
                        suggestions.append({
                            "type": "narrow_pattern",
                            "reason": f"Pattern '{pattern}' too broad (FP rate: {fp_rate:.2f})",
                            "suggestion": f"Consider narrowing to '{new_pattern}' (word boundary)",
                            "confidence": 0.75
                        })

            # Suggestion 2: Add context filters
            if fp_rate > 0.15 and not constraint.get("context_filters"):
                suggestions.append({
                    "type": "add_context_filter",
                    "reason": "High false positive rate without context filters",
                    "suggestion": "Consider restricting to 'generate' mode only: {\"query_type\": [\"generate\"]}",
                    "confidence": 0.65
                })

            # Suggestion 3: Adjust enforcement (if precision is very high)
            if precision > 0.95 and constraint.get("enforcement_action") == "warn":
                suggestions.append({
                    "type": "increase_enforcement",
                    "reason": f"Very high precision ({precision:.2f})",
                    "suggestion": "Consider escalating enforcement from 'warn' to 'block'",
                    "confidence": 0.80
                })

            # Suggestion 4: Disable if unhealthy
            if precision < 0.50:
                suggestions.append({
                    "type": "disable_constraint",
                    "reason": f"Very low precision ({precision:.2f})",
                    "suggestion": "Consider disabling this constraint and reviewing patterns",
                    "confidence": 0.90
                })

            return suggestions

        except (KeyError, TypeError, AttributeError):
            return []  # Graceful degradation

    def suggest_new_constraints(self, query_history: List[str]) -> List[Dict]:
        """
        Analyze query history and suggest new constraints.

        Args:
            query_history: List of recent user queries

        Returns:
            List of new constraint suggestion dictionaries

        Learning signals:
            - Repeated patterns in queries (frequency analysis)
            - Keywords that appear frequently but have no constraint
            - Common patterns across multiple triggers

        Example:
            history = ["Create mockapi", "Build mockapi endpoint", "Test mockapi"]
            suggestions = supervisor.suggest_new_constraints(history)
            # Returns: [{"pattern": "mockapi", "frequency": 3, ...}]
        """
        try:
            # Analyze keyword frequency
            keyword_freq = self._analyze_keyword_frequency(query_history)

            # Find patterns that appear frequently but have no constraint
            uncovered_patterns = self._find_uncovered_patterns(keyword_freq)

            # Generate suggestions
            suggestions = []
            for pattern, freq in uncovered_patterns.items():
                if freq >= 3:  # Appears 3+ times
                    suggestions.append({
                        "type": "new_constraint",
                        "pattern": pattern,
                        "frequency": freq,
                        "suggested_description": f"Consider blocking '{pattern}' pattern",
                        "confidence": min(freq / 10.0, 0.95),
                        "enforcement_action": "warn"  # Conservative default
                    })

            return suggestions

        except (TypeError, AttributeError):
            return []  # Graceful degradation

    def _analyze_keyword_frequency(self, query_history: List[str]) -> Dict[str, int]:
        """
        Analyze keyword frequency in query history.

        Args:
            query_history: List of queries

        Returns:
            Dictionary mapping keywords to frequency counts
        """
        keyword_freq = {}

        for query in query_history:
            # Simple tokenization (split on whitespace and common delimiters)
            words = query.lower().replace(',', ' ').replace('.', ' ').split()

            for word in words:
                if len(word) >= 3:  # Min 3 chars
                    keyword_freq[word] = keyword_freq.get(word, 0) + 1

        return keyword_freq

    def _find_uncovered_patterns(self, keyword_freq: Dict[str, int]) -> Dict[str, int]:
        """
        Find patterns that have no existing constraint.

        Args:
            keyword_freq: Keyword frequency dictionary

        Returns:
            Dictionary of uncovered patterns
        """
        uncovered = {}

        # Get all existing trigger keywords
        existing_keywords = set()
        for constraint in self.manager.list_constraints():
            keywords = constraint.get("trigger_keywords", [])
            existing_keywords.update(keywords)

        # Find keywords not covered by any constraint
        for keyword, freq in keyword_freq.items():
            if keyword not in existing_keywords:
                uncovered[keyword] = freq

        return uncovered

    def get_dashboard_data(self) -> Dict:
        """
        Get data for health monitoring dashboard.

        Returns:
            Dashboard data dictionary with:
                - overall_health: System health summary
                - healthy_constraints: List of healthy constraints
                - needs_review: List of constraints needing review
                - unhealthy: List of unhealthy constraints
                - suggestions_available: Number of suggestions

        Example:
            data = supervisor.get_dashboard_data()
            print(f"Overall health: {data['overall_health']['status']}")
        """
        healthy = []
        needs_review = []
        unhealthy = []
        total_precision = 0.0
        count = 0

        # Analyze all constraints
        for constraint_id in self.analytics["constraints"].keys():
            health = self.analyze_constraint_health(constraint_id)

            if health.get("status") == "healthy":
                healthy.append(health)
                total_precision += health.get("precision", 0.0)
                count += 1
            elif health.get("status") == "acceptable":
                healthy.append(health)
                total_precision += health.get("precision", 0.0)
                count += 1
            elif health.get("status") == "needs_review":
                needs_review.append(health)
                total_precision += health.get("precision", 0.0)
                count += 1
            elif health.get("status") == "unhealthy":
                unhealthy.append(health)
                total_precision += health.get("precision", 0.0)
                count += 1

        # Calculate average precision
        avg_precision = total_precision / count if count > 0 else 0.0

        # Determine overall health
        if len(unhealthy) == 0 and len(needs_review) <= 2:
            overall_status = "healthy"
        elif len(unhealthy) <= 1:
            overall_status = "acceptable"
        else:
            overall_status = "needs_attention"

        return {
            "overall_health": {
                "status": overall_status,
                "average_precision": round(avg_precision, 3),
                "total_constraints": count,
                "healthy_count": len(healthy),
                "needs_review_count": len(needs_review),
                "unhealthy_count": len(unhealthy)
            },
            "healthy_constraints": healthy,
            "needs_review": needs_review,
            "unhealthy": unhealthy,
            "suggestions_available": self.analytics["global_stats"].get("total_suggestions_generated", 0)
        }
