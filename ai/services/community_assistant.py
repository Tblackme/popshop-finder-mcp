"""
Community AI Assistant — Vendor Atlas AI Services

Answers vendor/shopper questions about markets, pricing, products,
and events using knowledge of the platform and general market wisdom.

Requires AI_ASSISTANT_ENABLED=true and a valid Anthropic API key.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("vendor-atlas.ai.community_assistant")

SYSTEM_PROMPT = """You are the Vendor Atlas Community Assistant — a friendly, practical helper
for vendors, shoppers, and event organizers who use the Vendor Atlas platform.

You specialize in:
- Pop-up markets, craft fairs, and vendor events
- Booth setup, pricing strategy, and product display
- Finding good markets by category and location
- Application tips for getting into competitive events
- General advice for small creative businesses

Keep answers concise (2-4 sentences max unless a list is better).
Be warm, direct, and practical. Never make up specific event names or dates.
If you don't know something, say so briefly and suggest a helpful next step."""


@dataclass
class AssistantResponse:
    answer: str
    follow_up_prompts: list[str]


class CommunityAssistant:
    """AI Q&A assistant for the community page."""

    def ask(self, question: str, context: str = "") -> AssistantResponse:
        """Answer a community question. Returns rule-based fallback if AI unavailable."""
        try:
            import anthropic
            client = anthropic.Anthropic()

            user_content = question.strip()
            if context:
                user_content = f"[Context: {context.strip()}]\n\n{user_content}"

            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            answer = message.content[0].text.strip() if message.content else ""
            follow_ups = _generate_follow_ups(question)
            return AssistantResponse(answer=answer, follow_up_prompts=follow_ups)

        except Exception as exc:
            logger.warning("Community assistant error: %s", exc)
            return AssistantResponse(
                answer=_fallback_answer(question),
                follow_up_prompts=_generate_follow_ups(question),
            )


# ─── Helpers ──────────────────────────────────────────────────────────────────

_FALLBACK_ANSWERS = {
    "pric": "Pricing for pop-up vendors varies by category — handmade goods typically sell best between $15–$75, with clear price tags and a range of price points to capture impulse buyers.",
    "market": "To find the right markets, filter Discover by your vendor category and location. Prioritize events with 1,000+ foot traffic and booth fees under 10% of your expected revenue.",
    "booth": "A strong booth setup includes a clear focal point, vertical height (risers, shelves), and consistent branding. Arrive early and practice your layout at home first.",
    "apply": "When applying to events, lead with your best product photos and be specific about your category. Organizers love vendors who clearly describe what they sell and who they serve.",
    "sell": "Best-selling items at markets tend to be priced $10–$40, easy to understand at a glance, and work well as gifts. Bundles and tiered pricing can increase average order value.",
}

def _fallback_answer(question: str) -> str:
    q = question.lower()
    for key, answer in _FALLBACK_ANSWERS.items():
        if key in q:
            return answer
    return (
        "Great question! Browse the Discover page to find events in your area, "
        "and check the Community groups for vendor advice from fellow makers. "
        "The Profit Planner tool also helps estimate whether an event is worth the booth fee."
    )


def _generate_follow_ups(question: str) -> list[str]:
    q = question.lower()
    if "pric" in q or "fee" in q or "cost" in q:
        return ["How do I calculate booth ROI?", "What booth fees are typical for craft fairs?"]
    if "market" in q or "event" in q or "fair" in q:
        return ["How do I apply to a market?", "What makes a market worth attending?"]
    if "booth" in q or "display" in q or "setup" in q:
        return ["What signage works best?", "How much inventory should I bring?"]
    if "sell" in q or "product" in q or "item" in q:
        return ["What products sell best outdoors?", "How do I bundle products effectively?"]
    return ["What markets are best for my category?", "How do I improve my booth setup?"]
