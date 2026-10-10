"""No direct model provider path in the WebUI (plan 3.12, rule 13, package R3).

A scan of every file in ``api/`` and ``static/`` for

* provider hosts from the E.7.1 list (``PROVIDER_HOSTS_TXT`` below, a byte copy
  of STACK ``modules/egress/provider-hosts.txt``, pinned by its sha256),
* provider SDK imports and constructors, and
* reads of provider key variables.

Comments, docstrings and host comparisons can never make a request, so the
scan classifies them as request-free itself (proven on samples below). Every
other finding needs an allowance, and every allowance is proven by a test in
this file:

* the model-listing and billing URLs in ``api/config.py``, ``api/providers.py``
  and ``api/onboarding.py`` (the listing files build no inference route; every
  provider URL in them is an API base, a listing, credit or usage endpoint, or
  a token claim name);
* request-free references in files no Wave 1 package owns: the live model
  listing table and a documentation link in ``api/routes.py``, and the base URL
  placeholders in ``static/i18n/*.js``;
* the availability probe in ``api/upload.py`` (presence checks only);
* the realtime voice runtime that D58 (b) names, refused under enforcement;
* the Edge TTS branch of ``/api/tts`` in ``api/routes.py``, never reached under
  enforcement;
* the provider account sign-in in ``api/oauth.py`` (sign-in and token paths
  only; refusing it under enforcement is a request to the orchestrator).

An allowance that no longer matches a finding fails the scan, so the list can
only shrink with the code.
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import io
import json
import os
import re
import sys
import tokenize
import types
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("api", "static")

# Byte copy of STACK modules/egress/provider-hosts.txt (E.7.1, orchestrator
# owned). A change there is copied here together with the pin below.
PROVIDER_HOSTS_SHA256 = "01db555af6b7590c208d7de6200ac3a86356f1960efb0daf12400838fdb7c573"
PROVIDER_HOSTS_TXT = """\
# Model provider hosts: every host a model call can leave an installation for.
#
# PLAN 3.12 design 5 and Appendix E.7.1. One host pattern per line: an exact
# host or a "*." suffix (any subdomain, never the bare domain), then a comment
# naming the provider. Derived read-only from the engine's provider table and
# the providers named in 3.12. Never a secret.
#
# Installations block model traffic by default-deny egress, so this list never
# has to be complete to block anything. It feeds the static scans (R1, R3, R4),
# the audits (R8, R11), the egress proxy's allowlist check (R7: an allowlist
# entry that matches this list is refused) and HQ's nft rules (R11).
#
# Orchestrator-owned; modules/egress/provider-hosts.sha256 pins the bytes and
# the HQ config repo keeps a byte copy (hermes/egress/provider-hosts.txt).
# Changes are requests to the orchestrator (from R1, R7, R8 and R11).

