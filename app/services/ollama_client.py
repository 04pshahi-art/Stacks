"""Thin client for a locally running Ollama server (https://ollama.com).

The URL comes only from server configuration, never from user input, so this
can't be pointed at other machines by a visitor.
"""
import re

import requests
from flask import current_app

MAX_REPLY_CHARS = 1500

# Reasoning models (DeepSeek R1) write their thinking inside <think> tags first.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Drop the model's thinking so only the final answer is shown."""
    without_blocks = _THINK_BLOCK_RE.sub("", text)
    # A reply cut off mid-thought has an opening tag and no answer at all.
    return without_blocks.split("<think>", 1)[0].strip()


class AssistantUnavailable(Exception):
    """The local AI isn't running, is slow, or returned something unusable."""


def is_available() -> bool:
    if not current_app.config["AI_ENABLED"]:
        return False
    try:
        response = requests.get(f"{current_app.config['OLLAMA_URL']}/api/tags", timeout=1.5)
        return response.ok
    except requests.RequestException:
        return False


def chat(messages: list[dict[str, str]]) -> str:
    """Send a conversation to the local model and return its reply text."""
    if not current_app.config["AI_ENABLED"]:
        raise AssistantUnavailable("AI is switched off.")
    try:
        response = requests.post(
            f"{current_app.config['OLLAMA_URL']}/api/chat",
            json={
                "model": current_app.config["OLLAMA_MODEL"],
                "messages": messages,
                "stream": False,
                "think": False,  # ask reasoning models to skip the long thinking step
                "options": {
                    "temperature": 0.6,
                    "num_predict": current_app.config["OLLAMA_MAX_TOKENS"],
                },
            },
            timeout=current_app.config["OLLAMA_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        raise AssistantUnavailable(str(error)) from error

    reply = strip_reasoning(content)[:MAX_REPLY_CHARS]
    if not reply:
        raise AssistantUnavailable("Empty reply.")
    return reply
