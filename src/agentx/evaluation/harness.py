"""
Evaluation Harness - Orchestrates benchmark evaluations.

This module provides the core infrastructure for running reproducible
evaluations of AI agents on software engineering tasks.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from agentx.a2a.protocol import A2AProtocol, AgentCard, TaskStatus
from agentx.green_agent.evaluator import EvaluationRun, GreenAgent
from agentx.green_agent.tasks import TaskDefinition, TaskRegistry

logger = structlog.get_logger()


@dataclass
class EvaluationConfig:
    """Configuration for an evaluation run."""

    # Agent endpoints
    green_agent_endpoint: str = "http://localhost:8000"
    purple_agent_endpoint: str = "http://localhost:8001"

    # Task selection
    task_ids: list[str] | None = None
    task_categories: list[str] | None = None
    task_difficulties: list[str] | None = None

    # Reproducibility settings
    num_runs: int = 3
    seed: int | None = None
    deterministic: bool = True

    # Execution settings
    timeout_seconds: int = 300
    max_concurrent_tasks: int = 1
    retry_failed: bool = False
    max_retries: int = 3

    # Output settings
    output_directory: Path = field(default_factory=lambda: Path("results"))
    save_intermediate: bool = True
    verbose: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "green_agent_endpoint": self.green_agent_endpoint,
            "purple_agent_endpoint": self.purple_agent_endpoint,
            "task_ids": self.task_ids,
            "num_runs": self.num_runs,
            "seed": self.seed,
            "deterministic": self.deterministic,
            "timeout_seconds": self.timeout_seconds,
        }

    def get_fingerprint(self) -> str:
        """Generate a unique fingerprint for this configuration."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    @classmethod
    def from_file(cls, path: Path) -> EvaluationConfig:
        """Load configuration from a YAML or JSON file."""
        import yaml

        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        return cls(**data)


