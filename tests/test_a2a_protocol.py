"""Tests for A2A protocol implementation."""

import pytest
from datetime import datetime

from agentx.a2a.protocol import (
    A2AMessage,
    AgentCard,
    MessageType,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)


class TestAgentCard:
    """Tests for AgentCard."""

    def test_create_agent_card(self):
        """Test creating an agent card."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            endpoint="http://localhost:8000",
        )

        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert card.endpoint == "http://localhost:8000"
        assert card.agent_id is not None
        assert card.protocol_version == "1.0"

    def test_agent_card_capabilities(self):
        """Test agent card with capabilities."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            endpoint="http://localhost:8000",
            capabilities=["code_generation", "bug_fixing"],
            supported_tasks=["code_gen", "bug_fix"],
        )

        assert "code_generation" in card.capabilities
        assert "bug_fix" in card.supported_tasks


class TestA2AMessage:
    """Tests for A2AMessage."""

    def test_create_message(self):
        """Test creating a basic A2A message."""
        message = A2AMessage(
            message_type=MessageType.TASK_REQUEST,
            sender_id="agent-001",
            receiver_id="agent-002",
            payload={"task": "test"},
        )

        assert message.message_type == MessageType.TASK_REQUEST
        assert message.sender_id == "agent-001"
        assert message.receiver_id == "agent-002"
        assert message.payload == {"task": "test"}
        assert message.message_id is not None
        assert message.timestamp is not None

    def test_message_serialization(self):
        """Test message JSON serialization."""
        message = A2AMessage(
            message_type=MessageType.TASK_RESPONSE,
            sender_id="agent-001",
            payload={"result": "success"},
        )

        json_str = message.to_json()
        assert "task_response" in json_str
        assert "agent-001" in json_str

        # Deserialize
        restored = A2AMessage.from_json(json_str)
        assert restored.message_type == MessageType.TASK_RESPONSE
        assert restored.sender_id == "agent-001"


class TestTaskRequest:
    """Tests for TaskRequest."""

    def test_create_task_request(self):
        """Test creating a task request."""
        request = TaskRequest(
            task_type="code_generation",
            description="Implement a function",
            files={"main.py": "# starter code"},
            timeout_seconds=120,
        )

        assert request.task_type == "code_generation"
        assert request.description == "Implement a function"
        assert "main.py" in request.files
        assert request.timeout_seconds == 120
        assert request.task_id is not None

    def test_task_request_with_tests(self):
        """Test task request with test cases."""
        request = TaskRequest(
            task_type="bug_fix",
            description="Fix the bug",
            test_cases=[
                {"input": [1, 2], "expected": 3},
                {"input": [0, 0], "expected": 0},
            ],
        )

        assert len(request.test_cases) == 2


class TestTaskResponse:
    """Tests for TaskResponse."""

    def test_create_success_response(self):
        """Test creating a successful task response."""
        response = TaskResponse(
            task_id="task-001",
            status=TaskStatus.COMPLETED,
            output_files={"solution.py": "def solve(): pass"},
            execution_time_seconds=5.5,
        )

        assert response.task_id == "task-001"
        assert response.status == TaskStatus.COMPLETED
        assert "solution.py" in response.output_files
        assert response.execution_time_seconds == 5.5

    def test_create_failed_response(self):
        """Test creating a failed task response."""
        response = TaskResponse(
            task_id="task-002",
            status=TaskStatus.FAILED,
            error_message="Execution timeout",
        )

        assert response.status == TaskStatus.FAILED
        assert response.error_message == "Execution timeout"


class TestMessageTypes:
    """Tests for message type enum."""

    def test_task_lifecycle_types(self):
        """Test task lifecycle message types."""
        assert MessageType.TASK_REQUEST.value == "task_request"
        assert MessageType.TASK_RESPONSE.value == "task_response"
        assert MessageType.TASK_STATUS.value == "task_status"
        assert MessageType.TASK_CANCEL.value == "task_cancel"

    def test_evaluation_types(self):
        """Test evaluation message types."""
        assert MessageType.EVALUATION_START.value == "evaluation_start"
        assert MessageType.EVALUATION_RESULT.value == "evaluation_result"
        assert MessageType.EVALUATION_END.value == "evaluation_end"


class TestTaskStatus:
    """Tests for task status enum."""

    def test_status_values(self):
        """Test task status values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.TIMEOUT.value == "timeout"
