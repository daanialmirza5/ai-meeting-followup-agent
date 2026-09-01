"""Turns a raw meeting transcript into structured decisions + action items via Groq
(OpenAI-compatible API, free tier, no card required) — using an open Llama model."""
import json
import os

from openai import OpenAI

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are an assistant that reads a meeting transcript and extracts every \
concrete decision and action item from it.

For each action item, identify:
- "task": a short, clear description of what needs to be done
- "owner": the person responsible, taken from the transcript. If genuinely no owner is \
mentioned or implied, use "Unassigned".
- "deadline": a specific date/time if one is mentioned or reasonably inferable from context \
(e.g. "by Friday", "next week"), otherwise null. If a relative date is given, resolve it \
against the transcript's own apparent context as best you can; if that's not possible, return \
the phrase as-is (e.g. "next Friday").
- "decision": the underlying decision or context this action item came from, in one sentence.

Only extract items that are genuine decisions or action items — not general discussion. If the \
transcript contains no clear decisions or action items, return an empty list.

Respond with strict JSON: {"items": [{"task": "...", "owner": "...", "deadline": "..." or null, \
"decision": "..."}]}"""


def _get_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("No GROQ_API_KEY configured.")
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def extract_action_items(transcript: str) -> list[dict]:
    """Calls the LLM once and returns a list of {task, owner, deadline, decision} dicts."""
    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    data = json.loads(content)
    items = data.get("items", [])
    if not isinstance(items, list):
        return []
    return items
