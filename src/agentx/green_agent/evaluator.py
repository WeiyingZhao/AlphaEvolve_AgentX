"""
Green Agent Evaluator - Main orchestrator for task evaluation.

The Green Agent is responsible for:
1. Defining evaluation environments
2. Managing task execution
3. Automated scoring of submissions
4. Publishing results to leaderboards
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from agentx.a2a.protocol import (
    A2AProtocol,
    AgentCard,
    EvaluationResult,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)
from agentx.green_agent.scoring import ScoringEngine, ScoringResult
from agentx.green_agent.tasks import Task, TaskDefinition, TaskRegistry

logger = structlog.get_logger()


class EvaluationRun:
    """Represents a single evaluation run for reproducibility tracking."""

    def __init__(
        self,
        run_id: str | None = None,
        seed: int | None = None,
    ):
        self.run_id = run_id or str(uuid.uuid4())
        self.seed = seed or random.randint(0, 2**32 - 1)
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.results: list[EvaluationResult] = []
        self.config: dict[str, Any] = {}

    def start(self) -> None:
        """Mark run as started."""
        self.started_at = datetime.utcnow()
        random.seed(self.seed)

    def complete(self) -> None:
        """Mark run as completed."""
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Export run data for reproducibility."""
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "config": self.config,
            "results": [r.model_dump() for r in self.results],
        }


