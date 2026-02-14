import json
import os
import re
import uuid
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .cache import TTLCache
from .prompts import (
    AMBIGUITY_SYSTEM,
    AMBIGUITY_USER_TEMPLATE,
    INVENTORY_SYSTEM,
    INVENTORY_USER_TEMPLATE,
    ITER_FOCUSED_SYSTEM,
    ITER_FOCUSED_USER_TEMPLATE,
    ONEPASS_SYSTEM,
    ONEPASS_USER_TEMPLATE,
)
from .schemas import (
    Ambiguity,
    Inventory,
    IterChooseResponse,
    IterStartResponse,
    OnePassResponse,
)

load_dotenv()
MODEL = os.getenv("MODEL", "gpt-4.1-mini")

client = OpenAI()
cache = TTLCache(ttl_seconds=1800)

# session store for iterative mode
sessions: dict[
    str, dict[str, Any]
] = {}  # {session_id: {"inventory": Inventory, "question": str, "ambiguity": Ambiguity}}


def _extract_json(text: str) -> str:
    """Extract a JSON object from model output that may contain markdown/extra text."""
    text = (text or "").strip()
    if not text:
        return ""

    # ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()

    # first {...} block
    m2 = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m2:
        return m2.group(1).strip()

    return ""


def _debug_preview(s: str, n: int = 600) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n] + "\n...[truncated]..."


def _chat_with_image_json(
    system: str, user: str, image_data_url: str, temperature: float = 0.2
) -> dict:
    """Call VLM and force JSON parsing robustly:
    - strips markdown fences
    - extracts first JSON object
    - retries once with stricter instruction
    """
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system
                + "\nReturn ONLY valid JSON. No markdown, no commentary.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            },
        ],
        temperature=temperature,
    )

    raw = resp.choices[0].message.content or ""
    json_str = _extract_json(raw)

    if not json_str:
        # retry once, stricter + deterministic
        resp2 = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system
                    + "\nReturn ONLY valid JSON. No markdown, no commentary.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user + "\n\nReturn ONLY JSON.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                    ],
                },
            ],
            temperature=0.0,
        )
        raw2 = resp2.choices[0].message.content or ""
        json_str = _extract_json(raw2)
        if not json_str:
            raise ValueError(
                "Model did not return JSON.\n\n"
                f"First try output:\n{_debug_preview(raw)}\n\n"
                f"Second try output:\n{_debug_preview(raw2)}"
            )

    try:
        return json.loads(json_str)
    except Exception as e:
        raise ValueError(
            "Failed to parse JSON from model output.\n\n"
            f"Extracted JSON:\n{_debug_preview(json_str)}\n\n"
            f"Raw output:\n{_debug_preview(raw)}"
        ) from e


def _chat_json(system: str, user: str, temperature: float = 0.0) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return json.loads(resp.choices[0].message.content)


def _chat_text(system: str, user: str, temperature: float = 0.2) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content


def build_inventory(
    image_data_url: str, question: str, cache_key: str | None = None
) -> Inventory:
    if cache_key:
        hit = cache.get(f"inv:{cache_key}")
        if hit:
            return Inventory.model_validate(hit)

    user = INVENTORY_USER_TEMPLATE.format(question=question)
    data = _chat_with_image_json(
        INVENTORY_SYSTEM, user, image_data_url, temperature=0.1
    )

    inv = Inventory(**data)

    if cache_key:
        cache.set(f"inv:{cache_key}", inv.model_dump())
    return inv


def detect_ambiguity(
    question: str, inv: Inventory, cache_key: str | None = None
) -> Ambiguity:
    if cache_key:
        hit = cache.get(f"amb:{cache_key}:{question}")
        if hit:
            return Ambiguity.model_validate(hit)

    object_names = sorted({o.name for o in inv.objects if o.name})
    user = AMBIGUITY_USER_TEMPLATE.format(
        question=question, object_names=object_names
    )

    data = _chat_json(AMBIGUITY_SYSTEM, user, temperature=0.0)
    amb = Ambiguity(**data)

    if cache_key:
        cache.set(f"amb:{cache_key}:{question}", amb.model_dump())
    return amb


def one_pass(
    image_data_url: str, question: str, cache_key: str | None = None
) -> OnePassResponse:
    inv = build_inventory(image_data_url, question, cache_key=cache_key)
    amb = detect_ambiguity(question, inv, cache_key=cache_key)

    prompt = ONEPASS_USER_TEMPLATE.format(
        inventory_json=inv.model_dump_json(indent=2),
        ambiguity_json=amb.model_dump_json(indent=2),
        question=question,
    )
    ans = _chat_text(ONEPASS_SYSTEM, prompt, temperature=0.2)
    return OnePassResponse(inventory=inv, ambiguity=amb, answer=ans)


def scene_only(
    image_data_url: str, question: str, cache_key: str | None = None
) -> tuple[Inventory, Ambiguity]:
    inv = build_inventory(image_data_url, question, cache_key=cache_key)
    amb = detect_ambiguity(question, inv, cache_key=cache_key)
    return inv, amb


def iter_start(
    image_data_url: str, question: str, cache_key: str | None = None
) -> IterStartResponse:
    inv, amb = scene_only(image_data_url, question, cache_key=cache_key)

    # brief summary for turn 1
    brief_items = []
    for o in inv.objects[:8]:
        c = o.count if o.count is not None else "some"
        brief_items.append(f"{c} {o.name} ({o.location})")
    inventory_brief = (
        "; ".join(brief_items)
        if brief_items
        else "I couldn't confidently detect objects."
    )

    if amb.ambiguous and amb.candidates:
        options = amb.candidates[:6]
        clarification_question = (
            "I found multiple possible targets for your question. "
            f"Which one do you mean: {', '.join(options)}?"
        )
    else:
        # still provide options: user may want details anyway
        all_names = sorted({o.name for o in inv.objects if o.name})
        options = all_names[:6]
        clarification_question = (
            "I don't detect strong ambiguity, but I can describe a specific object in more detail. "
            "Which one would you like?"
        )

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "inventory": inv.model_dump(),
        "question": question,
        "ambiguity": amb.model_dump(),
    }

    return IterStartResponse(
        session_id=session_id,
        inventory_brief=inventory_brief,
        ambiguity=amb,
        clarification_question=clarification_question,
        options=options,
    )


def iter_choose(session_id: str, chosen: str) -> IterChooseResponse:
    if session_id not in sessions:
        return IterChooseResponse(
            focused_answer="Session expired or not found. Please start again.",
            followup_suggestions=[],
            updated_state={"error": "session_not_found"},
        )
    state = sessions[session_id]
    inv = Inventory.model_validate(state["inventory"])
    question = state["question"]

    prompt = ITER_FOCUSED_USER_TEMPLATE.format(
        question=question,
        chosen=chosen,
        inventory_json=inv.model_dump_json(indent=2),
    )
    text = _chat_text(ITER_FOCUSED_SYSTEM, prompt, temperature=0.2)

    updated = {"session_id": session_id, "chosen": chosen}
    return IterChooseResponse(
        focused_answer=text,
        followup_suggestions=[
            "Ask about its color/material",
            "Ask where it is relative to other objects",
            "Ask what text is visible",
            "Ask how many instances there are",
        ],
        updated_state=updated,
    )
