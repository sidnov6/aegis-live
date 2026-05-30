"""LLM SAR drafting (Part 8) — the GenAI layer, used right.

Feeds the explained subgraph + screening hit + features to an LLM (via LiteLLM:
Groq/Gemini/Ollama) that drafts a structured Suspicious Activity Report narrative
grounded STRICTLY in the detected facts (Part 10.5 determinism boundary — the LLM
narrates, it never invents figures). Graceful degradation: no model / quota hit
=> a deterministic template SAR (Part 10.8).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..conf.settings import settings
from ..schema import Alert

log = logging.getLogger("aegis.sar")

# Last LLM failure reason (surfaced via /api/health for diagnostics).
LAST_ERROR: str = ""

_SYSTEM = (
    "You are an AML analyst drafting a Suspicious Activity Report (SAR) narrative "
    "for a crypto transaction monitoring system. Write a concise, professional, "
    "structured narrative. CRITICAL: use ONLY the facts provided. Do not invent "
    "amounts, names, dates, or addresses. If a detail is not provided, omit it. "
    "State explicitly that the risk determination is an automated prediction "
    "pending human review (except sanctions exact-hits, which are designations)."
)


def _facts_block(alert: Alert, facts: dict) -> str:
    f = facts.get("features", {})
    return (
        f"Subject address: {alert.address}\n"
        f"Chain: {alert.chain}\n"
        f"Transaction: {alert.txid}\n"
        f"Risk score: {alert.risk:.2f} (level: {alert.level})\n"
        f"Trigger reason: {alert.reason}\n"
        f"Subgraph size: {len(facts.get('subgraph', {}).get('nodes', []))} addresses, "
        f"{len(facts.get('subgraph', {}).get('edges', []))} transfers\n"
        f"Key features: fan-out_max={f.get('max_out_deg')}, fan-in_max={f.get('max_in_deg')}, "
        f"value={f.get('value')}, pass_through={f.get('pass_through')}\n"
        f"Detected at: {datetime.now(timezone.utc).isoformat()}"
    )


def _template_sar(alert: Alert, facts: dict) -> str:
    confirmed = alert.level == "sanctioned" and "Direct match" in alert.reason
    basis = (
        "This determination is based on a sanctions/known-illicit list designation."
        if confirmed
        else "This is an automated risk prediction pending human analyst review; "
        "it does not assert confirmed money laundering."
    )
    return (
        f"SUSPICIOUS ACTIVITY REPORT (DRAFT)\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"1. SUBJECT\n"
        f"   Address: {alert.address} (chain: {alert.chain})\n\n"
        f"2. ACTIVITY\n"
        f"   Transaction {alert.txid} was flagged by automated transaction "
        f"monitoring. Trigger: {alert.reason}. Assigned risk level: "
        f"{alert.level} (score {alert.risk:.2f}).\n\n"
        f"3. PATTERN\n"
        f"   The triggering subgraph comprises "
        f"{len(facts.get('subgraph', {}).get('nodes', []))} addresses and "
        f"{len(facts.get('subgraph', {}).get('edges', []))} transfers in the "
        f"current monitoring window.\n\n"
        f"4. BASIS\n   {basis}\n\n"
        f"5. RECOMMENDATION\n"
        f"   Refer to a human analyst for review prior to any regulatory filing."
    )


def draft_sar(alert: Alert, facts: dict) -> tuple[str, str]:
    """Returns (sar_text, source). Falls back to template on any failure."""
    if not settings.sar_model:
        return _template_sar(alert, facts), "template"
    try:
        from litellm import completion

        resp = completion(
            model=settings.sar_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": "Draft a SAR from these facts only:\n\n"
                 + _facts_block(alert, facts)},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        text = resp["choices"][0]["message"]["content"].strip()
        global LAST_ERROR
        LAST_ERROR = ""
        return text, f"llm:{settings.sar_model}"
    except Exception as e:  # noqa: BLE001
        globals()["LAST_ERROR"] = f"{type(e).__name__}: {e}"
        log.warning("SAR LLM failed (%s) — template fallback", e)
        return _template_sar(alert, facts), "template"
