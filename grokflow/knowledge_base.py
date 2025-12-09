"""
GrokFlow Knowledge Base System

Modular knowledge management for:
- Error tracking and solutions
- Code patterns and best practices
- GUKS (Global Universal Knowledge System)
- Solution database
- Query interface

Features:
- Persistent storage
- Fast search and retrieval
- Categorization
- Usage statistics
- Auto-learning from errors
"""

import json
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from grokflow.exceptions import KnowledgeBaseError
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.knowledge_base')


class EntryType(Enum):
    """Type of knowledge base entry"""
    ERROR_SOLUTION = "error_solution"
    CODE_PATTERN = "code_pattern"
    BEST_PRACTICE = "best_practice"
    GUKS_ENTRY = "guks_entry"
    USER_TIP = "user_tip"


class Severity(Enum):
    """Severity level for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KnowledgeEntry:
    """Single knowledge base entry"""
    id: str
    entry_type: EntryType
    title: str
    description: str
    solution: Optional[str] = None
    code_example: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    severity: Optional[Severity] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    related_entries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['entry_type'] = self.entry_type.value
        if self.severity:
            data['severity'] = self.severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeEntry':
        """Create from dictionary"""
        data = data.copy()
        data['entry_type'] = EntryType(data['entry_type'])
        if data.get('severity'):
            data['severity'] = Severity(data['severity'])
        return cls(**data)
    
    def increment_access(self) -> None:
        """Increment access counter"""
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    error_type: str
    error_message: str
    context: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    solution_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorRecord':
        """Create from dictionary"""
        return cls(**data)


class KnowledgeBase:
    """
    Knowledge base for error tracking and solutions
    
    Features:
    - Store and retrieve knowledge entries
    - Track errors and solutions
    - Search by tags, type, severity
    - Usage statistics
    - Auto-learning
    
    Example:
        >>> kb = KnowledgeBase()
        >>> kb.add_error_solution(
        ...     title="Import Error",
        ...     description="Module not found",
        ...     solution="pip install module"
        ... )
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize knowledge base
        
        Args:
            storage_path: Path to storage file
        """
        self.storage_path = storage_path or Path.home() / '.grokflow' / 'knowledge_base.json'
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.entries: Dict[str, KnowledgeEntry] = {}
        self.error_records: List[ErrorRecord] = []
        
        self._load()
        logger.info(f"KnowledgeBase initialized: {len(self.entries)} entries")
    
    def _load(self) -> None:
        """Load knowledge base from storage"""
        if not self.storage_path.exists():
            logger.debug("No existing knowledge base, starting fresh")
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Load entries
            for entry_data in data.get('entries', []):
                entry = KnowledgeEntry.from_dict(entry_data)
                self.entries[entry.id] = entry
            
            # Load error records
            for record_data in data.get('error_records', []):
                record = ErrorRecord.from_dict(record_data)
                self.error_records.append(record)
            
            logger.info(f"Loaded {len(self.entries)} entries, {len(self.error_records)} error records")
            
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}", exc_info=True)
            raise KnowledgeBaseError(f"Failed to load knowledge base: {e}") from e
    
    def _save(self) -> None:
        """Save knowledge base to storage"""
        try:
            data = {
                'entries': [entry.to_dict() for entry in self.entries.values()],
                'error_records': [record.to_dict() for record in self.error_records],
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'total_entries': len(self.entries),
                    'total_errors': len(self.error_records)
                }
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved knowledge base: {len(self.entries)} entries")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}", exc_info=True)
            raise KnowledgeBaseError(f"Failed to save knowledge base: {e}") from e
    
    def add_entry(self, entry: KnowledgeEntry) -> str:
        """
        Add knowledge entry
        
        Args:
            entry: Knowledge entry to add
            
        Returns:
            Entry ID
        """
        self.entries[entry.id] = entry
        self._save()
        logger.info(f"Added entry: {entry.id} ({entry.entry_type.value})")
        return entry.id
    
    def add_error_solution(
        self,
        title: str,
        description: str,
        solution: str,
        error_type: Optional[str] = None,
        severity: Severity = Severity.MEDIUM,
        tags: Optional[List[str]] = None,
        code_example: Optional[str] = None
    ) -> str:
        """
        Add error solution
        
        Args:
            title: Error title
            description: Error description
            solution: Solution text
            error_type: Type of error
            severity: Severity level
            tags: Tags for categorization
            code_example: Example code
            
        Returns:
            Entry ID
        """
        entry_id = f"error_{len(self.entries)}_{datetime.now().timestamp()}"
        
        entry = KnowledgeEntry(
            id=entry_id,
            entry_type=EntryType.ERROR_SOLUTION,
            title=title,
            description=description,
            solution=solution,
            code_example=code_example,
            tags=tags or [],
            severity=severity,
            metadata={'error_type': error_type} if error_type else {}
        )
        
        return self.add_entry(entry)
    
    def add_code_pattern(
        self,
        title: str,
        description: str,
        code_example: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add code pattern
        
        Args:
            title: Pattern title
            description: Pattern description
            code_example: Example code
            tags: Tags for categorization
            
        Returns:
            Entry ID
        """
        entry_id = f"pattern_{len(self.entries)}_{datetime.now().timestamp()}"
        
        entry = KnowledgeEntry(
            id=entry_id,
            entry_type=EntryType.CODE_PATTERN,
            title=title,
            description=description,
            code_example=code_example,
            tags=tags or []
        )
        
        return self.add_entry(entry)
    
    def add_guks_entry(
        self,
        title: str,
        description: str,
        solution: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add GUKS (Global Universal Knowledge System) entry
        
        Args:
            title: Entry title
            description: Entry description
            solution: Optional solution
            tags: Tags for categorization
            metadata: Additional metadata
            
        Returns:
            Entry ID
        """
        entry_id = f"guks_{len(self.entries)}_{datetime.now().timestamp()}"
        
        entry = KnowledgeEntry(
            id=entry_id,
            entry_type=EntryType.GUKS_ENTRY,
            title=title,
            description=description,
            solution=solution,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        return self.add_entry(entry)
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: str,
        solution_id: Optional[str] = None
    ) -> None:
        """
        Record error occurrence
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Context where error occurred
            solution_id: ID of solution if resolved
        """
        record = ErrorRecord(
            error_type=error_type,
            error_message=error_message,
            context=context,
            resolved=solution_id is not None,
            solution_id=solution_id
        )
        
        self.error_records.append(record)
        self._save()
        logger.info(f"Recorded error: {error_type}")
    
    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """
        Get entry by ID
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Knowledge entry or None
        """
        entry = self.entries.get(entry_id)
        if entry:
            entry.increment_access()
            self._save()
        return entry
    
    def search(
        self,
        query: Optional[str] = None,
        entry_type: Optional[EntryType] = None,
        tags: Optional[List[str]] = None,
        severity: Optional[Severity] = None
    ) -> List[KnowledgeEntry]:
        """
        Search knowledge base
        
        Args:
            query: Text query (searches title and description)
            entry_type: Filter by entry type
            tags: Filter by tags (any match)
            severity: Filter by severity
            
        Returns:
            List of matching entries
        """
        results = list(self.entries.values())
        
        # Filter by type
        if entry_type:
            results = [e for e in results if e.entry_type == entry_type]
        
        # Filter by severity
        if severity:
            results = [e for e in results if e.severity == severity]
        
        # Filter by tags
        if tags:
            results = [
                e for e in results
                if any(tag in e.tags for tag in tags)
            ]
        
        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if query_lower in e.title.lower() or query_lower in e.description.lower()
            ]
        
        # Sort by access count (most accessed first)
        results.sort(key=lambda e: e.access_count, reverse=True)
        
        logger.debug(f"Search found {len(results)} entries")
        return results
    
    def get_related_entries(self, entry_id: str) -> List[KnowledgeEntry]:
        """
        Get related entries
        
        Args:
            entry_id: Entry ID
            
        Returns:
            List of related entries
        """
        entry = self.entries.get(entry_id)
        if not entry:
            return []
        
        related = []
        for related_id in entry.related_entries:
            related_entry = self.entries.get(related_id)
            if related_entry:
                related.append(related_entry)
        
        return related
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics
        
        Returns:
            Statistics dictionary
        """
        total_errors = len(self.error_records)
        resolved_errors = sum(1 for r in self.error_records if r.resolved)
        
        # Count by type
        error_types: Dict[str, int] = {}
        for record in self.error_records:
            error_types[record.error_type] = error_types.get(record.error_type, 0) + 1
        
        return {
            'total_errors': total_errors,
            'resolved_errors': resolved_errors,
            'unresolved_errors': total_errors - resolved_errors,
            'resolution_rate': resolved_errors / total_errors if total_errors > 0 else 0,
            'error_types': error_types,
            'most_common_error': max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }
    
    def get_popular_entries(self, limit: int = 10) -> List[KnowledgeEntry]:
        """
        Get most accessed entries
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of popular entries
        """
        entries = sorted(
            self.entries.values(),
            key=lambda e: e.access_count,
            reverse=True
        )
        return entries[:limit]
    
    def get_recent_entries(self, limit: int = 10) -> List[KnowledgeEntry]:
        """
        Get most recent entries
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of recent entries
        """
        entries = sorted(
            self.entries.values(),
            key=lambda e: e.created_at,
            reverse=True
        )
        return entries[:limit]
    
    def get_all_tags(self) -> Set[str]:
        """
        Get all unique tags
        
        Returns:
            Set of tags
        """
        tags = set()
        for entry in self.entries.values():
            tags.update(entry.tags)
        return tags
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete entry
        
        Args:
            entry_id: Entry ID
            
        Returns:
            True if deleted, False if not found
        """
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()
            logger.info(f"Deleted entry: {entry_id}")
            return True
        return False
    
    def clear_all(self) -> None:
        """Clear all entries and error records"""
        self.entries.clear()
        self.error_records.clear()
        self._save()
        logger.warning("Cleared all knowledge base data")
    
    def detect_patterns(self, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """
        Detect recurring error patterns from error records

        Analyzes error history to find patterns that occur frequently,
        enabling proactive alerting and knowledge sharing.

        Args:
            min_frequency: Minimum occurrence count to be considered a pattern

        Returns:
            List of detected patterns with metadata:
            - pattern: The error pattern string
            - frequency: Number of occurrences
            - projects: List of affected projects/contexts
            - recommended_solution: Suggested fix if available
            - success_rate: Resolution rate for this pattern
            - avg_time_to_fix: Average resolution time (if tracked)
        """
        from collections import defaultdict

        # Group errors by type/message pattern
        pattern_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'contexts': set(),
            'resolved_count': 0,
            'solution_ids': set()
        })

        for record in self.error_records:
            # Create pattern key from error type and message prefix
            error_key = record.error_type
            if record.error_message:
                # Include first 50 chars of message for grouping
                msg_prefix = record.error_message[:50].strip()
                if msg_prefix:
                    error_key = f"{record.error_type}: {msg_prefix}"

            data = pattern_data[error_key]
            data['count'] += 1
            data['contexts'].add(record.context)

            if record.resolved:
                data['resolved_count'] += 1
                if record.solution_id:
                    data['solution_ids'].add(record.solution_id)

        # Filter by minimum frequency and build result
        patterns = []
        for pattern_key, data in pattern_data.items():
            if data['count'] >= min_frequency:
                # Calculate success rate
                success_rate = data['resolved_count'] / data['count'] if data['count'] > 0 else 0.0

                # Find recommended solution from most-used solution entry
                recommended_solution = None
                if data['solution_ids']:
                    # Get the first solution entry that exists
                    for sol_id in data['solution_ids']:
                        entry = self.entries.get(sol_id)
                        if entry and entry.solution:
                            recommended_solution = entry.solution
                            break

                patterns.append({
                    'pattern': pattern_key,
                    'frequency': data['count'],
                    'projects': list(data['contexts']),
                    'recommended_solution': recommended_solution,
                    'success_rate': success_rate,
                    'avg_time_to_fix': None  # Could be calculated if we track timestamps
                })

        # Sort by frequency (highest first)
        patterns.sort(key=lambda p: p['frequency'], reverse=True)

        logger.debug(f"Detected {len(patterns)} patterns (min_freq={min_frequency})")
        return patterns

    def export_to_dict(self) -> Dict[str, Any]:
        """
        Export knowledge base to dictionary

        Returns:
            Dictionary with all data
        """
        return {
            'entries': [entry.to_dict() for entry in self.entries.values()],
            'error_records': [record.to_dict() for record in self.error_records],
            'statistics': self.get_error_statistics(),
            'metadata': {
                'total_entries': len(self.entries),
                'total_errors': len(self.error_records),
                'all_tags': list(self.get_all_tags())
            }
        }
    
    def import_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Import knowledge base from dictionary
        
        Args:
            data: Dictionary with knowledge base data
        """
        try:
            # Import entries
            for entry_data in data.get('entries', []):
                entry = KnowledgeEntry.from_dict(entry_data)
                self.entries[entry.id] = entry
            
            # Import error records
            for record_data in data.get('error_records', []):
                record = ErrorRecord.from_dict(record_data)
                self.error_records.append(record)
            
            self._save()
            logger.info(f"Imported {len(data.get('entries', []))} entries")
            
        except Exception as e:
            logger.error(f"Failed to import data: {e}", exc_info=True)
            raise KnowledgeBaseError(f"Failed to import data: {e}") from e


# Global knowledge base instance
_global_kb: Optional[KnowledgeBase] = None


def get_knowledge_base(
    storage_path: Optional[Path] = None,
    force_new: bool = False
) -> KnowledgeBase:
    """
    Get global knowledge base instance
    
    Args:
        storage_path: Optional storage path
        force_new: Force new instance
        
    Returns:
        KnowledgeBase instance
    """
    global _global_kb
    
    if _global_kb is None or force_new:
        _global_kb = KnowledgeBase(storage_path=storage_path)
    
    return _global_kb
