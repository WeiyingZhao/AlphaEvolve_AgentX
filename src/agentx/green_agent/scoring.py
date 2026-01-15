"""
Scoring engine for automated evaluation.

This module provides comprehensive scoring capabilities including:
- Test case execution and validation
- Code quality analysis
- Performance metrics
- Multi-criteria scoring
"""

from __future__ import annotations

import ast
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentx.green_agent.tasks import TaskDefinition, TestCase


class ScoreCategory(str, Enum):
    """Categories of scoring metrics."""

    CORRECTNESS = "correctness"
    TEST_PASS_RATE = "test_pass_rate"
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    STYLE = "style"


class TestResult(BaseModel):
    """Result of running a single test case."""

    test_id: str
    passed: bool
    execution_time_ms: float = 0.0
    actual_output: Any = None
    expected_output: Any = None
    error_message: str | None = None
    stdout: str = ""
    stderr: str = ""


class ScoringResult(BaseModel):
    """Complete scoring result for a task submission."""

    task_id: str
    total_score: float
    max_score: float
    normalized_score: float = Field(
        description="Score as percentage (0-100)"
    )

    # Detailed breakdown
    category_scores: dict[str, float] = Field(default_factory=dict)
    test_results: list[TestResult] = Field(default_factory=list)

    # Summary statistics
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    pass_rate: float = 0.0

    # Quality metrics
    code_quality_score: float = 0.0
    performance_score: float = 0.0

    # Feedback
    feedback: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    # Metadata
    execution_time_seconds: float = 0.0
    evaluation_timestamp: str = ""


@dataclass
class CodeAnalysisResult:
    """Result of static code analysis."""

    syntax_valid: bool = True
    syntax_errors: list[str] = field(default_factory=list)
    complexity_score: float = 0.0
    line_count: int = 0
    function_count: int = 0
    class_count: int = 0
    import_violations: list[str] = field(default_factory=list)
    style_issues: list[str] = field(default_factory=list)


