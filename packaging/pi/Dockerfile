FROM node:22-trixie-slim AS node
FROM python:3.14-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends git gh curl build-essential tini tigervnc-standalone-server xfce4-panel xfwm4 xfdesktop4 xfce4-settings xfce4-terminal dbus-x11 x11-xserver-utils x11-utils x11-xkb-utils xauth fonts-dejavu-core chromium xdotool scrot && git --version && gh --version && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && npm install -g @openai/codex@0.162.1 @anthropic-ai/claude-code@2.1.296 && node /usr/local/lib/node_modules/@anthropic-ai/claude-code/install.cjs && claude --version && npm cache clean --force
ARG ENGINE_REF=9412abd379ea92418557ffd6beb84bd136dc290f
RUN git clone https://github.com/Synthwave-Solutions/hermes-agent.git /opt/synthpulse/hermes-agent && cd /opt/synthpulse/hermes-agent && git checkout "$ENGINE_REF" && rm -rf .git
RUN python -m venv /opt/synthpulse/hermes-agent/venv && /opt/synthpulse/hermes-agent/venv/bin/pip install --no-cache-dir -e "/opt/synthpulse/hermes-agent[computer-use]"
COPY packaging/pi/office-requirements.txt /tmp/office-requirements.txt
RUN /opt/synthpulse/hermes-agent/venv/bin/pip install --no-cache-dir -r /tmp/office-requirements.txt
COPY . /opt/synthpulse/hermes-webui
RUN /opt/synthpulse/hermes-agent/venv/bin/pip install --no-cache-dir -r /opt/synthpulse/hermes-webui/requirements.txt
ENV HERMES_WEBUI_AGENT_DIR=/opt/synthpulse/hermes-agent HERMES_WEBUI_PYTHON=/opt/synthpulse/hermes-agent/venv/bin/python SP_WEBUI_DIR=/opt/synthpulse/hermes-webui HERMES_WEBUI_DISABLE_LOCAL_VENV=1 HERMES_WEBUI_AUTO_INSTALL=0 HERMES_WEBUI_HOST=0.0.0.0 HERMES_WEBUI_PORT=8787 HERMES_HOME=/home/synthpulse/.synthpulse-engine HERMES_RUNTIME_DIR=/opt/synthpulse/tool-runtime
ENV PATH=/opt/synthpulse/hermes-agent/venv/bin:$PATH
RUN useradd -m -u 1000 -s /bin/bash synthpulse && mkdir -p /home/synthpulse/.synthpulse-engine /opt/synthpulse/tool-runtime && chown synthpulse:synthpulse /opt/synthpulse/tool-runtime && chown -R synthpulse:synthpulse /home/synthpulse
COPY packaging/pi/botscreen packaging/pi/synthpulse-office /usr/local/bin/
RUN chmod 755 /usr/local/bin/botscreen /usr/local/bin/synthpulse-office
COPY packaging/pi/webui-entrypoint.sh /usr/local/bin/synthpulse-webui
RUN chmod 755 /usr/local/bin/synthpulse-webui && touch /.within_container
USER synthpulse
WORKDIR /opt/synthpulse/hermes-webui
RUN python -c "import sys;sys.path.insert(0,'/opt/synthpulse/hermes-agent');import yaml;from run_agent import AIAgent"
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/synthpulse-webui"]

# Locked browser/desktop control binaries shared by profiles; no account state.
RUN /opt/synthpulse/hermes-agent/venv/bin/python -c "from pm import ensure; ensure('agent-browser', explicit=True); ensure('cua-driver', explicit=True)"
