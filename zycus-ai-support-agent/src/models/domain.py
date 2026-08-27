"""Domain models for the raw supplied dataset (tickets, accounts).

These mirror DATA_SCHEMA.md exactly and are intentionally permissive
(`Optional` fields, `extra="ignore"`) since the dataset is treated as
untrusted external input that may have gaps.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class PrimaryContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    title: Optional[str] = None


class Ticket(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticket_id: str
    account_id: Optional[str] = None
    company: Optional[str] = None
    subject: str = ""
    body: str = ""
    product: Optional[str] = None
    product_area: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = None
    plan_tier: Optional[str] = None
    assigned_agent: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: list[str] = []
    channel: Optional[str] = None
    satisfaction_score: Optional[int] = None


class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str
    company: Optional[str] = None
    tam: Optional[str] = None
    plan_tier: Optional[str] = None
    arr_usd: Optional[int] = None
    seats_licensed: Optional[int] = None
    seats_active: Optional[int] = None
    products: list[str] = []
    health_status: Optional[str] = None
    usage_trend: Optional[str] = None
    open_tickets: Optional[int] = None
    p1_tickets_last_30d: Optional[int] = None
    customer_since: Optional[str] = None
    renewal_date: Optional[str] = None
    last_qbr_date: Optional[str] = None
    primary_contact: Optional[PrimaryContact] = None
    escalation_notes: list[str] = []
    nps_score: Optional[int] = None
    last_login_days_ago: Optional[int] = None
    integrations_active: list[str] = []
    region: Optional[str] = None
    industry: Optional[str] = None
