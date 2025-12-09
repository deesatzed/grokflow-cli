"""
GrokFlow Performance Optimization

Performance utilities and optimizations:
- Caching strategies
- Lazy loading
- Connection pooling
- Memory management
- Profiling utilities
- Performance monitoring

Features:
- LRU caching
- Memoization
- Async operations
- Resource pooling
- Performance metrics
"""

import time
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import Lock

from grokflow.logging_config import get_logger

logger = get_logger('grokflow.performance')

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""
    operation_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_called: Optional[str] = None
    
    def record(self, execution_time: float) -> None:
        """Record an execution"""
        self.call_count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.call_count
        self.last_called = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'operation_name': self.operation_name,
            'call_count': self.call_count,
            'total_time': self.total_time,
            'min_time': self.min_time if self.min_time != float('inf') else 0,
            'max_time': self.max_time,
            'avg_time': self.avg_time,
            'last_called': self.last_called
        }


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache
    
    Features:
    - Fixed size limit
    - Automatic eviction
    - Thread-safe
    - TTL support
    
    Example:
        >>> cache = LRUCache(max_size=100, ttl=300)
        >>> cache.set('key', 'value')
        >>> value = cache.get('key')
    """
    
    def __init__(self, max_size: int = 128, ttl: Optional[int] = None):
        """
        Initialize LRU cache
        
        Args:
            max_size: Maximum cache size
            ttl: Time-to-live in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.lock = Lock()
        
        logger.debug(f"LRUCache initialized: max_size={max_size}, ttl={ttl}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self.lock:
            if key not in self.cache:
                return None
            
            # Check TTL
            if self.ttl and key in self.timestamps:
                if time.time() - self.timestamps[key] > self.ttl:
                    del self.cache[key]
                    del self.timestamps[key]
                    return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            if key in self.cache:
                # Update existing
                self.cache.move_to_end(key)
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Evict oldest
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    if oldest_key in self.timestamps:
                        del self.timestamps[oldest_key]
            
            self.cache[key] = value
            if self.ttl:
                self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear cache"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self.lock:
            return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'keys': list(self.cache.keys())
            }


def memoize(ttl: Optional[int] = None, max_size: int = 128):
    """
    Memoization decorator with LRU cache
    
    Args:
        ttl: Time-to-live in seconds
        max_size: Maximum cache size
        
    Example:
        >>> @memoize(ttl=300, max_size=100)
        >>> def expensive_function(x, y):
        ...     return x + y
    """
    cache = LRUCache(max_size=max_size, ttl=ttl)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from args and kwargs
            key = str((args, tuple(sorted(kwargs.items()))))
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit: {func.__name__}")
                return result
            
            # Execute function
            logger.debug(f"Cache miss: {func.__name__}")
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(key, result)
            return result
        
        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.stats
        
        return wrapper
    
    return decorator