api.openai.com                               # OpenAI
auth.openai.com                              # OpenAI Codex (OAuth)
chatgpt.com                                  # OpenAI Codex (OAuth)
*.openai.azure.com                           # Azure OpenAI and Azure AI Foundry
*.services.ai.azure.com                      # Azure OpenAI and Azure AI Foundry
*.models.ai.azure.com                        # Azure OpenAI and Azure AI Foundry
*.inference.ai.azure.com                     # Azure OpenAI and Azure AI Foundry
*.cognitiveservices.azure.com                # Azure OpenAI and Azure AI Foundry
*.tts.speech.microsoft.com                   # Azure Speech
*.stt.speech.microsoft.com                   # Azure Speech
speech.platform.bing.com                     # Microsoft Edge text-to-speech
api.anthropic.com                            # Anthropic
generativelanguage.googleapis.com            # Google generative language (Gemini API)
cloudcode-pa.googleapis.com                  # Google Gemini CLI (Code Assist)
aiplatform.googleapis.com                    # Google Vertex AI
europe-west1-aiplatform.googleapis.com       # Google Vertex AI
europe-west3-aiplatform.googleapis.com       # Google Vertex AI
europe-west4-aiplatform.googleapis.com       # Google Vertex AI
europe-west8-aiplatform.googleapis.com       # Google Vertex AI
europe-west9-aiplatform.googleapis.com       # Google Vertex AI
europe-north1-aiplatform.googleapis.com      # Google Vertex AI
europe-central2-aiplatform.googleapis.com    # Google Vertex AI
europe-southwest1-aiplatform.googleapis.com  # Google Vertex AI
us-central1-aiplatform.googleapis.com        # Google Vertex AI
us-east5-aiplatform.googleapis.com           # Google Vertex AI
texttospeech.googleapis.com                  # Google Cloud text-to-speech
eu-texttospeech.googleapis.com               # Google Cloud text-to-speech
speech.googleapis.com                        # Google Cloud speech-to-text
eu-speech.googleapis.com                     # Google Cloud speech-to-text
bedrock-runtime.eu-central-1.amazonaws.com   # AWS Bedrock runtime
bedrock-runtime.eu-west-1.amazonaws.com      # AWS Bedrock runtime
bedrock-runtime.eu-west-3.amazonaws.com      # AWS Bedrock runtime
bedrock-runtime.eu-north-1.amazonaws.com     # AWS Bedrock runtime
bedrock-runtime.eu-south-1.amazonaws.com     # AWS Bedrock runtime
bedrock-runtime.eu-south-2.amazonaws.com     # AWS Bedrock runtime
bedrock-runtime.us-east-1.amazonaws.com      # AWS Bedrock runtime
bedrock-runtime.us-west-2.amazonaws.com      # AWS Bedrock runtime
*.githubcopilot.com                          # GitHub Copilot (OAuth)
openrouter.ai                                # OpenRouter
eu.openrouter.ai                             # OpenRouter
api.mistral.ai                               # Mistral
codestral.mistral.ai                         # Mistral
api.cortecs.ai                               # Cortecs
api.scaleway.ai                              # Scaleway AI endpoints
*.ifr.fr-par.scaleway.com                    # Scaleway AI endpoints
*.ifr.nl-ams.scaleway.com                    # Scaleway AI endpoints
api.regolo.ai                                # Regolo
api.lyceum.technology                        # Lyceum
api.elevenlabs.io                            # ElevenLabs
api.eu.residency.elevenlabs.io               # ElevenLabs
api.us.elevenlabs.io                         # ElevenLabs
fal.run                                      # fal
*.fal.run                                    # fal
rest.alpha.fal.ai                            # fal
api.x.ai                                     # xAI
api.groq.com                                 # Groq
api.deepseek.com                             # DeepSeek
api.together.xyz                             # Together
api.together.ai                              # Together
api.cohere.com                               # Cohere
api.cohere.ai                                # Cohere
api.voyageai.com                             # Voyage
api.deepgram.com                             # Deepgram
*.nousresearch.com                           # Nous portal, inference and tool gateway
api.perplexity.ai                            # Perplexity
api.replicate.com                            # Replicate
router.huggingface.co                        # Hugging Face Inference
api-inference.huggingface.co                 # Hugging Face Inference
*.endpoints.huggingface.cloud                # Hugging Face Inference
api.fireworks.ai                             # Fireworks
api.cerebras.ai                              # Cerebras
api.jina.ai                                  # Jina
api.moonshot.ai                              # Moonshot (Kimi)
api.moonshot.cn                              # Moonshot (Kimi)
api.kimi.com                                 # Moonshot (Kimi)
open.bigmodel.cn                             # Zhipu (GLM)
api.z.ai                                     # Zhipu (GLM)
dashscope.aliyuncs.com                       # Alibaba DashScope (Qwen)
dashscope-intl.aliyuncs.com                  # Alibaba DashScope (Qwen)
*.dashscope.aliyuncs.com                     # Alibaba DashScope (Qwen)
*.maas.aliyuncs.com                          # Alibaba DashScope (Qwen)
portal.qwen.ai                               # Alibaba DashScope (Qwen)
chat.qwen.ai                                 # Alibaba DashScope (Qwen)
api.assemblyai.com                           # AssemblyAI
api.eu.assemblyai.com                        # AssemblyAI
streaming.assemblyai.com                     # AssemblyAI
streaming.eu.assemblyai.com                  # AssemblyAI
*.api.speechmatics.com                       # Speechmatics
*.rt.speechmatics.com                        # Speechmatics
api.minimax.io                               # MiniMax
api.minimaxi.com                             # MiniMax
api.stepfun.ai                               # StepFun
api.stepfun.com                              # StepFun
integrate.api.nvidia.com                     # NVIDIA
api.lkeap.cloud.tencent.com                  # Tencent
tokenhub.tencentmaas.com                     # Tencent
api.arcee.ai                                 # Arcee
api.gmi-serving.com                          # GMI Cloud
api.actual.inc                               # Actual
api.upstage.ai                               # Upstage
api.tokenfactory.nebius.com                  # Nebius
ollama.com                                   # Ollama Cloud
opencode.ai                                  # OpenCode Zen
api.kilo.ai                                  # Kilo
ai-gateway.vercel.sh                         # Vercel AI gateway
api.xiaomimimo.com                           # Xiaomi MiMo
api.deepinfra.com                            # DeepInfra
api.novita.ai                                # Novita
api.krea.ai                                  # Krea
api.router.com                               # Router
api.commandcode.ai                           # Command Code
"""


def _host_patterns():
    patterns = []
    for raw in PROVIDER_HOSTS_TXT.splitlines():
        host = raw.split("#", 1)[0].strip().lower()
        if not host:
            continue
        if host.startswith("*."):
            rx = re.compile(r"(?<![A-Za-z0-9.-])(?:[A-Za-z0-9-]+\.)+" + re.escape(host[2:])
                            + r"(?![A-Za-z0-9-])", re.I)
        else:
            rx = re.compile(r"(?<![A-Za-z0-9.-])" + re.escape(host) + r"(?![A-Za-z0-9-])", re.I)
        patterns.append((host, rx))
    return tuple(patterns)


HOST_PATTERNS = _host_patterns()
# A literal every match of a pattern contains: a cheap substring prefilter.
_HOST_ANCHORS = tuple((host, rx, host[2:] if host.startswith("*.") else host) for host, rx in HOST_PATTERNS)

# Provider key variables (names only). Kept equal to or below the WebUI's own
# list (api.profiles.provider_key_env_names), which the profile env uses.
KEY_NAMES = frozenset({
    "OPENAI_API_KEY", "VOICE_TOOLS_OPENAI_KEY", "AZURE_OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "ANTHROPIC_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "AZURE_ANTHROPIC_KEY", "OPENROUTER_API_KEY",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "ELEVENLABS_API_KEY", "FAL_KEY", "GROQ_API_KEY",
    "MISTRAL_API_KEY", "XAI_API_KEY", "DEEPSEEK_API_KEY", "DEEPGRAM_API_KEY", "COHERE_API_KEY",
    "TOGETHER_API_KEY", "FIREWORKS_API_KEY", "PERPLEXITY_API_KEY", "REPLICATE_API_TOKEN",
    "HF_TOKEN", "CORTECS_API_KEY", "REGOLO_API_KEY", "LYCEUM_API_KEY", "VOYAGE_API_KEY",
    "JINA_API_KEY", "CEREBRAS_API_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY", "GLM_API_KEY",
    "ZAI_API_KEY", "DASHSCOPE_API_KEY", "MINIMAX_API_KEY", "NVIDIA_API_KEY",
    "ASSEMBLYAI_API_KEY", "SPEECHMATICS_API_KEY", "AZURE_SPEECH_KEY", "KREA_API_KEY",
    "AZURE_FOUNDRY_API_KEY", "AWS_BEARER_TOKEN_BEDROCK", "XIAOMI_API_KEY", "OLLAMA_API_KEY",
})
_KEY_READERS = frozenset({"getenv", "get", "env", "get_env_value", "_get_env"})

_PY_SDK_MODULES = (
    "openai", "anthropic", "google.generativeai", "google.genai", "elevenlabs", "mistralai",
    "groq", "cohere", "fal_client", "edge_tts", "replicate", "together", "litellm", "voyageai",
    "deepgram", "assemblyai", "speechmatics", "azure.ai.inference", "azure.ai.openai",
    "azure.cognitiveservices.speech",
)
_PY_SDK_NAMES = frozenset({"openai", "anthropic", "genai", "elevenlabs", "mistralai", "groq", "cohere",
                           "fal_client", "edge_tts", "replicate", "together", "litellm", "voyageai"})
_PY_SDK_CONSTRUCTORS = frozenset({
    "OpenAI", "AsyncOpenAI", "AzureOpenAI", "AsyncAzureOpenAI", "Anthropic", "AsyncAnthropic",
    "AnthropicBedrock", "AnthropicVertex", "ElevenLabs", "AsyncElevenLabs", "Mistral", "Groq",
    "AsyncGroq", "Together", "AsyncTogether", "GenerativeModel",
})
_JS_SDK = re.compile(
    r"new\s+(?:OpenAI|Anthropic|GoogleGenerativeAI|GoogleGenAI|ElevenLabsClient|Mistral|Groq|CohereClient)\s*\("
    r"|(?:from\s+|require\(\s*)['\"](?:openai|@anthropic-ai/sdk|@google/generative-ai|@google/genai|"
    r"elevenlabs|@elevenlabs/[a-z-]+|@mistralai/mistralai|groq-sdk|cohere-ai|@fal-ai/client|replicate)['\"]")

# Model inference routes: a listing file never builds one.
_INFERENCE_ROUTE = re.compile(
    r"/chat/completions|(?<![A-Za-z])/completions\b|/responses\b|/messages\b|/embeddings\b|/audio/"
    r"|/images/|/realtime|:generateContent|:streamGenerateContent|/text-to-speech|/transcriptions"
    r"|/rerank\b|/moderations\b|/videos?\b|/generate\b", re.I)

LISTING_FILES = ("api/config.py", "api/providers.py", "api/onboarding.py")
R3_FILES = ("api/tts_backend.py", "api/profiles.py", "api/realtime_voice_runtime.py")


@dataclass(frozen=True)
class Finding:
    check: str      # host, sdk or key
    path: str
    line: int
    what: str       # the host pattern, SDK name or key name
    owner: str      # the module-level name or function a Python finding sits in
    kind: str       # request-free kind (comment, docstring, comparison) or "code"
    value: str      # the string constant (Python) or the line (other files)
    parent: str     # the syntactic context of a Python string constant


@dataclass(frozen=True)
class Allowance:
    check: str
    path: str       # an exact path or an fnmatch pattern
    owner: str      # an owner name or "*"
    kind: str
    reason: str

    def matches(self, finding: Finding) -> bool:
        return (finding.check == self.check and fnmatch.fnmatchcase(finding.path, self.path)
                and self.owner in ("*", finding.owner))


ALLOWANCES = (
    *(Allowance(kind, "api/tts_legacy.py", "synthesize", "legacy_tts_refused",
                "hardened HQ adapter, refuses before reading provider keys under enforcement")
      for kind in ("host", "key")),
    *(Allowance("host", path, "*", "listing_billing", "model-listing and billing URLs (plan 3.12)")
      for path in LISTING_FILES),
    Allowance("key", "api/config.py", "*", "listing_billing",
              "provider keys for model listing and credit checks"),
    Allowance("host", "api/routes.py", "_OPENAI_COMPAT_ENDPOINTS", "listing",
              "the live model listing table, only ever joined with /models"),
    Allowance("host", "api/routes.py", "_LLM_WIKI_DOCS_URL", "docs_link",
              "a documentation link shown to the user"),
    Allowance("host", "static/i18n/*.js", "*", "ui_placeholder",
              "base URL placeholders of the settings forms"),
    Allowance("key", "api/upload.py", "*", "availability_probe",
              "presence checks of the speech-to-text capability probe"),
    Allowance("host", "api/realtime_voice.py", "DIRECT_BASE_URL", "realtime_d58b",
              "the direct realtime route, refused under enforcement (D58 (b))"),
    Allowance("key", "api/realtime_voice.py", "_route_key", "realtime_d58b",
              "the direct realtime key, never read under enforcement (D58 (b))"),
    Allowance("sdk", "api/routes.py", "_handle_tts", "edge_tts_refused",
              "the Edge branch of /api/tts, never reached under enforcement"),
    Allowance("host", "api/oauth.py", "CODEX_ISSUER", "provider_sign_in",
              "provider account sign-in; refusal under enforcement is requested from the orchestrator"),
    Allowance("host", "api/oauth.py", "CODEX_BASE_URL", "provider_sign_in",
              "the provider base URL stored with a linked account, never requested by the WebUI"),
)


# ── Source indexing ──────────────────────────────────────────────────────────


def _scan_files():
    files = []
    for base in SCAN_DIRS:
        for path in sorted((ROOT / base).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or "node_modules" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary assets
            files.append((path.relative_to(ROOT).as_posix(), text))
    return files


class _PyIndex:
    def __init__(self, text: str):
        self.text = text
        self.tree = ast.parse(text)
        self.parents = {}
        for node in ast.walk(self.tree):
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node
        self._comments = None
        self._strings = None

    @property
    def comments(self):
        if self._comments is None:
            self._comments = {}
            for token in tokenize.generate_tokens(io.StringIO(self.text).readline):
                if token.type == tokenize.COMMENT:
                    self._comments.setdefault(token.start[0], []).append((token.start[1], token.end[1]))
        return self._comments

    @property
    def strings(self):
        if self._strings is None:
            self._strings = {}
            for node in ast.walk(self.tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        self._strings.setdefault(line, []).append(node)
        return self._strings

    def owner(self, node) -> str:
        current = node
        while current in self.parents:
            current = self.parents[current]
            if isinstance(current, (ast.Assign, ast.AnnAssign)) and isinstance(self.parents.get(current), ast.Module):
                targets = current.targets if isinstance(current, ast.Assign) else [current.target]
                names = [target.id for target in targets if isinstance(target, ast.Name)]
                if names:
                    return names[0]
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return current.name
        return "<module>"

    def _lift(self, node):
        """Step out of f-string pieces to the expression that uses the string."""
        parent = self.parents.get(node)
        while isinstance(parent, (ast.JoinedStr, ast.FormattedValue)):
            node, parent = parent, self.parents.get(parent)
        return node, parent

    def parent_label(self, node) -> str:
        node, parent = self._lift(node)
        if isinstance(parent, ast.Call):
            func = parent.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            return f"call:{name}"
        return type(parent).__name__.lower() if parent is not None else "none"

    def context(self, node) -> str:
        """comment-free context of a string constant: docstring, comparison or code."""
        node, parent = self._lift(node)
        if isinstance(parent, ast.Expr):
            return "docstring"
        if isinstance(parent, (ast.Tuple, ast.List, ast.Set)):
            node, parent = parent, self.parents.get(parent)
        if isinstance(parent, ast.Compare):
            return "comparison"
        if (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute)
                and parent.func.attr in ("endswith", "startswith") and node in parent.args):
            return "comparison"
        return "code"


def _classify_python_hit(index: _PyIndex, line: int, column: int, matched: str):
    for start, end in index.comments.get(line, ()):
        if start <= column < end:
            return "comment", "<comment>", "", "comment"
    candidates = [node for node in index.strings.get(line, ()) if matched.lower() in node.value.lower()]
    if not candidates:
        return "code", "<unknown>", "", "unknown"
    kinds = {index.context(node) for node in candidates}
    code = [node for node in candidates if index.context(node) == "code"]
    if not code:
        return sorted(kinds)[0], index.owner(candidates[0]), candidates[0].value, index.parent_label(candidates[0])
    return "code", index.owner(code[0]), code[0].value, index.parent_label(code[0])


def _host_findings_for(path: str, text: str):
    findings = []
    index = None
    lowered = text.lower()
    present = [(host, rx, anchor) for host, rx, anchor in _HOST_ANCHORS if anchor in lowered]
    if not present:
        return findings
    for number, line in enumerate(text.splitlines(), 1):
        lowered_line = line.lower()
        for host, rx, anchor in present:
            if anchor not in lowered_line:
                continue
            for match in rx.finditer(line):
                if path.endswith(".py"):
                    index = index or _PyIndex(text)
                    kind, owner, value, parent = _classify_python_hit(index, number, match.start(), match.group(0))
                else:
                    stripped = line.strip()
                    kind = "comment" if stripped.startswith(("//", "/*", "*", "<!--")) else "code"
                    owner, value, parent = "*", line.strip(), "text"
                findings.append(Finding("host", path, number, host, owner, kind, value, parent))
    return findings


_PY_PREFILTER = tuple(sorted(KEY_NAMES | _PY_SDK_NAMES | _PY_SDK_CONSTRUCTORS | {m.split(".")[0] for m in _PY_SDK_MODULES}))


def _python_sdk_and_key_findings(path: str, text: str):
    findings = []
    if not any(word in text for word in _PY_PREFILTER):
        return findings
    index = _PyIndex(text)
    for node in ast.walk(index.tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for module in modules:
                if any(module == sdk or module.startswith(sdk + ".") for sdk in _PY_SDK_MODULES):
                    findings.append(Finding("sdk", path, node.lineno, module, index.owner(node), "code", module, "import"))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _PY_SDK_CONSTRUCTORS:
                findings.append(Finding("sdk", path, node.lineno, func.id, index.owner(node), "code", func.id, "call"))
            elif isinstance(func, ast.Attribute) and (
                    func.attr in _PY_SDK_CONSTRUCTORS
                    or (isinstance(func.value, ast.Name) and func.value.id in _PY_SDK_NAMES)):
                base = func.value.id if isinstance(func.value, ast.Name) else "?"
                findings.append(Finding("sdk", path, node.lineno, f"{base}.{func.attr}", index.owner(node),
                                        "code", f"{base}.{func.attr}", "call"))
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if (name in _KEY_READERS and node.args and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value in KEY_NAMES):
                findings.append(Finding("key", path, node.lineno, node.args[0].value, index.owner(node),
                                        "code", node.args[0].value, index.parent_label(node)))
        elif (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
              and isinstance(node.slice, ast.Constant) and node.slice.value in KEY_NAMES):
            findings.append(Finding("key", path, node.lineno, node.slice.value, index.owner(node),
                                    "code", node.slice.value, "subscript"))
    return findings


def _text_sdk_and_key_findings(path: str, text: str):
    findings = []
    key_rx = re.compile(r"\b(" + "|".join(sorted(KEY_NAMES)) + r")\b")
    for number, line in enumerate(text.splitlines(), 1):
        if _JS_SDK.search(line):
            findings.append(Finding("sdk", path, number, _JS_SDK.search(line).group(0), "*", "code", line.strip(), "text"))
        for match in key_rx.finditer(line):
            findings.append(Finding("key", path, number, match.group(1), "*", "code", line.strip(), "text"))
    return findings


_CACHE = {}


def _all_findings():
    if "all" not in _CACHE:
        findings = []
        for path, text in _scan_files():
            findings.extend(_host_findings_for(path, text))
            if path.endswith(".py"):
                findings.extend(_python_sdk_and_key_findings(path, text))
            elif path.endswith((".js", ".mjs", ".cjs", ".html")):
                findings.extend(_text_sdk_and_key_findings(path, text))
        _CACHE["all"] = findings
    return _CACHE["all"]


def _code_findings(check: str):
    return [f for f in _all_findings() if f.check == check and f.kind == "code"]


def _unallowed(check: str):
    return [f for f in _code_findings(check) if not any(a.matches(f) for a in ALLOWANCES)]


def _describe(findings):
    return "\n".join(f"{f.path}:{f.line} {f.check} {f.what} in {f.owner}: {f.value[:120]!r}" for f in findings)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# ── The list and the classifier ─────────────────────────────────────────────


def test_provider_host_list_is_the_pinned_e71_copy():
    assert hashlib.sha256(PROVIDER_HOSTS_TXT.encode("utf-8")).hexdigest() == PROVIDER_HOSTS_SHA256
    hosts = {host for host, _ in HOST_PATTERNS}
    assert len(hosts) > 100
    for host in ("api.openai.com", "api.anthropic.com", "api.elevenlabs.io", "speech.platform.bing.com",
                 "*.nousresearch.com", "openrouter.ai", "generativelanguage.googleapis.com"):
        assert host in hosts, host


def test_host_patterns_match_hosts_and_subdomains_only():
    rx = dict(HOST_PATTERNS)
    assert rx["api.openai.com"].search("https://api.openai.com/v1")
    assert not rx["api.openai.com"].search("https://myapi.openai.company.test")
    assert rx["*.openai.azure.com"].search("https://acme.openai.azure.com/openai")
    assert not rx["*.openai.azure.com"].search("https://openai.azure.com/")


def test_classifier_marks_only_comments_docstrings_and_comparisons_request_free():
    sample = (
        '"""Module docs mention https://api.openai.com/v1."""\n'
        "import requests\n"
        "# see https://api.anthropic.com for details\n"
        "TABLE = {'x': 'https://api.mistral.ai/v1'}\n"
        "def f(host, url):\n"
        "    '''Docs: api.x.ai'''\n"
        "    if host == 'api.openai.com' or host.endswith('.openai.azure.com'):\n"
        "        return 1\n"
        "    if host in ('openrouter.ai', 'api.deepseek.com'):\n"
        "        return 2\n"
        "    requests.post('https://api.openai.com/v1/chat/completions')\n"
        "    return requests.get(f'https://api.groq.com/{url}')\n"
    )
    found = {(f.line, f.what): (f.kind, f.owner) for f in _host_findings_for("api/sample.py", sample)}
    assert found[(1, "api.openai.com")][0] == "docstring"
    assert found[(3, "api.anthropic.com")][0] == "comment"
    assert found[(4, "api.mistral.ai")] == ("code", "TABLE")
    assert found[(6, "api.x.ai")][0] == "docstring"
    assert found[(7, "api.openai.com")][0] == "comparison"
    assert found[(9, "openrouter.ai")][0] == "comparison"
    assert found[(11, "api.openai.com")] == ("code", "f")
    assert found[(12, "api.groq.com")] == ("code", "f")
    js = "// https://api.openai.com in a comment\nfetch('https://api.openai.com/v1/responses')\n"
    kinds = [f.kind for f in _host_findings_for("static/sample.js", js)]
    assert kinds == ["comment", "code"]


