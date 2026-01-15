"""Green Agent (Evaluator) - Defines environments, tasks, and automated scoring."""

from agentx.green_agent.evaluator import GreenAgent
from agentx.green_agent.scoring import ScoringEngine, ScoringResult
from agentx.green_agent.tasks import Task, TaskDefinition, TaskRegistry

__all__ = [
    "GreenAgent",
    "ScoringEngine",
    "ScoringResult",
    "Task",
    "TaskDefinition",
    "TaskRegistry",
]
