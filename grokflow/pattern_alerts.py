"""
GrokFlow Pattern Detection Alert System

Monitors the Universal Knowledge System (GUKS) for recurring error patterns
and generates alerts when patterns are detected that may indicate:
- Recurring bugs in the codebase
- Missing best practices
- Configuration issues
- Common developer mistakes

Features:
- Real-time pattern detection
- Alert prioritization by severity
- Actionable recommendations
- Alert history tracking
"""

from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from grokflow.logging_config import get_logger

logger = get_logger('grokflow.pattern_alerts')


class AlertSeverity(Enum):
    """Severity levels for pattern alerts"""
    INFO = "info"  # Informational, low-priority patterns
    WARNING = "warning"  # Patterns that may need attention
    HIGH = "high"  # Significant patterns requiring action
    CRITICAL = "critical"  # Critical patterns requiring immediate attention


class AlertStatus(Enum):
    """Status of an alert"""
    NEW = "new"  # Newly detected
    ACKNOWLEDGED = "acknowledged"  # User has seen it
    IN_PROGRESS = "in_progress"  # Being addressed
    RESOLVED = "resolved"  # Pattern has been addressed
    DISMISSED = "dismissed"  # User chose to ignore


@dataclass
class PatternAlert:
    """An alert about a detected error pattern"""
    id: str
    pattern_type: str
    pattern_description: str
    severity: AlertSeverity
    status: AlertStatus
    frequency: int
    affected_projects: List[str]
    recommended_action: Optional[str]
    solution_available: bool
    solution_success_rate: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'pattern_type': self.pattern_type,
            'pattern_description': self.pattern_description,
            'severity': self.severity.value,
            'status': self.status.value,
            'frequency': self.frequency,
            'affected_projects': self.affected_projects,
            'recommended_action': self.recommended_action,
            'solution_available': self.solution_available,
            'solution_success_rate': self.solution_success_rate,
            'created_at': self.created_at,
            'acknowledged_at': self.acknowledged_at,
            'resolved_at': self.resolved_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PatternAlert':
        """Create from dictionary"""
        data = data.copy()
        data['severity'] = AlertSeverity(data['severity'])
        data['status'] = AlertStatus(data['status'])
        return cls(**data)


@dataclass
class AlertThresholds:
    """Thresholds for generating alerts"""
    min_frequency_info: int = 3  # Minimum occurrences for INFO alert
    min_frequency_warning: int = 5  # Minimum occurrences for WARNING
    min_frequency_high: int = 10  # Minimum occurrences for HIGH
    min_frequency_critical: int = 20  # Minimum occurrences for CRITICAL
    min_projects_for_escalation: int = 2  # Min projects to escalate severity
    low_success_rate_threshold: float = 0.5  # Below this, escalate severity


