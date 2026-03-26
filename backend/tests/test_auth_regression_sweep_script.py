from __future__ import annotations

from pathlib import Path

from scripts.run_auth_regression_sweep import _scan_paths


def test_scan_flags_only_obvious_unauthenticated_403(tmp_path: Path) -> None:
    test_file = tmp_path / "test_auth_cluster_sample.py"
    test_file.write_text(
        """
async def test_api_requires_auth(client):
    resp = await client.get("/api/v1/search")
    assert resp.status_code == 403


async def test_admin_forbidden_with_wrong_role(client):
    resp = await client.get("/api/v1/search", headers=_headers(token))
    assert resp.status_code == 403
""".lstrip(),
        encoding="utf-8",
    )

    findings = _scan_paths([test_file])

    assert len(findings) == 1
    assert findings[0].test_name == "test_api_requires_auth"
    assert findings[0].line_no == 3
