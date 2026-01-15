"""
Purple Agent HTTP Server - A2A Protocol Endpoints.

Provides the HTTP API for the Purple Agent including:
- Agent card endpoint
- Task processing endpoint
- Status and statistics endpoints
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agentx.a2a.protocol import A2AMessage, MessageType, TaskRequest, TaskResponse
from agentx.purple_agent.agent import PurpleAgent

logger = structlog.get_logger()

# Global Purple Agent instance
purple_agent: PurpleAgent | None = None


class TaskSubmission(BaseModel):
    """Task submission wrapper."""

    message_type: str = MessageType.TASK_REQUEST.value
    sender_id: str = ""
    payload: dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global purple_agent

    # Startup
    purple_agent = PurpleAgent(
        name="AlphaEvolve-Baseline-Agent",
        description="Baseline Purple Agent for benchmark evaluation",
    )
    logger.info("Purple Agent server started", agent_id=purple_agent.agent_card.agent_id)

    yield

    # Shutdown
    logger.info("Purple Agent server stopped")


app = FastAPI(
    title="AlphaEvolve Purple Agent",
    description="Baseline Agent for Software Engineering Benchmarks",
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
    return {"status": "healthy", "agent": "purple"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    if purple_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return {"status": "ready"}


# A2A Protocol endpoints
@app.get("/a2a/agent-card")
async def get_agent_card():
    """Get the Purple Agent's card (A2A protocol)."""
    if purple_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return purple_agent.agent_card.model_dump()


@app.post("/a2a/message")
async def handle_message(message: A2AMessage):
    """Handle generic A2A protocol messages."""
    if purple_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if message.message_type == MessageType.TASK_REQUEST:
        task = TaskRequest.model_validate(message.payload)
        response = await purple_agent.process_task(task)
        return A2AMessage(
            message_type=MessageType.TASK_RESPONSE,
            sender_id=purple_agent.agent_card.agent_id,
            receiver_id=message.sender_id,
            correlation_id=message.message_id,
            payload=response.model_dump(),
        )
    elif message.message_type == MessageType.AGENT_HEARTBEAT:
        return A2AMessage(
            message_type=MessageType.AGENT_HEARTBEAT,
            sender_id=purple_agent.agent_card.agent_id,
            receiver_id=message.sender_id,
            payload={"status": "alive"},
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported message type: {message.message_type}",
        )


@app.post("/a2a/task")
async def process_task(submission: TaskSubmission):
    """
    Process a task request (A2A protocol).

    This is the main endpoint for receiving evaluation tasks from
    the Green Agent.
    """
    if purple_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        task = TaskRequest.model_validate(submission.payload)
        response = await purple_agent.process_task(task)

        return A2AMessage(
            message_type=MessageType.TASK_RESPONSE,
            sender_id=purple_agent.agent_card.agent_id,
            payload=response.model_dump(),
        )

    except Exception as e:
        logger.error("Task processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Statistics endpoints
@app.get("/statistics")
async def get_statistics():
    """Get agent statistics."""
    if purple_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return purple_agent.get_statistics()


@app.get("/history")
async def get_task_history():
    """Get task processing history."""
    if purple_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return {
        "history": purple_agent.get_task_history(),
        "total": len(purple_agent.get_task_history()),
    }


def main():
    """Run the Purple Agent server."""
    uvicorn.run(
        "agentx.purple_agent.server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
