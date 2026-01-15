"""
Green Agent HTTP Server - A2A Protocol Endpoints.

Provides the HTTP API for the Green Agent evaluator including:
- Agent card endpoint
- Task listing and retrieval
- Evaluation endpoints
- Leaderboard API
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agentx.green_agent.evaluator import EvaluationRun, GreenAgent
from agentx.green_agent.tasks import TaskCategory, TaskDefinition, TaskDifficulty

logger = structlog.get_logger()

# Global Green Agent instance
green_agent: GreenAgent | None = None


class EvaluationRequest(BaseModel):
    """Request to evaluate a Purple Agent."""

    purple_agent_endpoint: str
    task_ids: list[str] | None = None
    num_runs: int = Field(default=1, ge=1, le=10)
    seed: int | None = None


class EvaluationResponse(BaseModel):
    """Response from an evaluation request."""

    run_ids: list[str]
    total_tasks: int
    summary: dict[str, Any]


class TaskListResponse(BaseModel):
    """Response containing list of tasks."""

    tasks: list[dict[str, Any]]
    total: int


class LeaderboardResponse(BaseModel):
    """Leaderboard data response."""

    entries: list[dict[str, Any]]
    metadata: dict[str, Any]


class ReproducibilityResponse(BaseModel):
    """Reproducibility verification response."""

    status: str
    runs_analyzed: int
    reproducibility_rate: float
    details: dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global green_agent

    # Startup
    tasks_dir = Path(__file__).parent.parent.parent.parent / "benchmarks" / "tasks"
    green_agent = GreenAgent(
        name="AlphaEvolve-SWE-Benchmark",
        description="Software Engineering Benchmark Evaluator",
        tasks_directory=tasks_dir if tasks_dir.exists() else None,
    )
    await green_agent.initialize()
    logger.info("Green Agent server started")

    yield

    # Shutdown
    if green_agent:
        await green_agent.shutdown()
    logger.info("Green Agent server stopped")


app = FastAPI(
    title="AlphaEvolve Green Agent",
    description="Evaluator Agent for Software Engineering Benchmarks",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "green"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return {"status": "ready", "tasks_loaded": len(green_agent.task_registry)}


# A2A Protocol endpoints
@app.get("/a2a/agent-card")
async def get_agent_card():
    """Get the Green Agent's card (A2A protocol)."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return green_agent.agent_card.model_dump()


# Task endpoints
@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    category: TaskCategory | None = None,
    difficulty: TaskDifficulty | None = None,
    tags: list[str] | None = Query(None),
):
    """List available evaluation tasks."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    tasks = green_agent.task_registry.list_tasks(
        category=category,
        difficulty=difficulty,
        tags=tags,
    )

    return TaskListResponse(
        tasks=[
            {
                "task_id": t.task_id,
                "name": t.name,
                "category": t.category.value,
                "difficulty": t.difficulty.value,
                "description": t.description,
                "max_score": t.max_score,
                "tags": t.tags,
            }
            for t in tasks
        ],
        total=len(tasks),
    )


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task definition."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    task = green_agent.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Return task without reference solution
    data = task.model_dump()
    data.pop("reference_solution", None)
    data.pop("hidden_tests", None)
    return data


# Evaluation endpoints
@app.post("/evaluate", response_model=EvaluationResponse)
async def run_evaluation(request: EvaluationRequest):
    """
    Run evaluation against a Purple Agent.

    This endpoint will:
    1. Send tasks to the Purple Agent
    2. Score the responses
    3. Return evaluation results
    """
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        runs = await green_agent.evaluate_agent(
            purple_agent_endpoint=request.purple_agent_endpoint,
            task_ids=request.task_ids,
            num_runs=request.num_runs,
            seed=request.seed,
        )

        # Generate summary
        leaderboard = green_agent.generate_leaderboard(runs)

        return EvaluationResponse(
            run_ids=[r.run_id for r in runs],
            total_tasks=sum(len(r.results) for r in runs),
            summary=leaderboard.get("entries", [{}])[0] if leaderboard.get("entries") else {},
        )

    except Exception as e:
        logger.error("Evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluation/{run_id}")
async def get_evaluation_run(run_id: str):
    """Get details of a specific evaluation run."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    for run in green_agent.evaluation_runs:
        if run.run_id == run_id:
            return run.to_dict()

    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@app.get("/evaluations")
async def list_evaluations():
    """List all evaluation runs."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return {
        "runs": [
            {
                "run_id": r.run_id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "task_count": len(r.results),
                "config": r.config,
            }
            for r in green_agent.evaluation_runs
        ],
        "total": len(green_agent.evaluation_runs),
    }


# Leaderboard endpoints
@app.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard():
    """Get the current leaderboard."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    leaderboard = green_agent.generate_leaderboard()
    return LeaderboardResponse(
        entries=leaderboard.get("entries", []),
        metadata=leaderboard.get("metadata", {}),
    )


# Reproducibility endpoints
@app.get("/reproducibility", response_model=ReproducibilityResponse)
async def verify_reproducibility():
    """Verify reproducibility across evaluation runs."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    result = green_agent.verify_reproducibility(green_agent.evaluation_runs)

    return ReproducibilityResponse(
        status=result.get("status", "unknown"),
        runs_analyzed=result.get("runs_analyzed", 0),
        reproducibility_rate=result.get("reproducibility_rate", 0.0),
        details=result,
    )


@app.post("/export")
async def export_results(output_path: str = "results/evaluation_results.json"):
    """Export evaluation results to a file."""
    if green_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        green_agent.export_results(Path(output_path))
        return {"status": "exported", "path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the Green Agent server."""
    uvicorn.run(
        "agentx.green_agent.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
