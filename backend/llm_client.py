"""
DevHandoff — LLM Client (IBM watsonx.ai)
=========================================
Thin async wrapper around the IBM watsonx.ai text generation REST API.

Required environment variables (set in .env or shell):
  WATSONX_API_KEY     IBM Cloud API key
  WATSONX_PROJECT_ID  watsonx.ai project ID (UUID)

Optional:
  WATSONX_URL         Instance URL (default: https://us-south.ml.cloud.ibm.com)
  WATSONX_MODEL_ID    Model to use  (default: ibm/granite-3-8b-instruct)
"""

from __future__ import annotations

import json
import logging
import os
import re as _re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration helpers — always read direct from .env so the values are
# current regardless of when the process started.
# ---------------------------------------------------------------------------

def _read_env_value(key_or_keys: str | list[str], default: str = "") -> str:
    """Return env var value, falling back to reading .env file directly. Strips surrounding quotes."""
    keys = [key_or_keys] if isinstance(key_or_keys, str) else key_or_keys

    # Check os.getenv first
    for k in keys:
        val = os.getenv(k, "").strip()
        if val:
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1].strip()
            if val:
                return val

    # Fall back to reading .env file directly
    try:
        from pathlib import Path as _P
        env_path = _P(__file__).resolve().parent.parent / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                for k in keys:
                    if line.startswith(f"{k}=") and not line.startswith("#"):
                        val = line.split("=", 1)[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1].strip()
                        if val:
                            return val
    except Exception:
        pass
    return default


# Module-level defaults & test patch points
_WX_URL_DEFAULT = "https://us-south.ml.cloud.ibm.com"
_WX_MODEL_DEFAULT = "ibm/granite-3-8b-instruct"

# Module-level patch variables (used by test suites/mocks if assigned)
_WX_API_KEY: str | None = None
_WX_PROJECT_ID: str | None = None
_WX_URL: str | None = None
_WX_GENERATE_URL: str | None = None

_IAM_URL = "https://iam.cloud.ibm.com/identity/token"
_TIMEOUT = 120  # seconds

# Token cache: api_key -> (access_token, expire_timestamp)
_iam_token_cache: dict[str, tuple[str, float]] = {}


def get_watsonx_api_key() -> str:
    """Resolve IBM API key from module patch, env vars, or .env."""
    if _WX_API_KEY:
        return _WX_API_KEY
    return _read_env_value(["WATSONX_API_KEY", "IBM_API_KEY", "IBM_CLOUD_API_KEY", "WATSONX_APIKEY"])


def get_watsonx_project_id() -> str:
    """Resolve watsonx Project ID from module patch, env vars, or .env."""
    if _WX_PROJECT_ID:
        return _WX_PROJECT_ID
    return _read_env_value(["WATSONX_PROJECT_ID", "IBM_PROJECT_ID", "WATSONX_PROJECTID"])


def get_watsonx_url() -> str:
    """Resolve watsonx base URL from module patch, env vars, or .env."""
    if _WX_URL:
        return _WX_URL.rstrip("/")
    return _read_env_value(["WATSONX_URL", "IBM_URL"], _WX_URL_DEFAULT).rstrip("/")


def get_watsonx_model_id() -> str:
    """Resolve watsonx model ID from env vars or .env."""
    return _read_env_value(["WATSONX_MODEL_ID", "IBM_MODEL_ID"], _WX_MODEL_DEFAULT)


# ---------------------------------------------------------------------------
# watsonx.ai API calls
# ---------------------------------------------------------------------------

async def _get_iam_token(api_key: str) -> str:
    """Exchange an IBM Cloud API key for a short-lived IAM bearer token (cached for ~50m)."""
    import time
    now = time.time()
    cached = _iam_token_cache.get(api_key)
    if cached and cached[1] > now:
        return cached[0]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _IAM_URL,
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        _iam_token_cache[api_key] = (token, now + max(60, expires_in - 300))
        return token


