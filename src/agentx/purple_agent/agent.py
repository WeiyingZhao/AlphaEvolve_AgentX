"""
Purple Agent - Baseline A2A-compatible agent for evaluation.

The Purple Agent receives tasks from the Green Agent, processes them,
and returns solutions for scoring.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

import structlog

from agentx.a2a.protocol import (
    AgentCard,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)
from agentx.purple_agent.strategies import BaseStrategy, CompositeStrategy

logger = structlog.get_logger()


class PurpleAgent:
    """
    Purple Agent - Baseline agent for benchmark evaluation.

    This agent provides a simple baseline implementation for solving
    software engineering tasks. It can be extended or replaced with
    more sophisticated agents for comparison.
    """

    def __init__(
        self,
        name: str = "AlphaEvolve-PurpleAgent-Baseline",
        description: str = "Baseline agent for software engineering tasks",
        endpoint: str = "http://localhost:8001",
        strategy: BaseStrategy | None = None,
    ):
        self.agent_card = AgentCard(
            name=name,
            description=description,
            version="0.1.0",
            capabilities=[
                "code_generation",
                "bug_fixing",
                "refactoring",
                "test_writing",
            ],
            supported_tasks=[
                "code_generation",
                "bug_fix",
                "refactoring",
                "test_writing",
                "debugging",
                "optimization",
            ],
            endpoint=endpoint,
            protocol_version="1.0",
        )

        self.strategy = strategy or CompositeStrategy()
        self._task_history: list[dict[str, Any]] = []

    async def process_task(self, task: TaskRequest) -> TaskResponse:
        """
        Process a task request and return a response.

        Args:
            task: The task request from the Green Agent

        Returns:
            TaskResponse with the solution or error
        """
        logger.info(
            "Processing task",
            task_id=task.task_id,
            task_type=task.task_type,
        )

        start_time = time.time()
        logs = []

        try:
            logs.append(f"[{datetime.utcnow().isoformat()}] Task received: {task.task_id}")
            logs.append(f"[{datetime.utcnow().isoformat()}] Task type: {task.task_type}")

            # Check if we can handle this task type
            if not self.strategy.can_handle(task.task_type):
                logs.append(f"[{datetime.utcnow().isoformat()}] Warning: No specific strategy for {task.task_type}")

            # Execute the strategy
            logs.append(f"[{datetime.utcnow().isoformat()}] Executing solution strategy...")
            output_files = await self.strategy.solve(task)

            execution_time = time.time() - start_time
            logs.append(f"[{datetime.utcnow().isoformat()}] Solution generated in {execution_time:.2f}s")
            logs.append(f"[{datetime.utcnow().isoformat()}] Output files: {list(output_files.keys())}")

            # Record in history
            self._task_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": "completed",
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            })

            return TaskResponse(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result={"message": "Task completed successfully"},
                output_files=output_files,
                logs=logs,
                execution_time_seconds=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logs.append(f"[{datetime.utcnow().isoformat()}] ERROR: {error_msg}")

            logger.error(
                "Task processing failed",
                task_id=task.task_id,
                error=error_msg,
            )

            # Record failure in history
            self._task_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": "failed",
                "error": error_msg,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            })

            return TaskResponse(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                logs=logs,
                execution_time_seconds=execution_time,
                error_message=error_msg,
            )

    def get_task_history(self) -> list[dict[str, Any]]:
        """Get the history of processed tasks."""
        return self._task_history.copy()

    def get_statistics(self) -> dict[str, Any]:
        """Get agent statistics."""
        if not self._task_history:
            return {
                "total_tasks": 0,
                "completed": 0,
                "failed": 0,
                "success_rate": 0.0,
            }

        total = len(self._task_history)
        completed = sum(1 for t in self._task_history if t["status"] == "completed")
        failed = total - completed

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / total * 100, 2) if total > 0 else 0.0,
            "average_execution_time": round(
                sum(t["execution_time"] for t in self._task_history) / total, 3
            ),
        }


class AdvancedPurpleAgent(PurpleAgent):
    """
    Advanced Purple Agent with LLM integration capability.

    This agent can optionally use an LLM backend for more sophisticated
    code generation. When no LLM is available, it falls back to the
    baseline strategies.
    """

    def __init__(
        self,
        llm_endpoint: str | None = None,
        llm_api_key: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_endpoint = llm_endpoint
        self.llm_api_key = llm_api_key
        self._llm_available = llm_endpoint is not None

        if self._llm_available:
            self.agent_card.capabilities.append("llm_enhanced")

    async def process_task(self, task: TaskRequest) -> TaskResponse:
        """
        Process task with optional LLM enhancement.

        If an LLM endpoint is configured, it will be used for
        more sophisticated code generation.
        """
        if self._llm_available:
            try:
                return await self._process_with_llm(task)
            except Exception as e:
                logger.warning(
                    "LLM processing failed, falling back to baseline",
                    error=str(e),
                )

        # Fall back to baseline processing
        return await super().process_task(task)

    async def _process_with_llm(self, task: TaskRequest) -> TaskResponse:
        """Process task using LLM backend."""
        # This is a placeholder for LLM integration
        # In a real implementation, this would call the LLM API
        raise NotImplementedError("LLM integration not yet implemented")
