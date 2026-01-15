"""
Evaluation Runner - Command-line and programmatic evaluation execution.

This module provides utilities for running evaluations from the command line
or programmatically.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from agentx.evaluation.harness import EvaluationConfig, EvaluationHarness, EvaluationReport

logger = structlog.get_logger()


class EvaluationRunner:
    """Runner for executing single evaluation sessions."""

    def __init__(
        self,
        config: EvaluationConfig | None = None,
        tasks_directory: Path | None = None,
    ):
        self.config = config or EvaluationConfig()
        self.tasks_directory = tasks_directory
        self.harness: EvaluationHarness | None = None

    async def setup(self) -> None:
        """Initialize the runner."""
        self.harness = EvaluationHarness(config=self.config)
        await self.harness.initialize()

        if self.tasks_directory:
            self.harness.load_tasks(self.tasks_directory)

    async def teardown(self) -> None:
        """Cleanup the runner."""
        if self.harness:
            await self.harness.shutdown()

    async def run(
        self,
        purple_agent_endpoint: str | None = None,
    ) -> EvaluationReport:
        """Run the evaluation."""
        if not self.harness:
            await self.setup()

        try:
            report = await self.harness.run_evaluation(purple_agent_endpoint)
            return report
        finally:
            pass  # Keep harness alive for potential reuse

    async def run_and_report(
        self,
        purple_agent_endpoint: str | None = None,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Run evaluation and generate a report."""
        report = await self.run(purple_agent_endpoint)

        # Save report
        if output_path:
            report.save(output_path)

        # Return summary
        return {
            "status": "completed" if not report.errors else "completed_with_errors",
            "total_score": report.total_score,
            "average_score": report.average_score,
            "max_possible": report.max_possible_score,
            "normalized_score": (
                report.average_score / report.max_possible_score * 100
                if report.max_possible_score > 0 else 0
            ),
            "reproducibility_verified": report.reproducibility_verified,
            "num_runs": len(report.runs),
            "total_tasks": report.total_tasks,
            "errors": report.errors,
        }


class BatchRunner:
    """Runner for batch evaluation of multiple agents."""

    def __init__(
        self,
        config: EvaluationConfig | None = None,
        tasks_directory: Path | None = None,
    ):
        self.config = config or EvaluationConfig()
        self.tasks_directory = tasks_directory
        self.results: list[dict[str, Any]] = []

    async def run_batch(
        self,
        purple_agent_endpoints: list[str],
        output_directory: Path | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run evaluations for multiple Purple Agents.

        Args:
            purple_agent_endpoints: List of Purple Agent URLs
            output_directory: Directory to save results

        Returns:
            List of result summaries
        """
        output_dir = output_directory or self.config.output_directory
        output_dir.mkdir(parents=True, exist_ok=True)

        runner = EvaluationRunner(
            config=self.config,
            tasks_directory=self.tasks_directory,
        )

        try:
            await runner.setup()

            for endpoint in purple_agent_endpoints:
                logger.info("Evaluating agent", endpoint=endpoint)

                try:
                    report = await runner.run(endpoint)

                    # Save individual report
                    agent_name = endpoint.replace("://", "_").replace("/", "_").replace(":", "_")
                    report_path = output_dir / f"report_{agent_name}.json"
                    report.save(report_path)

                    self.results.append({
                        "endpoint": endpoint,
                        "status": "success",
                        "score": report.average_score,
                        "max_score": report.max_possible_score,
                        "report_path": str(report_path),
                    })

                except Exception as e:
                    logger.error("Evaluation failed", endpoint=endpoint, error=str(e))
                    self.results.append({
                        "endpoint": endpoint,
                        "status": "failed",
                        "error": str(e),
                    })

        finally:
            await runner.teardown()

        # Save batch summary
        self._save_batch_summary(output_dir)

        return self.results

    def _save_batch_summary(self, output_dir: Path) -> None:
        """Save batch evaluation summary."""
        summary = {
            "batch_results": self.results,
            "total_agents": len(self.results),
            "successful": sum(1 for r in self.results if r.get("status") == "success"),
            "failed": sum(1 for r in self.results if r.get("status") == "failed"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Sort by score for leaderboard
        successful_results = [r for r in self.results if r.get("status") == "success"]
        summary["leaderboard"] = sorted(
            successful_results,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        summary_path = output_dir / "batch_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Batch summary saved", path=str(summary_path))

    def generate_leaderboard(self) -> list[dict[str, Any]]:
        """Generate leaderboard from batch results."""
        successful = [r for r in self.results if r.get("status") == "success"]
        leaderboard = sorted(
            successful,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        for rank, entry in enumerate(leaderboard, 1):
            entry["rank"] = rank

        return leaderboard


async def main_cli():
    """Command-line interface for running evaluations."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AlphaEvolve AgentX - Evaluation Runner"
    )
    parser.add_argument(
        "--purple-agent",
        "-p",
        default="http://localhost:8001",
        help="Purple Agent endpoint URL",
    )
    parser.add_argument(
        "--green-agent",
        "-g",
        default="http://localhost:8000",
        help="Green Agent endpoint URL",
    )
    parser.add_argument(
        "--tasks-dir",
        "-t",
        type=Path,
        default=None,
        help="Directory containing task definitions",
    )
    parser.add_argument(
        "--num-runs",
        "-n",
        type=int,
        default=3,
        help="Number of evaluation runs for reproducibility",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Configure logging
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if args.verbose else logging.INFO
        ),
    )

    # Create configuration
    config = EvaluationConfig(
        green_agent_endpoint=args.green_agent,
        purple_agent_endpoint=args.purple_agent,
        num_runs=args.num_runs,
        seed=args.seed,
        output_directory=args.output,
        verbose=args.verbose,
    )

    # Run evaluation
    runner = EvaluationRunner(
        config=config,
        tasks_directory=args.tasks_dir,
    )

    try:
        result = await runner.run_and_report(
            output_path=args.output / "evaluation_report.json",
        )

        print("\n" + "=" * 50)
        print("EVALUATION COMPLETE")
        print("=" * 50)
        print(f"Status: {result['status']}")
        print(f"Average Score: {result['average_score']:.2f} / {result['max_possible']:.2f}")
        print(f"Normalized Score: {result['normalized_score']:.2f}%")
        print(f"Reproducibility Verified: {result['reproducibility_verified']}")
        print(f"Total Tasks: {result['total_tasks']}")
        print(f"Number of Runs: {result['num_runs']}")

        if result['errors']:
            print(f"\nErrors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")

        print("=" * 50)

    finally:
        await runner.teardown()


if __name__ == "__main__":
    import logging
    asyncio.run(main_cli())
