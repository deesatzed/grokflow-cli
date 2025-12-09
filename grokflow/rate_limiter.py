"""
GrokFlow Rate Limiter

Intelligent rate limiting for:
- API calls (prevent 429 errors)
- Image analysis (10/hour, 50/day)
- Cost tracking
- Usage statistics
- Persistent state

Prevents abuse and tracks resource usage across sessions.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

from grokflow.exceptions import RateLimitError
from grokflow.logging_config import get_logger

logger = get_logger('grokflow.rate_limiter')


@dataclass
class RateLimit:
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    name: str
    
    def __str__(self):
        if self.window_seconds < 3600:
            return f"{self.max_requests}/{self.window_seconds}s"
        elif self.window_seconds < 86400:
            hours = self.window_seconds / 3600
            return f"{self.max_requests}/{hours:.0f}h"
        else:
            days = self.window_seconds / 86400
            return f"{self.max_requests}/{days:.0f}d"


@dataclass
class UsageRecord:
    """Single usage record"""
    timestamp: float
    operation: str
    cost: float = 0.0
    metadata: Optional[Dict] = None


class RateLimiter:
    """
    Intelligent rate limiter with persistent state
    
    Features:
    - Multiple rate limits per operation
    - Sliding window algorithm
    - Cost tracking
    - Usage statistics
    - Persistent across sessions
    - Auto-cleanup of old records
    
    Example:
        >>> limiter = RateLimiter(Path("~/.grokflow/rate_limits.json"))
        >>> limiter.check_and_record('image_analysis')
    """
    
    # Default rate limits
    DEFAULT_LIMITS = {
        'image_analysis': [
            RateLimit(10, 3600, 'hourly'),      # 10 per hour
            RateLimit(50, 86400, 'daily'),      # 50 per day
        ],
        'api_call': [
            RateLimit(100, 60, 'per_minute'),   # 100 per minute
            RateLimit(1000, 3600, 'hourly'),    # 1000 per hour
        ],
        'file_write': [
            RateLimit(100, 60, 'per_minute'),   # 100 per minute
        ],
        'context_add': [
            RateLimit(50, 60, 'per_minute'),    # 50 per minute
        ],
    }
    
    # Cost estimates (in USD)
    OPERATION_COSTS = {
        'image_analysis': 0.01,      # ~$0.01 per image
        'api_call_planner': 0.001,   # ~$0.001 per call
        'api_call_executor': 0.0005, # ~$0.0005 per call
    }
    
    def __init__(self, state_file: Path):
        """
        Initialize rate limiter
        
        Args:
            state_file: Path to persistent state file
        """
        self.state_file = state_file.expanduser().resolve()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory usage records
        self.usage_records: Dict[str, List[UsageRecord]] = defaultdict(list)
        
        # Load persistent state
        self._load_state()
        
        logger.debug(f"RateLimiter initialized: {self.state_file}")
    
    def check_and_record(
        self,
        operation: str,
        cost: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Check rate limits and record usage
        
        Args:
            operation: Operation name (e.g., 'image_analysis')
            cost: Optional cost in USD
            metadata: Optional metadata to store
            
        Raises:
            RateLimitError: If rate limit exceeded
        """
        # Check all limits for this operation
        limits = self.DEFAULT_LIMITS.get(operation, [])
        
        for limit in limits:
            if not self._check_limit(operation, limit):
                # Calculate wait time
                wait_seconds = self._calculate_wait_time(operation, limit)
                
                logger.warning(
                    f"Rate limit exceeded for {operation}: {limit}. "
                    f"Wait {wait_seconds:.0f}s"
                )
                
                raise RateLimitError(
                    f"Rate limit exceeded for {operation}: {limit}. "
                    f"Please wait {self._format_wait_time(wait_seconds)}."
                )
        
        # Record usage
        if cost is None:
            cost = self.OPERATION_COSTS.get(operation, 0.0)
        
        record = UsageRecord(
            timestamp=time.time(),
            operation=operation,
            cost=cost,
            metadata=metadata
        )
        
        self.usage_records[operation].append(record)
        logger.debug(f"Recorded usage: {operation} (cost: ${cost:.4f})")
        
        # Cleanup old records
        self._cleanup_old_records()
        
        # Save state
        self._save_state()
    
    def _check_limit(self, operation: str, limit: RateLimit) -> bool:
        """
        Check if operation is within rate limit
        
        Args:
            operation: Operation name
            limit: Rate limit to check
            
        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        window_start = now - limit.window_seconds
        
        # Count requests in window
        records = self.usage_records.get(operation, [])
        count = sum(1 for r in records if r.timestamp >= window_start)
        
        is_within_limit = count < limit.max_requests
        
        if not is_within_limit:
            logger.debug(
                f"Limit check failed: {operation} has {count}/{limit.max_requests} "
                f"in {limit.name} window"
            )
        
        return is_within_limit
    
    def _calculate_wait_time(self, operation: str, limit: RateLimit) -> float:
        """
        Calculate seconds to wait before next request
        
        Args:
            operation: Operation name
            limit: Rate limit that was exceeded
            
        Returns:
            Seconds to wait
        """
        now = time.time()
        window_start = now - limit.window_seconds
        
        # Get records in window
        records = self.usage_records.get(operation, [])
        records_in_window = [r for r in records if r.timestamp >= window_start]
        
        if len(records_in_window) < limit.max_requests:
            return 0.0
        
        # Sort by timestamp
        records_in_window.sort(key=lambda r: r.timestamp)
        
        # Oldest record will expire first
        oldest = records_in_window[0]
        wait_until = oldest.timestamp + limit.window_seconds
        
        return max(0.0, wait_until - now)
    
    def _format_wait_time(self, seconds: float) -> str:
        """
        Format wait time as human-readable string
        
        Args:
            seconds: Seconds to wait
            
        Returns:
            Formatted string (e.g., "5m 30s")
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    def get_usage_stats(self, operation: Optional[str] = None) -> Dict:
        """
        Get usage statistics
        
        Args:
            operation: Optional operation name (None = all operations)
            
        Returns:
            Dictionary with usage statistics
        """
        now = time.time()
        
        if operation:
            operations = [operation]
        else:
            operations = list(self.usage_records.keys())
        
        stats = {}
        
        for op in operations:
            records = self.usage_records.get(op, [])
            
            # Calculate stats for different time windows
            hour_ago = now - 3600
            day_ago = now - 86400
            week_ago = now - 604800
            
            hour_records = [r for r in records if r.timestamp >= hour_ago]
            day_records = [r for r in records if r.timestamp >= day_ago]
            week_records = [r for r in records if r.timestamp >= week_ago]
            
            stats[op] = {
                'total': len(records),
                'last_hour': len(hour_records),
                'last_day': len(day_records),
                'last_week': len(week_records),
                'total_cost': sum(r.cost for r in records),
                'hour_cost': sum(r.cost for r in hour_records),
                'day_cost': sum(r.cost for r in day_records),
                'week_cost': sum(r.cost for r in week_records),
            }
            
            # Add limit info
            limits = self.DEFAULT_LIMITS.get(op, [])
            if limits:
                stats[op]['limits'] = [str(limit) for limit in limits]
                
                # Calculate remaining quota
                for limit in limits:
                    window_start = now - limit.window_seconds
                    count = sum(1 for r in records if r.timestamp >= window_start)
                    remaining = max(0, limit.max_requests - count)
                    stats[op][f'remaining_{limit.name}'] = remaining
        
        return stats
    
    def get_remaining_quota(self, operation: str) -> Dict[str, int]:
        """
        Get remaining quota for operation
        
        Args:
            operation: Operation name
            
        Returns:
            Dictionary mapping limit name to remaining count
        """
        now = time.time()
        records = self.usage_records.get(operation, [])
        limits = self.DEFAULT_LIMITS.get(operation, [])
        
        remaining = {}
        
        for limit in limits:
            window_start = now - limit.window_seconds
            count = sum(1 for r in records if r.timestamp >= window_start)
            remaining[limit.name] = max(0, limit.max_requests - count)
        
        return remaining
    
    def reset_operation(self, operation: str) -> None:
        """
        Reset usage for specific operation
        
        Args:
            operation: Operation name to reset
        """
        if operation in self.usage_records:
            del self.usage_records[operation]
            logger.info(f"Reset usage for: {operation}")
            self._save_state()
    
    def reset_all(self) -> None:
        """Reset all usage records"""
        self.usage_records.clear()
        logger.info("Reset all usage records")
        self._save_state()
    
    def _cleanup_old_records(self) -> None:
        """Remove records older than longest window"""
        now = time.time()
        
        # Find longest window across all limits
        max_window = 0
        for limits in self.DEFAULT_LIMITS.values():
            for limit in limits:
                max_window = max(max_window, limit.window_seconds)
        
        # Add buffer (keep 2x longest window)
        cutoff = now - (max_window * 2)
        
        # Cleanup each operation
        for operation in list(self.usage_records.keys()):
            records = self.usage_records[operation]
            self.usage_records[operation] = [
                r for r in records if r.timestamp >= cutoff
            ]
            
            # Remove empty lists
            if not self.usage_records[operation]:
                del self.usage_records[operation]
    
    def _load_state(self) -> None:
        """Load persistent state from disk"""
        if not self.state_file.exists():
            logger.debug("No rate limit state file found")
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct usage records
            for operation, records_data in data.get('usage_records', {}).items():
                self.usage_records[operation] = [
                    UsageRecord(
                        timestamp=r['timestamp'],
                        operation=r['operation'],
                        cost=r.get('cost', 0.0),
                        metadata=r.get('metadata')
                    )
                    for r in records_data
                ]
            
            logger.info(
                f"Loaded rate limit state: "
                f"{sum(len(r) for r in self.usage_records.values())} records"
            )
            
        except Exception as e:
            logger.error(f"Failed to load rate limit state: {e}", exc_info=True)
            # Continue with empty state
    
    def _save_state(self) -> None:
        """Save persistent state to disk"""
        try:
            # Convert to serializable format
            data = {
                'usage_records': {
                    operation: [
                        {
                            'timestamp': r.timestamp,
                            'operation': r.operation,
                            'cost': r.cost,
                            'metadata': r.metadata
                        }
                        for r in records
                    ]
                    for operation, records in self.usage_records.items()
                },
                'last_saved': datetime.now().isoformat()
            }
            
            # Write to file
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved rate limit state: {self.state_file}")
            
        except Exception as e:
            logger.error(f"Failed to save rate limit state: {e}", exc_info=True)
    
    def get_cost_summary(self) -> Dict:
        """
        Get cost summary across all operations
        
        Returns:
            Dictionary with cost breakdown
        """
        now = time.time()
        
        # Time windows
        hour_ago = now - 3600
        day_ago = now - 86400
        week_ago = now - 604800
        month_ago = now - 2592000
        
        all_records = []
        for records in self.usage_records.values():
            all_records.extend(records)
        
        hour_records = [r for r in all_records if r.timestamp >= hour_ago]
        day_records = [r for r in all_records if r.timestamp >= day_ago]
        week_records = [r for r in all_records if r.timestamp >= week_ago]
        month_records = [r for r in all_records if r.timestamp >= month_ago]
        
        return {
            'total_cost': sum(r.cost for r in all_records),
            'hour_cost': sum(r.cost for r in hour_records),
            'day_cost': sum(r.cost for r in day_records),
            'week_cost': sum(r.cost for r in week_records),
            'month_cost': sum(r.cost for r in month_records),
            'total_operations': len(all_records),
            'by_operation': {
                operation: sum(r.cost for r in records)
                for operation, records in self.usage_records.items()
            }
        }
    
    def can_perform(self, operation: str) -> tuple[bool, Optional[str]]:
        """
        Check if operation can be performed without raising exception
        
        Args:
            operation: Operation name
            
        Returns:
            Tuple of (can_perform, reason_if_not)
        """
        limits = self.DEFAULT_LIMITS.get(operation, [])
        
        for limit in limits:
            if not self._check_limit(operation, limit):
                wait_seconds = self._calculate_wait_time(operation, limit)
                reason = (
                    f"Rate limit exceeded: {limit}. "
                    f"Wait {self._format_wait_time(wait_seconds)}."
                )
                return False, reason
        
        return True, None


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(state_file: Optional[Path] = None) -> RateLimiter:
    """
    Get global rate limiter instance
    
    Args:
        state_file: Optional custom state file path
        
    Returns:
        RateLimiter instance
    """
    global _global_limiter
    
    if _global_limiter is None:
        if state_file is None:
            state_file = Path.home() / '.grokflow' / 'rate_limits.json'
        _global_limiter = RateLimiter(state_file)
    
    return _global_limiter
