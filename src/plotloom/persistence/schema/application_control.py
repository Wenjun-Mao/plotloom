from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class VideoPilotLedgerRow(Base):
    __tablename__ = "v2_video_pilot_ledger"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    limit_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
class VideoPilotLedgerEventRow(Base):
    __tablename__ = "v2_video_pilot_ledger_events"
    __table_args__ = (Index("ix_v2_video_pilot_ledger_events_ledger_created", "ledger_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ledger_id: Mapped[str] = mapped_column(ForeignKey("v2_video_pilot_ledger.id", ondelete="RESTRICT"), nullable=False)
    video_job_id: Mapped[str] = mapped_column(String(67), nullable=False)
    event: Mapped[str] = mapped_column(String(48), nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class ProviderSettingsRow(Base):
    __tablename__ = "v2_provider_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TextProviderProfileRow(Base):
    __tablename__ = "v2_text_provider_profiles"

    id: Mapped[str] = mapped_column(String(63), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    availability_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adapter_id: Mapped[str] = mapped_column(String(120), nullable=False, default="openai_compatible")
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderProfileSelectionRow(Base):
    __tablename__ = "v2_provider_profile_selection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_profile_id: Mapped[str] = mapped_column(
        ForeignKey("v2_text_provider_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
