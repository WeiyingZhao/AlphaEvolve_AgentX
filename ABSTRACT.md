# AlphaEvolve AgentX: Green Agent Evaluator for Software Engineering Tasks

## Abstract

**AlphaEvolve AgentX** is a comprehensive benchmark framework designed to evaluate AI agents on software engineering tasks requiring genuine agentic reasoning, multi-step planning, and complex problem-solving. Unlike traditional coding benchmarks that test isolated function implementation, our Green Agent evaluator assesses agents on realistic software engineering workflows that mirror real-world development challenges.

## Task Categories

Our benchmark evaluates Purple Agents across six primary categories:

1. **Code Generation**: From simple function implementation to complex system design
2. **Bug Detection & Fixing**: Identifying and resolving bugs across multiple files
3. **Refactoring**: Improving code structure while preserving behavior
4. **Multi-Step Planning**: Tasks requiring decomposition and sequential execution
5. **API Integration**: Building systems that interact with external services
6. **ML Engineering**: End-to-end machine learning pipeline development

## Key Innovations

### Multi-Step Agentic Tasks
Our benchmark includes tasks that cannot be solved by simple pattern matching or single-turn generation. Tasks require agents to:
- Decompose complex requirements into subtasks
- Maintain state across multiple steps
- Make decisions based on intermediate results
- Handle errors and adapt strategies

### Nuanced Multi-Dimensional Scoring
Beyond binary pass/fail evaluation, our scoring engine assesses:
- **Correctness** (50%): Functional accuracy via test execution
- **Code Quality** (25%): Maintainability, readability, style compliance
- **Performance** (15%): Efficiency, resource utilization, time complexity
- **Robustness** (10%): Error handling, edge cases, input validation

### Reproducibility Guarantees
- Deterministic evaluation with seed control
- Multi-run consistency verification (coefficient of variation < 5%)
- Isolated Docker execution environments
- Comprehensive logging and result tracking

## Technical Implementation

### A2A Protocol Compliance
Full implementation of the Agent-to-Agent protocol enabling:
- Standardized task submission and response format
- Agent capability discovery via Agent Cards
- Streaming result collection
- Error propagation and handling

### Docker Deployment
- Pre-built Green and Purple Agent containers
- Orchestration via Docker Compose
- Health checks and automatic recovery
- Volume mounts for result persistence

## Evaluation Methodology

1. **Task Distribution**: Balanced across difficulty levels (easy to expert)
2. **Hidden Test Sets**: Prevents overfitting to visible test cases
3. **Iterative Feedback**: ML tasks support multiple attempts with feedback
4. **Statistical Analysis**: Variance tracking and reproducibility metrics

## Impact

AlphaEvolve AgentX addresses gaps in existing agent evaluation by:
- Testing genuine multi-step reasoning rather than single-turn generation
- Providing nuanced feedback beyond binary scores
- Ensuring reproducibility for meaningful comparisons
- Supporting the growing ecosystem of AI coding assistants

## Getting Started

```bash
# Start evaluation environment
docker-compose up -d

# Run evaluation against Purple Agent
docker-compose --profile evaluation up evaluation-runner
```

## Links

- **Repository**: https://github.com/WeiyingZhao/AlphaEvolve_AgentX
- **Leaderboard**: https://agentbeats.dev
- **A2A Protocol**: https://github.com/google/A2A
