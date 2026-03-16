"""Diagnostic quality assessment schemas."""

import uuid

from pydantic import BaseModel, ConfigDict


class DiagnosticQualityScore(BaseModel):
    """Quality evaluation for a single diagnostic."""

    diagnostic_id: uuid.UUID
    overall_score: float  # 0-100
    grade: str  # A-F
    sample_density_score: float  # 0-100
    pollutant_coverage_score: float  # 0-100
    methodology_score: float  # 0-100
    documentation_score: float  # 0-100
    lab_accreditation_score: float  # 0-100
    total_samples: int
    total_zones: int
    pollutants_tested: list[str]
    pollutants_missing: list[str]

    model_config = ConfigDict(from_attributes=True)


class DiagnosticianPerformance(BaseModel):
    """Performance metrics for a single diagnostician."""

    diagnostician_id: uuid.UUID
    diagnostician_name: str
    diagnostic_count: int
    avg_quality_score: float
    avg_samples_per_diagnostic: float
    avg_days_to_completion: float | None
    completeness_rate: float  # 0-100: % of diagnostics with status completed/validated
    rank: int

    model_config = ConfigDict(from_attributes=True)


class DiagnosticianComparisonResult(BaseModel):
    """Comparison of diagnosticians within an organization."""

    organization_id: uuid.UUID
    diagnosticians: list[DiagnosticianPerformance]
    total_diagnosticians: int

    model_config = ConfigDict(from_attributes=True)


class DiagnosticDeficiency(BaseModel):
    """A specific deficiency found in a diagnostic."""

    deficiency_type: str  # insufficient_sampling, missing_pollutant, outdated_methodology, incomplete_report
    severity: str  # low, medium, high, critical
    description: str
    fix_action: str
    zone_id: uuid.UUID | None = None
    pollutant_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DiagnosticDeficiencyResult(BaseModel):
    """All deficiencies detected for a diagnostic."""

    diagnostic_id: uuid.UUID
    deficiencies: list[DiagnosticDeficiency]
    total_deficiencies: int
    critical_count: int
    high_count: int

    model_config = ConfigDict(from_attributes=True)


class DiagnosticBenchmarks(BaseModel):
    """System-wide diagnostic quality benchmarks."""

    total_diagnostics: int
    avg_quality_score: float
    median_quality_score: float
    avg_sample_count: float
    avg_pollutants_tested: float
    best_practice_threshold: float  # score above which is considered best practice
    grade_distribution: dict[str, int]  # {"A": 5, "B": 12, ...}
    pollutant_coverage_rate: dict[str, float]  # {"asbestos": 0.95, ...}

    model_config = ConfigDict(from_attributes=True)
