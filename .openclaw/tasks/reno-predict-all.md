# Task: RénoPredict — estimation coûts remédiation

## Commit message
feat(reno-predict): complete cost estimation pipeline (model, service, API, frontend)

## What to do
Implement the full RénoPredict module for remediation cost estimation. Build on existing RemediationCostReference model and cost_predictor_service. Wire up the API endpoint (POST /predict/cost), create the cost prediction service if missing, seed reference data (CHF/m² for asbestos, PCB, lead, HAP, radon, PFAS). Add canton + accessibility + condition coefficients. Create frontend button on DiagnosticView that opens a modal with cost range (min/median/max) and breakdown (dépose, traitement, analyses, remise en état, frais généraux). Export results as PDF via Gotenberg. Tests for edge cases + fourchettes.

## Files to modify
- `backend/app/models/remediation_cost_reference.py` (verify schema exists, seed data structure)
- `backend/app/services/cost_predictor_service.py` (complete service: lookup reference, apply coefficients, compute fourchette)
- `backend/app/seeds/seed_cost_references.py` (populate realistic Swiss market prices)
- `backend/app/api/cost_prediction.py` (complete endpoint: POST /predict/cost with validation)
- `backend/tests/test_cost_predictor.py` (add tests for all pollutants + coefficients + fourchette logic)
- `frontend/src/components/DiagnosticView/CostEstimationModal.tsx` (create modal with input form + results display + export button)
- `frontend/src/hooks/useCostPrediction.ts` (API hook for cost prediction)

## Existing patterns to follow

From `cost_predictor_service.py` (coefficients + constants):
```python
CANTON_COEFFICIENTS: dict[str, float] = {
    "VD": 1.0, "GE": 1.15, "ZH": 1.10, "BE": 1.0, "VS": 0.95, "FR": 1.0,
}
ACCESSIBILITY_COEFFICIENTS: dict[str, float] = {
    "facile": 0.9, "normal": 1.0, "difficile": 1.3, "tres_difficile": 1.6,
}
CONDITION_COEFFICIENTS: dict[str, float] = {
    "bon": 0.85, "degrade": 1.0, "friable": 1.25,
}
BREAKDOWN_TEMPLATE: list[tuple[str, float]] = [
    ("Dépose / Intervention", 0.45),
    ("Traitement déchets", 0.20),
    ("Analyses contrôle", 0.08),
    ("Remise en état", 0.22),
    ("Frais généraux", 0.05),
]

async def predict_cost(
    request: CostPredictionRequest, session: AsyncSession
) -> CostPredictionResponse:
    """Lookup reference → apply coefficients → compute fourchette (min/median/max)."""
```

From existing modal patterns (frontend):
```tsx
<Modal title="Estimation des coûts" onClose={onClose}>
  <Form onSubmit={handleEstimate}>
    <SelectField name="pollutant" options={pollutants} />
    <SelectField name="canton" options={cantons} />
    <SelectField name="accessibility" options={accessibilities} />
    <NumberField name="volume_m3" placeholder="Volume estimé (m³)" />
    <Button type="submit">Estimer</Button>
  </Form>
  {result && <CostBreakdown result={result} />}
  <Button onClick={exportPDF}>Télécharger PDF</Button>
</Modal>
```

## Acceptance criteria
- [ ] RemediationCostReference seeded with 6 pollutants × 5+ cantons = 30+ reference prices
- [ ] Service computes min/median/max based on volume + coefficients
- [ ] API endpoint accepts pollutant, canton, accessibility, condition, volume_m3
- [ ] Frontend modal on DiagnosticView with inputs + cost breakdown display
- [ ] PDF export via Gotenberg includes building_id, pollutant, volume, fourchette, breakdown
- [ ] Tests cover all pollutants + coefficient combinations + edge cases (0 volume, missing canton, etc.)
- [ ] All tests pass

## Test command
cd backend && python -m pytest tests/test_cost_predictor.py -v && cd ../.. && cd frontend && npm test -- CostEstimationModal

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Use existing Gotenberg service (no new dependencies)
- Follow Swiss market prices (realistic data, not synthetic)
- Commit with the message above if tests pass
