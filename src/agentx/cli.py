"""
AlphaEvolve AgentX CLI - Command-line interface for the evaluation framework.

This module provides a comprehensive CLI for:
- Running evaluations
- Managing tasks
- Viewing results and leaderboards
- Starting agent servers
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="agentx",
    help="AlphaEvolve AgentX - Green Agent Evaluator for Software Engineering Tasks",
    add_completion=False,
)

console = Console()


@app.command()
def version():
    """Show version information."""
    from agentx import __version__
    console.print(f"AlphaEvolve AgentX v{__version__}")


@app.command()
def serve_green(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
    tasks_dir: Optional[Path] = typer.Option(None, help="Tasks directory"),
):
    """Start the Green Agent (evaluator) server."""
    console.print("[green]Starting Green Agent server...[/green]")

    import uvicorn
    uvicorn.run(
        "agentx.green_agent.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


@app.command()
def serve_purple(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8001, help="Port to listen on"),
):
    """Start the Purple Agent (baseline) server."""
    console.print("[purple]Starting Purple Agent server...[/purple]")

    import uvicorn
    uvicorn.run(
        "agentx.purple_agent.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


@app.command()
def evaluate(
    purple_agent: str = typer.Option(
        "http://localhost:8001",
        "--purple", "-p",
        help="Purple Agent endpoint URL",
    ),
    green_agent: str = typer.Option(
        "http://localhost:8000",
        "--green", "-g",
        help="Green Agent endpoint URL",
    ),
    num_runs: int = typer.Option(3, "--runs", "-n", help="Number of evaluation runs"),
    seed: Optional[int] = typer.Option(None, "--seed", "-s", help="Random seed"),
    output: Path = typer.Option(
        Path("results"),
        "--output", "-o",
        help="Output directory",
    ),
    task_ids: Optional[str] = typer.Option(
        None,
        "--tasks", "-t",
        help="Comma-separated list of task IDs to run",
    ),
):
    """Run an evaluation against a Purple Agent."""
    from agentx.evaluation.harness import EvaluationConfig, EvaluationHarness

    console.print("[bold]AlphaEvolve AgentX Evaluation[/bold]")
    console.print(f"Purple Agent: {purple_agent}")
    console.print(f"Green Agent: {green_agent}")
    console.print(f"Number of runs: {num_runs}")

    config = EvaluationConfig(
        green_agent_endpoint=green_agent,
        purple_agent_endpoint=purple_agent,
        num_runs=num_runs,
        seed=seed,
        output_directory=output,
        task_ids=task_ids.split(",") if task_ids else None,
    )

    async def run_eval():
        harness = EvaluationHarness(config=config)
        await harness.initialize()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running evaluation...", total=None)
            report = await harness.run_evaluation()
            progress.update(task, completed=True)

        await harness.shutdown()
        return report

    report = asyncio.run(run_eval())

    # Display results
    console.print("\n[bold green]Evaluation Complete[/bold green]")

    table = Table(title="Results Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Score", f"{report.total_score:.2f}")
    table.add_row("Max Possible", f"{report.max_possible_score:.2f}")
    table.add_row("Average Score", f"{report.average_score:.2f}")
    table.add_row(
        "Normalized Score",
        f"{(report.average_score / report.max_possible_score * 100):.2f}%"
        if report.max_possible_score > 0 else "N/A",
    )
    table.add_row("Reproducibility", "✓" if report.reproducibility_verified else "✗")
    table.add_row("Score Std Dev", f"{report.score_std_dev:.4f}")
    table.add_row("Total Tasks", str(report.total_tasks))
    table.add_row("Number of Runs", str(len(report.runs)))

    console.print(table)

    if report.errors:
        console.print("\n[red]Errors:[/red]")
        for error in report.errors:
            console.print(f"  • {error}")

    # Save report
    report_path = output / "evaluation_report.json"
    report.save(report_path)
    console.print(f"\nReport saved to: {report_path}")


@app.command()
def list_tasks(
    tasks_dir: Path = typer.Option(
        Path("benchmarks/tasks"),
        "--dir", "-d",
        help="Tasks directory",
    ),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    difficulty: Optional[str] = typer.Option(None, "--difficulty", help="Filter by difficulty"),
):
    """List available benchmark tasks."""
    from agentx.green_agent.tasks import TaskRegistry, TaskCategory, TaskDifficulty

    registry = TaskRegistry()

    if tasks_dir.exists():
        registry.load_from_directory(tasks_dir)
    else:
        console.print(f"[yellow]Tasks directory not found: {tasks_dir}[/yellow]")
        return

    # Filter tasks
    cat = TaskCategory(category) if category else None
    diff = TaskDifficulty(difficulty) if difficulty else None
    tasks = registry.list_tasks(category=cat, difficulty=diff)

    if not tasks:
        console.print("[yellow]No tasks found matching criteria[/yellow]")
        return

    table = Table(title=f"Available Tasks ({len(tasks)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Category", style="green")
    table.add_column("Difficulty", style="yellow")
    table.add_column("Max Score", style="magenta")

    for task in tasks:
        table.add_row(
            task.task_id,
            task.name,
            task.category.value,
            task.difficulty.value,
            str(task.max_score),
        )

    console.print(table)


@app.command()
def show_task(
    task_id: str = typer.Argument(..., help="Task ID to show"),
    tasks_dir: Path = typer.Option(
        Path("benchmarks/tasks"),
        "--dir", "-d",
        help="Tasks directory",
    ),
):
    """Show details of a specific task."""
    from agentx.green_agent.tasks import TaskRegistry

    registry = TaskRegistry()

    if tasks_dir.exists():
        registry.load_from_directory(tasks_dir)

    task = registry.get(task_id)
    if not task:
        console.print(f"[red]Task not found: {task_id}[/red]")
        return

    console.print(f"\n[bold cyan]{task.name}[/bold cyan]")
    console.print(f"ID: {task.task_id}")
    console.print(f"Category: {task.category.value}")
    console.print(f"Difficulty: {task.difficulty.value}")
    console.print(f"Max Score: {task.max_score}")

    console.print("\n[bold]Description:[/bold]")
    console.print(task.description)

    if task.detailed_instructions:
        console.print("\n[bold]Instructions:[/bold]")
        console.print(task.detailed_instructions)

    console.print(f"\n[bold]Public Tests:[/bold] {len(task.public_tests)}")
    console.print(f"[bold]Hidden Tests:[/bold] {len(task.hidden_tests)}")
    console.print(f"[bold]Tags:[/bold] {', '.join(task.tags)}")


@app.command()
def leaderboard(
    results_file: Path = typer.Option(
        Path("results/evaluation_results.json"),
        "--file", "-f",
        help="Results file",
    ),
):
    """Display the evaluation leaderboard."""
    if not results_file.exists():
        console.print(f"[red]Results file not found: {results_file}[/red]")
        console.print("Run an evaluation first with: agentx evaluate")
        return

    with open(results_file) as f:
        data = json.load(f)

    leaderboard_data = data.get("leaderboard", {})
    entries = leaderboard_data.get("entries", [])

    if not entries:
        console.print("[yellow]No leaderboard entries found[/yellow]")
        return

    table = Table(title="Evaluation Leaderboard")
    table.add_column("Rank", style="bold")
    table.add_column("Agent", style="cyan")
    table.add_column("Avg Score", style="green")
    table.add_column("Best", style="yellow")
    table.add_column("Worst", style="red")
    table.add_column("Runs", style="white")
    table.add_column("Std Dev", style="magenta")

    for entry in entries:
        table.add_row(
            str(entry.get("rank", "-")),
            entry.get("agent", "Unknown"),
            f"{entry.get('average_score', 0):.2f}",
            f"{entry.get('best_score', 0):.2f}",
            f"{entry.get('worst_score', 0):.2f}",
            str(entry.get("run_count", 0)),
            f"{entry.get('std_dev', 0):.4f}",
        )

    console.print(table)


@app.command()
def init(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialize",
    ),
):
    """Initialize a new AgentX project structure."""
    console.print(f"Initializing AgentX project in: {directory}")

    # Create directories
    dirs = [
        directory / "benchmarks" / "tasks" / "code_generation",
        directory / "benchmarks" / "tasks" / "bug_fix",
        directory / "benchmarks" / "tasks" / "refactoring",
        directory / "benchmarks" / "tasks" / "test_writing",
        directory / "results",
        directory / "config",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  Created: {d}")

    # Create sample config
    config_path = directory / "config" / "evaluation.yaml"
    if not config_path.exists():
        config_content = """# AlphaEvolve AgentX Evaluation Configuration

green_agent_endpoint: "http://localhost:8000"
purple_agent_endpoint: "http://localhost:8001"

# Reproducibility settings
num_runs: 3
seed: 42
deterministic: true

# Execution settings
timeout_seconds: 300
max_concurrent_tasks: 1

# Output settings
output_directory: "results"
save_intermediate: true
verbose: false
"""
        config_path.write_text(config_content)
        console.print(f"  Created: {config_path}")

    console.print("\n[green]Project initialized successfully![/green]")
    console.print("\nNext steps:")
    console.print("  1. Add task definitions to benchmarks/tasks/")
    console.print("  2. Start the Green Agent: agentx serve-green")
    console.print("  3. Start the Purple Agent: agentx serve-purple")
    console.print("  4. Run evaluation: agentx evaluate")


if __name__ == "__main__":
    app()
