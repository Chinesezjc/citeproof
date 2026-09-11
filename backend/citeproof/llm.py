"""Client for the language-model step of the audit.

The model is asked one narrow question: given a sentence from the document that
cites an authority, and passages taken from that authority, does the authority
support the proposition the sentence asserts? The prompt requires the model to
answer from the supplied passages only and to answer ``unknown`` when they are
insufficient, so the check cannot substitute its own recollection of the law for
evidence from the source.

Any OpenAI-compatible ``/chat/completions`` endpoint works.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .normalize import normalize_quote
from .schemas import FidelityCheck, SupportLevel

_SYSTEM_PROMPT = """You review legal citations. You are given one sentence from a \
document and passages taken from the authority that sentence cites. Decide only \
whether the passages support the proposition the sentence asserts about that \
authority.

Rules:
- Judge only from the supplied passages. Do not use your own recollection of the \
case or the law, even if you believe you know it.
- Answer "unknown" when the passages do not contain enough information to decide. \
An "unknown" answer is preferred over a guess.
- "contradicted" means the passages state the opposite of the proposition.
- "not_supported" means the passages address the topic but do not support the \
proposition.
- "partial" means the passages support part of the proposition but not all of it.

Reply with a single JSON object and nothing else, using these keys:
{"support": "supported" | "partial" | "not_supported" | "contradicted" | "unknown",
 "confidence": a number between 0 and 1,
 "rationale": one or two sentences explaining the decision,
 "passage": the exact sentence from the supplied passages that decides the answer, or "" }"""

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_VALID_SUPPORT = {level.value for level in SupportLevel}


class LLMError(RuntimeError):
    """Raised when the model endpoint cannot be reached or returns unusable output."""


@dataclass
class LLMClient:
    """Minimal JSON-mode chat client."""

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout: float = 90.0
    max_tokens: int = 700

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def complete_json(self, user_prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise LLMError("no language-model API key is configured")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self._endpoint(), headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"transport error contacting the model endpoint: {exc}") from exc

        if response.status_code >= 400:
            raise LLMError(f"model endpoint returned HTTP {response.status_code}: {response.text[:200]}")

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMError("model endpoint returned a non-JSON response") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("model response had no message content") from exc

        return _parse_json_object(content)

    def assess_support(
        self,
        sentence: str,
        case_name: str | None,
        passage: str | None,
        citation: str | None = None,
    ) -> FidelityCheck:
        """Ask whether the cited authority supports the proposition in ``sentence``."""

        if not passage or not passage.strip():
            return FidelityCheck(
                support=SupportLevel.UNKNOWN,
                rationale="No passage from the cited authority was available to review.",
                model=self.model,
            )

        prompt = (
            f"SENTENCE FROM THE DOCUMENT:\n{sentence.strip()}\n\n"
            f"AUTHORITY CITED BY THAT SENTENCE:\n{case_name or 'unknown'}"
            f"{f' ({citation})' if citation else ''}\n\n"
            f"PASSAGES FROM THAT AUTHORITY:\n{passage.strip()}\n\n"
            "Does the authority support the proposition asserted in the sentence?"
        )
        try:
            result = self.complete_json(prompt)
        except LLMError as exc:
            return FidelityCheck(
                support=SupportLevel.UNKNOWN,
                rationale=f"The support check could not be completed: {exc}",
                model=self.model,
            )

        raw_support = str(result.get("support", "")).strip().lower().replace(" ", "_")
        support = (
            SupportLevel(raw_support) if raw_support in _VALID_SUPPORT else SupportLevel.UNKNOWN
        )
        confidence: float | None = None
        try:
            confidence = max(0.0, min(1.0, float(result.get("confidence"))))
        except (TypeError, ValueError):
            confidence = None

        rationale = str(result.get("rationale") or "").strip() or None
        deciding = str(result.get("passage") or "").strip()
        if deciding and passage:
            # Only keep the model's quoted passage when it actually occurs in the
            # supplied text, so a fabricated phrase cannot be presented as evidence.
            if normalize_quote(deciding) and normalize_quote(deciding) in normalize_quote(passage):
                pass
            else:
                deciding = ""
        return FidelityCheck(
            support=support,
            confidence=confidence,
            rationale=rationale,
            model=self.model,
            passage=deciding or None,
        )


def _parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object out of a model reply, tolerating code fences."""

    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        if not match:
            raise LLMError("model reply contained no JSON object") from None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError(f"model reply was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("model reply was JSON but not an object")
    return parsed
