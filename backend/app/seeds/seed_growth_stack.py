"""Seed data for Growth Stack (subscription changes, AI extraction logs)."""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_extraction_log import AIExtractionLog
from app.models.company_subscription import CompanySubscription
from app.models.subscription_change import SubscriptionChange


async def seed_growth_stack(db: AsyncSession) -> dict:
    """Seed growth stack data. Idempotent — checks before inserting."""
    stats = {"subscription_changes": 0, "ai_extraction_logs": 0}

    # Find an existing subscription to attach changes to
    sub_result = await db.execute(select(CompanySubscription).limit(1))
    sub = sub_result.scalar_one_or_none()

    if sub:
        # Check if already seeded
        existing = await db.execute(
            select(SubscriptionChange).where(SubscriptionChange.subscription_id == sub.id).limit(1)
        )
        if existing.scalar_one_or_none() is None:
            changes = [
                SubscriptionChange(
                    subscription_id=sub.id,
                    change_type="created",
                    new_plan=sub.plan_type,
                    reason="Initial subscription",
                    created_at=datetime.now(UTC) - timedelta(days=30),
                ),
                SubscriptionChange(
                    subscription_id=sub.id,
                    change_type="plan_changed",
                    old_plan="free_trial",
                    new_plan=sub.plan_type,
                    reason="Upgraded after trial",
                    created_at=datetime.now(UTC) - timedelta(days=15),
                ),
            ]
            for c in changes:
                db.add(c)
            stats["subscription_changes"] = 2

    # AI extraction logs
    existing_ext = await db.execute(select(AIExtractionLog).limit(1))
    if existing_ext.scalar_one_or_none() is None:
        logs = [
            AIExtractionLog(
                extraction_type="quote_pdf",
                source_filename="devis_amiante_2026.pdf",
                input_hash=hashlib.sha256(b"devis_amiante_2026.pdf").hexdigest(),
                output_data={
                    "scope_items": ["asbestos_removal", "waste_disposal"],
                    "exclusions": ["scaffolding"],
                    "timeline_weeks": 6,
                    "amount_chf": 45000,
                    "confidence_per_field": {"scope_items": 0.85, "amount_chf": 0.90},
                },
                confidence_score=0.87,
                ai_model="stub-v0",
                ambiguous_fields=[],
                unknown_fields=[],
                status="confirmed",
                confirmed_at=datetime.now(UTC) - timedelta(days=5),
            ),
            AIExtractionLog(
                extraction_type="completion_report",
                source_filename="rapport_fin_travaux.pdf",
                input_hash=hashlib.sha256(b"rapport_fin_travaux.pdf").hexdigest(),
                output_data={
                    "completed_items": ["asbestos_removal", "final_report"],
                    "residual_items": ["air_monitoring_post"],
                    "final_amount_chf": 43500,
                    "confidence_per_field": {"completed_items": 0.90, "final_amount_chf": 0.95},
                },
                confidence_score=0.92,
                ai_model="stub-v0",
                ambiguous_fields=[{"field": "residual_items", "reason": "Partial completion"}],
                unknown_fields=[],
                status="corrected",
                confirmed_at=datetime.now(UTC) - timedelta(days=2),
            ),
        ]
        for log in logs:
            db.add(log)
        stats["ai_extraction_logs"] = 2

    await db.flush()
    return stats
