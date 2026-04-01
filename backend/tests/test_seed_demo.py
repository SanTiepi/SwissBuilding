from __future__ import annotations

from argparse import Namespace

import pytest

from app.seeds import seed_demo


@pytest.fixture(autouse=True)
def _patch_v3_seeds(monkeypatch):
    """Patch V3 seeds that require real DB tables not available in this test's SQLite."""

    async def _noop_form(db):
        return 0

    async def _noop_source(db):
        return 0

    async def _noop_proc(db):
        return 0

    async def _noop_prospect(db):
        return {"total": 0}

    monkeypatch.setattr(seed_demo, "seed_form_templates", _noop_form)
    monkeypatch.setattr(seed_demo, "seed_source_registry", _noop_source)
    monkeypatch.setattr(seed_demo, "seed_procedure_templates", _noop_proc)
    monkeypatch.setattr(seed_demo, "seed_prospect_demo", _noop_prospect)


def test_has_vd_filter() -> None:
    assert seed_demo._has_vd_filter(Namespace(commune="Lausanne", municipality_ofs=None, postal_code=None))
    assert seed_demo._has_vd_filter(Namespace(commune=None, municipality_ofs=5586, postal_code=None))
    assert seed_demo._has_vd_filter(Namespace(commune=None, municipality_ofs=None, postal_code="1000"))
    assert not seed_demo._has_vd_filter(Namespace(commune=None, municipality_ofs=None, postal_code=None))


async def test_main_skip_vaud_only_runs_seed(monkeypatch, capsys) -> None:
    called = {"seed": 0, "workspace": 0, "harvest": 0}

    async def _seed() -> None:
        called["seed"] += 1

    async def _seed_workspace() -> dict:
        called["workspace"] += 1
        return {
            "building_address": "Avenue des Alpes 18",
            "contacts_count": 9,
            "leases_count": 3,
            "contracts_count": 3,
        }

    async def _harvest(**kwargs):  # pragma: no cover - should not be called
        called["harvest"] += 1
        return [], {}

    monkeypatch.setattr(
        seed_demo,
        "parse_args",
        lambda: Namespace(
            skip_vaud=True,
            skip_enrich=False,
            dry_run_vaud=False,
            commune=None,
            municipality_ofs=None,
            postal_code=None,
            limit=150,
            concurrency=8,
            created_by_email="admin@swissbuildingos.ch",
            output_json=None,
        ),
    )
    monkeypatch.setattr(seed_demo, "seed", _seed)
    monkeypatch.setattr(seed_demo, "_seed_workspace", _seed_workspace)
    monkeypatch.setattr(seed_demo, "harvest_vd_buildings", _harvest)

    await seed_demo.main()

    out = capsys.readouterr().out
    assert called == {"seed": 1, "workspace": 1, "harvest": 0}
    assert "Vaud import skipped" in out


async def test_main_requires_filter_without_skip(monkeypatch) -> None:
    async def _seed() -> None:
        return None

    async def _seed_workspace() -> dict:
        return {
            "building_address": "Avenue des Alpes 18",
            "contacts_count": 9,
            "leases_count": 3,
            "contracts_count": 3,
        }

    monkeypatch.setattr(
        seed_demo,
        "parse_args",
        lambda: Namespace(
            skip_vaud=False,
            skip_enrich=True,
            dry_run_vaud=False,
            commune=None,
            municipality_ofs=None,
            postal_code=None,
            limit=150,
            concurrency=8,
            created_by_email="admin@swissbuildingos.ch",
            output_json=None,
        ),
    )
    monkeypatch.setattr(seed_demo, "seed", _seed)
    monkeypatch.setattr(seed_demo, "_seed_workspace", _seed_workspace)

    with pytest.raises(SystemExit, match="Missing Vaud filter"):
        await seed_demo.main()


