"""Alert rules CRUD API and alert history."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter(tags=["Alerts"])

# ── In-memory stores ────────────────────────────────────────────────────

_alert_rules: dict[str, dict] = {}
_alert_history: list[dict] = []  # last 100 alerts


def _init_default_rules() -> None:
    """Seed with default alert rules."""
    if _alert_rules:
        return
    defaults = [
        {
            "name": "No Mask Alert",
            "event_type": "no_mask",
            "conditions": {"confidence_min": 0.6},
            "channels": ["log"],
            "cooldown_seconds": 60,
            "is_active": True,
        },
        {
            "name": "Crowd Detection",
            "event_type": "crowd",
            "conditions": {"person_count_min": 10},
            "channels": ["log"],
            "cooldown_seconds": 120,
            "is_active": True,
        },
        {
            "name": "Aggressive Emotion",
            "event_type": "aggressive_emotion",
            "conditions": {"emotions": ["angry", "fear"], "confidence_min": 0.5},
            "channels": ["log"],
            "cooldown_seconds": 30,
            "is_active": True,
        },
    ]
    for rule in defaults:
        rid = str(uuid.uuid4())
        _alert_rules[rid] = {
            "id": rid,
            **rule,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


_init_default_rules()


def record_alert(alert_type: str, title: str, camera: str = "CAM 01") -> None:
    """Called by the alert dispatcher to log an alert into history."""
    entry = {
        "id": str(uuid.uuid4()),
        "type": "danger" if "no_mask" in alert_type.lower() else "warning",
        "title": title,
        "cam": camera,
        "time": datetime.now(timezone.utc).isoformat(),
        "rule_name": alert_type,
    }
    _alert_history.insert(0, entry)
    if len(_alert_history) > 100:
        _alert_history.pop()


# ── Schemas ─────────────────────────────────────────────────────────────

class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., pattern=r"^(no_mask|crowd|intrusion|aggressive_emotion|custom)$")
    conditions: dict = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["log"])
    cooldown_seconds: int = Field(60, ge=0, le=3600)
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    event_type: Optional[str] = None
    conditions: Optional[dict] = None
    channels: Optional[list[str]] = None
    cooldown_seconds: Optional[int] = Field(None, ge=0, le=3600)
    is_active: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    event_type: str
    conditions: dict
    channels: list[str]
    cooldown_seconds: int
    is_active: bool
    created_at: str | None = None


class AlertHistoryItem(BaseModel):
    id: str
    type: str
    title: str
    cam: str
    time: str
    rule_name: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/alerts/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules():
    """List all configured alert rules."""
    return list(_alert_rules.values())


@router.post("/alerts/rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(rule: AlertRuleCreate):
    """Create a new alert rule."""
    rid = str(uuid.uuid4())
    entry = {
        "id": rid,
        "name": rule.name,
        "event_type": rule.event_type,
        "conditions": rule.conditions,
        "channels": rule.channels,
        "cooldown_seconds": rule.cooldown_seconds,
        "is_active": rule.is_active,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _alert_rules[rid] = entry
    logger.info("alert_rule_created", rule_id=rid, name=rule.name)
    return entry


@router.put("/alerts/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: str, update: AlertRuleUpdate):
    """Update an existing alert rule."""
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    rule = _alert_rules[rule_id]
    for field in ("name", "event_type", "conditions", "channels", "cooldown_seconds", "is_active"):
        val = getattr(update, field, None)
        if val is not None:
            rule[field] = val
    logger.info("alert_rule_updated", rule_id=rule_id)
    return rule


@router.delete("/alerts/rules/{rule_id}", status_code=204)
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule."""
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    del _alert_rules[rule_id]
    logger.info("alert_rule_deleted", rule_id=rule_id)


@router.get("/alerts/history", response_model=list[AlertHistoryItem])
async def get_alert_history():
    """Get the last 100 triggered alerts."""
    return _alert_history
