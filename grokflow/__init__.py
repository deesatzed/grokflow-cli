"""
GrokFlow - Professional SWE Development CLI

A context-aware, AI-powered development environment with:
- Smart code fixing with dual-model architecture
- Universal knowledge system for cross-project learning
- Image analysis with vision AI
- Enhanced CLI with tab completion
- Comprehensive logging and error handling
- Input validation and security
"""

__version__ = "2.0.0"
__author__ = "GrokFlow Team"

from grokflow.logging_config import setup_logging, get_logger, log_operation
from grokflow.validators import InputValidator, PathSanitizer
from grokflow.session_manager import SessionManager, transactional_session
from grokflow.rate_limiter import RateLimiter, get_rate_limiter
from grokflow.api_client import GrokAPIClient, get_api_client
from grokflow.dual_model import DualModelOrchestrator, SimpleExecutor, get_orchestrator
from grokflow.knowledge_base import KnowledgeBase, get_knowledge_base
from grokflow.context_manager import ContextManager, get_context_manager
from grokflow.undo_manager import UndoManager, get_undo_manager
from grokflow.performance import (
    PerformanceMonitor, get_performance_monitor,
    LRUCache, memoize, timed, profile_function
)
from grokflow.security import (
    SecretManager, get_secret_manager,
    InputSanitizer, get_input_sanitizer,
    SecurityAuditor, get_security_auditor,
    generate_secure_token
)
from grokflow.cli import CLI, get_cli, ErrorFormatter
from grokflow.test_suggester import TestSuggester, get_test_suggester
from grokflow.pattern_alerts import (
    PatternAlertManager, get_alert_manager,
    PatternAlert, AlertSeverity, AlertStatus, AlertThresholds
)
from grokflow.commands import GrokFlowCommands, main as cli_main
from grokflow.supervisor import (
    SupervisorAgent, get_supervisor, create_supervisor,
    PlanManager, ExecutionPlan, PlanTask, TaskStatus,
    GuardrailEngine, Guardrail, GuardrailSeverity,
    ThinkingMonitor, ThinkingPattern,
    InterventionType, SupervisorDecision
)

__all__ = [
    'setup_logging',
    'get_logger',
    'log_operation',
    'InputValidator',
    'PathSanitizer',
    'SessionManager',
    'transactional_session',
    'RateLimiter',
    'get_rate_limiter',
    'GrokAPIClient',
    'get_api_client',
    'DualModelOrchestrator',
    'SimpleExecutor',
    'get_orchestrator',
    'KnowledgeBase',
    'get_knowledge_base',
    'ContextManager',
    'get_context_manager',
    'UndoManager',
    'get_undo_manager',
    'PerformanceMonitor',
    'get_performance_monitor',
    'LRUCache',
    'memoize',
    'timed',
    'profile_function',
    'SecretManager',
    'get_secret_manager',
    'InputSanitizer',
    'get_input_sanitizer',
    'SecurityAuditor',
    'get_security_auditor',
    'generate_secure_token',
    'CLI',
    'get_cli',
    'ErrorFormatter',
    'TestSuggester',
    'get_test_suggester',
    'PatternAlertManager',
    'get_alert_manager',
    'PatternAlert',
    'AlertSeverity',
    'AlertStatus',
    'AlertThresholds',
    'GrokFlowCommands',
    'cli_main',
    'SupervisorAgent',
    'get_supervisor',
    'create_supervisor',
    'PlanManager',
    'ExecutionPlan',
    'PlanTask',
    'TaskStatus',
    'GuardrailEngine',
    'Guardrail',
    'GuardrailSeverity',
    'ThinkingMonitor',
    'ThinkingPattern',
    'InterventionType',
    'SupervisorDecision'
]
