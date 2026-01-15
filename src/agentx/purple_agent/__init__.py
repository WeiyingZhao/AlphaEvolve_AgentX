"""Purple Agent (Baseline) - A2A-compatible agent for evaluation."""

from agentx.purple_agent.agent import PurpleAgent
from agentx.purple_agent.strategies import (
    BaseStrategy,
    CodeGenerationStrategy,
    DebugStrategy,
    RefactoringStrategy,
)

__all__ = [
    "PurpleAgent",
    "BaseStrategy",
    "CodeGenerationStrategy",
    "DebugStrategy",
    "RefactoringStrategy",
]
