"""
DevHandoff — IBM watsonx.ai Connection Tester
==============================================
Quick diagnostic script to verify your IBM Cloud API Key and watsonx Project ID.

Run with:
    python test_ibm_connection.py
"""

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load .env if present
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file, override=True)
except ImportError:
    pass

import httpx

from backend.llm_client import (
    get_watsonx_api_key,
    get_watsonx_project_id,
    get_watsonx_url,
    get_watsonx_model_id,
    _get_iam_token,
    generate,
)


async def main() -> None:
    print("=" * 60)
    print("  DevHandoff — IBM watsonx.ai Credential Check")
    print("=" * 60)

    api_key = get_watsonx_api_key()
    project_id = get_watsonx_project_id()
    url = get_watsonx_url()
    model_id = get_watsonx_model_id()

    print(f"watsonx URL:       {url}")
    print(f"Model ID:          {model_id}")
    print(f"API Key present:   {'✅ Yes (' + api_key[:4] + '...' + api_key[-4:] + ')' if api_key else '❌ Missing'}")
    print(f"Project ID:        {'✅ ' + project_id if project_id else '❌ Missing'}")
    print("-" * 60)

    if not api_key:
        print("❌ Error: IBM Cloud API Key is not set.")
        print("   Set WATSONX_API_KEY in .env or run:")
        print("   set WATSONX_API_KEY=your_key  (Windows)")
        print("   export WATSONX_API_KEY=your_key  (Linux/macOS)")
        sys.exit(1)

    if not project_id:
        print("❌ Error: watsonx Project ID is not set.")
        print("   Set WATSONX_PROJECT_ID in .env or run:")
        print("   set WATSONX_PROJECT_ID=your_project_id  (Windows)")
        sys.exit(1)

    print("Step 1: Testing IBM Cloud IAM authentication...")
    try:
        token = await _get_iam_token(api_key)
        print("  ✅ IAM Token generated successfully! (IBM Cloud API Key is valid)")
    except httpx.HTTPStatusError as exc:
        print(f"  ❌ IAM Authentication failed with HTTP {exc.response.status_code}.")
        print("     Please check that your IBM Cloud API key is correct and not revoked.")
        sys.exit(1)
    except Exception as exc:
        print(f"  ❌ IAM Connection error: {exc}")
        sys.exit(1)

    print("\nStep 2: Testing watsonx.ai text generation...")
    test_prompt = "Say 'IBM watsonx.ai is connected to DevHandoff!' in one sentence."
    try:
        response = await generate(test_prompt, max_tokens=64)
        if response.startswith("⚠️"):
            print(f"  ❌ Text generation warning: {response}")
            sys.exit(1)
        print(f"  ✅ watsonx.ai responded successfully!")
        print(f"  Model output: {response.strip()}")
    except Exception as exc:
        print(f"  ❌ Error calling watsonx.ai: {exc}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 All checks passed! DevHandoff is ready to use IBM watsonx.ai.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
