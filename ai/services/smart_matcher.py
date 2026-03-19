"""
AI Smart Matcher — Vendor Atlas

Goes beyond the rule-based scoring algorithm to explain WHY an event is a
good or bad fit for a specific vendor, using natural language reasoning.

Enable with: AI_MATCHING_ENABLED=true + ANTHROPIC_API_KEY=sk-...
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class MatchResult:
    score: int                      # 0–100
    verdict: str                    # "strong fit" | "moderate fit" | "poor fit"
    reasons_for: list[str]          # why this event suits the vendor
    reasons_against: list[str]      # potential concerns
    recommendation: str             # 1-2 sentence summary


@dataclass
class RankedEvent:
    event_id: str
    event_title: str
    match: MatchResult


class SmartMatcher:
    """
    AI-powered vendor ↔ event compatibility analysis.

    This does NOT replace the existing score_event / rank_events_for_vendor
    MCP tools. It adds a natural-language explanation layer on top.

    Usage:
        matcher = SmartMatcher()
        result = await matcher.match_vendor_to_event(
            vendor={...},
            event={...},
        )
    """

    MODEL = "claude-haiku-4-5-20251001"

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise RuntimeError("Run: pip install anthropic") from e
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set.")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _call(self, system: str, user: str) -> str:
        client = self._get_client()
        msg = client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def match_vendor_to_event(
        self,
        *,
        vendor: dict,
        event: dict,
    ) -> MatchResult:
        """
        Analyze fit between one vendor and one event.

        vendor dict keys (all optional): name, category, products, price_range,
            typical_revenue, audience, location, bio
        event dict keys (all optional): title, type, location, date, booth_fee,
            expected_traffic, audience_type, categories, description
        """
        system = (
            "You are an expert advisor helping vendors decide which pop-up markets to attend. "
            "Analyze the vendor-event fit and return ONLY valid JSON with keys: "
            "score (int 0-100), verdict (string: 'strong fit'|'moderate fit'|'poor fit'), "
            "reasons_for (list of strings, max 3), "
            "reasons_against (list of strings, max 3), "
            "recommendation (string, 1-2 sentences)."
        )
        user = (
            f"VENDOR:\n{_dict_to_text(vendor)}\n\n"
            f"EVENT:\n{_dict_to_text(event)}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {})
        return MatchResult(
            score=int(data.get("score", 50)),
            verdict=data.get("verdict", "moderate fit"),
            reasons_for=data.get("reasons_for", []),
            reasons_against=data.get("reasons_against", []),
            recommendation=data.get("recommendation", ""),
        )

    def rank_events_for_vendor(
        self,
        *,
        vendor: dict,
        events: list[dict],
        top_n: int = 5,
    ) -> list[RankedEvent]:
        """
        Rank a list of events for a vendor and return top_n with explanations.
        Processes in one API call for efficiency.
        """
        if not events:
            return []

        events_text = "\n\n".join(
            f"EVENT {i+1} (id={e.get('id', i)}):\n{_dict_to_text(e)}"
            for i, e in enumerate(events[:20])  # cap at 20 to stay within token limits
        )
        system = (
            "You are an expert advisor ranking pop-up market opportunities for a vendor. "
            f"Return ONLY valid JSON: a list of the top {top_n} events, each with keys: "
            "event_id (string), score (int 0-100), verdict (string), "
            "reasons_for (list), reasons_against (list), recommendation (string)."
        )
        user = (
            f"VENDOR:\n{_dict_to_text(vendor)}\n\n"
            f"EVENTS TO RANK:\n{events_text}\n\n"
            f"Return the top {top_n} ranked by fit score."
        )
        raw = self._call(system, user)
        items = _parse_json_list(raw)
        result = []
        event_map = {str(e.get("id", i)): e for i, e in enumerate(events)}
        for item in items[:top_n]:
            eid = str(item.get("event_id", ""))
            ev = event_map.get(eid, {})
            result.append(RankedEvent(
                event_id=eid,
                event_title=ev.get("title", eid),
                match=MatchResult(
                    score=int(item.get("score", 50)),
                    verdict=item.get("verdict", "moderate fit"),
                    reasons_for=item.get("reasons_for", []),
                    reasons_against=item.get("reasons_against", []),
                    recommendation=item.get("recommendation", ""),
                ),
            ))
        return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _dict_to_text(d: dict) -> str:
    return "\n".join(f"  {k}: {v}" for k, v in d.items() if v)


def _parse_json(raw: str, fallback: dict) -> dict:
    import json, re
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except Exception:
        return fallback


def _parse_json_list(raw: str) -> list:
    import json, re
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(clean)
        return data if isinstance(data, list) else []
    except Exception:
        return []