class GreenAgent:
    """
    Green Agent - Evaluator for AI agent benchmarking.

    The Green Agent defines environments, manages tasks, and performs
    automated scoring of Purple Agent submissions.
    """

    def __init__(
        self,
        name: str = "AlphaEvolve-GreenAgent",
        description: str = "Evaluator for software engineering tasks",
        endpoint: str = "http://localhost:8000",
        tasks_directory: Path | None = None,
    ):
        self.agent_card = AgentCard(
            name=name,
            description=description,
            version="0.1.0",
            capabilities=[
                "task_definition",
                "automated_scoring",
                "test_execution",
                "leaderboard_publishing",
            ],
            supported_tasks=[
                "code_generation",
                "bug_fix",
                "refactoring",
                "test_writing",
                "code_review",
            ],
            endpoint=endpoint,
            protocol_version="1.0",
        )

        self.task_registry = TaskRegistry()
        self.evaluation_runs: list[EvaluationRun] = []
        self._protocol: A2AProtocol | None = None

        # Load tasks if directory provided
        if tasks_directory and tasks_directory.exists():
            self.task_registry.load_from_directory(tasks_directory)
            logger.info(
                "Loaded tasks from directory",
                directory=str(tasks_directory),
                task_count=len(self.task_registry),
            )

    async def initialize(self) -> None:
        """Initialize the Green Agent."""
        self._protocol = A2AProtocol(self.agent_card)
        await self._protocol.__aenter__()
        logger.info("Green Agent initialized", agent_id=self.agent_card.agent_id)

    async def shutdown(self) -> None:
        """Shutdown the Green Agent."""
        if self._protocol:
            await self._protocol.__aexit__(None, None, None)
        logger.info("Green Agent shutdown")

    def register_task(self, task: TaskDefinition) -> None:
        """Register a new task for evaluation."""
        self.task_registry.register(task)
        logger.info("Task registered", task_id=task.task_id, category=task.category.value)

    def get_task(self, task_id: str) -> TaskDefinition | None:
        """Get a task definition by ID."""
        return self.task_registry.get(task_id)

    def list_tasks(self) -> list[TaskDefinition]:
        """List all available tasks."""
        return list(self.task_registry)

    async def evaluate_agent(
        self,
        purple_agent_endpoint: str,
        task_ids: list[str] | None = None,
        num_runs: int = 1,
        seed: int | None = None,
    ) -> list[EvaluationRun]:
        """
        Evaluate a Purple Agent on specified tasks.

        Args:
            purple_agent_endpoint: URL of the Purple Agent
            task_ids: List of task IDs to evaluate (None = all tasks)
            num_runs: Number of evaluation runs for reproducibility
            seed: Random seed for reproducibility

        Returns:
            List of EvaluationRun results
        """
        if not self._protocol:
            raise RuntimeError("Green Agent not initialized. Call initialize() first.")

        # Determine tasks to run
        tasks_to_evaluate = []
        if task_ids:
            for tid in task_ids:
                task = self.task_registry.get(tid)
                if task:
                    tasks_to_evaluate.append(task)
        else:
            tasks_to_evaluate = list(self.task_registry)

        if not tasks_to_evaluate:
            logger.warning("No tasks to evaluate")
            return []

        runs = []
        base_seed = seed or random.randint(0, 2**32 - 1)

        for run_num in range(num_runs):
            run = EvaluationRun(seed=base_seed + run_num)
            run.config = {
                "purple_agent": purple_agent_endpoint,
                "task_count": len(tasks_to_evaluate),
                "run_number": run_num + 1,
                "total_runs": num_runs,
            }
            run.start()

            logger.info(
                "Starting evaluation run",
                run_id=run.run_id,
                run_number=run_num + 1,
                seed=run.seed,
            )

            for task_def in tasks_to_evaluate:
                result = await self._evaluate_single_task(
                    purple_agent_endpoint,
                    task_def,
                )
                run.results.append(result)

            run.complete()
            runs.append(run)
            self.evaluation_runs.append(run)

            logger.info(
                "Evaluation run completed",
                run_id=run.run_id,
                results_count=len(run.results),
            )

        return runs

    async def _evaluate_single_task(
        self,
        purple_agent_endpoint: str,
        task_def: TaskDefinition,
    ) -> EvaluationResult:
        """Evaluate a single task against a Purple Agent."""
        logger.info("Evaluating task", task_id=task_def.task_id)

        # Determine if this is an ML task requiring persistence
        work_dir = None
        is_ml_task = task_def.category.value == "ml_engineering"  # String comparison to avoid import issues
        
        if is_ml_task:
            # Use a persistent workspace for this task
            work_dir = Path("/workspace") / task_def.task_id
            work_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Using persistent workspace", path=str(work_dir))

        # Iteration loop for ML tasks (self-evolution)
        max_iterations = 3 if is_ml_task else 1
        current_feedback = ""
        best_result = None

        for iteration in range(max_iterations):
            logger.info("Starting iteration", iteration=iteration+1, task_id=task_def.task_id)
            
            # Create task request
            task_request = TaskRequest(
                task_id=task_def.task_id,
                task_type=task_def.category.value,
                description=task_def.description,
                context={
                    "detailed_instructions": task_def.detailed_instructions,
                    "iteration": iteration + 1,
                    "max_iterations": max_iterations,
                    "previous_feedback": current_feedback
                },
                files={**task_def.context_files, **task_def.starter_code},
                test_cases=[t.model_dump() for t in task_def.public_tests],
                constraints={
                    "time_limit_seconds": task_def.time_limit_seconds,
                    "allowed_languages": task_def.allowed_languages,
                },
                timeout_seconds=task_def.time_limit_seconds,
                evaluation_criteria=task_def.evaluation_criteria,
                max_score=task_def.max_score,
            )

            # Send to Purple Agent
            response = await self._protocol.send_task_request(
                purple_agent_endpoint,
                task_request,
            )

            # Score the response
            current_eval_result = None
            if response and response.status == TaskStatus.COMPLETED:
                scoring_engine = ScoringEngine(
                    task_def, 
                    work_dir=work_dir if is_ml_task else None
                )
                score_result = scoring_engine.score_submission(
                    response.output_files,
                    run_hidden_tests=True,
                )
                
                # Check for ML metrics in logs if needed
                if is_ml_task and task_def.evaluation_metric:
                    # Hypothetical: scan stdout for "METRIC_XX"
                    # For now just use score_result
                    pass

                current_eval_result = EvaluationResult(
                    task_id=task_def.task_id,
                    score=score_result.total_score,
                    max_score=score_result.max_score,
                    passed_criteria=[
                        f"Test {r.test_id}" for r in score_result.test_results if r.passed
                    ],
                    failed_criteria=[
                        f"Test {r.test_id}" for r in score_result.test_results if not r.passed
                    ],
                    detailed_scores=score_result.category_scores,
                    feedback="\n".join(score_result.feedback),
                    test_results=[r.model_dump() for r in score_result.test_results],
                )
                
                # Update best result
                if best_result is None or current_eval_result.score > best_result.score:
                    best_result = current_eval_result
                
                # If perfect score, break early
                if score_result.normalized_score >= 100.0:
                    logger.info("Perfect score achieved, stopping iterations")
                    break
                
                # Generate feedback for next iteration
                current_feedback = f"Attempt {iteration+1} Score: {score_result.normalized_score}%\n"
                current_feedback += f"Feedback: {current_eval_result.feedback}\n"
                if is_ml_task:
                     current_feedback += "Please try to improve your solution based on this feedback."

            else:
                error_msg = response.error_message if response else "No response received"
                current_eval_result = EvaluationResult(
                    task_id=task_def.task_id,
                    score=0.0,
                    max_score=task_def.max_score,
                    feedback=f"Evaluation failed: {error_msg}",
                )
                if best_result is None:
                    best_result = current_eval_result
        
        return best_result

    def generate_leaderboard(
        self,
        runs: list[EvaluationRun] | None = None,
    ) -> dict[str, Any]:
        """Generate leaderboard data from evaluation runs."""
        runs = runs or self.evaluation_runs

        if not runs:
            return {"entries": [], "metadata": {}}

        # Aggregate results
        agent_scores: dict[str, list[float]] = {}
        task_results: dict[str, list[dict]] = {}

        for run in runs:
            agent_endpoint = run.config.get("purple_agent", "unknown")
            if agent_endpoint not in agent_scores:
                agent_scores[agent_endpoint] = []

            run_total = sum(r.score for r in run.results)
            run_max = sum(r.max_score for r in run.results)
            normalized = (run_total / run_max * 100) if run_max > 0 else 0
            agent_scores[agent_endpoint].append(normalized)

            for result in run.results:
                if result.task_id not in task_results:
                    task_results[result.task_id] = []
                task_results[result.task_id].append({
                    "agent": agent_endpoint,
                    "score": result.score,
                    "max_score": result.max_score,
                })

        # Build leaderboard entries
        entries = []
        for agent, scores in agent_scores.items():
            entries.append({
                "agent": agent,
                "average_score": sum(scores) / len(scores),
                "best_score": max(scores),
                "worst_score": min(scores),
                "run_count": len(scores),
                "std_dev": self._calculate_std_dev(scores),
            })

        # Sort by average score descending
        entries.sort(key=lambda x: x["average_score"], reverse=True)

        # Add ranks
        for i, entry in enumerate(entries, 1):
            entry["rank"] = i

        return {
            "entries": entries,
            "task_breakdown": task_results,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_runs": len(runs),
                "total_agents": len(entries),
            },
        }

    def _calculate_std_dev(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def export_results(
        self,
        output_path: Path,
        runs: list[EvaluationRun] | None = None,
    ) -> None:
        """Export evaluation results to file."""
        runs = runs or self.evaluation_runs
        data = {
            "agent": self.agent_card.model_dump(),
            "runs": [run.to_dict() for run in runs],
            "leaderboard": self.generate_leaderboard(runs),
            "exported_at": datetime.utcnow().isoformat(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("Results exported", path=str(output_path))

    def verify_reproducibility(
        self,
        runs: list[EvaluationRun],
    ) -> dict[str, Any]:
        """
        Verify reproducibility across multiple runs.

        Returns statistics about score consistency.
        """
        if len(runs) < 2:
            return {"status": "insufficient_runs", "min_required": 2}

        task_scores: dict[str, list[float]] = {}
        for run in runs:
            for result in run.results:
                if result.task_id not in task_scores:
                    task_scores[result.task_id] = []
                task_scores[result.task_id].append(result.score)

        consistency_report = {}
        for task_id, scores in task_scores.items():
            std_dev = self._calculate_std_dev(scores)
            mean = sum(scores) / len(scores)
            cv = (std_dev / mean * 100) if mean > 0 else 0  # Coefficient of variation

            consistency_report[task_id] = {
                "mean_score": round(mean, 2),
                "std_dev": round(std_dev, 2),
                "coefficient_of_variation": round(cv, 2),
                "is_reproducible": cv < 5.0,  # Less than 5% variation
            }

        reproducible_count = sum(
            1 for v in consistency_report.values() if v["is_reproducible"]
        )

        return {
            "status": "verified",
            "runs_analyzed": len(runs),
            "tasks_analyzed": len(task_scores),
            "reproducible_tasks": reproducible_count,
            "reproducibility_rate": round(
                reproducible_count / len(task_scores) * 100, 2
            ) if task_scores else 0,
            "task_details": consistency_report,
        }