class ScoringEngine:
    """Engine for scoring task submissions."""

    def __init__(
        self,
        task: TaskDefinition,
        sandbox_enabled: bool = True,
        timeout_seconds: int = 30,
    ):
        self.task = task
        self.sandbox_enabled = sandbox_enabled
        self.timeout = timeout_seconds

    def score_submission(
        self,
        submitted_files: dict[str, str],
        run_hidden_tests: bool = True,
    ) -> ScoringResult:
        """
        Score a complete submission.

        Args:
            submitted_files: Dict mapping filename to content
            run_hidden_tests: Whether to run hidden test cases

        Returns:
            Complete scoring result
        """
        start_time = time.time()
        results = []
        feedback = []
        suggestions = []
        category_scores: dict[str, float] = {}

        # 1. Static code analysis
        analysis = self._analyze_code(submitted_files)
        if not analysis.syntax_valid:
            feedback.extend([f"Syntax error: {e}" for e in analysis.syntax_errors])
            return ScoringResult(
                task_id=self.task.task_id,
                total_score=0.0,
                max_score=self.task.max_score,
                normalized_score=0.0,
                feedback=feedback,
                execution_time_seconds=time.time() - start_time,
            )

        # Check for forbidden imports
        if analysis.import_violations:
            feedback.extend(
                [f"Forbidden import used: {imp}" for imp in analysis.import_violations]
            )
            suggestions.append("Remove forbidden imports and use allowed alternatives")

        # 2. Run test cases
        tests_to_run = list(self.task.public_tests)
        if run_hidden_tests:
            tests_to_run.extend(self.task.hidden_tests)

        for test_case in tests_to_run:
            result = self._run_test(submitted_files, test_case)
            results.append(result)

        # 3. Calculate scores
        tests_passed = sum(1 for r in results if r.passed)
        tests_total = len(results)
        pass_rate = tests_passed / tests_total if tests_total > 0 else 0.0

        # Weighted test scoring
        weighted_score = 0.0
        total_weight = sum(t.weight for t in tests_to_run)
        for test, result in zip(tests_to_run, results):
            if result.passed:
                weighted_score += (test.weight / total_weight) if total_weight > 0 else 0

        # Test pass rate score (50% of total)
        test_score = weighted_score * (self.task.max_score * 0.5)
        category_scores[ScoreCategory.TEST_PASS_RATE.value] = test_score

        # Code quality score (30% of total)
        quality_score = self._calculate_quality_score(analysis) * (self.task.max_score * 0.3)
        category_scores[ScoreCategory.CODE_QUALITY.value] = quality_score

        # Correctness bonus for all tests passing (20% of total)
        correctness_score = (self.task.max_score * 0.2) if pass_rate == 1.0 else 0.0
        category_scores[ScoreCategory.CORRECTNESS.value] = correctness_score

        total_score = sum(category_scores.values())
        normalized = (total_score / self.task.max_score) * 100 if self.task.max_score > 0 else 0

        # Generate feedback
        if pass_rate < 1.0:
            failed_tests = [r for r in results if not r.passed]
            for ft in failed_tests[:3]:  # Show first 3 failures
                feedback.append(f"Test '{ft.test_id}' failed: {ft.error_message or 'No details'}")
            if len(failed_tests) > 3:
                feedback.append(f"... and {len(failed_tests) - 3} more test(s) failed")

        if analysis.style_issues:
            suggestions.extend(analysis.style_issues[:3])

        return ScoringResult(
            task_id=self.task.task_id,
            total_score=round(total_score, 2),
            max_score=self.task.max_score,
            normalized_score=round(normalized, 2),
            category_scores=category_scores,
            test_results=results,
            tests_passed=tests_passed,
            tests_failed=tests_total - tests_passed,
            tests_total=tests_total,
            pass_rate=round(pass_rate * 100, 2),
            code_quality_score=round(quality_score, 2),
            feedback=feedback,
            suggestions=suggestions,
            execution_time_seconds=round(time.time() - start_time, 3),
        )

    def _analyze_code(self, files: dict[str, str]) -> CodeAnalysisResult:
        """Perform static analysis on submitted code."""
        result = CodeAnalysisResult()

        for filename, content in files.items():
            if not filename.endswith(".py"):
                continue

            result.line_count += len(content.splitlines())

            # Syntax check
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                result.syntax_valid = False
                result.syntax_errors.append(f"{filename}:{e.lineno}: {e.msg}")
                continue

            # Count constructs
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    result.function_count += 1
                elif isinstance(node, ast.ClassDef):
                    result.class_count += 1
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.task.forbidden_imports:
                            result.import_violations.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module in self.task.forbidden_imports:
                        result.import_violations.append(node.module)

            # Basic style checks
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if len(line) > 120:
                    result.style_issues.append(
                        f"{filename}:{i}: Line exceeds 120 characters"
                    )
                if line.rstrip() != line:
                    result.style_issues.append(
                        f"{filename}:{i}: Trailing whitespace"
                    )

        return result

    def _run_test(
        self,
        files: dict[str, str],
        test_case: TestCase,
    ) -> TestResult:
        """Run a single test case against submitted code."""
        start_time = time.time()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)

                # Write submitted files
                for filename, content in files.items():
                    filepath = tmppath / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(content)

                # Create test runner script
                test_script = self._generate_test_script(test_case)
                test_file = tmppath / "_test_runner.py"
                test_file.write_text(test_script)

                # Execute test
                result = subprocess.run(
                    ["python", str(test_file)],
                    cwd=tmppath,
                    capture_output=True,
                    text=True,
                    timeout=min(test_case.timeout_seconds, self.timeout),
                )

                execution_time = (time.time() - start_time) * 1000

                if result.returncode == 0:
                    return TestResult(
                        test_id=test_case.test_id,
                        passed=True,
                        execution_time_ms=execution_time,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        expected_output=test_case.expected_output,
                    )
                else:
                    return TestResult(
                        test_id=test_case.test_id,
                        passed=False,
                        execution_time_ms=execution_time,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        expected_output=test_case.expected_output,
                        error_message=result.stderr or "Test failed",
                    )

        except subprocess.TimeoutExpired:
            return TestResult(
                test_id=test_case.test_id,
                passed=False,
                error_message=f"Test timed out after {test_case.timeout_seconds}s",
            )
        except Exception as e:
            return TestResult(
                test_id=test_case.test_id,
                passed=False,
                error_message=str(e),
            )

    def _generate_test_script(self, test_case: TestCase) -> str:
        """Generate a Python script to run a test case."""
        input_data = test_case.input_data
        expected = test_case.expected_output

        script = f'''
import sys
import json

# Test: {test_case.name}
try:
    input_data = {repr(input_data)}
    expected_output = {repr(expected)}

    # Import the solution module
    from solution import *

    # Execute the test
    if "function" in input_data:
        func_name = input_data["function"]
        args = input_data.get("args", [])
        kwargs = input_data.get("kwargs", {{}})
        result = globals()[func_name](*args, **kwargs)
    elif "code" in input_data:
        exec(input_data["code"])
        result = locals().get("result", None)
    else:
        result = None

    # Validate result
    if expected_output is not None:
        if result == expected_output:
            print("PASS")
            sys.exit(0)
        else:
            print(f"FAIL: Expected {{expected_output}}, got {{result}}")
            sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)

except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{e}}")
    sys.exit(1)
'''
        return script

    def _calculate_quality_score(self, analysis: CodeAnalysisResult) -> float:
        """Calculate code quality score (0-1)."""
        score = 1.0

        # Penalize style issues
        style_penalty = min(len(analysis.style_issues) * 0.05, 0.3)
        score -= style_penalty

        # Penalize forbidden imports
        import_penalty = len(analysis.import_violations) * 0.2
        score -= import_penalty

        # Bonus for reasonable code size
        if 10 <= analysis.line_count <= 500:
            score += 0.1

        return max(0.0, min(1.0, score))


class BatchScorer:
    """Score multiple submissions in batch."""

    def __init__(self, tasks: list[TaskDefinition]):
        self.tasks = {t.task_id: t for t in tasks}

    def score_all(
        self,
        submissions: dict[str, dict[str, str]],  # task_id -> files
    ) -> dict[str, ScoringResult]:
        """Score all submissions."""
        results = {}
        for task_id, files in submissions.items():
            if task_id in self.tasks:
                engine = ScoringEngine(self.tasks[task_id])
                results[task_id] = engine.score_submission(files)
        return results

    def aggregate_scores(
        self,
        results: dict[str, ScoringResult],
    ) -> dict[str, Any]:
        """Aggregate scores across all tasks."""
        if not results:
            return {"total": 0, "average": 0, "count": 0}

        total = sum(r.total_score for r in results.values())
        max_total = sum(r.max_score for r in results.values())
        count = len(results)

        return {
            "total_score": total,
            "max_possible": max_total,
            "average_normalized": total / max_total * 100 if max_total > 0 else 0,
            "task_count": count,
            "tasks_passed": sum(1 for r in results.values() if r.pass_rate == 100),
            "overall_pass_rate": sum(r.pass_rate for r in results.values()) / count,
        }