async def test_main_harvests_and_applies_vaud_records(monkeypatch, tmp_path, capsys) -> None:
    calls: dict[str, object] = {}

    async def _seed() -> None:
        calls["seed"] = True

    async def _seed_workspace() -> dict:
        calls["workspace"] = True
        return {
            "building_address": "Avenue des Alpes 18",
            "contacts_count": 9,
            "leases_count": 3,
            "contracts_count": 3,
        }

    async def _harvest(**kwargs):
        calls["harvest"] = kwargs
        return ["record-1"], {"normalized": 1, "unique_egids": 1, "address_records": 2, "skipped": 0}

    def _write(records, output_json):
        calls["write_output_json"] = (records, output_json)

    async def _apply(records, *, created_by_email):
        calls["apply"] = {"records": records, "created_by_email": created_by_email}
        return 1, 0, 0

    output_json = tmp_path / "vaud.json"
    monkeypatch.setattr(
        seed_demo,
        "parse_args",
        lambda: Namespace(
            skip_vaud=False,
            skip_enrich=True,
            dry_run_vaud=False,
            commune="Lausanne",
            municipality_ofs=None,
            postal_code=None,
            limit=50,
            concurrency=4,
            created_by_email="admin@swissbuildingos.ch",
            output_json=output_json,
        ),
    )
    monkeypatch.setattr(seed_demo, "seed", _seed)
    monkeypatch.setattr(seed_demo, "_seed_workspace", _seed_workspace)
    monkeypatch.setattr(seed_demo, "harvest_vd_buildings", _harvest)
    monkeypatch.setattr(seed_demo, "write_output_json", _write)
    monkeypatch.setattr(seed_demo, "apply_records", _apply)

    await seed_demo.main()

    out = capsys.readouterr().out
    assert calls["seed"] is True
    assert calls["workspace"] is True
    assert calls["harvest"] == {
        "commune": "Lausanne",
        "municipality_ofs": None,
        "postal_code": None,
        "limit": 50,
        "concurrency": 4,
    }
    assert calls["write_output_json"] == (["record-1"], output_json)
    assert calls["apply"] == {
        "records": ["record-1"],
        "created_by_email": "admin@swissbuildingos.ch",
    }
    assert "Vaud import applied: created=1, updated=0, unchanged=0" in out


async def test_main_dry_run_vaud_skips_apply(monkeypatch, tmp_path, capsys) -> None:
    calls: dict[str, object] = {}

    async def _seed() -> None:
        calls["seed"] = True

    async def _seed_workspace() -> dict:
        calls["workspace"] = True
        return {
            "building_address": "Avenue des Alpes 18",
            "contacts_count": 9,
            "leases_count": 3,
            "contracts_count": 3,
        }

    async def _harvest(**kwargs):
        calls["harvest"] = kwargs
        return ["record-1"], {"normalized": 1, "unique_egids": 1, "address_records": 1, "skipped": 0}

    def _write(records, output_json):
        calls["write_output_json"] = (records, output_json)

    async def _apply(records, *, created_by_email):  # pragma: no cover - should not be called
        calls["apply"] = {"records": records, "created_by_email": created_by_email}
        return 1, 0, 0

    output_json = tmp_path / "vaud.json"
    monkeypatch.setattr(
        seed_demo,
        "parse_args",
        lambda: Namespace(
            skip_vaud=False,
            skip_enrich=True,
            dry_run_vaud=True,
            commune="Lausanne",
            municipality_ofs=None,
            postal_code=None,
            limit=25,
            concurrency=2,
            created_by_email="admin@swissbuildingos.ch",
            output_json=output_json,
        ),
    )
    monkeypatch.setattr(seed_demo, "seed", _seed)
    monkeypatch.setattr(seed_demo, "_seed_workspace", _seed_workspace)
    monkeypatch.setattr(seed_demo, "harvest_vd_buildings", _harvest)
    monkeypatch.setattr(seed_demo, "write_output_json", _write)
    monkeypatch.setattr(seed_demo, "apply_records", _apply)

    await seed_demo.main()

    out = capsys.readouterr().out
    assert calls["seed"] is True
    assert calls["workspace"] is True
    assert "apply" not in calls
    assert "Dry-run Vaud mode enabled" in out
