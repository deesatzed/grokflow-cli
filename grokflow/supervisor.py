"""
GrokFlow Supervisor Agent

A parent orchestrator that monitors and steers child agents with:
- Thinking block analysis for early intervention
- Plan state machine for drift detection
- Guardrails engine for rule enforcement
- Auto-proceed logic for seamless workflow
- Human escalation when needed

Architecture:
    Supervisor (coordination tools) → Worker (execution tools)

The supervisor has access to the worker's thinking, enabling
proactive intervention before violations occur.
"""

import re
import json
import asyncio
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from abc import ABC, abstractmethod

from grokflow.logging_config import get_logger

logger = get_logger('grokflow.supervisor')


# =============================================================================
# Plan State Machine
# =============================================================================

class TaskStatus(Enum):
    """Status of a plan task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PlanTask:
    """A single task in the execution plan"""
    id: str
    description: str
    completion_criteria: List[str]
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[str] = None
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        return data


@dataclass
class ExecutionPlan:
    """
    Execution plan with state tracking

    Tracks progress through a multi-step plan,
    enabling drift detection and auto-proceed.
    """
    name: str
    tasks: List[PlanTask]
    current_task_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def current_task(self) -> Optional[PlanTask]:
        """Get current task"""
        if 0 <= self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None

    @property
    def progress_percent(self) -> float:
        """Calculate completion percentage"""
        if not self.tasks:
            return 100.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all tasks are done"""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)
            for t in self.tasks
        )

    def advance(self) -> Optional[PlanTask]:
        """Move to next pending task"""
        for i, task in enumerate(self.tasks):
            if task.status == TaskStatus.PENDING:
                self.current_task_index = i
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = datetime.now().isoformat()
                return task
        return None

    def complete_current(self, output: Optional[str] = None) -> bool:
        """Mark current task as completed"""
        task = self.current_task
        if task and task.status == TaskStatus.IN_PROGRESS:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.output = output
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'tasks': [t.to_dict() for t in self.tasks],
            'current_task_index': self.current_task_index,
            'created_at': self.created_at,
            'progress_percent': self.progress_percent,
            'is_complete': self.is_complete
        }