async def _call_watsonx(
    prompt: str,
    api_key: str,
    project_id: str,
    max_tokens: int = 2048,
    model_id: str | None = None,
    url: str | None = None,
) -> str:
    """Send a prompt to watsonx.ai and return the generated text."""
    if _WX_GENERATE_URL:
        generate_url = _WX_GENERATE_URL
    else:
        wx_url = (url or get_watsonx_url()).rstrip("/")
        generate_url = f"{wx_url}/ml/v1/text/generation?version=2023-05-29"

    model_to_use = model_id or get_watsonx_model_id()
    token = await _get_iam_token(api_key)

    payload = {
        "model_id": model_to_use,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_tokens,
            "repetition_penalty": 1.1,
        },
        "project_id": project_id,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            generate_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            return results[0].get("generated_text", "").strip()
        return ""


# ---------------------------------------------------------------------------
# Public generate() — single entry point for all LLM calls
# ---------------------------------------------------------------------------

async def generate(
    prompt: str,
    max_tokens: int = 2048,
    api_key: str | None = None,
    project_id: str | None = None,
    model_id: str | None = None,
    url: str | None = None,
) -> str:
    """
    Call watsonx.ai and return the generated text string.

    On any failure returns a descriptive ⚠️ error string (never raises)
    so the pipeline degrades gracefully.

    Credentials can be passed explicitly or resolved from .env / environment
    (WATSONX_API_KEY / IBM_API_KEY and WATSONX_PROJECT_ID).
    """
    effective_api_key = api_key or get_watsonx_api_key()
    effective_project_id = project_id or get_watsonx_project_id()

    if not effective_api_key or not effective_project_id:
        missing = []
        if not effective_api_key:
            missing.append("WATSONX_API_KEY (or IBM_API_KEY)")
        if not effective_project_id:
            missing.append("WATSONX_PROJECT_ID")
        return (
            f"⚠️ watsonx.ai not configured. Set {' and '.join(missing)} in .env or the UI."
        )

    try:
        active_model = model_id or get_watsonx_model_id()
        logger.info("Calling watsonx.ai model: %s", active_model)
        response = await _call_watsonx(
            prompt=prompt,
            api_key=effective_api_key,
            project_id=effective_project_id,
            max_tokens=max_tokens,
            model_id=model_id,
            url=url,
        )
        if response:
            return response
        logger.warning("watsonx.ai returned an empty response")
        return "⚠️ watsonx.ai returned an empty response. Raw subagent data is still available."
    except httpx.HTTPStatusError as exc:
        logger.error("watsonx.ai HTTP error %s: %s", exc.response.status_code, exc.response.text)
        return (
            f"⚠️ watsonx.ai returned HTTP {exc.response.status_code}. "
            "Check WATSONX_API_KEY, WATSONX_PROJECT_ID, and WATSONX_URL."
        )
    except httpx.ConnectError:
        wx_url = url or get_watsonx_url()
        logger.error("Cannot reach watsonx.ai at %s", wx_url)
        return (
            f"⚠️ watsonx.ai unreachable at {wx_url}. "
            "Check WATSONX_URL and network connectivity."
        )
    except Exception as exc:
        logger.error("watsonx.ai call failed: %s", exc)
        return f"⚠️ watsonx.ai call failed: {exc}."


# ---------------------------------------------------------------------------
# Error detection helper
# ---------------------------------------------------------------------------

_LLM_ERROR_PREFIXES = ("⚠️ watsonx.ai",)


def _llm_failed(text: str) -> bool:
    """Return True if generate() returned an error notice instead of real output."""
    return any(text.startswith(p) for p in _LLM_ERROR_PREFIXES)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _json_snippet(data: Any, max_chars: int = 4000) -> str:
    """Safely serialize data to a truncated JSON string for prompt injection."""
    try:
        raw = json.dumps(data, indent=2, default=str)
    except Exception:
        raw = str(data)
    return raw[:max_chars] + (" ... [truncated]" if len(raw) > max_chars else "")


