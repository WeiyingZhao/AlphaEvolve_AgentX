"""Tests for the scoring engine."""

import pytest

from agentx.green_agent.scoring import (
    CodeAnalysisResult,
    ScoringEngine,
    ScoringResult,
    TestResult,
)
from agentx.green_agent.tasks import (
    TaskCategory,
    TaskDefinition,
    TaskDifficulty,
    TestCase,
)


class TestScoringResult:
    """Tests for ScoringResult."""

    def test_create_scoring_result(self):
        """Test creating a scoring result."""
        result = ScoringResult(
            task_id="test_task",
            total_score=85.0,
            max_score=100.0,
            normalized_score=85.0,
            tests_passed=8,
            tests_failed=2,
            tests_total=10,
            pass_rate=80.0,
        )

        assert result.task_id == "test_task"
        assert result.total_score == 85.0
        assert result.normalized_score == 85.0
        assert result.pass_rate == 80.0


class TestTestResult:
    """Tests for TestResult."""

    def test_passed_test_result(self):
        """Test creating a passed test result."""
        result = TestResult(
            test_id="test_001",
            passed=True,
            execution_time_ms=150.5,
            expected_output=42,
            actual_output=42,
        )

        assert result.passed
        assert result.execution_time_ms == 150.5

    def test_failed_test_result(self):
        """Test creating a failed test result."""
        result = TestResult(
            test_id="test_002",
            passed=False,
            expected_output=42,
            actual_output=0,
            error_message="Assertion failed",
        )

        assert not result.passed
        assert result.error_message == "Assertion failed"


class TestCodeAnalysisResult:
    """Tests for CodeAnalysisResult."""

    def test_valid_code_analysis(self):
        """Test analysis result for valid code."""
        result = CodeAnalysisResult(
            syntax_valid=True,
            line_count=50,
            function_count=5,
            class_count=2,
        )

        assert result.syntax_valid
        assert result.line_count == 50
        assert result.function_count == 5

    def test_invalid_code_analysis(self):
        """Test analysis result for invalid code."""
        result = CodeAnalysisResult(
            syntax_valid=False,
            syntax_errors=["Line 10: unexpected indent"],
        )

        assert not result.syntax_valid
        assert len(result.syntax_errors) == 1


class TestScoringEngine:
    """Tests for ScoringEngine."""

    @pytest.fixture
    def simple_task(self):
        """Create a simple task for testing."""
        return TaskDefinition(
            task_id="simple_task",
            name="Simple Task",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Implement a simple function",
            public_tests=[
                TestCase(
                    test_id="test_1",
                    name="Basic test",
                    input_data={
                        "function": "add",
                        "args": [1, 2],
                    },
                    expected_output=3,
                    weight=1.0,
                ),
            ],
            max_score=100.0,
        )

    def test_score_valid_submission(self, simple_task):
        """Test scoring a valid submission."""
        engine = ScoringEngine(simple_task)

        submitted_files = {
            "solution.py": """
def add(a, b):
    return a + b
"""
        }

        result = engine.score_submission(submitted_files, run_hidden_tests=False)

        assert result.task_id == "simple_task"
        assert result.max_score == 100.0
        assert result.tests_total >= 1

    def test_score_syntax_error(self, simple_task):
        """Test scoring submission with syntax error."""
        engine = ScoringEngine(simple_task)

        submitted_files = {
            "solution.py": """
def add(a, b)  # Missing colon
    return a + b
"""
        }

        result = engine.score_submission(submitted_files, run_hidden_tests=False)

        assert result.total_score == 0.0
        assert len(result.feedback) > 0

    def test_analyze_code_valid(self, simple_task):
        """Test code analysis on valid code."""
        engine = ScoringEngine(simple_task)

        files = {
            "solution.py": """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
"""
        }

        analysis = engine._analyze_code(files)

        assert analysis.syntax_valid
        assert analysis.function_count == 2
        assert analysis.line_count > 0

    def test_analyze_code_with_imports(self, simple_task):
        """Test code analysis with forbidden imports."""
        task = TaskDefinition(
            task_id="import_task",
            name="Import Task",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Task with forbidden imports",
            forbidden_imports=["os", "subprocess"],
            max_score=100.0,
        )

        engine = ScoringEngine(task)

        files = {
            "solution.py": """
import os
import json

def get_cwd():
    return os.getcwd()
"""
        }

        analysis = engine._analyze_code(files)

        assert "os" in analysis.import_violations

    def test_quality_score_calculation(self, simple_task):
        """Test code quality score calculation."""
        engine = ScoringEngine(simple_task)

        # Good quality code
        good_analysis = CodeAnalysisResult(
            syntax_valid=True,
            line_count=50,
            style_issues=[],
        )

        score = engine._calculate_quality_score(good_analysis)
        assert score > 0.9

        # Code with style issues
        bad_analysis = CodeAnalysisResult(
            syntax_valid=True,
            line_count=50,
            style_issues=["issue1", "issue2", "issue3", "issue4"],
        )

        score = engine._calculate_quality_score(bad_analysis)
        assert score < 0.9


class TestScoringIntegration:
    """Integration tests for scoring."""

    def test_full_scoring_workflow(self):
        """Test complete scoring workflow."""
        task = TaskDefinition(
            task_id="integration_task",
            name="Integration Task",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.MEDIUM,
            description="Implement fibonacci",
            public_tests=[
                TestCase(
                    test_id="fib_0",
                    name="Fibonacci 0",
                    input_data={"function": "fibonacci", "args": [0]},
                    expected_output=0,
                    weight=1.0,
                ),
                TestCase(
                    test_id="fib_1",
                    name="Fibonacci 1",
                    input_data={"function": "fibonacci", "args": [1]},
                    expected_output=1,
                    weight=1.0,
                ),
            ],
            hidden_tests=[
                TestCase(
                    test_id="fib_10",
                    name="Fibonacci 10",
                    input_data={"function": "fibonacci", "args": [10]},
                    expected_output=55,
                    weight=2.0,
                    is_hidden=True,
                ),
            ],
            max_score=100.0,
        )

        engine = ScoringEngine(task)

        # Correct solution
        correct_solution = {
            "solution.py": """
def fibonacci(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
        }

        result = engine.score_submission(correct_solution, run_hidden_tests=True)

        assert result.total_score > 0
        assert result.tests_total == 3
        assert result.max_score == 100.0
