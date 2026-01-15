"""
A2A (Agent-to-Agent) Protocol Implementation.

This module implements the A2A protocol for communication between Green (evaluator)
and Purple (evaluated) agents. The protocol supports task submission, status updates,
and result collection.

Protocol Specification:
- JSON-based message format
- HTTP/REST transport layer
- Async-first design
- Support for streaming responses
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of A2A protocol messages."""

    # Task lifecycle
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_STATUS = "task_status"
    TASK_CANCEL = "task_cancel"

    # Agent discovery
    AGENT_CARD = "agent_card"
    AGENT_HEARTBEAT = "agent_heartbeat"

    # Evaluation
    EVALUATION_START = "evaluation_start"
    EVALUATION_RESULT = "evaluation_result"
    EVALUATION_END = "evaluation_end"

    # Errors
    ERROR = "error"


class TaskStatus(str, Enum):
    """Status of a task in the A2A protocol."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AgentCard(BaseModel):
    """Agent Card describing an agent's capabilities (A2A standard)."""

    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: list[str] = Field(default_factory=list)
    supported_tasks: list[str] = Field(default_factory=list)
    endpoint: str
    protocol_version: str = "1.0"
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "green-agent-001",
                "name": "SWE-Bench Green Agent",
                "description": "Evaluator agent for software engineering tasks",
                "version": "0.1.0",
                "capabilities": ["code_evaluation", "test_execution", "scoring"],
                "supported_tasks": ["code_generation", "bug_fix", "refactoring"],
                "endpoint": "http://localhost:8000",
                "protocol_version": "1.0",
            }
        }


class A2AMessage(BaseModel):
    """Base message format for A2A protocol."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    sender_id: str
    receiver_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None  # For request-response correlation

    def to_json(self) -> str:
        """Serialize message to JSON."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> A2AMessage:
        """Deserialize message from JSON."""
        return cls.model_validate_json(data)


class TaskRequest(BaseModel):
    """Task request from Green Agent to Purple Agent."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    description: str
    context: dict[str, Any] = Field(default_factory=dict)
    files: dict[str, str] = Field(default_factory=dict)  # filename -> content
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 300
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Evaluation criteria
    evaluation_criteria: list[str] = Field(default_factory=list)
    max_score: float = 100.0


class TaskResponse(BaseModel):
    """Task response from Purple Agent to Green Agent."""

    task_id: str
    status: TaskStatus
    result: dict[str, Any] = Field(default_factory=dict)
    output_files: dict[str, str] = Field(default_factory=dict)  # filename -> content
    logs: list[str] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Evaluation result from Green Agent."""

    task_id: str
    evaluation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    score: float
    max_score: float
    passed_criteria: list[str] = Field(default_factory=list)
    failed_criteria: list[str] = Field(default_factory=list)
    detailed_scores: dict[str, float] = Field(default_factory=dict)
    feedback: str = ""
    test_results: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class A2AProtocol:
    """A2A Protocol handler for agent communication."""

    def __init__(
        self,
        agent_card: AgentCard,
        timeout: float = 30.0,
    ):
        self.agent_card = agent_card
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> A2AProtocol:
        """Initialize async HTTP client."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close async HTTP client."""
        if self._client:
            await self._client.aclose()

    async def send_message(
        self,
        endpoint: str,
        message: A2AMessage,
    ) -> A2AMessage | None:
        """Send an A2A message to another agent."""
        if not self._client:
            raise RuntimeError("Protocol not initialized. Use 'async with' context.")

        try:
            response = await self._client.post(
                f"{endpoint}/a2a/message",
                json=message.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return A2AMessage.model_validate(response.json())
        except httpx.HTTPError as e:
            return A2AMessage(
                message_type=MessageType.ERROR,
                sender_id=endpoint,
                payload={"error": str(e)},
            )

    async def send_task_request(
        self,
        endpoint: str,
        task: TaskRequest,
    ) -> TaskResponse | None:
        """Send a task request to a Purple Agent."""
        if not self._client:
            raise RuntimeError("Protocol not initialized. Use 'async with' context.")

        message = A2AMessage(
            message_type=MessageType.TASK_REQUEST,
            sender_id=self.agent_card.agent_id,
            payload=task.model_dump(mode="json"),
        )

        try:
            response = await self._client.post(
                f"{endpoint}/a2a/task",
                json=message.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
                timeout=task.timeout_seconds + 10,  # Extra buffer
            )
            response.raise_for_status()
            data = response.json()
            return TaskResponse.model_validate(data.get("payload", data))
        except httpx.HTTPError as e:
            return TaskResponse(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error_message=str(e),
            )

    async def get_agent_card(self, endpoint: str) -> AgentCard | None:
        """Retrieve an agent's card (capabilities and info)."""
        if not self._client:
            raise RuntimeError("Protocol not initialized. Use 'async with' context.")

        try:
            response = await self._client.get(f"{endpoint}/a2a/agent-card")
            response.raise_for_status()
            return AgentCard.model_validate(response.json())
        except httpx.HTTPError:
            return None

    async def check_health(self, endpoint: str) -> bool:
        """Check if an agent endpoint is healthy."""
        if not self._client:
            raise RuntimeError("Protocol not initialized. Use 'async with' context.")

        try:
            response = await self._client.get(f"{endpoint}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def create_task_request(
        self,
        task_type: str,
        description: str,
        files: dict[str, str] | None = None,
        test_cases: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> TaskRequest:
        """Helper to create a TaskRequest."""
        return TaskRequest(
            task_type=task_type,
            description=description,
            files=files or {},
            test_cases=test_cases or [],
            **kwargs,
        )