class PlanManager:
    """
    Manages execution plans and tracks progress

    Features:
    - Load/save plans
    - Track task completion
    - Detect when to auto-proceed
    - Report progress
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / '.grokflow' / 'plans.json'
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_plan: Optional[ExecutionPlan] = None
        self._load()

    def _load(self) -> None:
        """Load saved plan state"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                if data.get('current_plan'):
                    plan_data = data['current_plan']
                    tasks = [
                        PlanTask(
                            id=t['id'],
                            description=t['description'],
                            completion_criteria=t['completion_criteria'],
                            status=TaskStatus(t['status']),
                            started_at=t.get('started_at'),
                            completed_at=t.get('completed_at'),
                            output=t.get('output'),
                            blockers=t.get('blockers', [])
                        )
                        for t in plan_data['tasks']
                    ]
                    self.current_plan = ExecutionPlan(
                        name=plan_data['name'],
                        tasks=tasks,
                        current_task_index=plan_data['current_task_index'],
                        created_at=plan_data['created_at']
                    )
            except Exception as e:
                logger.error(f"Failed to load plan: {e}")

    def _save(self) -> None:
        """Save plan state"""
        data = {
            'current_plan': self.current_plan.to_dict() if self.current_plan else None,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_plan(self, name: str, task_descriptions: List[Dict[str, Any]]) -> ExecutionPlan:
        """
        Create a new execution plan

        Args:
            name: Plan name
            task_descriptions: List of {description, completion_criteria}
        """
        tasks = [
            PlanTask(
                id=f"task_{i}",
                description=td['description'],
                completion_criteria=td.get('completion_criteria', [])
            )
            for i, td in enumerate(task_descriptions)
        ]
        self.current_plan = ExecutionPlan(name=name, tasks=tasks)
        self._save()
        return self.current_plan

    def check_completion_criteria(self, output: str) -> bool:
        """Check if current task's completion criteria are met"""
        task = self.current_plan.current_task if self.current_plan else None
        if not task or not task.completion_criteria:
            return True

        for criterion in task.completion_criteria:
            # Simple keyword matching - could be more sophisticated
            if criterion.lower() not in output.lower():
                return False
        return True

    def should_auto_proceed(self, output: str) -> bool:
        """Determine if we should automatically proceed to next task"""
        if not self.current_plan:
            return False

        task = self.current_plan.current_task
        if not task or task.status != TaskStatus.IN_PROGRESS:
            return False

        # Check completion criteria
        if self.check_completion_criteria(output):
            self.current_plan.complete_current(output)
            self._save()
            return True

        return False

    def get_progress_report(self) -> str:
        """Generate progress report"""
        if not self.current_plan:
            return "No active plan"

        lines = [
            f"Plan: {self.current_plan.name}",
            f"Progress: {self.current_plan.progress_percent:.0f}%",
            ""
        ]

        for task in self.current_plan.tasks:
            status_icon = {
                TaskStatus.PENDING: "[ ]",
                TaskStatus.IN_PROGRESS: "[>]",
                TaskStatus.COMPLETED: "[x]",
                TaskStatus.BLOCKED: "[!]",
                TaskStatus.SKIPPED: "[-]",
                TaskStatus.FAILED: "[X]"
            }.get(task.status, "[ ]")

            lines.append(f"{status_icon} {task.description}")

        return "\n".join(lines)


# =============================================================================
# Guardrails Engine
# =============================================================================

class GuardrailSeverity(Enum):
    """How seriously to treat a guardrail violation"""
    INFO = "info"           # Log only
    WARNING = "warning"     # Warn but allow
    BLOCK = "block"         # Block and require correction
    ESCALATE = "escalate"   # Require human approval


@dataclass
class Guardrail:
    """A single guardrail rule"""
    id: str
    name: str
    description: str
    pattern: str  # Regex pattern to detect violation
    severity: GuardrailSeverity
    check_thinking: bool = True  # Check thinking blocks
    check_output: bool = True    # Check output
    auto_fix: Optional[str] = None  # Automatic correction message

    def matches(self, text: str) -> bool:
        """Check if text violates this guardrail"""
        return bool(re.search(self.pattern, text, re.IGNORECASE))


class GuardrailViolation:
    """Record of a guardrail violation"""

    def __init__(
        self,
        guardrail: Guardrail,
        matched_text: str,
        source: str,  # "thinking" or "output"
        timestamp: Optional[str] = None
    ):
        self.guardrail = guardrail
        self.matched_text = matched_text
        self.source = source
        self.timestamp = timestamp or datetime.now().isoformat()

    def __str__(self) -> str:
        return (
            f"[{self.guardrail.severity.value.upper()}] "
            f"{self.guardrail.name}: {self.matched_text[:100]}..."
        )


class GuardrailEngine:
    """
    Enforces guardrails on agent behavior

    Monitors both thinking and output for violations,
    enabling early intervention before bad actions occur.
    """

    # Default guardrails based on user's CLAUDE.md rules
    DEFAULT_GUARDRAILS = [
        Guardrail(
            id="no_mock",
            name="No Mock/Placeholder",
            description="Prevent use of mocks, placeholders, or simulations",
            pattern=r"\b(mock|placeholder|simulation|cached.?response|demo.?data|fake|stub)\b",
            severity=GuardrailSeverity.BLOCK,
            check_thinking=True,
            check_output=True,
            auto_fix="Use real implementations only. Mocks require explicit user approval."
        ),
        Guardrail(
            id="no_time_estimates",
            name="No Time Estimates",
            description="Prevent time/cost estimates in plans",
            pattern=r"\b(\d+\s*(days?|weeks?|hours?|months?)|timeline|estimate|ETA)\b.*\b(task|step|phase|implementation)\b",
            severity=GuardrailSeverity.WARNING,
            check_thinking=False,
            check_output=True,
            auto_fix="Remove time estimates from plans."
        ),
        Guardrail(
            id="no_model_guessing",
            name="No AI Model Version Guessing",
            description="Prevent using LLM knowledge for AI model versions",
            pattern=r"\b(gpt-?4|claude-?3|gemini|llama|mistral)\b.*\b(version|latest|current|recommend)\b",
            severity=GuardrailSeverity.ESCALATE,
            check_thinking=True,
            check_output=True,
            auto_fix="Ask user for current AI model versions instead of guessing."
        ),
        Guardrail(
            id="use_conda_env",
            name="Use Correct Conda Environment",
            description="Ensure correct Python environment is used",
            pattern=r"(?<!miniforge3/envs/py313/bin/)python\s+(-m\s+)?pytest",
            severity=GuardrailSeverity.BLOCK,
            check_thinking=False,
            check_output=True,
            auto_fix="Use /Users/o2satz/miniforge3/envs/py313/bin/python"
        ),
        Guardrail(
            id="test_coverage",
            name="100% Test Coverage Required",
            description="Flag when test coverage is below 100%",
            pattern=r"coverage.*(\d{1,2})%|(\d{1,2})%.*coverage",
            severity=GuardrailSeverity.WARNING,
            check_thinking=False,
            check_output=True,
            auto_fix="Create action plan to address coverage gap."
        ),
        Guardrail(
            id="drift_detected",
            name="Plan Drift Detection",
            description="Detect deviation from approved plan",
            pattern=r"\b(instead|alternatively|different.?approach|change.?plan|deviat)\b",
            severity=GuardrailSeverity.WARNING,
            check_thinking=True,
            check_output=False
        ),
    ]

    def __init__(self, guardrails: Optional[List[Guardrail]] = None):
        self.guardrails = guardrails or self.DEFAULT_GUARDRAILS.copy()
        self.violations: List[GuardrailViolation] = []
        self.suppressed: Set[str] = set()  # Guardrail IDs to suppress

    def add_guardrail(self, guardrail: Guardrail) -> None:
        """Add a custom guardrail"""
        self.guardrails.append(guardrail)

    def suppress_guardrail(self, guardrail_id: str) -> None:
        """Temporarily suppress a guardrail (user override)"""
        self.suppressed.add(guardrail_id)

    def check_thinking(self, thinking: str) -> List[GuardrailViolation]:
        """
        Check thinking block for violations

        This enables EARLY intervention - we can catch
        problematic intent before it becomes action.
        """
        violations = []

        for guardrail in self.guardrails:
            if guardrail.id in self.suppressed:
                continue
            if not guardrail.check_thinking:
                continue
            if guardrail.matches(thinking):
                violation = GuardrailViolation(
                    guardrail=guardrail,
                    matched_text=self._extract_match(thinking, guardrail.pattern),
                    source="thinking"
                )
                violations.append(violation)
                self.violations.append(violation)
                logger.warning(f"Thinking violation: {violation}")

        return violations

    def check_output(self, output: str) -> List[GuardrailViolation]:
        """Check output for violations"""
        violations = []

        for guardrail in self.guardrails:
            if guardrail.id in self.suppressed:
                continue
            if not guardrail.check_output:
                continue
            if guardrail.matches(output):
                violation = GuardrailViolation(
                    guardrail=guardrail,
                    matched_text=self._extract_match(output, guardrail.pattern),
                    source="output"
                )
                violations.append(violation)
                self.violations.append(violation)
                logger.warning(f"Output violation: {violation}")

        return violations

    def _extract_match(self, text: str, pattern: str) -> str:
        """Extract the matching text for context"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            return text[start:end]
        return ""

    def get_blocking_violations(
        self,
        violations: List[GuardrailViolation]
    ) -> List[GuardrailViolation]:
        """Get violations that should block execution"""
        return [
            v for v in violations
            if v.guardrail.severity in (
                GuardrailSeverity.BLOCK,
                GuardrailSeverity.ESCALATE
            )
        ]

    def get_correction_message(
        self,
        violations: List[GuardrailViolation]
    ) -> str:
        """Generate correction message for violations"""
        lines = ["GUARDRAIL VIOLATIONS DETECTED:", ""]

        for v in violations:
            lines.append(f"- [{v.guardrail.severity.value.upper()}] {v.guardrail.name}")
            if v.guardrail.auto_fix:
                lines.append(f"  Fix: {v.guardrail.auto_fix}")

        lines.append("")
        lines.append("Please correct these issues before proceeding.")

        return "\n".join(lines)


# =============================================================================
# Thinking Monitor
# =============================================================================

class ThinkingPattern(Enum):
    """Patterns to detect in thinking blocks"""
    UNCERTAINTY = "uncertainty"
    PLAN_DEVIATION = "plan_deviation"
    MOCK_INTENT = "mock_intent"
    NEEDS_INFO = "needs_info"
    COMPLETION = "completion"
    ERROR_LOOP = "error_loop"


@dataclass
class ThinkingAnalysis:
    """Analysis of an agent's thinking block"""
    patterns_detected: List[ThinkingPattern]
    confidence_scores: Dict[ThinkingPattern, float]
    extracted_intent: Optional[str] = None
    recommended_action: Optional[str] = None
    should_intervene: bool = False


class ThinkingMonitor:
    """
    Analyzes agent thinking blocks for proactive intervention

    This is the key differentiator - by monitoring thinking,
    we can catch issues BEFORE they become actions.
    """

    # Patterns to detect in thinking
    PATTERNS = {
        ThinkingPattern.UNCERTAINTY: [
            r"i'm not sure",
            r"i don't know",
            r"unclear",
            r"might be",
            r"possibly",
            r"need to ask",
            r"should I",
        ],
        ThinkingPattern.PLAN_DEVIATION: [
            r"instead of",
            r"different approach",
            r"change the plan",
            r"deviate from",
            r"skip this step",
            r"not follow",
        ],
        ThinkingPattern.MOCK_INTENT: [
            r"use a mock",
            r"placeholder for now",
            r"simulate",
            r"fake data",
            r"stub out",
            r"temporary implementation",
        ],
        ThinkingPattern.NEEDS_INFO: [
            r"need to know",
            r"ask the user",
            r"missing information",
            r"don't have access",
            r"need clarification",
        ],
        ThinkingPattern.COMPLETION: [
            r"task (is )?complete",
            r"finished (the|this)",
            r"successfully",
            r"all (tests )?pass",
            r"done with",
        ],
        ThinkingPattern.ERROR_LOOP: [
            r"same error",
            r"still failing",
            r"tried .* times",
            r"not working",
            r"stuck on",
        ],
    }

    def __init__(self):
        self.history: List[ThinkingAnalysis] = []
        self.error_count = 0

    def analyze(self, thinking: str) -> ThinkingAnalysis:
        """
        Analyze a thinking block

        Args:
            thinking: The agent's thinking text

        Returns:
            Analysis with detected patterns and recommendations
        """
        detected = []
        scores = {}

        thinking_lower = thinking.lower()

        for pattern_type, patterns in self.PATTERNS.items():
            matches = sum(
                1 for p in patterns
                if re.search(p, thinking_lower)
            )
            if matches > 0:
                detected.append(pattern_type)
                scores[pattern_type] = min(1.0, matches * 0.3)

        # Determine if intervention is needed
        should_intervene = False
        recommended_action = None

        if ThinkingPattern.MOCK_INTENT in detected:
            should_intervene = True
            recommended_action = "BLOCK: Mock/placeholder detected. Require explicit approval."

        elif ThinkingPattern.ERROR_LOOP in detected:
            self.error_count += 1
            if self.error_count >= 3:
                should_intervene = True
                recommended_action = "ESCALATE: Error loop detected. Need human guidance."
        else:
            self.error_count = 0

        if ThinkingPattern.NEEDS_INFO in detected:
            should_intervene = True
            recommended_action = "PAUSE: Agent needs information. Escalate to user."

        if ThinkingPattern.PLAN_DEVIATION in detected:
            should_intervene = True
            recommended_action = "WARN: Potential plan drift. Verify with user."

        analysis = ThinkingAnalysis(
            patterns_detected=detected,
            confidence_scores=scores,
            extracted_intent=self._extract_intent(thinking),
            recommended_action=recommended_action,
            should_intervene=should_intervene
        )

        self.history.append(analysis)
        return analysis

    def _extract_intent(self, thinking: str) -> Optional[str]:
        """Extract the primary intent from thinking"""
        # Look for common intent patterns
        intent_patterns = [
            r"I will (.+?)(?:\.|$)",
            r"I'm going to (.+?)(?:\.|$)",
            r"Let me (.+?)(?:\.|$)",
            r"I need to (.+?)(?:\.|$)",
        ]

        for pattern in intent_patterns:
            match = re.search(pattern, thinking, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None


# =============================================================================
# Supervisor Agent
# =============================================================================

class InterventionType(Enum):
    """Types of supervisor intervention"""
    NONE = "none"
    INJECT_STEERING = "inject_steering"
    BLOCK_ACTION = "block_action"
    AUTO_PROCEED = "auto_proceed"
    ESCALATE = "escalate"
    CORRECT = "correct"


@dataclass
class SupervisorDecision:
    """Decision made by supervisor"""
    intervention_type: InterventionType
    message: Optional[str] = None
    inject_prompt: Optional[str] = None
    block_reason: Optional[str] = None
    escalation_context: Optional[str] = None


class SupervisorAgent:
    """
    Parent agent that monitors and steers child agents

    Features:
    - Monitors thinking blocks for early intervention
    - Enforces guardrails automatically
    - Manages plan execution and auto-proceed
    - Escalates to human when needed
    - Injects steering prompts as needed

    Usage:
        supervisor = SupervisorAgent()
        supervisor.load_plan(plan_tasks)

        # For each agent response:
        decision = supervisor.process_response(thinking, output)
        if decision.intervention_type == InterventionType.BLOCK_ACTION:
            # Don't execute, send correction
            ...
    """

    def __init__(
        self,
        plan_manager: Optional[PlanManager] = None,
        guardrail_engine: Optional[GuardrailEngine] = None,
        thinking_monitor: Optional[ThinkingMonitor] = None
    ):
        self.plan_manager = plan_manager or PlanManager()
        self.guardrail_engine = guardrail_engine or GuardrailEngine()
        self.thinking_monitor = thinking_monitor or ThinkingMonitor()

        # Steering prompts to inject
        self.steering_prompts: List[str] = []

        # Callbacks for different events
        self.on_violation: Optional[Callable[[GuardrailViolation], None]] = None
        self.on_progress: Optional[Callable[[str], None]] = None
        self.on_escalation: Optional[Callable[[str], bool]] = None

        logger.info("SupervisorAgent initialized")

    def add_steering(self, prompt: str) -> None:
        """Add a steering prompt to inject"""
        self.steering_prompts.append(prompt)

    def process_thinking(self, thinking: str) -> SupervisorDecision:
        """
        Process agent's thinking block BEFORE action

        This is the key to proactive intervention - we can
        catch and correct issues before they become actions.
        """
        # Analyze thinking
        analysis = self.thinking_monitor.analyze(thinking)

        # Check guardrails on thinking
        violations = self.guardrail_engine.check_thinking(thinking)
        blocking = self.guardrail_engine.get_blocking_violations(violations)

        # Decide on intervention
        if blocking:
            return SupervisorDecision(
                intervention_type=InterventionType.BLOCK_ACTION,
                block_reason=self.guardrail_engine.get_correction_message(blocking),
                message="Blocked due to guardrail violation in thinking"
            )

        if analysis.should_intervene:
            if "ESCALATE" in (analysis.recommended_action or ""):
                return SupervisorDecision(
                    intervention_type=InterventionType.ESCALATE,
                    escalation_context=analysis.recommended_action,
                    message="Escalating to human for guidance"
                )

            return SupervisorDecision(
                intervention_type=InterventionType.INJECT_STEERING,
                inject_prompt=analysis.recommended_action,
                message="Injecting steering based on thinking analysis"
            )

        return SupervisorDecision(intervention_type=InterventionType.NONE)

    def process_output(self, output: str) -> SupervisorDecision:
        """
        Process agent's output AFTER action

        Check for violations and determine if we should auto-proceed.
        """
        # Check guardrails on output
        violations = self.guardrail_engine.check_output(output)
        blocking = self.guardrail_engine.get_blocking_violations(violations)

        if blocking:
            return SupervisorDecision(
                intervention_type=InterventionType.CORRECT,
                inject_prompt=self.guardrail_engine.get_correction_message(blocking),
                message="Correction needed due to output violation"
            )

        # Check if we should auto-proceed
        if self.plan_manager.should_auto_proceed(output):
            next_task = self.plan_manager.current_plan.advance() if self.plan_manager.current_plan else None
            if next_task:
                return SupervisorDecision(
                    intervention_type=InterventionType.AUTO_PROCEED,
                    inject_prompt=f"Proceeding to next task: {next_task.description}",
                    message=f"Auto-proceeding to: {next_task.description}"
                )

        # Check for any pending steering
        if self.steering_prompts:
            prompt = self.steering_prompts.pop(0)
            return SupervisorDecision(
                intervention_type=InterventionType.INJECT_STEERING,
                inject_prompt=prompt
            )

        return SupervisorDecision(intervention_type=InterventionType.NONE)

    def process_response(
        self,
        thinking: Optional[str],
        output: str
    ) -> SupervisorDecision:
        """
        Process complete agent response (thinking + output)

        Args:
            thinking: Agent's thinking block (if available)
            output: Agent's output/response

        Returns:
            Decision on what intervention to take
        """
        # First check thinking if available
        if thinking:
            decision = self.process_thinking(thinking)
            if decision.intervention_type != InterventionType.NONE:
                return decision

        # Then check output
        return self.process_output(output)

    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status"""
        return {
            'plan': self.plan_manager.current_plan.to_dict() if self.plan_manager.current_plan else None,
            'violations_count': len(self.guardrail_engine.violations),
            'recent_violations': [
                str(v) for v in self.guardrail_engine.violations[-5:]
            ],
            'guardrails_active': len(self.guardrail_engine.guardrails),
            'guardrails_suppressed': list(self.guardrail_engine.suppressed)
        }

    def approve_guardrail_override(self, guardrail_id: str) -> None:
        """User approves override of a guardrail"""
        self.guardrail_engine.suppress_guardrail(guardrail_id)
        logger.info(f"Guardrail override approved: {guardrail_id}")


# =============================================================================
# Integration Helper
# =============================================================================

def create_supervisor(
    custom_guardrails: Optional[List[Dict[str, Any]]] = None,
    plan_tasks: Optional[List[Dict[str, Any]]] = None
) -> SupervisorAgent:
    """
    Factory function to create configured supervisor

    Args:
        custom_guardrails: Additional guardrails to enforce
        plan_tasks: Initial plan tasks

    Returns:
        Configured SupervisorAgent
    """
    supervisor = SupervisorAgent()

    # Add custom guardrails
    if custom_guardrails:
        for g in custom_guardrails:
            supervisor.guardrail_engine.add_guardrail(Guardrail(
                id=g['id'],
                name=g['name'],
                description=g.get('description', ''),
                pattern=g['pattern'],
                severity=GuardrailSeverity(g.get('severity', 'warning')),
                check_thinking=g.get('check_thinking', True),
                check_output=g.get('check_output', True),
                auto_fix=g.get('auto_fix')
            ))

    # Load plan if provided
    if plan_tasks:
        supervisor.plan_manager.create_plan("Current Plan", plan_tasks)

    return supervisor


# Global instance
_supervisor: Optional[SupervisorAgent] = None


def get_supervisor(force_new: bool = False) -> SupervisorAgent:
    """Get global supervisor instance"""
    global _supervisor
    if _supervisor is None or force_new:
        _supervisor = SupervisorAgent()
    return _supervisor
