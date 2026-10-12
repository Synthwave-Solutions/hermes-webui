FROM node:22-trixie-slim AS node
FROM python:3.14-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends git curl build-essential tini && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && npm install -g @openai/codex@0.162.1 @anthropic-ai/claude-code@2.1.296 && npm cache clean --force
ARG ENGINE_REF=a8082ff74de0bb7f15323ac72501044a392f4552
RUN git clone https://github.com/Synthwave-Solutions/hermes-agent.git /opt/synthpulse/hermes-agent && cd /opt/synthpulse/hermes-agent && git checkout "$ENGINE_REF" && rm -rf .git
RUN python -m venv /opt/synthpulse/hermes-agent/venv && /opt/synthpulse/hermes-agent/venv/bin/pip install --no-cache-dir /opt/synthpulse/hermes-agent
COPY . /opt/synthpulse/hermes-webui
RUN /opt/synthpulse/hermes-agent/venv/bin/pip install --no-cache-dir -r /opt/synthpulse/hermes-webui/requirements.txt
ENV HERMES_WEBUI_AGENT_DIR=/opt/synthpulse/hermes-agent HERMES_WEBUI_PYTHON=/opt/synthpulse/hermes-agent/venv/bin/python SP_WEBUI_DIR=/opt/synthpulse/hermes-webui HERMES_WEBUI_DISABLE_LOCAL_VENV=1 HERMES_WEBUI_AUTO_INSTALL=0 HERMES_WEBUI_HOST=0.0.0.0 HERMES_WEBUI_PORT=8787 HERMES_HOME=/home/synthpulse/.synthpulse-engine
ENV PATH=/opt/synthpulse/hermes-agent/venv/bin:$PATH
RUN useradd -m -u 1000 -s /bin/bash synthpulse && mkdir -p /home/synthpulse/.synthpulse-engine && chown -R synthpulse:synthpulse /home/synthpulse
COPY packaging/pi/webui-entrypoint.sh /usr/local/bin/synthpulse-webui
RUN chmod 755 /usr/local/bin/synthpulse-webui && touch /.within_container
USER synthpulse
WORKDIR /opt/synthpulse/hermes-webui
RUN python -c "import sys;sys.path.insert(0,'/opt/synthpulse/hermes-agent');import yaml;from run_agent import AIAgent"
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/synthpulse-webui"]
