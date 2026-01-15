"""
Task definitions for Green Agent evaluator.

This module provides the framework for defining evaluation tasks including:
- Task specifications
- Input/output schemas
- Evaluation criteria
- Test case definitions
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import yaml
from pydantic import BaseModel, Field


class TaskCategory(str, Enum):
    """Categories of software engineering tasks."""

    CODE_GENERATION = "code_generation"
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    TEST_WRITING = "test_writing"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    OPTIMIZATION = "optimization"
    SECURITY_FIX = "security_fix"
    API_DESIGN = "api_design"
    DEBUGGING = "debugging"


class TaskDifficulty(str, Enum):
    """Difficulty levels for tasks."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TestCase(BaseModel):
    """Test case for evaluating task solutions."""

    test_id: str
    name: str
    description: str = ""
    input_data: dict[str, Any] = Field(default_factory=dict)
    expected_output: Any = None
    timeout_seconds: float = 30.0
    weight: float = 1.0
    is_hidden: bool = False  # Hidden tests not shown to agent
    tags: list[str] = Field(default_factory=list)


class TaskDefinition(BaseModel):
    """Definition of an evaluation task."""

    task_id: str
    name: str
    category: TaskCategory
    difficulty: TaskDifficulty
    description: str
    detailed_instructions: str = ""

    # Context and files
    context_files: dict[str, str] = Field(default_factory=dict)
    starter_code: dict[str, str] = Field(default_factory=dict)
    reference_solution: dict[str, str] = Field(default_factory=dict)

    # Test cases
    public_tests: list[TestCase] = Field(default_factory=list)
    hidden_tests: list[TestCase] = Field(default_factory=list)

    # Evaluation criteria
    evaluation_criteria: list[str] = Field(default_factory=list)
    scoring_rubric: dict[str, float] = Field(default_factory=dict)
    max_score: float = 100.0

    # Constraints
    time_limit_seconds: int = 300
    memory_limit_mb: int = 512
    allowed_languages: list[str] = Field(default_factory=lambda: ["python"])
    forbidden_imports: list[str] = Field(default_factory=list)

    # Metadata
    tags: list[str] = Field(default_factory=list)
    author: str = ""
    version: str = "1.0.0"
    source: str = ""

    def get_fingerprint(self) -> str:
        """Generate a unique fingerprint for this task definition."""
        content = json.dumps(
            {
                "task_id": self.task_id,
                "description": self.description,
                "context_files": self.context_files,
                "public_tests": [t.model_dump() for t in self.public_tests],
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_task_request_format(self) -> dict[str, Any]:
        """Convert to A2A TaskRequest format."""
        return {
            "task_type": self.category.value,
            "description": self.description,
            "context": {
                "detailed_instructions": self.detailed_instructions,
                "difficulty": self.difficulty.value,
                "evaluation_criteria": self.evaluation_criteria,
            },
            "files": {**self.context_files, **self.starter_code},
            "test_cases": [t.model_dump() for t in self.public_tests],
            "constraints": {
                "time_limit_seconds": self.time_limit_seconds,
                "memory_limit_mb": self.memory_limit_mb,
                "allowed_languages": self.allowed_languages,
                "forbidden_imports": self.forbidden_imports,
            },
            "evaluation_criteria": self.evaluation_criteria,
            "max_score": self.max_score,
        }


class Task:
    """Runtime representation of a task with execution context."""

    def __init__(self, definition: TaskDefinition):
        self.definition = definition
        self._run_count = 0

    @property
    def task_id(self) -> str:
        return self.definition.task_id

    @property
    def all_tests(self) -> list[TestCase]:
        """Get all test cases (public + hidden)."""
        return self.definition.public_tests + self.definition.hidden_tests

    def increment_run(self) -> int:
        """Increment and return run count."""
        self._run_count += 1
        return self._run_count


class TaskRegistry:
    """Registry for managing task definitions."""

    def __init__(self):
        self._tasks: dict[str, TaskDefinition] = {}
        self._loaders: dict[str, Callable[[Path], TaskDefinition]] = {
            ".yaml": self._load_yaml,
            ".yml": self._load_yaml,
            ".json": self._load_json,
        }

    def register(self, task: TaskDefinition) -> None:
        """Register a task definition."""
        self._tasks[task.task_id] = task

    def get(self, task_id: str) -> TaskDefinition | None:
        """Get a task definition by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        category: TaskCategory | None = None,
        difficulty: TaskDifficulty | None = None,
        tags: list[str] | None = None,
    ) -> list[TaskDefinition]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())

        if category:
            tasks = [t for t in tasks if t.category == category]
        if difficulty:
            tasks = [t for t in tasks if t.difficulty == difficulty]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]

        return tasks

    def load_from_file(self, path: Path) -> TaskDefinition:
        """Load a task definition from a file."""
        suffix = path.suffix.lower()
        if suffix not in self._loaders:
            raise ValueError(f"Unsupported file format: {suffix}")

        task = self._loaders[suffix](path)
        self.register(task)
        return task

    def load_from_directory(self, directory: Path) -> list[TaskDefinition]:
        """Load all task definitions from a directory."""
        tasks = []
        for path in directory.rglob("*"):
            if path.suffix.lower() in self._loaders:
                try:
                    task = self.load_from_file(path)
                    tasks.append(task)
                except Exception as e:
                    print(f"Warning: Failed to load {path}: {e}")
        return tasks

    def _load_yaml(self, path: Path) -> TaskDefinition:
        """Load task definition from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return TaskDefinition.model_validate(data)

    def _load_json(self, path: Path) -> TaskDefinition:
        """Load task definition from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return TaskDefinition.model_validate(data)

    def __len__(self) -> int:
        return len(self._tasks)

    def __iter__(self):
        return iter(self._tasks.values())
