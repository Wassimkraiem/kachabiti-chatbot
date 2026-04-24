#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.settings import get_settings
from app.infrastructure.ai.langsmith_integration import build_default_chat_prompt, configure_langsmith_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Push the default Kachabiti chat prompt to LangSmith so it can be edited in the Playground."
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Prompt name in LangSmith. Defaults to LANGSMITH_PROMPT_NAME or 'kachabiti-chat'.",
    )
    return parser


def main() -> int:
    settings = get_settings()
    configure_langsmith_environment(settings)

    prompt_name = (build_parser().parse_args().name or settings.langsmith_prompt_name or "kachabiti-chat").strip()
    if not settings.langsmith_api_key:
        print("Push failed: LANGSMITH_API_KEY is not configured.", file=sys.stderr)
        return 1

    try:
        from langsmith import Client
    except ModuleNotFoundError as exc:
        print("Push failed: langsmith is not installed in this environment.", file=sys.stderr)
        return 1

    client = Client()
    url = client.push_prompt(prompt_name, object=build_default_chat_prompt())
    print(f"Pushed prompt '{prompt_name}' to LangSmith.")
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