def test_sdk_and_key_detection_on_samples():
    sample = (
        "import os\n"
        "import openai\n"
        "from edge_tts import Communicate\n"
        "client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))\n"
        "key = os.environ['ANTHROPIC_API_KEY']\n"
        "ok = bool(env('GROQ_API_KEY'))\n"
        "names = ('OPENAI_API_KEY',)\n"
    )
    findings = _python_sdk_and_key_findings("api/sample.py", sample)
    sdk = sorted(f.what for f in findings if f.check == "sdk")
    keys = sorted((f.line, f.what) for f in findings if f.check == "key")
    assert sdk == ["OpenAI", "edge_tts", "openai"]
    assert keys == [(4, "OPENAI_API_KEY"), (5, "ANTHROPIC_API_KEY"), (6, "GROQ_API_KEY")]


# ── The scan ────────────────────────────────────────────────────────────────


def test_no_provider_host_outside_the_allowances():
    unallowed = _unallowed("host")
    assert not unallowed, "Direct provider hosts in the WebUI:\n" + _describe(unallowed)


def test_no_provider_sdk_outside_the_allowances():
    unallowed = _unallowed("sdk")
    assert not unallowed, "Provider SDKs in the WebUI:\n" + _describe(unallowed)


def test_no_provider_key_read_outside_the_allowances():
    unallowed = _unallowed("key")
    assert not unallowed, "Provider key reads in the WebUI:\n" + _describe(unallowed)


