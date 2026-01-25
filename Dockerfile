# Production Dockerfile for AlphaEvolve AgentX
# Green Agent Evaluator for AgentBeats Competition
#
# Build: docker build -t ghcr.io/alphaevolve/agentx:latest .
# Run:   docker run -p 8000:8000 ghcr.io/alphaevolve/agentx:latest

FROM python:3.11-slim AS base

LABEL maintainer="AlphaEvolve Team"
LABEL org.opencontainers.image.title="AlphaEvolve AgentX"
LABEL org.opencontainers.image.description="Green Agent Evaluator for Software Engineering Benchmarks"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.source="https://github.com/alphaevolve/agentx"
LABEL org.opencontainers.image.licenses="MIT"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 agent

WORKDIR /app

# ---------- Builder stage ----------
FROM base AS builder

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e . && \
    pip install pandas scikit-learn numpy matplotlib

# ---------- Production stage ----------
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=root:root pyproject.toml ./
COPY --chown=root:root src/ ./src/
COPY --chown=root:root benchmarks/ ./benchmarks/
COPY --chown=root:root config/ ./config/
COPY --chown=root:root scripts/ ./scripts/

# Create directories for results and workspace
RUN mkdir -p /app/results /workspace /tmp/agent_work && \
    chown -R agent:agent /app/results /workspace /tmp/agent_work && \
    chmod 755 /app/results /workspace && \
    chmod 700 /tmp/agent_work

# Set temp directory for Python
ENV TMPDIR=/tmp/agent_work

# Volume for persistent data
VOLUME ["/app/results", "/workspace"]

# Switch to non-root user
USER agent

# Expose the agent port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run Green Agent server
CMD ["python", "-m", "agentx.green_agent.server"]
