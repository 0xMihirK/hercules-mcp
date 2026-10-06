FROM node:22-bookworm-slim AS node
FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.14-slim-bookworm
COPY --from=node /usr/local/ /usr/local/
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates build-essential && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@2.1.291 @openai/codex@0.147.0 opencode-ai@1.18.34
RUN git init /opt/hermes && cd /opt/hermes && git remote add origin https://github.com/NousResearch/hermes-agent.git && git fetch --depth 1 origin 3f524a2459efe4ab32061c418e309e5da1a931fd && git checkout FETCH_HEAD && uv sync --frozen --extra mcp --no-dev
RUN uv pip install --python /opt/hermes/.venv/bin/python pyte==0.8.2
RUN useradd --create-home --uid 1000 capture && mkdir /out && chown capture:capture /out
ENV PATH="/opt/hermes/.venv/bin:$PATH" TERM=xterm-256color COLORTERM=truecolor LANG=C.UTF-8
USER capture
WORKDIR /home/capture
ENTRYPOINT ["python", "/capture/record.py"]