@pytest.mark.parametrize("allowance", ALLOWANCES, ids=lambda a: f"{a.check}:{a.path}:{a.owner}")
def test_every_allowance_is_still_needed(allowance):
    assert any(allowance.matches(f) for f in _code_findings(allowance.check)), (
        f"stale allowance {allowance}: remove it")


def test_r3_files_need_no_allowance():
    for path in R3_FILES:
        found = [f for f in _all_findings() if f.path == path and f.kind == "code"]
        assert not found, _describe(found)
    voice = [f for f in _all_findings() if f.path == "api/realtime_voice.py" and f.kind == "code"]
    assert {(f.check, f.owner) for f in voice} == {("host", "DIRECT_BASE_URL"), ("key", "_route_key")}


def test_scan_keys_are_the_profile_env_provider_keys():
    from api.profiles import provider_key_env_names

    assert KEY_NAMES <= provider_key_env_names()


# ── Proofs of the allowances ────────────────────────────────────────────────


def _docstring_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            ids.add(id(node.value))
    return ids


@pytest.mark.parametrize("path", LISTING_FILES)
def test_listing_files_build_no_inference_route(path):
    tree = ast.parse(_read(path))
    docstrings = _docstring_ids(tree)
    routes = [(node.lineno, node.value[:100]) for node in ast.walk(tree)
              if isinstance(node, ast.Constant) and isinstance(node.value, str)
              and id(node) not in docstrings and _INFERENCE_ROUTE.search(node.value)]
    assert not routes, f"{path} builds a model inference route: {routes}"


