# Task N.1 — Scan Conformite Automatique

## What to do
Create a new service `compliance_auto_scan_service.py` that performs a comprehensive scan of regulatory compliance for a building.

For each applicable rule in `swiss_rules_spine_service` (which covers OTConst, ORRChim, OFEN, CFST, LCI):
- Evaluate applicability to the building (canton, construction_year, size, usage)
- Check if compliance evidence exists (diagnostic, certificate, intervention, etc.)
- Flag non-conformities, obligations, and coming deadlines

Output JSON with:
```json
{
  "building_id": "...",
  "scan_date": "2026-04-01",
  "canton": "VD",
  "total_rules_applicable": 47,
  "compliant": 42,
  "non_compliant": 3,
  "unknown": 2,
  "score": 89,
  "non_conformities": [
    {"rule": "OTConst Art. 82 — Analyse amiante avant travaux",
     "status": "non_compliant",
     "evidence_needed": "diagnostic_amiante",
     "deadline": "2026-06-30",
     "severity": "high"}
  ],
  "obligations": [
    {"rule": "...", "deadline": "2026-12-31", "type": "analysis | inspection | certification"}
  ]
}
```

## Files to create/modify
- **Create:** `backend/app/services/compliance_auto_scan_service.py` (~250 lines)
- **Modify:** `backend/app/api/compliance_summary.py` - add POST scan endpoint (15 lines)
- **Create:** `backend/tests/test_compliance_auto_scan.py` (~100 lines, 4 tests)
- **Modify:** `backend/app/models/compliance_summary.py` (if exists) — optional caching of scan results

## Existing patterns to copy

From `backend/app/services/swiss_rules_spine_service.py` (read earlier, offset 101+):
The spine service already has rule templates, applicability logic, etc.
Copy the `ApplicabilityEvaluation` pattern:
```python
def evaluate_applicability(building: Building, rule: RuleTemplate) -> ApplicabilityEvaluation:
    """Evaluate if a rule applies to this building."""
    
    # Check jurisdiction
    if rule.jurisdiction != Jurisdiction.CH and rule.jurisdiction != building.canton:
        return ApplicabilityEvaluation(status=ApplicabilityStatus.NOT_APPLICABLE)
    
    # Check building age
    if rule.min_construction_year and building.construction_year < rule.min_construction_year:
        return ApplicabilityEvaluation(status=ApplicabilityStatus.NOT_APPLICABLE)
    
    # Check surface
    if rule.min_surface_m2 and building.gwr_surface_m2 < rule.min_surface_m2:
        return ApplicabilityEvaluation(status=ApplicabilityStatus.NOT_APPLICABLE)
    
    return ApplicabilityEvaluation(status=ApplicabilityStatus.APPLICABLE)
```

From action/obligation detection pattern:
```python
async def check_compliance_status(db: AsyncSession, building_id: UUID, rule_code: str) -> str:
    """Check if compliance evidence exists for a rule."""
    
    building = await db.execute(select(Building).where(Building.id == building_id))
    building = building.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    
    # Map rule to evidence model
    evidence_map = {
        "OTConst Art. 82": ("diagnostic", "pollutant_diagnostic"),  # Need diagnostic
        "OTConst Art. 81": ("diagnostic", "asbestos_diagnostic"),
        "OFEN": ("certificate", "energy_certificate"),  # Need CECB
        "CFST": ("inspection", "safety_inspection"),
    }
    
    if rule_code not in evidence_map:
        return "unknown"
    
    model_name, field_name = evidence_map[rule_code]
    
    if model_name == "diagnostic":
        diags = await db.execute(
            select(Diagnostic).where(Diagnostic.building_id == building_id, Diagnostic.type == field_name)
        )
        return "compliant" if diags.scalar_one_or_none() else "non_compliant"
    
    # ... etc
    return "unknown"
```

API endpoint pattern:
```python
@router.post("/buildings/{building_id}/compliance/scan")
async def trigger_compliance_scan(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger full compliance scan for building."""
    result = await compliance_auto_scan_service.scan_compliance(db, building_id)
    return result
```

## Commit message
```
feat(programme-n): compliance auto-scan service (OTConst+ORRChim+OFEN+CFST conformity check)
```

## Test command
```bash
cd backend && python -m pytest tests/test_compliance_auto_scan.py -v
```

## Notes
- Use existing `swiss_rules_spine_service` as source of rules
- Cache results in database (optional model: `compliance_scan_result`)
- Score = (compliant / total_applicable) * 100
- Non-conformities: high severity = regulation, low severity = recommendation
- Obligations flow to existing `obligation` model (with deadline dates)
- Deadlines = regulatory deadline + buffer (e.g., "Analysis must be done within 30 days of permit")
