# AlphaEvolve AgentX

**Green Agent Evaluator for Software Engineering Tasks**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![A2A Protocol](https://img.shields.io/badge/Protocol-A2A-green.svg)](https://github.com/google/A2A)

## Abstract

**AlphaEvolve AgentX** is a comprehensive benchmark framework for evaluating AI agents on software engineering tasks. This Green Agent (evaluator) provides:

- **Multi-category Task Evaluation**: Code generation, bug fixing, refactoring, test writing, and more
- **Automated Scoring Engine**: Objective assessment through test execution, code quality analysis, and performance metrics
- **A2A Protocol Compliance**: Full support for Agent-to-Agent communication standard for interoperability
- **Reproducibility Guarantees**: Deterministic evaluation with seed control and multi-run consistency verification
- **Dockerized Deployment**: End-to-end containerized execution for consistent evaluation environments

The benchmark evaluates Purple Agents (agents being tested) across diverse software engineering challenges, measuring their ability to understand requirements, generate correct code, identify and fix bugs, and produce maintainable solutions. Results are aggregated into a leaderboard with detailed per-task breakdowns and reproducibility metrics.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Task Categories](#task-categories)
- [A2A Protocol](#a2a-protocol)
- [Running Evaluations](#running-evaluations)
- [Reproducibility](#reproducibility)
- [Docker Deployment](#docker-deployment)
- [Creating Custom Tasks](#creating-custom-tasks)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Green Agent (Evaluator)
- Define evaluation environments with isolated task execution
- Automated test execution and scoring
- Multi-criteria evaluation (correctness, efficiency, code quality)
- Hidden test cases for robust evaluation
- Real-time leaderboard generation

### Purple Agent (Baseline)
- A2A-compliant baseline implementation
- Pluggable task-solving strategies
- Support for multiple task categories
- LLM integration capability (optional)

### Evaluation Infrastructure
- Configurable multi-run evaluation for reproducibility
- Statistical analysis of score variance
- Detailed per-task result breakdowns
- Export capabilities (JSON, leaderboard format)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/WeiyingZhao/AlphaEvolve_AgentX.git
cd AlphaEvolve_AgentX

# Install dependencies
pip install -e .
```

### Running with Docker (Recommended)

```bash
# Start both Green and Purple agents
docker-compose up -d

# Run evaluation (interactive mode)
docker-compose --profile evaluation up evaluation-runner

# View results
cat results/evaluation_results.json
```

### Running Locally

```bash
# Terminal 1: Start Green Agent
agentx serve-green

# Terminal 2: Start Purple Agent
agentx serve-purple

# Terminal 3: Run evaluation
agentx evaluate --purple http://localhost:8001 --runs 3
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Evaluation Harness                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐         A2A Protocol         ┌───────────────────┐
│  │   Green Agent   │◄────────────────────────────►│   Purple Agent    │
│  │   (Evaluator)   │                              │   (Evaluated)     │
│  │                 │                              │                   │
│  │  ┌───────────┐  │    Task Request/Response    │  ┌─────────────┐  │
│  │  │   Tasks   │  │◄────────────────────────────►│  │  Strategy   │  │
│  │  │  Registry │  │                              │  │   Engine    │  │
│  │  └───────────┘  │                              │  └─────────────┘  │
│  │                 │                              │                   │
│  │  ┌───────────┐  │      Evaluation Results     │                   │
│  │  │  Scoring  │  │◄────────────────────────────│                   │
│  │  │  Engine   │  │                              │                   │
│  │  └───────────┘  │                              │                   │
│  └─────────────────┘                              └───────────────────┘
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    Results & Leaderboard                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Task Categories

The benchmark includes tasks across multiple software engineering categories:

| Category | Description | Difficulty Range |
|----------|-------------|------------------|
| **Code Generation** | Implement functions/classes from specifications | Easy - Expert |
| **Bug Fix** | Identify and correct bugs in existing code | Easy - Hard |
| **Refactoring** | Improve code structure without changing behavior | Medium - Expert |
| **Test Writing** | Generate comprehensive test suites | Medium - Hard |
| **Code Review** | Identify issues and suggest improvements | Medium - Expert |
| **Documentation** | Generate docstrings and documentation | Easy - Medium |
| **Optimization** | Improve performance of existing code | Hard - Expert |
| **Security Fix** | Identify and remediate security vulnerabilities | Hard - Expert |

### Example Tasks

- `code_gen_fibonacci`: Implement Fibonacci sequence generator (Easy)
- `code_gen_two_sum`: Classic two-sum array problem (Medium)
- `bug_fix_binary_search`: Fix bugs in binary search implementation (Medium)
- `refactor_extract_method`: Extract methods from long functions (Medium)

---

## A2A Protocol

AlphaEvolve AgentX implements the [A2A (Agent-to-Agent) Protocol](https://github.com/google/A2A) for standardized communication between agents.

### Key Endpoints

**Green Agent (Port 8000)**
```
GET  /a2a/agent-card     # Agent capabilities and metadata
GET  /tasks              # List available evaluation tasks
GET  /tasks/{task_id}    # Get specific task details
POST /evaluate           # Trigger evaluation of a Purple Agent
GET  /leaderboard        # Get current leaderboard
GET  /reproducibility    # Verify reproducibility metrics
```

**Purple Agent (Port 8001)**
```
GET  /a2a/agent-card     # Agent capabilities and metadata
POST /a2a/task           # Receive and process task requests
GET  /statistics         # Get processing statistics
```

### Message Format

```json
{
  "message_id": "uuid",
  "message_type": "task_request",
  "sender_id": "green-agent-001",
  "receiver_id": "purple-agent-001",
  "timestamp": "2024-01-15T10:30:00Z",
  "payload": {
    "task_id": "code_gen_fibonacci",
    "task_type": "code_generation",
    "description": "Implement fibonacci function",
    "files": {...},
    "test_cases": [...]
  }
}
```

---

## Running Evaluations

### Basic Evaluation

```bash
# Run with default settings (3 runs, all tasks)
agentx evaluate

# Specify Purple Agent endpoint
agentx evaluate --purple http://my-agent:8001

# Run with specific seed for reproducibility
agentx evaluate --seed 42 --runs 5

# Evaluate specific tasks
agentx evaluate --tasks code_gen_fibonacci,bug_fix_binary_search
```

### Programmatic Evaluation

```python
import asyncio
from agentx.evaluation import EvaluationConfig, EvaluationHarness

async def run_evaluation():
    config = EvaluationConfig(
        purple_agent_endpoint="http://localhost:8001",
        num_runs=3,
        seed=42,
    )

    harness = EvaluationHarness(config)
    await harness.initialize()

    report = await harness.run_evaluation()

    print(f"Score: {report.average_score:.2f}")
    print(f"Reproducible: {report.reproducibility_verified}")

    await harness.shutdown()

asyncio.run(run_evaluation())
```

---

## Reproducibility

Reproducibility is a core requirement for meaningful benchmarking. AlphaEvolve AgentX ensures reproducibility through:

### Deterministic Evaluation
- Fixed random seeds across all evaluation runs
- Consistent task ordering
- Isolated execution environments

### Multi-Run Verification
```bash
# Run multiple evaluation iterations
agentx evaluate --runs 5 --seed 42

# Check reproducibility metrics
curl http://localhost:8000/reproducibility
```

### Reproducibility Report
```json
{
  "status": "verified",
  "runs_analyzed": 5,
  "reproducibility_rate": 100.0,
  "score_std_dev": 0.0,
  "task_details": {
    "code_gen_fibonacci": {
      "mean_score": 95.0,
      "std_dev": 0.0,
      "is_reproducible": true
    }
  }
}
```

---

## Docker Deployment

### Build Images

```bash
# Build both agents
docker-compose build

# Build specific agent
docker build -f Dockerfile.green -t alphaevolve-green .
docker build -f Dockerfile.purple -t alphaevolve-purple .
```

### Run Containers

```bash
# Start all services
docker-compose up -d

# Run evaluation
docker-compose --profile evaluation up evaluation-runner

# View logs
docker-compose logs -f green-agent

# Stop all services
docker-compose down
```

### Health Checks

```bash
# Check Green Agent health
curl http://localhost:8000/health

# Check Purple Agent health
curl http://localhost:8001/health
```

---

## Creating Custom Tasks

### Task Definition Format (YAML)

```yaml
task_id: "my_custom_task"
name: "My Custom Task"
category: "code_generation"
difficulty: "medium"
description: |
  Clear description of what the agent needs to accomplish.

detailed_instructions: |
  Step-by-step instructions and requirements.

starter_code:
  solution.py: |
    def my_function():
        # TODO: Implement
        pass

reference_solution:
  solution.py: |
    def my_function():
        return "correct implementation"

public_tests:
  - test_id: "test_basic"
    name: "Basic test"
    input_data:
      function: "my_function"
      args: []
    expected_output: "correct implementation"
    weight: 1.0

hidden_tests:
  - test_id: "test_hidden"
    name: "Hidden edge case"
    input_data:
      function: "my_function"
      args: []
    expected_output: "correct implementation"
    weight: 2.0
    is_hidden: true

evaluation_criteria:
  - "Function returns correct value"
  - "Code is efficient"

max_score: 100.0
time_limit_seconds: 60
allowed_languages:
  - python

tags:
  - custom
  - example
```

### Adding Tasks

1. Create a YAML file in `benchmarks/tasks/<category>/`
2. Follow the schema above
3. Tasks are automatically loaded on startup

---

## API Reference

### Green Agent API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/a2a/agent-card` | GET | Get agent card |
| `/tasks` | GET | List all tasks |
| `/tasks/{task_id}` | GET | Get task details |
| `/evaluate` | POST | Start evaluation |
| `/evaluation/{run_id}` | GET | Get evaluation run |
| `/evaluations` | GET | List all evaluations |
| `/leaderboard` | GET | Get leaderboard |
| `/reproducibility` | GET | Verify reproducibility |
| `/export` | POST | Export results |

### Purple Agent API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/a2a/agent-card` | GET | Get agent card |
| `/a2a/message` | POST | Handle A2A message |
| `/a2a/task` | POST | Process task request |
| `/statistics` | GET | Get agent statistics |
| `/history` | GET | Get task history |

---

## CLI Commands

```bash
# Show version
agentx version

# Initialize new project
agentx init ./my-project

# Start servers
agentx serve-green --port 8000
agentx serve-purple --port 8001

# Run evaluation
agentx evaluate --purple http://localhost:8001 --runs 3

# List tasks
agentx list-tasks --category code_generation

# Show task details
agentx show-task code_gen_fibonacci

# View leaderboard
agentx leaderboard
```

---

## Project Structure

```
AlphaEvolve_AgentX/
├── src/agentx/
│   ├── __init__.py
│   ├── cli.py                    # Command-line interface
│   ├── a2a/
│   │   ├── __init__.py
│   │   └── protocol.py           # A2A protocol implementation
│   ├── green_agent/
│   │   ├── __init__.py
│   │   ├── evaluator.py          # Main evaluator logic
│   │   ├── scoring.py            # Scoring engine
│   │   ├── server.py             # HTTP server
│   │   └── tasks.py              # Task definitions
│   ├── purple_agent/
│   │   ├── __init__.py
│   │   ├── agent.py              # Baseline agent
│   │   ├── server.py             # HTTP server
│   │   └── strategies.py         # Task-solving strategies
│   └── evaluation/
│       ├── __init__.py
│       ├── harness.py            # Evaluation harness
│       └── runner.py             # CLI runner
├── benchmarks/
│   └── tasks/                    # Task definitions
│       ├── code_generation/
│       ├── bug_fix/
│       └── refactoring/
├── config/
│   └── evaluation.yaml           # Configuration
├── results/                      # Evaluation results
├── tests/                        # Test suite
├── Dockerfile.green              # Green Agent container
├── Dockerfile.purple             # Purple Agent container
├── docker-compose.yml            # Container orchestration
├── pyproject.toml                # Project configuration
└── README.md                     # This file
```

---

## Contributing

Contributions are welcome! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add your changes with tests
4. Ensure all tests pass (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Adding New Task Categories

1. Define the category in `src/agentx/green_agent/tasks.py`
2. Add corresponding strategy in `src/agentx/purple_agent/strategies.py`
3. Create example tasks in `benchmarks/tasks/<category>/`
4. Update documentation

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Inspired by the [SWE-bench](https://www.swebench.com/) benchmark
- Built on the [A2A Protocol](https://github.com/google/A2A) specification
- Part of the AgentBeats competition ecosystem

---

## Contact

- **Repository**: [github.com/WeiyingZhao/AlphaEvolve_AgentX](https://github.com/WeiyingZhao/AlphaEvolve_AgentX)
- **Leaderboard**: [agentbeats.dev](https://agentbeats.dev)
- **Issues**: [GitHub Issues](https://github.com/WeiyingZhao/AlphaEvolve_AgentX/issues)
