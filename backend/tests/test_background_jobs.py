"""Tests for generic background job tracking."""

import uuid

import pytest

from app.models.background_job import BackgroundJob
from app.services import background_job_service


class TestBackgroundJobService:
    """Unit tests for background_job_service functions."""

    async def test_create_job(self, db_session):
        job = await background_job_service.create_job(
            db_session,
            job_type="pack_generation",
            building_id=uuid.uuid4(),
            params={"format": "pdf"},
        )
        assert job.id is not None
        assert job.job_type == "pack_generation"
        assert job.status == "queued"
        assert job.params_json == {"format": "pdf"}
        assert job.started_at is None
        assert job.completed_at is None

    async def test_start_job(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="search_sync")
        started = await background_job_service.start_job(db_session, job.id)
        assert started.status == "running"
        assert started.started_at is not None

    async def test_complete_job(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="signal_generation")
        await background_job_service.start_job(db_session, job.id)
        completed = await background_job_service.complete_job(db_session, job.id, result={"signals_created": 5})
        assert completed.status == "completed"
        assert completed.result_json == {"signals_created": 5}
        assert completed.completed_at is not None
        assert completed.progress_pct == 100

    async def test_fail_job(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="dossier_completion")
        await background_job_service.start_job(db_session, job.id)
        failed = await background_job_service.fail_job(db_session, job.id, error_message="Connection timeout")
        assert failed.status == "failed"
        assert failed.error_message == "Connection timeout"
        assert failed.completed_at is not None

    async def test_cancel_job(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="pack_generation")
        cancelled = await background_job_service.cancel_job(db_session, job.id)
        assert cancelled.status == "cancelled"
        assert cancelled.completed_at is not None

    async def test_cancel_running_job_raises(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="pack_generation")
        await background_job_service.start_job(db_session, job.id)
        with pytest.raises(ValueError, match="Only queued jobs can be cancelled"):
            await background_job_service.cancel_job(db_session, job.id)

    async def test_get_job(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="search_sync")
        fetched = await background_job_service.get_job(db_session, job.id)
        assert fetched is not None
        assert fetched.id == job.id

    async def test_get_job_not_found(self, db_session):
        result = await background_job_service.get_job(db_session, uuid.uuid4())
        assert result is None

    async def test_list_jobs_no_filter(self, db_session):
        for jt in ("pack_generation", "search_sync", "signal_generation"):
            await background_job_service.create_job(db_session, job_type=jt)
        jobs = await background_job_service.list_jobs(db_session)
        assert len(jobs) == 3

    async def test_list_jobs_filter_by_type(self, db_session):
        await background_job_service.create_job(db_session, job_type="pack_generation")
        await background_job_service.create_job(db_session, job_type="search_sync")
        jobs = await background_job_service.list_jobs(db_session, job_type="pack_generation")
        assert len(jobs) == 1
        assert jobs[0].job_type == "pack_generation"

    async def test_list_jobs_filter_by_status(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="pack_generation")
        await background_job_service.start_job(db_session, job.id)
        await background_job_service.create_job(db_session, job_type="search_sync")

        running = await background_job_service.list_jobs(db_session, status="running")
        assert len(running) == 1
        assert running[0].status == "running"

    async def test_list_jobs_filter_by_building(self, db_session):
        bid = uuid.uuid4()
        await background_job_service.create_job(db_session, job_type="pack_generation", building_id=bid)
        await background_job_service.create_job(db_session, job_type="search_sync", building_id=uuid.uuid4())
        jobs = await background_job_service.list_jobs(db_session, building_id=bid)
        assert len(jobs) == 1

    async def test_update_progress(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="pack_generation")
        await background_job_service.start_job(db_session, job.id)
        updated = await background_job_service.update_progress(db_session, job.id, 50)
        assert updated.progress_pct == 50

    async def test_update_progress_clamped(self, db_session):
        job = await background_job_service.create_job(db_session, job_type="pack_generation")
        updated = await background_job_service.update_progress(db_session, job.id, 150)
        assert updated.progress_pct == 100

    async def test_create_job_with_user_and_org(self, db_session):
        uid = uuid.uuid4()
        oid = uuid.uuid4()
        job = await background_job_service.create_job(
            db_session,
            job_type="dossier_completion",
            org_id=oid,
            user_id=uid,
        )
        assert job.created_by == uid
        assert job.organization_id == oid


class TestBackgroundJobAPI:
    """Integration tests for the background jobs API endpoints."""

    async def test_list_jobs_empty(self, client, admin_user, auth_headers):
        response = await client.get("/api/v1/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_jobs_with_items(self, client, admin_user, auth_headers, db_session):
        db_session.add(
            BackgroundJob(
                id=uuid.uuid4(),
                job_type="pack_generation",
                status="queued",
                created_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.get("/api/v1/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["job_type"] == "pack_generation"

    async def test_list_jobs_filter_type(self, client, admin_user, auth_headers, db_session):
        for jt in ("pack_generation", "search_sync"):
            db_session.add(
                BackgroundJob(
                    id=uuid.uuid4(),
                    job_type=jt,
                    status="queued",
                    created_by=admin_user.id,
                )
            )
        await db_session.commit()

        response = await client.get("/api/v1/jobs?job_type=search_sync", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["job_type"] == "search_sync"

    async def test_get_job(self, client, admin_user, auth_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            BackgroundJob(
                id=job_id,
                job_type="signal_generation",
                status="running",
                created_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "signal_generation"
        assert data["status"] == "running"

    async def test_get_job_not_found(self, client, admin_user, auth_headers):
        response = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404

    async def test_cancel_job(self, client, admin_user, auth_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            BackgroundJob(
                id=job_id,
                job_type="pack_generation",
                status="queued",
                created_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_cancel_running_job_fails(self, client, admin_user, auth_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            BackgroundJob(
                id=job_id,
                job_type="pack_generation",
                status="running",
                created_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
        assert response.status_code == 400