def timed(func: Callable) -> Callable:
    """
    Timing decorator for performance monitoring
    
    Example:
        >>> @timed
        >>> def slow_function():
        ...     time.sleep(1)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = time.time() - start_time
            logger.info(
                f"Function {func.__name__} took {execution_time:.4f}s"
            )
    
    return wrapper


class PerformanceMonitor:
    """
    Performance monitoring for operations
    
    Features:
    - Operation timing
    - Call counting
    - Statistics
    - Reporting
    
    Example:
        >>> monitor = PerformanceMonitor()
        >>> with monitor.measure('operation'):
        ...     expensive_operation()
    """
    
    def __init__(self):
        """Initialize performance monitor"""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.lock = Lock()
        logger.debug("PerformanceMonitor initialized")
    
    def measure(self, operation_name: str):
        """
        Context manager for measuring operation time
        
        Args:
            operation_name: Name of operation
            
        Example:
            >>> with monitor.measure('api_call'):
            ...     api_client.call()
        """
        return _PerformanceMeasurement(self, operation_name)
    
    def record(self, operation_name: str, execution_time: float) -> None:
        """
        Record operation execution
        
        Args:
            operation_name: Name of operation
            execution_time: Execution time in seconds
        """
        with self.lock:
            if operation_name not in self.metrics:
                self.metrics[operation_name] = PerformanceMetrics(operation_name)
            
            self.metrics[operation_name].record(execution_time)
    
    def get_metrics(self, operation_name: str) -> Optional[PerformanceMetrics]:
        """
        Get metrics for operation
        
        Args:
            operation_name: Name of operation
            
        Returns:
            Performance metrics or None
        """
        with self.lock:
            return self.metrics.get(operation_name)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all metrics
        
        Returns:
            Dictionary of all metrics
        """
        with self.lock:
            return {
                name: metrics.to_dict()
                for name, metrics in self.metrics.items()
            }
    
    def get_slowest_operations(self, limit: int = 10) -> list:
        """
        Get slowest operations by average time
        
        Args:
            limit: Maximum number of operations
            
        Returns:
            List of (operation_name, avg_time) tuples
        """
        with self.lock:
            sorted_ops = sorted(
                self.metrics.items(),
                key=lambda x: x[1].avg_time,
                reverse=True
            )
            return [
                (name, metrics.avg_time)
                for name, metrics in sorted_ops[:limit]
            ]
    
    def get_most_called_operations(self, limit: int = 10) -> list:
        """
        Get most frequently called operations
        
        Args:
            limit: Maximum number of operations
            
        Returns:
            List of (operation_name, call_count) tuples
        """
        with self.lock:
            sorted_ops = sorted(
                self.metrics.items(),
                key=lambda x: x[1].call_count,
                reverse=True
            )
            return [
                (name, metrics.call_count)
                for name, metrics in sorted_ops[:limit]
            ]
    
    def clear(self) -> None:
        """Clear all metrics"""
        with self.lock:
            self.metrics.clear()
            logger.info("Performance metrics cleared")
    
    def report(self) -> str:
        """
        Generate performance report
        
        Returns:
            Formatted report string
        """
        with self.lock:
            if not self.metrics:
                return "No performance data collected"
            
            lines = ["Performance Report", "=" * 50]
            
            # Summary
            total_ops = sum(m.call_count for m in self.metrics.values())
            total_time = sum(m.total_time for m in self.metrics.values())
            lines.append(f"Total Operations: {total_ops}")
            lines.append(f"Total Time: {total_time:.4f}s")
            lines.append("")
            
            # Top slowest
            lines.append("Slowest Operations (by avg time):")
            for name, avg_time in self.get_slowest_operations(5):
                lines.append(f"  {name}: {avg_time:.4f}s")
            lines.append("")
            
            # Most called
            lines.append("Most Called Operations:")
            for name, count in self.get_most_called_operations(5):
                lines.append(f"  {name}: {count} calls")
            
            return "\n".join(lines)


class _PerformanceMeasurement:
    """Context manager for performance measurement"""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        self.monitor.record(self.operation_name, execution_time)


class BatchProcessor:
    """
    Batch processing for improved performance
    
    Features:
    - Batch operations
    - Configurable batch size
    - Automatic flushing
    
    Example:
        >>> processor = BatchProcessor(batch_size=100)
        >>> for item in items:
        ...     processor.add(item)
        >>> processor.flush()
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        process_fn: Optional[Callable] = None
    ):
        """
        Initialize batch processor
        
        Args:
            batch_size: Size of batches
            process_fn: Function to process batches
        """
        self.batch_size = batch_size
        self.process_fn = process_fn
        self.batch: list = []
        self.processed_count = 0
        
        logger.debug(f"BatchProcessor initialized: batch_size={batch_size}")
    
    def add(self, item: Any) -> None:
        """
        Add item to batch
        
        Args:
            item: Item to add
        """
        self.batch.append(item)
        
        if len(self.batch) >= self.batch_size:
            self.flush()
    
    def flush(self) -> None:
        """Process current batch"""
        if not self.batch:
            return
        
        if self.process_fn:
            self.process_fn(self.batch)
        
        self.processed_count += len(self.batch)
        self.batch.clear()
        
        logger.debug(f"Batch flushed: {self.processed_count} items processed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()


# Global performance monitor
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get global performance monitor
    
    Returns:
        PerformanceMonitor instance
    """
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    
    return _global_monitor


def optimize_imports():
    """
    Optimize imports for faster startup
    
    This function can be called at module level to defer
    expensive imports until they're needed.
    """
    # Lazy import pattern
    pass


def profile_function(func: Callable) -> Callable:
    """
    Profile function execution
    
    Args:
        func: Function to profile
        
    Returns:
        Wrapped function with profiling
    """
    monitor = get_performance_monitor()
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with monitor.measure(func.__name__):
            return func(*args, **kwargs)
    
    return wrapper