@dataclass
class EvaluationReport:
    """Complete report from an evaluation session."""

    config: EvaluationConfig
    runs: list[EvaluationRun]
    started_at: datetime
    completed_at: datetime | None = None

    # Aggregated metrics
    total_tasks: int = 0
    total_score: float = 0.0
    max_possible_score: float = 0.0
    average_score: float = 0.0

    # Reproducibility metrics
    reproducibility_verified: bool = False
    score_variance: float = 0.0
    score_std_dev: float = 0.0

    # Detailed results
    task_results: dict[str, list[dict]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "config": self.config.to_dict(),
            "runs": [r.to_dict() for r in self.runs],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_tasks": self.total_tasks,
            "total_score": self.total_score,
            "max_possible_score": self.max_possible_score,
            "average_score": self.average_score,
            "reproducibility_verified": self.reproducibility_verified,
            "score_variance": self.score_variance,
            "score_std_dev": self.score_std_dev,
            "errors": self.errors,
        }

    def save(self, path: Path) -> None:
        """Save report to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


class EvaluationHarness:
    """
    Main harness for running benchmark evaluations.

    The harness orchestrates evaluation runs, manages reproducibility,
    and generates comprehensive reports.
    """

    def __init__(
        self,
        config: EvaluationConfig | None = None,
        green_agent: GreenAgent | None = None,
    ):
        self.config = config or EvaluationConfig()
        self.green_agent = green_agent
        self._reports: list[EvaluationReport] = []

    async def initialize(self) -> None:
        """Initialize the harness and Green Agent."""
        if self.green_agent is None:
            self.green_agent = GreenAgent(
                endpoint=self.config.green_agent_endpoint,
            )
        await self.green_agent.initialize()
        logger.info("Evaluation harness initialized")

    async def shutdown(self) -> None:
        """Shutdown the harness."""
        if self.green_agent:
            await self.green_agent.shutdown()
        logger.info("Evaluation harness shutdown")

    def load_tasks(self, tasks_directory: Path) -> int:
        """Load tasks from a directory."""
        if self.green_agent is None:
            raise RuntimeError("Harness not initialized")

        tasks = self.green_agent.task_registry.load_from_directory(tasks_directory)
        logger.info("Tasks loaded", count=len(tasks))
        return len(tasks)

    async def run_evaluation(
        self,
        purple_agent_endpoint: str | None = None,
    ) -> EvaluationReport:
        """
        Run a complete evaluation session.

        This method:
        1. Runs multiple evaluation iterations for reproducibility
        2. Aggregates results across runs
        3. Verifies reproducibility
        4. Generates a comprehensive report

        Args:
            purple_agent_endpoint: Override endpoint for the Purple Agent

        Returns:
            Complete EvaluationReport
        """
        if self.green_agent is None:
            raise RuntimeError("Harness not initialized. Call initialize() first.")

        endpoint = purple_agent_endpoint or self.config.purple_agent_endpoint
        report = EvaluationReport(
            config=self.config,
            runs=[],
            started_at=datetime.utcnow(),
        )

        logger.info(
            "Starting evaluation",
            purple_agent=endpoint,
            num_runs=self.config.num_runs,
            seed=self.config.seed,
        )

        try:
            # Set random seed for reproducibility
            if self.config.deterministic and self.config.seed:
                random.seed(self.config.seed)

            # Run evaluations
            runs = await self.green_agent.evaluate_agent(
                purple_agent_endpoint=endpoint,
                task_ids=self.config.task_ids,
                num_runs=self.config.num_runs,
                seed=self.config.seed,
            )

            report.runs = runs

            # Aggregate metrics
            self._aggregate_metrics(report)

            # Verify reproducibility
            if self.config.num_runs >= 2:
                self._verify_reproducibility(report)

            # Save intermediate results if configured
            if self.config.save_intermediate:
                self._save_intermediate(report)

        except Exception as e:
            logger.error("Evaluation failed", error=str(e))
            report.errors.append(str(e))

        report.completed_at = datetime.utcnow()
        self._reports.append(report)

        logger.info(
            "Evaluation completed",
            total_score=report.total_score,
            average_score=report.average_score,
            reproducibility_verified=report.reproducibility_verified,
        )

        return report

    def _aggregate_metrics(self, report: EvaluationReport) -> None:
        """Aggregate metrics across all runs."""
        all_scores = []
        task_scores: dict[str, list[float]] = {}

        for run in report.runs:
            run_score = 0.0
            run_max = 0.0

            for result in run.results:
                run_score += result.score
                run_max += result.max_score

                if result.task_id not in task_scores:
                    task_scores[result.task_id] = []
                task_scores[result.task_id].append(result.score)

            all_scores.append(run_score)
            report.max_possible_score = max(report.max_possible_score, run_max)

        if all_scores:
            report.total_score = sum(all_scores)
            report.average_score = report.total_score / len(all_scores)
            report.total_tasks = sum(len(r.results) for r in report.runs)

        report.task_results = {
            task_id: [{"score": s} for s in scores]
            for task_id, scores in task_scores.items()
        }

    def _verify_reproducibility(self, report: EvaluationReport) -> None:
        """Verify reproducibility across runs."""
        if len(report.runs) < 2:
            return

        # Calculate variance and std dev of total scores
        scores = []
        for run in report.runs:
            run_score = sum(r.score for r in run.results)
            scores.append(run_score)

        if scores:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5

            report.score_variance = variance
            report.score_std_dev = std_dev

            # Consider reproducible if coefficient of variation < 5%
            cv = (std_dev / mean * 100) if mean > 0 else 0
            report.reproducibility_verified = cv < 5.0

    def _save_intermediate(self, report: EvaluationReport) -> None:
        """Save intermediate results during evaluation."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = self.config.output_directory / f"eval_{timestamp}.json"
        report.save(output_path)
        logger.info("Intermediate results saved", path=str(output_path))

    async def run_batch_evaluation(
        self,
        purple_agent_endpoints: list[str],
    ) -> list[EvaluationReport]:
        """
        Run evaluations against multiple Purple Agents.

        Useful for comparing different agent implementations.
        """
        reports = []
        for endpoint in purple_agent_endpoints:
            report = await self.run_evaluation(endpoint)
            reports.append(report)
        return reports

    def generate_comparison_report(
        self,
        reports: list[EvaluationReport] | None = None,
    ) -> dict[str, Any]:
        """Generate a comparison report across multiple evaluations."""
        reports = reports or self._reports

        comparison = {
            "agents": [],
            "rankings": [],
            "task_comparisons": {},
        }

        for report in reports:
            agent_summary = {
                "endpoint": report.config.purple_agent_endpoint,
                "average_score": report.average_score,
                "max_possible": report.max_possible_score,
                "normalized_score": (
                    report.average_score / report.max_possible_score * 100
                    if report.max_possible_score > 0 else 0
                ),
                "reproducibility_verified": report.reproducibility_verified,
                "score_std_dev": report.score_std_dev,
            }
            comparison["agents"].append(agent_summary)

        # Sort by normalized score for rankings
        comparison["rankings"] = sorted(
            comparison["agents"],
            key=lambda x: x["normalized_score"],
            reverse=True,
        )

        return comparison

    def export_results(
        self,
        output_path: Path | None = None,
        format: str = "json",
    ) -> None:
        """Export all evaluation results."""
        if not self._reports:
            logger.warning("No reports to export")
            return

        output_path = output_path or (
            self.config.output_directory / f"all_results.{format}"
        )

        data = {
            "reports": [r.to_dict() for r in self._reports],
            "comparison": self.generate_comparison_report(),
            "exported_at": datetime.utcnow().isoformat(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("Results exported", path=str(output_path))
