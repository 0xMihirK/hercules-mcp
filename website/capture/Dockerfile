FROM node:22-bookworm-slim AS node
FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.14-slim-bookworm
COPY --from=node /usr/local/ /usr/local/
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates build-essential && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@2.1.292 @openai/codex@0.160.1 opencode-ai@1.18.35
# Hermes 0.21.5 / v2026.9.24. Keep the native modern TUI prebuilt so the
# account-free runtime never needs package access or external networking.
RUN git init /opt/hermes && cd /opt/hermes && git remote add origin https://github.com/NousResearch/hermes-agent.git && git fetch --depth 1 origin f97608f178d1ffeca59860195ab7da295f7c8e5f && git checkout FETCH_HEAD && uv sync --frozen --extra mcp --no-dev
RUN cd /opt/hermes && npm install --workspace ui-tui && npm run build --workspace ui-tui && mkdir -p hermes_cli/tui_dist && cp ui-tui/dist/entry.js hermes_cli/tui_dist/entry.js
RUN uv pip install --python /opt/hermes/.venv/bin/python pyte==0.8.2
RUN useradd --create-home --uid 1000 capture && mkdir /out && chown capture:capture /out
# Codex 0.160's native daemon verifies process ownership using ps.
RUN apt-get update && apt-get install -y --no-install-recommends procps && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/hermes/.venv/bin:$PATH" TERM=xterm-256color COLORTERM=truecolor LANG=C.UTF-8 HERMES_TUI_DIR=/opt/hermes/ui-tui
USER capture
WORKDIR /home/capture
ENTRYPOINT ["python", "/capture/record.py"]
