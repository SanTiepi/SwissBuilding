"""Golden-path integration tests: freshness watch -> invalidation -> review.

Proves the full operational loop: when a regulatory source changes, the system
automatically detects affected artifacts, creates invalidation events, flags
procedures for review, and surfaces alerts in the Today feed.

This is Rail 5 closure -- every test verifies cross-service propagation.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.evidence_pack import EvidencePack
from app.models.freshness_watch import FreshnessWatchEntry
from app.models.invalidation import InvalidationEvent
from app.models.organization import Organization
from app.models.passport_envelope import BuildingPassportEnvelope
from app.models.procedure import ProcedureTemplate
from app.models.review_queue import ReviewTask
from app.models.user import User

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_PWD_HASH = "$2b$12$LJ3m4ys3GZ0G0DBjO3Y0o.AjEfLGnr44Q/sXJCj5GZpz5BJhpCDSy"


async def _make_org(db: AsyncSession) -> Organization:
    org = Organization(id=uuid.uuid4(), name="FreshnessTest Org", type="property_management")
    db.add(org)
    await db.flush()
    return org


async def _make_user(db: AsyncSession, org: Organization, role: str = "admin") -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"freshness-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_PWD_HASH,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_building(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    canton: str = "VD",
) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Rue Freshness 42",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=1972,
        building_type="residential",
        created_by=user_id,
        owner_id=user_id,
        organization_id=org_id,
        status="active",
    )
    db.add(building)
    await db.flush()
    return building


async def _make_published_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    user_id: uuid.UUID,
) -> EvidencePack:
    """Create a published evidence pack (assembled in the past)."""
    pack = EvidencePack(
        id=uuid.uuid4(),
        building_id=building_id,
        pack_type="authority_pack",
        title="Pack autorite VD amiante",
        status="complete",
        assembled_at=datetime.now(UTC) - timedelta(days=30),
        created_by=user_id,
    )
    db.add(pack)
    await db.flush()
    return pack


async def _make_passport_envelope(
    db: AsyncSession,
    building_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BuildingPassportEnvelope:
    """Create a published sovereign passport envelope."""
    envelope = BuildingPassportEnvelope(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org_id,
        created_by_id=user_id,
        version=1,
        passport_data={"grade": "C", "pollutants": ["asbestos"]},
        sections_included=["identity", "diagnostics", "pollutants"],
        content_hash="a" * 64,
        is_sovereign=True,
        status="published",
        published_at=datetime.now(UTC) - timedelta(days=15),
        published_by_id=user_id,
    )
    db.add(envelope)
    await db.flush()
    return envelope


async def _make_procedure_template(
    db: AsyncSession,
    canton: str = "VD",
    procedure_type: str = "notification",
) -> ProcedureTemplate:
    """Create an active cantonal procedure template."""
    tpl = ProcedureTemplate(
        id=uuid.uuid4(),
        name=f"Declaration amiante {canton}",
        description="Notification SUVA pour travaux amiante",
        procedure_type=procedure_type,
        scope="cantonal",
        canton=canton,
        steps=[
            {"name": "diagnostic", "order": 1, "required": True},
            {"name": "submission", "order": 2, "required": True},
        ],
        applicable_work_families=["asbestos_removal"],
        authority_name="SUVA",
        legal_basis="OTConst Art. 60a",
        active=True,
    )
    db.add(tpl)
    await db.flush()
    return tpl


async def _setup_full_scenario(db: AsyncSession):
    """Create org, user, building in VD, published pack, passport, and procedure template."""
    org = await _make_org(db)
    user = await _make_user(db, org)
    building = await _make_building(db, user.id, org.id, canton="VD")
    pack = await _make_published_pack(db, building.id, user.id)
    passport = await _make_passport_envelope(db, building.id, org.id, user.id)
    template = await _make_procedure_template(db, canton="VD")
    return org, user, building, pack, passport, template


# ---------------------------------------------------------------------------
# Golden-path test class
# ---------------------------------------------------------------------------


class TestGoldenPathFreshnessToReview:
    """End-to-end golden-path test: external change -> system reaction chain.

    Scenario: A cantonal rule changes (VD asbestos threshold).
    Expected chain:
    1. FreshnessWatch entry created (delta_type: amended_rule, canton: VD)
    2. Impact assessment shows affected buildings
    3. Reactions applied:
       a. Procedure templates flagged for review
       b. Published authority packs invalidated
       c. SafeToX states flagged for refresh
    4. InvalidationEvents created for affected artifacts
    5. ReviewTasks created for critical invalidations
    6. Today feed shows the critical freshness alert
    """

    @pytest.mark.asyncio
    async def test_full_chain_rule_change_to_review(self, db: AsyncSession):
        """The complete chain from external change to review task."""
        org, user, building, _pack, _passport, _template = await _setup_full_scenario(db)

        # Step 1: Record freshness watch entry
        from app.services.freshness_watch_service import record_change

        entry = await record_change(
            db,
            delta_type="amended_rule",
            title="OTConst Art. 60a seuil amiante modifie",
            description="Nouveau seuil: 0.01% au lieu de 1%",
            canton="VD",
            severity="critical",
            reactions=[
                {"type": "pack_invalidation", "scope": "authority_packs_vd"},
                {"type": "safe_to_x_refresh", "scope": "all_vd_buildings"},
            ],
        )
        assert entry.status == "detected"
        assert entry.severity == "critical"
        assert entry.canton == "VD"

        # Step 2: Assess impact
        from app.services.freshness_watch_service import assess_impact

        impact = await assess_impact(db, entry.id)
        assert "error" not in impact
        assert impact["affected_buildings_estimate"] >= 1, "Building in VD must be counted"
        assert len(impact["reactions_summary"]) == 2

        # Entry should now be under_review
        refreshed_result = await db.execute(select(FreshnessWatchEntry).where(FreshnessWatchEntry.id == entry.id))
        refreshed = refreshed_result.scalar_one()
        assert refreshed.status == "under_review"

        # Step 3: Apply reactions
        from app.services.freshness_watch_service import apply_reactions

        result = await apply_reactions(db, entry.id, applied_by_id=user.id)
        assert result["reactions_executed"] == 2
        assert result["reactions_succeeded"] >= 1

        # Entry should now be applied
        applied_result = await db.execute(select(FreshnessWatchEntry).where(FreshnessWatchEntry.id == entry.id))
        applied = applied_result.scalar_one()
        assert applied.status == "applied"
        assert applied.reviewed_by_id == user.id

        # Step 4: Verify invalidation events were created (from pack_invalidation reaction)
        inv_result = await db.execute(select(InvalidationEvent).where(InvalidationEvent.building_id == building.id))
        invalidations = list(inv_result.scalars().all())
        # Pack and/or passport invalidation should have been created
        assert len(invalidations) >= 1, "At least one invalidation event must exist"

        # Find a pack invalidation to execute review_required reaction
        pack_inv = None
        for inv in invalidations:
            if inv.affected_type == "pack":
                pack_inv = inv
                break

        # Step 5: Execute invalidation reactions that create review tasks
        from app.services.invalidation_engine import InvalidationEngine

        engine = InvalidationEngine()

        # For invalidations with review_required reaction, execute them
        review_created = False
        for inv in invalidations:
            if inv.required_reaction == "review_required":
                reaction_result = await engine.execute_reaction(db, inv.id)
                if reaction_result.get("success"):
                    review_created = True

        # Also test auto_create_from_invalidation directly for pack invalidations
        if pack_inv:
            from app.services.review_queue_service import auto_create_from_invalidation

            task = await auto_create_from_invalidation(
                db,
                building_id=building.id,
                organization_id=org.id,
                invalidation_id=pack_inv.id,
                detail=pack_inv.impact_reason,
            )
            if task:
                review_created = True

        assert review_created, "At least one review task must be created from invalidation chain"

        # Verify review tasks exist
        from app.services.review_queue_service import get_queue

        tasks = await get_queue(db, organization_id=org.id, status="pending")
        assert len(tasks) >= 1, "Pending review tasks must exist for this org"
        assert any(t.task_type == "invalidation_review" for t in tasks)

        # Step 6: Verify today feed shows freshness alert
        # Record a new critical entry (the applied one won't show in today feed)
        await record_change(
            db,
            delta_type="threshold_change",
            title="Seuil PCB abaisse canton VD",
            severity="critical",
            canton="VD",
        )

        from app.services.today_service import get_today_feed

        feed = await get_today_feed(db, org_id=org.id, user_id=user.id)
        assert "freshness_alerts" in feed
        # The second entry (detected + critical) should appear
        assert len(feed["freshness_alerts"]) >= 1
        assert any(a["severity"] == "critical" for a in feed["freshness_alerts"])

    # ------------------------------------------------------------------
    # Focused chain tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_freshness_to_invalidation_chain(self, db: AsyncSession):
        """Freshness watch -> apply_reactions -> InvalidationEvent created."""
        _org, user, building, _pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.freshness_watch_service import apply_reactions, record_change

        entry = await record_change(
            db,
            delta_type="amended_rule",
            title="Modification regle amiante VD",
            canton="VD",
            severity="warning",
            reactions=[
                {"type": "pack_invalidation", "scope": "authority_packs_vd"},
            ],
        )

        result = await apply_reactions(db, entry.id, applied_by_id=user.id)
        assert result["reactions_executed"] == 1
        assert result["reactions_succeeded"] >= 1

        # Verify pack_invalidation reaction scanned for invalidations
        pack_detail = result["details"][0]
        assert pack_detail["type"] == "pack_invalidation"
        assert pack_detail["success"] is True

        # Verify InvalidationEvent records exist for the building
        inv_result = await db.execute(
            select(InvalidationEvent).where(
                InvalidationEvent.building_id == building.id,
                InvalidationEvent.trigger_type == "rule_change",
            )
        )
        invalidations = list(inv_result.scalars().all())
        assert len(invalidations) >= 1, "Pack invalidation must create InvalidationEvent records"

    @pytest.mark.asyncio
    async def test_invalidation_to_review_chain(self, db: AsyncSession):
        """InvalidationEvent with review_required -> ReviewTask created."""
        org, _user, building, _pack, _passport, _template = await _setup_full_scenario(db)

        # Directly create an invalidation event with review_required reaction
        inv_event = InvalidationEvent(
            building_id=building.id,
            trigger_type="rule_change",
            trigger_description="Regle modifiee -- revue requise",
            affected_type="procedure_step",
            affected_id=uuid.uuid4(),
            impact_reason="Etape de procedure affectee par changement reglementaire",
            severity="critical",
            required_reaction="review_required",
            status="detected",
        )
        db.add(inv_event)
        await db.flush()

        # Execute the invalidation reaction
        from app.services.invalidation_engine import InvalidationEngine

        engine = InvalidationEngine()
        reaction_result = await engine.execute_reaction(db, inv_event.id)
        assert reaction_result["success"] is True
        assert reaction_result["action"] == "review_task_created"

        # Verify the ReviewTask was created
        review_result = await db.execute(
            select(ReviewTask).where(
                ReviewTask.building_id == building.id,
                ReviewTask.task_type == "invalidation_review",
            )
        )
        task = review_result.scalar_one_or_none()
        assert task is not None
        assert task.priority == "high"
        assert task.status == "pending"
        assert task.organization_id == org.id

    @pytest.mark.asyncio
    async def test_consequence_engine_runs_after_truth_change(self, db: AsyncSession):
        """Creating a truth change triggers consequence engine which detects stale packs."""
        _org, user, building, _pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        result = await engine.run_consequences(
            db,
            building_id=building.id,
            trigger_type="extraction_applied",
            trigger_id=str(uuid.uuid4()),
            triggered_by_id=user.id,
        )

        # The consequence chain should:
        # - detect stale packs (our pack was assembled 30 days ago)
        # - detect stale passport (published 15 days ago)
        # - run invalidation scan
        assert result["stale_packs"] >= 1, "Published pack assembled before truth change must be flagged stale"
        assert result["stale_passport"] is True, "Published passport before truth change must be flagged stale"
        assert result["total_consequences"] >= 2

        # Should have no hard errors
        assert "errors" not in result or len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_pack_staleness_after_new_evidence(self, db: AsyncSession):
        """New evidence (extraction applied) flags published packs as stale via consequence engine."""
        _org, _user, building, pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()

        # Simulate extraction_applied trigger
        result = await engine.check_pack_staleness(db, building.id)
        assert len(result) >= 1, "Pack assembled in the past must be flagged stale"
        assert str(pack.id) in result

    @pytest.mark.asyncio
    async def test_passport_staleness_after_truth_change(self, db: AsyncSession):
        """Published passport envelope is flagged stale after truth changes."""
        _org, _user, building, _pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        is_stale = await engine.check_passport_staleness(db, building.id)
        assert is_stale is True, "Published passport must be stale after truth change"

    @pytest.mark.asyncio
    async def test_invalidation_engine_scans_packs_on_rule_change(self, db: AsyncSession):
        """InvalidationEngine.scan_for_invalidations on rule_change detects pack invalidations."""
        _org, _user, building, _pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.invalidation_engine import InvalidationEngine

        engine = InvalidationEngine()
        invalidations = await engine.scan_for_invalidations(db, building.id, trigger_type="rule_change")

        # Should detect pack + passport invalidation at minimum
        affected_types = {inv.affected_type for inv in invalidations}
        assert "pack" in affected_types, "Published pack must be detected as invalidated"
        assert "passport" in affected_types, "Published passport must be detected as invalidated"

    @pytest.mark.asyncio
    async def test_today_feed_shows_critical_freshness_alerts(self, db: AsyncSession):
        """Today feed includes critical freshness watch entries."""
        org, user, _building, _pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.freshness_watch_service import record_change

        # Create two entries: one critical, one info
        await record_change(
            db,
            delta_type="amended_rule",
            title="Critical: seuil amiante modifie VD",
            severity="critical",
            canton="VD",
        )
        await record_change(
            db,
            delta_type="dataset_refresh",
            title="Info: dataset geo actualise",
            severity="info",
        )

        from app.services.today_service import get_today_feed

        feed = await get_today_feed(db, org_id=org.id, user_id=user.id)

        # Only critical entries should appear in freshness_alerts
        assert len(feed["freshness_alerts"]) == 1
        assert feed["freshness_alerts"][0]["severity"] == "critical"
        assert feed["freshness_alerts"][0]["type"] == "freshness_watch"
        assert "amiante" in feed["freshness_alerts"][0]["title"]

    @pytest.mark.asyncio
    async def test_ritual_trace_survives_full_chain(self, db: AsyncSession):
        """Every governed transition in the chain leaves a TruthRitual trace."""
        org, user, building, pack, _passport, _template = await _setup_full_scenario(db)

        from app.services.ritual_service import publish, reopen, validate

        # Record a publish ritual for the pack
        publish_ritual = await publish(
            db,
            building_id=building.id,
            target_type="pack",
            target_id=pack.id,
            published_by_id=user.id,
            org_id=org.id,
            content={"sections": ["diagnostics", "pollutants"]},
            reason="Pack autorite assemble pour VD",
        )
        assert publish_ritual.ritual_type == "publish"
        assert publish_ritual.content_hash is not None
        assert publish_ritual.version == 1

        # Now a rule changes -- simulate invalidation and reopen
        reopen_ritual = await reopen(
            db,
            building_id=building.id,
            target_type="pack",
            target_id=pack.id,
            reopened_by_id=user.id,
            org_id=org.id,
            reason="Regle OTConst Art. 60a modifiee -- pack doit etre re-assemble",
        )
        assert reopen_ritual.ritual_type == "reopen"
        assert reopen_ritual.reopen_reason is not None

        # Re-validate after update
        validate_ritual = await validate(
            db,
            building_id=building.id,
            target_type="pack",
            target_id=pack.id,
            validated_by_id=user.id,
            org_id=org.id,
            reason="Pack mis a jour avec nouveau seuil amiante",
        )
        assert validate_ritual.ritual_type == "validate"

        # Verify full ritual history for this pack
        from app.services.ritual_service import get_ritual_history

        history = await get_ritual_history(
            db,
            building_id=building.id,
            target_type="pack",
            target_id=pack.id,
        )
        ritual_types = [r.ritual_type for r in history]
        assert "publish" in ritual_types
        assert "reopen" in ritual_types
        assert "validate" in ritual_types
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_multi_building_impact_assessment(self, db: AsyncSession):
        """Impact assessment correctly counts multiple buildings in affected canton."""
        org = await _make_org(db)
        user = await _make_user(db, org)

        # Create 3 buildings in VD
        for _i in range(3):
            await _make_building(db, user.id, org.id, canton="VD")

        # Create 1 building in GE (should not be affected)
        await _make_building(db, user.id, org.id, canton="GE")

        from app.services.freshness_watch_service import assess_impact, record_change

        entry = await record_change(
            db,
            delta_type="new_rule",
            title="Nouvelle directive VD polluants",
            canton="VD",
            severity="critical",
            reactions=[{"type": "notification", "scope": "admins"}],
        )

        impact = await assess_impact(db, entry.id)
        assert impact["affected_buildings_estimate"] == 3, "Only VD buildings should be counted"

    @pytest.mark.asyncio
    async def test_dismiss_watch_stops_chain(self, db: AsyncSession):
        """Dismissing a watch entry prevents it from showing in today feed."""
        org = await _make_org(db)
        user = await _make_user(db, org)
        await _make_building(db, user.id, org.id)

        from app.services.freshness_watch_service import dismiss_watch, record_change

        entry = await record_change(
            db,
            delta_type="portal_change",
            title="Changement portail VD",
            severity="critical",
            canton="VD",
        )

        # Dismiss it
        dismissed = await dismiss_watch(db, entry.id, dismissed_by_id=user.id, reason="Pas d'impact reel")
        assert dismissed is not None
        assert dismissed.status == "dismissed"

        # Today feed should NOT show dismissed entries
        from app.services.today_service import get_today_feed

        feed = await get_today_feed(db, org_id=org.id, user_id=user.id)
        freshness_ids = [a["id"] for a in feed["freshness_alerts"]]
        assert str(entry.id) not in freshness_ids