_API_BASE_PATHS = {"", "/", "/v1", "/v1beta/openai", "/api/paas/v4", "/backend-api/codex"}
_LISTING_BILLING_PATH = re.compile(r"/(?:models|key|usage)/?$")
_TOKEN_CLAIM_PATHS = {"/auth", "/profile"}


def _url_literals(finding: Finding):
    """(url, parent) pairs of a finding; Python code held in a string is parsed."""
    try:
        embedded = ast.parse(finding.value) if "\n" in finding.value else None
    except SyntaxError:
        embedded = None
    if embedded is not None and len(embedded.body) > 1:
        pairs = []
        for inner in _host_findings_for(finding.path + "#embedded.py", finding.value + "\n"):
            if inner.kind == "code":
                pairs.extend((url, inner.parent) for url in re.findall(r"https?://[^\s'\"]+", inner.value))
        return pairs
    return [(url, finding.parent) for url in re.findall(r"https?://[^\s'\"]+", finding.value)]


@pytest.mark.parametrize("path", LISTING_FILES)
def test_listing_file_provider_urls_are_bases_listings_billing_or_claims(path):
    findings = [f for f in _code_findings("host") if f.path == path]
    assert findings, f"no provider URL left in {path}; drop its allowance"
    for finding in findings:
        pairs = _url_literals(finding)
        assert pairs, _describe([finding])
        for url, parent in pairs:
            url_path = urlsplit(url).path.rstrip("/")
            if url_path in _API_BASE_PATHS or _LISTING_BILLING_PATH.search(url_path):
                continue
            # A JWT claim name (for example https://api.openai.com/auth) is a
            # dictionary key of a decoded token, never a request.
            assert url_path in _TOKEN_CLAIM_PATHS and parent in ("call:get", "tuple"), (
                f"{url} ({parent}) in " + _describe([finding]))


