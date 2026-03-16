import uuid

from app.models.jurisdiction import Jurisdiction
from app.models.regulatory_pack import RegulatoryPack


class TestJurisdictionModel:
    async def test_create_jurisdiction(self, db_session):
        j = Jurisdiction(
            id=uuid.uuid4(),
            code="ch",
            name="Suisse",
            level="country",
            country_code="CH",
            is_active=True,
        )
        db_session.add(j)
        await db_session.commit()
        await db_session.refresh(j)
        assert j.code == "ch"
        assert j.level == "country"
        assert j.country_code == "CH"
        assert j.is_active is True
        assert j.parent_id is None

    async def test_parent_child_relationship(self, db_session):
        parent = Jurisdiction(
            id=uuid.uuid4(),
            code="eu",
            name="European Union",
            level="supranational",
        )
        db_session.add(parent)
        await db_session.flush()

        child = Jurisdiction(
            id=uuid.uuid4(),
            code="ch",
            name="Suisse",
            level="country",
            parent_id=parent.id,
            country_code="CH",
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        assert child.parent_id == parent.id

    async def test_jurisdiction_hierarchy(self, db_session):
        """Test EU -> CH -> VD hierarchy."""
        eu = Jurisdiction(id=uuid.uuid4(), code="eu", name="EU", level="supranational")
        db_session.add(eu)
        await db_session.flush()

        ch = Jurisdiction(
            id=uuid.uuid4(), code="ch", name="Suisse", level="country", parent_id=eu.id, country_code="CH"
        )
        db_session.add(ch)
        await db_session.flush()

        vd = Jurisdiction(
            id=uuid.uuid4(), code="ch-vd", name="Canton de Vaud", level="region", parent_id=ch.id, country_code="CH"
        )
        db_session.add(vd)
        await db_session.commit()

        await db_session.refresh(vd)
        assert vd.parent_id == ch.id
        assert ch.parent_id == eu.id


class TestRegulatoryPackModel:
    async def test_create_regulatory_pack(self, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country", country_code="CH")
        db_session.add(j)
        await db_session.flush()

        pack = RegulatoryPack(
            id=uuid.uuid4(),
            jurisdiction_id=j.id,
            pollutant_type="asbestos",
            version="1.0",
            threshold_value=1.0,
            threshold_unit="percent_weight",
            threshold_action="remediate",
            legal_reference="OTConst Art. 60a",
            notification_required=True,
            notification_authority="SUVA",
            notification_delay_days=14,
        )
        db_session.add(pack)
        await db_session.commit()
        await db_session.refresh(pack)

        assert pack.pollutant_type == "asbestos"
        assert pack.threshold_value == 1.0
        assert pack.threshold_unit == "percent_weight"
        assert pack.threshold_action == "remediate"
        assert pack.notification_required is True
        assert pack.notification_authority == "SUVA"

    async def test_regulatory_pack_relationship(self, db_session):
        from sqlalchemy import select as sa_select

        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        for pollutant in ("asbestos", "pcb", "lead"):
            pack = RegulatoryPack(
                id=uuid.uuid4(),
                jurisdiction_id=j.id,
                pollutant_type=pollutant,
                threshold_value=50.0,
                threshold_unit="mg_per_kg",
            )
            db_session.add(pack)

        await db_session.commit()

        # Use explicit query (async sessions cannot lazy-load)
        result = await db_session.execute(sa_select(RegulatoryPack).where(RegulatoryPack.jurisdiction_id == j.id))
        packs = result.scalars().all()
        assert len(packs) == 3


class TestJurisdictionSeed:
    async def test_seed_creates_hierarchy(self, db_session):
        """Verify the seed data creates the correct hierarchy by simulating it."""
        from app.seeds.seed_jurisdictions import JURISDICTIONS

        # Insert in order
        for jur_data in JURISDICTIONS:
            j = Jurisdiction(**jur_data)
            db_session.add(j)
        await db_session.commit()

        # Verify EU exists
        from sqlalchemy import select

        result = await db_session.execute(select(Jurisdiction).where(Jurisdiction.code == "eu"))
        eu = result.scalar_one()
        assert eu.level == "supranational"

        # Verify CH is child of EU
        result = await db_session.execute(select(Jurisdiction).where(Jurisdiction.code == "ch"))
        ch = result.scalar_one()
        assert ch.parent_id == eu.id
        assert ch.level == "country"
        assert ch.country_code == "CH"

        # Verify CH-VD is child of CH
        result = await db_session.execute(select(Jurisdiction).where(Jurisdiction.code == "ch-vd"))
        vd = result.scalar_one()
        assert vd.parent_id == ch.id
        assert vd.level == "region"

        # Verify total count
        result = await db_session.execute(select(Jurisdiction))
        all_j = result.scalars().all()
        assert len(all_j) == len(JURISDICTIONS)

    async def test_seed_creates_regulatory_packs(self, db_session):
        """Verify seed creates the correct regulatory packs."""
        from sqlalchemy import select

        from app.seeds.seed_jurisdictions import (
            JURISDICTIONS,
            REGULATORY_PACKS_CH,
            REGULATORY_PACKS_GE,
            REGULATORY_PACKS_VD,
        )

        # Seed jurisdictions first
        for jur_data in JURISDICTIONS:
            db_session.add(Jurisdiction(**jur_data))
        await db_session.flush()

        # Seed packs
        all_packs = REGULATORY_PACKS_CH + REGULATORY_PACKS_VD + REGULATORY_PACKS_GE
        for pack_data in all_packs:
            db_session.add(RegulatoryPack(**pack_data))
        await db_session.commit()

        # Verify CH packs
        result = await db_session.execute(select(Jurisdiction).where(Jurisdiction.code == "ch"))
        ch = result.scalar_one()

        result = await db_session.execute(select(RegulatoryPack).where(RegulatoryPack.jurisdiction_id == ch.id))
        ch_packs = result.scalars().all()
        assert len(ch_packs) == len(REGULATORY_PACKS_CH)

        # Verify asbestos pack details
        asbestos_packs = [p for p in ch_packs if p.pollutant_type == "asbestos"]
        assert len(asbestos_packs) == 1
        asbestos = asbestos_packs[0]
        assert asbestos.threshold_value == 1.0
        assert asbestos.threshold_unit == "percent_weight"
        assert asbestos.threshold_action == "remediate"
        assert asbestos.notification_required is True

        # Verify radon has two packs (reference + action)
        radon_packs = [p for p in ch_packs if p.pollutant_type == "radon"]
        assert len(radon_packs) == 2
        radon_thresholds = sorted([p.threshold_value for p in radon_packs])
        assert radon_thresholds == [300.0, 1000.0]

        # Verify VD has cantonal packs
        result = await db_session.execute(select(Jurisdiction).where(Jurisdiction.code == "ch-vd"))
        vd = result.scalar_one()
        result = await db_session.execute(select(RegulatoryPack).where(RegulatoryPack.jurisdiction_id == vd.id))
        vd_packs = result.scalars().all()
        assert len(vd_packs) == len(REGULATORY_PACKS_VD)


class TestJurisdictionAPI:
    async def test_list_jurisdictions(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country", country_code="CH")
        db_session.add(j)
        await db_session.commit()

        response = await client.get("/api/v1/jurisdictions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["code"] == "ch"

    async def test_list_jurisdictions_filter_by_level(self, client, admin_user, auth_headers, db_session):
        eu = Jurisdiction(id=uuid.uuid4(), code="eu", name="EU", level="supranational")
        ch = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country", parent_id=eu.id)
        db_session.add_all([eu, ch])
        await db_session.commit()

        response = await client.get("/api/v1/jurisdictions?level=country", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["code"] == "ch"

    async def test_list_jurisdictions_filter_by_parent(self, client, admin_user, auth_headers, db_session):
        eu = Jurisdiction(id=uuid.uuid4(), code="eu", name="EU", level="supranational")
        ch = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country", parent_id=eu.id)
        fr = Jurisdiction(id=uuid.uuid4(), code="fr", name="France", level="country", parent_id=eu.id)
        db_session.add_all([eu, ch, fr])
        await db_session.commit()

        response = await client.get(f"/api/v1/jurisdictions?parent_id={eu.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_get_jurisdiction_with_packs(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        pack = RegulatoryPack(
            id=uuid.uuid4(),
            jurisdiction_id=j.id,
            pollutant_type="asbestos",
            threshold_value=1.0,
            threshold_unit="percent_weight",
        )
        db_session.add(pack)
        await db_session.commit()

        response = await client.get(f"/api/v1/jurisdictions/{j.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ch"
        assert len(data["regulatory_packs"]) == 1
        assert data["regulatory_packs"][0]["pollutant_type"] == "asbestos"

    async def test_get_jurisdiction_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/jurisdictions/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_create_jurisdiction_admin(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/jurisdictions",
            json={"code": "ch", "name": "Suisse", "level": "country", "country_code": "CH"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "ch"
        assert data["level"] == "country"
        assert data["country_code"] == "CH"

    async def test_create_jurisdiction_forbidden_for_owner(self, client, owner_user, owner_headers):
        response = await client.post(
            "/api/v1/jurisdictions",
            json={"code": "ch", "name": "Suisse", "level": "country"},
            headers=owner_headers,
        )
        assert response.status_code == 403

    async def test_update_jurisdiction(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.commit()

        response = await client.put(
            f"/api/v1/jurisdictions/{j.id}",
            json={"name": "Confederation suisse"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Confederation suisse"

    async def test_delete_jurisdiction(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="test-del", name="To Delete", level="country")
        db_session.add(j)
        await db_session.commit()

        response = await client.delete(f"/api/v1/jurisdictions/{j.id}", headers=auth_headers)
        assert response.status_code == 204

    async def test_delete_jurisdiction_with_children_fails(self, client, admin_user, auth_headers, db_session):
        parent = Jurisdiction(id=uuid.uuid4(), code="eu", name="EU", level="supranational")
        child = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country", parent_id=parent.id)
        db_session.add_all([parent, child])
        await db_session.commit()

        response = await client.delete(f"/api/v1/jurisdictions/{parent.id}", headers=auth_headers)
        assert response.status_code == 409

    async def test_delete_jurisdiction_with_packs_fails(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        pack = RegulatoryPack(id=uuid.uuid4(), jurisdiction_id=j.id, pollutant_type="asbestos", threshold_value=1.0)
        db_session.add(pack)
        await db_session.commit()

        response = await client.delete(f"/api/v1/jurisdictions/{j.id}", headers=auth_headers)
        assert response.status_code == 409


class TestRegulatoryPackAPI:
    async def test_list_regulatory_packs(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        for pt in ("asbestos", "pcb", "lead"):
            db_session.add(
                RegulatoryPack(id=uuid.uuid4(), jurisdiction_id=j.id, pollutant_type=pt, threshold_value=50.0)
            )
        await db_session.commit()

        response = await client.get(f"/api/v1/jurisdictions/{j.id}/regulatory-packs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_list_regulatory_packs_filter_pollutant(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        for pt in ("asbestos", "pcb"):
            db_session.add(
                RegulatoryPack(id=uuid.uuid4(), jurisdiction_id=j.id, pollutant_type=pt, threshold_value=50.0)
            )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/jurisdictions/{j.id}/regulatory-packs?pollutant_type=pcb",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["pollutant_type"] == "pcb"

    async def test_create_regulatory_pack(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/jurisdictions/{j.id}/regulatory-packs",
            json={
                "pollutant_type": "asbestos",
                "threshold_value": 1.0,
                "threshold_unit": "percent_weight",
                "threshold_action": "remediate",
                "notification_required": True,
                "notification_authority": "SUVA",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["pollutant_type"] == "asbestos"
        assert data["threshold_value"] == 1.0
        assert data["notification_required"] is True

    async def test_update_regulatory_pack(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        pack = RegulatoryPack(id=uuid.uuid4(), jurisdiction_id=j.id, pollutant_type="pcb", threshold_value=50.0)
        db_session.add(pack)
        await db_session.commit()

        response = await client.put(
            f"/api/v1/jurisdictions/{j.id}/regulatory-packs/{pack.id}",
            json={"threshold_value": 100.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["threshold_value"] == 100.0

    async def test_delete_regulatory_pack(self, client, admin_user, auth_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.flush()

        pack = RegulatoryPack(id=uuid.uuid4(), jurisdiction_id=j.id, pollutant_type="pcb", threshold_value=50.0)
        db_session.add(pack)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/jurisdictions/{j.id}/regulatory-packs/{pack.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_create_pack_forbidden_for_diagnostician(self, client, diagnostician_user, diag_headers, db_session):
        j = Jurisdiction(id=uuid.uuid4(), code="ch", name="Suisse", level="country")
        db_session.add(j)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/jurisdictions/{j.id}/regulatory-packs",
            json={"pollutant_type": "pcb", "threshold_value": 50.0},
            headers=diag_headers,
        )
        assert response.status_code == 403


class TestBuildingJurisdictionFK:
    async def test_building_jurisdiction_id_nullable(self, db_session, admin_user):
        """Existing buildings without jurisdiction_id should work."""
        from app.models.building import Building

        building = Building(
            id=uuid.uuid4(),
            address="Rue Test 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=admin_user.id,
            status="active",
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        assert building.jurisdiction_id is None

    async def test_building_with_jurisdiction(self, db_session, admin_user):
        """Buildings can reference a jurisdiction."""
        from app.models.building import Building

        j = Jurisdiction(id=uuid.uuid4(), code="ch-vd", name="Canton de Vaud", level="region", country_code="CH")
        db_session.add(j)
        await db_session.flush()

        building = Building(
            id=uuid.uuid4(),
            address="Rue Test 2",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=admin_user.id,
            jurisdiction_id=j.id,
            status="active",
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        assert building.jurisdiction_id == j.id
