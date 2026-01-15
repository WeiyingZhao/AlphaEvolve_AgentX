"""
AlphaEvolve AgentX - Green Agent Evaluator for Software Engineering Tasks

This package provides a comprehensive benchmark framework for evaluating AI agents
on software engineering tasks including code generation, debugging, refactoring,
and test writing.
"""

__version__ = "0.1.0"
__author__ = "AlphaEvolve Team"

from agentx.a2a.protocol import A2AMessage, A2AProtocol, TaskRequest, TaskResponse
from agentx.evaluation.harness import EvaluationHarness
from agentx.green_agent.evaluator import GreenAgent
from agentx.purple_agent.agent import PurpleAgent

__all__ = [
    "A2AMessage",
    "A2AProtocol",
    "TaskRequest",
    "TaskResponse",
    "EvaluationHarness",
    "GreenAgent",
    "PurpleAgent",
]