def _function_containing(tree, target):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(child is target for child in ast.walk(node)):
                return node
    return None


def test_routes_listing_table_is_only_joined_with_models():
    tree = ast.parse(_read("api/routes.py"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    uses = [node for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == "_OPENAI_COMPAT_ENDPOINTS"
            and isinstance(node.ctx, ast.Load)]
    assert uses
    for use in uses:
        attribute = parents[use]
        call = parents[attribute]
        assign = parents[call]
        assert isinstance(attribute, ast.Attribute) and attribute.attr == "get"
        assert isinstance(assign, ast.Assign) and isinstance(assign.targets[0], ast.Name)
        variable = assign.targets[0].id
        # The block that assigns the table entry and everything in it.
        scope = parents[assign]
        assert any(statement is assign for statement in getattr(scope, "body", []))
        loads = [node for node in ast.walk(scope) if isinstance(node, ast.Name) and node.id == variable
                 and isinstance(node.ctx, ast.Load)]
        assert loads
        for load in loads:
            parent = parents[load]
            if isinstance(parent, ast.FormattedValue):
                joined = parents[parent]
                tail = joined.values[-1]
                assert isinstance(tail, ast.Constant) and tail.value == "/models", ast.unparse(joined)
            else:
                assert isinstance(parent, (ast.If, ast.BoolOp, ast.UnaryOp)), ast.unparse(parent)


def test_routes_docs_link_is_documentation_only():
    tree = ast.parse(_read("api/routes.py"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    value = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "_LLM_WIKI_DOCS_URL" for t in node.targets):
            value = node.value.value
    parts = urlsplit(value)
    assert parts.hostname == "hermes-agent.nousresearch.com" and parts.path.startswith("/docs/")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "_LLM_WIKI_DOCS_URL" and isinstance(node.ctx, ast.Load):
            container = parents[node]
            assert isinstance(container, ast.Dict)
            key = container.keys[container.values.index(node)]
            assert isinstance(key, ast.Constant) and key.value == "docs_url"


def test_i18n_hits_are_base_url_placeholders_only():
    placeholder = re.compile(r"^\s*[a-z0-9_]+_placeholder\s*:\s*'https?://[^']*'\s*,?\s*$")
    findings = [f for f in _code_findings("host") if fnmatch.fnmatchcase(f.path, "static/i18n/*.js")]
    assert findings
    for finding in findings:
        assert placeholder.match(finding.value), _describe([finding])


def test_upload_probe_only_checks_key_presence():
    tree = ast.parse(_read("api/upload.py"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    reads = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and node.args
             and isinstance(node.args[0], ast.Constant) and node.args[0].value in KEY_NAMES]
    assert reads
    for read in reads:
        wrapper = parents[read]
        assert isinstance(wrapper, ast.Call) and getattr(wrapper.func, "id", "") == "bool", ast.unparse(wrapper)


def test_realtime_direct_route_is_refused_and_its_key_never_read_under_enforcement(monkeypatch, tmp_path):
    from api import profiles
    from api import realtime_voice as voice

    for name in ("SP_MODEL_GATEWAY_REALTIME", "SP_MODEL_GATEWAY_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", tmp_path)
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: tmp_path)
    monkeypatch.setenv("SYNPULSE_REALTIME_VOICE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-must-not-be-read")
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    read = []

    def tracking_getenv(name, default=None):
        read.append(name)
        return os.environ.get(name, default)

    monkeypatch.setattr(voice, "os", types.SimpleNamespace(getenv=tracking_getenv, environ=os.environ))
    assert voice.realtime_route().kind == "refused"
    assert voice.configured() is False
    with pytest.raises(voice.RealtimeGatewayRequired):
        voice.create_call("v=0", "alice", post=lambda *a, **k: pytest.fail("provider reached"))
    assert "OPENAI_API_KEY" not in read


def test_edge_tts_branch_is_not_reached_under_enforcement(monkeypatch, tmp_path):
    from api import profiles, routes, tts_backend

    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", tmp_path)
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: tmp_path)
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    monkeypatch.delenv("SP_MODEL_GATEWAY_AUDIO", raising=False)
    import api.auth as auth
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    edge = types.ModuleType("edge_tts")

    def _refuse(*a, **k):
        raise AssertionError("Edge TTS reached under enforcement")

    edge.Communicate = _refuse
    monkeypatch.setitem(sys.modules, "edge_tts", edge)
    monkeypatch.setattr(tts_backend, "_engine_text_to_speech", lambda: pytest.fail("engine reached"))
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter
    body = json.dumps({"text": "Hello", "engine": "edge", "voice": "en-US-AriaNeural"}).encode()
    handler = types.SimpleNamespace(
        command="POST", rfile=io.BytesIO(body), wfile=io.BytesIO(), client_address=("7.7.7.8", 1),
        headers={"Content-Length": str(len(body))}, status=None,
    )
    handler.send_response = lambda status: setattr(handler, "status", status)
    handler.send_header = lambda *a: None
    handler.end_headers = lambda: None
    try:
        routes._handle_tts(handler, None)
    finally:
        if hasattr(routes._handle_tts, "_tts_limiter"):
            del routes._handle_tts._tts_limiter
    assert handler.status == 409
    assert json.loads(handler.wfile.getvalue())["code"] == "gateway_required"


def test_oauth_provider_hosts_are_sign_in_only():
    tree = ast.parse(_read("api/oauth.py"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            constants[node.targets[0].id] = node.value
    assert urlsplit(constants["CODEX_ISSUER"].value).path == ""
    sign_in_paths = {}
    for name, value in constants.items():
        if isinstance(value, ast.JoinedStr) and any(
                isinstance(part, ast.FormattedValue) and getattr(part.value, "id", "") == "CODEX_ISSUER"
                for part in value.values):
            suffix = value.values[-1].value
            assert not _INFERENCE_ROUTE.search(suffix), suffix
            sign_in_paths[name] = suffix
    assert set(sign_in_paths.values()) == {
        "/codex/device", "/api/accounts/deviceauth/usercode", "/api/accounts/deviceauth/token",
        "/oauth/token", "/deviceauth/callback"}
    # CODEX_ISSUER feeds only those sign-in URLs.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "CODEX_ISSUER" and isinstance(node.ctx, ast.Load):
            assert isinstance(parents[node], ast.FormattedValue)
    # Requests go only through _json_request, and only to the sign-in URLs.
    requests_made = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                     and getattr(node.func, "attr", "") in ("urlopen", "Request")]
    assert requests_made and all(_function_containing(tree, call).name == "_json_request" for call in requests_made)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_json_request":
            assert getattr(node.args[0], "id", "") in {"CODEX_USER_CODE_URL", "CODEX_DEVICE_TOKEN_URL", "CODEX_TOKEN_URL"}
    # The provider base URL is only stored with the linked account.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "CODEX_BASE_URL" and isinstance(node.ctx, ast.Load):
            container = parents[node]
            assert isinstance(container, ast.Dict)
            key = container.keys[container.values.index(node)]
            assert isinstance(key, ast.Constant) and key.value == "base_url"


@pytest.mark.parametrize("engine", ["openai", "elevenlabs"])
def test_legacy_tts_adapter_refuses_before_provider_keys_or_transport(monkeypatch, engine):
    from api import profiles, tts_legacy
    monkeypatch.setattr(profiles, "model_gateway_enforced", lambda: True)
    monkeypatch.setattr(tts_legacy, "os", types.SimpleNamespace(getenv=lambda *a: pytest.fail("legacy provider key read")))
    handler = types.SimpleNamespace(wfile=io.BytesIO(), status=None)
    handler.send_response = lambda status: setattr(handler, "status", status)
    handler.send_header = lambda *a: None
    handler.end_headers = lambda: None
    tts_legacy.synthesize(handler, "Hello", engine, "")
    assert handler.status == 409
    assert json.loads(handler.wfile.getvalue())["code"] == "gateway_required"