# ---------------------------------------------------------------------------
# Subagent-specific summarizers
# ---------------------------------------------------------------------------

async def summarize_inflight(data: dict, api_key: str | None = None, project_id: str | None = None, url: str | None = None) -> str:
    """Turn Subagent 1's raw JSON into 2-4 plain-English sentences."""
    prompt = f"""You are a senior developer reading a structured JSON report about the
current in-flight state of a code repository.  Write 2-4 plain-English sentences
(no bullet points, no markdown headers) summarizing:
- how many files have uncommitted changes and what kind of changes they are
- what GitHub issues or PRs are linked to the current branch (if any)
- whether the test suite is passing or failing, and how many tests failed

Be concise and factual.  Here is the JSON data:

{_json_snippet(data)}
"""
    res = await generate(prompt, max_tokens=300, api_key=api_key, project_id=project_id, url=url)
    if _llm_failed(res):
        uncommitted = len(data.get("uncommitted_changes", []))
        issues = len(data.get("linked_issues", []))
        tests = data.get("test_status", {})
        failed = tests.get("failed", 0)
        passed = tests.get("passed", 0)
        framework = tests.get("framework", "")
        if framework:
            test_info = f"passing ({passed} passed)" if failed == 0 else f"{failed} test(s) failed"
        else:
            test_info = "not run"
        return (
            f"⚠️ [LLM unavailable — heuristic summary] "
            f"{uncommitted} uncommitted change(s) found. "
            f"{issues} linked issue(s)/PR(s) identified. "
            f"Test suite status: {test_info}."
        )
    return res


async def summarize_archaeologist(data: dict, api_key: str | None = None, project_id: str | None = None, url: str | None = None) -> str:
    """Turn Subagent 2's raw JSON into 2-4 plain-English sentences."""
    prompt = f"""You are a senior developer reading a structured JSON report containing
git history data for files recently modified in a repository.  Write 2-4 plain-English
sentences summarizing:
- which files were changed and how recently
- what the commit messages suggest about the reason for those changes
- any issue references (#NNN) that indicate what work was in progress

Be concise and factual.  Here is the JSON data:

{_json_snippet(data)}
"""
    res = await generate(prompt, max_tokens=300, api_key=api_key, project_id=project_id, url=url)
    if _llm_failed(res):
        files = len(data.get("files", []))
        commits_count = sum(len(f.get("recent_commits", [])) for f in data.get("files", []))
        return (
            f"⚠️ [LLM unavailable — heuristic summary] "
            f"Analyzed Git commit history across {files} file(s) with {commits_count} recent commit records tracked."
        )
    return res


async def summarize_drift(data: dict, api_key: str | None = None, project_id: str | None = None, url: str | None = None) -> str:
    """Turn Subagent 3's raw JSON into 2-4 plain-English sentences."""
    prompt = f"""You are a senior developer reading a structured JSON report about
documentation drift and technical debt in a codebase.  Write 2-4 plain-English
sentences summarizing:
- how many public functions/classes are missing docstrings
- what documentation-vs-code mismatches were found
- how many TODO/FIXME/XXX comments exist and what themes they cover

Be concise and factual.  Here is the JSON data:

{_json_snippet(data)}
"""
    res = await generate(prompt, max_tokens=300, api_key=api_key, project_id=project_id, url=url)
    if _llm_failed(res):
        todos = len(data.get("todos", []))
        drift_items = len(data.get("drift_items", []))
        stats = data.get("stats", {})
        total_public = stats.get("total_public_symbols", 0)
        with_docs = stats.get("symbols_with_docstrings", 0)
        missing_docs = total_public - with_docs
        return (
            f"⚠️ [LLM unavailable — heuristic summary] "
            f"Found {todos} TODO/FIXME marker(s), "
            f"{missing_docs} undocumented public symbol(s), "
            f"and {drift_items} documentation drift point(s)."
        )
    return res