class PatternAlertManager:
    """
    Manages pattern detection alerts from GUKS

    Example:
        >>> manager = PatternAlertManager(knowledge_base)
        >>> alerts = manager.check_for_alerts()
        >>> for alert in alerts:
        ...     print(f"[{alert.severity.value}] {alert.pattern_type}")
    """

    def __init__(
        self,
        knowledge_base: Optional[object] = None,
        storage_path: Optional[Path] = None,
        thresholds: Optional[AlertThresholds] = None,
        on_alert: Optional[Callable[[PatternAlert], None]] = None
    ):
        """
        Initialize alert manager

        Args:
            knowledge_base: UniversalKnowledgeBase instance (optional)
            storage_path: Path for storing alert history
            thresholds: Custom alert thresholds
            on_alert: Callback function called when new alert is generated
        """
        self.knowledge_base = knowledge_base
        self.storage_path = storage_path or Path.home() / '.grokflow' / 'alerts.json'
        self.thresholds = thresholds or AlertThresholds()
        self.on_alert = on_alert

        self.alerts: Dict[str, PatternAlert] = {}
        self._load_alerts()

        logger.info("PatternAlertManager initialized")

    def _load_alerts(self) -> None:
        """Load alerts from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for alert_data in data.get('alerts', []):
                        alert = PatternAlert.from_dict(alert_data)
                        self.alerts[alert.id] = alert
                logger.debug(f"Loaded {len(self.alerts)} alerts")
            except Exception as e:
                logger.warning(f"Failed to load alerts: {e}")
                self.alerts = {}

    def _save_alerts(self) -> None:
        """Save alerts to storage"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump({
                    'alerts': [a.to_dict() for a in self.alerts.values()]
                }, f, indent=2)
            logger.debug(f"Saved {len(self.alerts)} alerts")
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")

    def check_for_alerts(self, min_frequency: int = 3) -> List[PatternAlert]:
        """
        Check GUKS for new patterns and generate alerts

        Args:
            min_frequency: Minimum pattern frequency to consider

        Returns:
            List of new alerts generated
        """
        if self.knowledge_base is None:
            logger.warning("No knowledge base configured, skipping pattern check")
            return []

        new_alerts = []

        try:
            # Detect patterns from knowledge base
            patterns = self.knowledge_base.detect_patterns(min_frequency=min_frequency)

            for pattern in patterns:
                alert = self._create_alert_from_pattern(pattern)
                if alert and alert.id not in self.alerts:
                    self.alerts[alert.id] = alert
                    new_alerts.append(alert)

                    # Trigger callback if configured
                    if self.on_alert:
                        self.on_alert(alert)

                    logger.info(f"New alert: [{alert.severity.value}] {alert.pattern_type}")

            if new_alerts:
                self._save_alerts()

        except Exception as e:
            logger.error(f"Error checking for patterns: {e}")

        return new_alerts

    def _create_alert_from_pattern(self, pattern: Dict) -> Optional[PatternAlert]:
        """Create an alert from a detected pattern"""
        frequency = pattern.get('frequency', 0)
        projects = pattern.get('projects', [])
        success_rate = pattern.get('success_rate', 0)
        solution = pattern.get('recommended_solution')

        # Determine severity based on frequency and other factors
        severity = self._calculate_severity(frequency, len(projects), success_rate)

        # Generate ID from pattern
        pattern_str = pattern.get('pattern', '')
        alert_id = f"alert_{hash(pattern_str) % 10**8:08x}"

        # Build recommended action
        recommended_action = None
        if solution:
            recommended_action = f"Suggested fix: {solution}"
        elif success_rate < self.thresholds.low_success_rate_threshold:
            recommended_action = "Consider investigating root cause - existing solutions have low success rate"
        else:
            recommended_action = "Review error pattern and add proper error handling"

        return PatternAlert(
            id=alert_id,
            pattern_type=pattern_str.split(':')[0] if ':' in pattern_str else pattern_str,
            pattern_description=pattern_str,
            severity=severity,
            status=AlertStatus.NEW,
            frequency=frequency,
            affected_projects=projects,
            recommended_action=recommended_action,
            solution_available=solution is not None,
            solution_success_rate=success_rate
        )

    def _calculate_severity(
        self,
        frequency: int,
        num_projects: int,
        success_rate: float
    ) -> AlertSeverity:
        """Calculate alert severity based on pattern characteristics"""
        # Start with frequency-based severity
        if frequency >= self.thresholds.min_frequency_critical:
            severity = AlertSeverity.CRITICAL
        elif frequency >= self.thresholds.min_frequency_high:
            severity = AlertSeverity.HIGH
        elif frequency >= self.thresholds.min_frequency_warning:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        # Escalate if pattern affects multiple projects
        if num_projects >= self.thresholds.min_projects_for_escalation:
            if severity == AlertSeverity.INFO:
                severity = AlertSeverity.WARNING
            elif severity == AlertSeverity.WARNING:
                severity = AlertSeverity.HIGH

        # Escalate if success rate is low (hard to fix)
        if success_rate < self.thresholds.low_success_rate_threshold and success_rate > 0:
            if severity == AlertSeverity.INFO:
                severity = AlertSeverity.WARNING
            elif severity == AlertSeverity.WARNING:
                severity = AlertSeverity.HIGH

        return severity

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Mark alert as acknowledged

        Args:
            alert_id: ID of alert to acknowledge

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
        self.alerts[alert_id].acknowledged_at = datetime.now().isoformat()
        self._save_alerts()
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark alert as resolved

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        self.alerts[alert_id].status = AlertStatus.RESOLVED
        self.alerts[alert_id].resolved_at = datetime.now().isoformat()
        self._save_alerts()
        return True

    def dismiss_alert(self, alert_id: str) -> bool:
        """
        Dismiss an alert

        Args:
            alert_id: ID of alert to dismiss

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        self.alerts[alert_id].status = AlertStatus.DISMISSED
        self._save_alerts()
        return True

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        min_severity: Optional[AlertSeverity] = None
    ) -> List[PatternAlert]:
        """
        Get alerts with optional filters

        Args:
            status: Filter by status
            severity: Filter by exact severity
            min_severity: Filter by minimum severity

        Returns:
            List of matching alerts
        """
        alerts = list(self.alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if min_severity:
            severity_order = [
                AlertSeverity.INFO,
                AlertSeverity.WARNING,
                AlertSeverity.HIGH,
                AlertSeverity.CRITICAL
            ]
            min_idx = severity_order.index(min_severity)
            alerts = [
                a for a in alerts
                if severity_order.index(a.severity) >= min_idx
            ]

        # Sort by severity (highest first), then by frequency
        severity_order = {
            AlertSeverity.CRITICAL: 4,
            AlertSeverity.HIGH: 3,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 1
        }
        alerts.sort(key=lambda a: (severity_order[a.severity], a.frequency), reverse=True)

        return alerts

    def get_active_alerts(self) -> List[PatternAlert]:
        """Get all non-resolved/dismissed alerts"""
        return [
            a for a in self.alerts.values()
            if a.status not in (AlertStatus.RESOLVED, AlertStatus.DISMISSED)
        ]

    def get_alert_summary(self) -> Dict:
        """
        Get summary of all alerts

        Returns:
            Dictionary with alert statistics
        """
        all_alerts = list(self.alerts.values())

        by_severity = {s.value: 0 for s in AlertSeverity}
        by_status = {s.value: 0 for s in AlertStatus}

        for alert in all_alerts:
            by_severity[alert.severity.value] += 1
            by_status[alert.status.value] += 1

        active = self.get_active_alerts()

        return {
            'total_alerts': len(all_alerts),
            'active_alerts': len(active),
            'by_severity': by_severity,
            'by_status': by_status,
            'highest_severity': max(
                (a.severity for a in active),
                key=lambda s: [AlertSeverity.INFO, AlertSeverity.WARNING,
                              AlertSeverity.HIGH, AlertSeverity.CRITICAL].index(s),
                default=None
            )
        }

    def clear_resolved_alerts(self, older_than_days: int = 30) -> int:
        """
        Remove resolved alerts older than specified days

        Args:
            older_than_days: Remove alerts resolved before this many days

        Returns:
            Number of alerts removed
        """
        cutoff = datetime.now() - timedelta(days=older_than_days)
        cutoff_str = cutoff.isoformat()

        removed = 0
        to_remove = []

        for alert_id, alert in self.alerts.items():
            if alert.status == AlertStatus.RESOLVED and alert.resolved_at:
                if alert.resolved_at < cutoff_str:
                    to_remove.append(alert_id)

        for alert_id in to_remove:
            del self.alerts[alert_id]
            removed += 1

        if removed > 0:
            self._save_alerts()
            logger.info(f"Cleared {removed} old resolved alerts")

        return removed


# Global instance
_global_alert_manager: Optional[PatternAlertManager] = None


def get_alert_manager(
    knowledge_base: Optional[object] = None,
    force_new: bool = False
) -> PatternAlertManager:
    """
    Get global alert manager instance

    Args:
        knowledge_base: UniversalKnowledgeBase instance
        force_new: Force new instance

    Returns:
        PatternAlertManager instance
    """
    global _global_alert_manager

    if _global_alert_manager is None or force_new:
        _global_alert_manager = PatternAlertManager(knowledge_base=knowledge_base)

    return _global_alert_manager
