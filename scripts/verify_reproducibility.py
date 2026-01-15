#!/usr/bin/env python3
"""
Script to verify reproducibility of the evaluation framework.

This script runs multiple evaluations with the same seed and verifies
that results are consistent across runs.

Usage:
    python scripts/verify_reproducibility.py [--runs N] [--seed S]
"""
import argparse
import asyncio
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentx.evaluation.harness import EvaluationConfig, EvaluationHarness


async def run_reproducibility_verification(
    num_runs: int = 3,
    seed: int = 42,
    output_path: str = "results/reproducibility_report.json",
):
    """
    Run multiple evaluation runs and verify reproducibility.

    Args:
        num_runs: Number of evaluation runs
        seed: Random seed for reproducibility
        output_path: Path to save the report
    """
    print(f"=" * 60)
    print("AlphaEvolve AgentX - Reproducibility Verification")
    print(f"=" * 60)
    print(f"Runs: {num_runs}")
    print(f"Seed: {seed}")
    print()

    config = EvaluationConfig(
        num_runs=num_runs,
        seed=seed,
        deterministic=True,
        save_intermediate=True,
    )

    harness = EvaluationHarness(config)

    try:
        await harness.initialize()

        # Load tasks from benchmarks directory
        tasks_dir = Path(__file__).parent.parent / "benchmarks" / "tasks"
        if tasks_dir.exists():
            task_count = harness.load_tasks(tasks_dir)
            print(f"Loaded {task_count} tasks")
        else:
            print("Warning: No tasks directory found")
            return

        print()
        print("Running evaluation...")
        print("-" * 40)

        # Run evaluation
        report = await harness.run_evaluation()

        # Analyze results
        print()
        print("=" * 60)
        print("REPRODUCIBILITY REPORT")
        print("=" * 60)

        # Calculate per-task consistency
        task_consistency = {}
        for task_id, results in report.task_results.items():
            scores = [r["score"] for r in results]
            if len(scores) > 1:
                std_dev = statistics.stdev(scores)
                mean = statistics.mean(scores)
                cv = (std_dev / mean * 100) if mean > 0 else 0
                task_consistency[task_id] = {
                    "mean": round(mean, 2),
                    "std_dev": round(std_dev, 4),
                    "coefficient_of_variation": round(cv, 2),
                    "is_reproducible": cv < 5.0,
                }

        reproducible_tasks = sum(
            1 for t in task_consistency.values() if t["is_reproducible"]
        )
        total_tasks = len(task_consistency)
        reproducibility_rate = (
            (reproducible_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        print(f"Total tasks evaluated: {total_tasks}")
        print(f"Reproducible tasks: {reproducible_tasks}/{total_tasks}")
        print(f"Reproducibility rate: {reproducibility_rate:.1f}%")
        print(f"Overall score variance: {report.score_variance:.4f}")
        print(f"Overall score std dev: {report.score_std_dev:.4f}")
        print()

        # Task-by-task breakdown
        print("Task-by-task analysis:")
        print("-" * 40)
        for task_id, stats in task_consistency.items():
            status = "✓" if stats["is_reproducible"] else "✗"
            print(f"  {status} {task_id}")
            print(f"      Mean: {stats['mean']:.2f}, StdDev: {stats['std_dev']:.4f}")

        # Generate report
        result = {
            "verification_time": datetime.utcnow().isoformat(),
            "num_runs": num_runs,
            "seed": seed,
            "reproducibility_rate": reproducibility_rate,
            "is_reproducible": reproducibility_rate >= 95.0,
            "overall_variance": report.score_variance,
            "overall_std_dev": report.score_std_dev,
            "task_details": task_consistency,
            "summary": {
                "total_tasks": total_tasks,
                "reproducible_tasks": reproducible_tasks,
                "average_score": report.average_score,
                "max_possible": report.max_possible_score,
            },
        }

        # Save report
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print()
        print(f"Report saved to: {output_file}")
        print()

        # Final verdict
        if result["is_reproducible"]:
            print("✅ REPRODUCIBILITY VERIFIED")
            print("   The evaluation framework produces consistent results.")
        else:
            print("❌ REPRODUCIBILITY CHECK FAILED")
            print("   Results vary significantly across runs.")

        return result

    finally:
        await harness.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="Verify reproducibility of evaluation framework"
    )
    parser.add_argument(
        "--runs", type=int, default=3, help="Number of evaluation runs"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/reproducibility_report.json",
        help="Output path for report",
    )

    args = parser.parse_args()

    result = asyncio.run(
        run_reproducibility_verification(
            num_runs=args.runs,
            seed=args.seed,
            output_path=args.output,
        )
    )

    # Exit with appropriate code
    sys.exit(0 if result and result.get("is_reproducible") else 1)


if __name__ == "__main__":
    main()
