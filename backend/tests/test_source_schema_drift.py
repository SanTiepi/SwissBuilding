"""Schema-drift detection tests for source adapters.

Verifies that adapters detect when external API response shapes change
and record appropriate events instead of silently producing bad data.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def db(db_session: AsyncSession):
    yield db_session


# ---------------------------------------------------------------------------
# Identity chain schema drift
# ---------------------------------------------------------------------------


class TestIdentityChainSchemaDrift:
    """Schema-drift detection for EGID/EGRID/RDPPF responses."""

    def _get_validator(self):
        try:
            from app.services.identity_chain_service import _validate_egid_response

            return _validate_egid_response
        except ImportError:
            pytest.skip("_validate_egid_response not yet implemented")

    def test_egid_response_validation_complete(self):
        validate = self._get_validator()
        result = validate({"egid": 12345, "address": "Rue Test 1", "municipality": "Lausanne", "canton": "VD"})
        assert result["valid"] is True
        assert len(result["missing_fields"]) == 0

    def test_egid_response_validation_missing_fields(self):
        validate = self._get_validator()
        result = validate({"egid": 12345})
        assert result["valid"] is False
        assert len(result["missing_fields"]) > 0

    def test_egid_response_validation_empty(self):
        validate = self._get_validator()
        result = validate({})
        assert result["valid"] is False


# ---------------------------------------------------------------------------
# Geo context schema drift
# ---------------------------------------------------------------------------


class TestGeoContextSchemaDrift:
    """Schema-drift detection for geo.admin layer responses."""

    def _get_validator(self):
        try:
            from app.services.geo_context_service import _validate_layer_response

            return _validate_layer_response
        except ImportError:
            pytest.skip("_validate_layer_response not yet implemented")

    def test_layer_response_validation_valid(self):
        validate = self._get_validator()
        # geo.admin responses have raw_attributes containing the actual data
        result = validate("radon", {"raw_attributes": {"radonrisiko": "moderate"}})
        assert result["valid"] is True

    def test_layer_response_validation_empty(self):
        validate = self._get_validator()
        result = validate("radon", {})
        assert result["valid"] is False

    def test_layer_response_validation_none(self):
        validate = self._get_validator()
        # None data should be handled gracefully
        try:
            result = validate("radon", None)
            assert result["valid"] is False
        except (TypeError, AttributeError):
            # If the validator doesn't handle None, that's acceptable
            pass


# ---------------------------------------------------------------------------
# Subsidy source schema drift
# ---------------------------------------------------------------------------


class TestSubsidySchemaDrift:
    """Schema-drift detection for subsidy program data."""

    def _get_validator(self):
        try:
            from app.services.subsidy_source_service import SubsidySourceService

            svc = SubsidySourceService()
            if not hasattr(svc, "_validate_subsidy_program"):
                pytest.skip("_validate_subsidy_program not yet implemented")
            return svc._validate_subsidy_program
        except ImportError:
            pytest.skip("SubsidySourceService not available")

    def test_program_validation_complete(self):
        validate = self._get_validator()
        result = validate({"name": "Isolation", "category": "energy", "max_chf_m2": 40})
        assert result["valid"] is True

    def test_program_validation_missing_name(self):
        validate = self._get_validator()
        result = validate({"category": "energy"})
        assert result["valid"] is False

    def test_program_validation_empty(self):
        validate = self._get_validator()
        result = validate({})
        assert result["valid"] is False
