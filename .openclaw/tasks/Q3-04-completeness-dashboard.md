# Task Q3.04 — Completeness Measurement Dashboard

## What to do
Implement completeness dashboard: measures how complete each building's dossier is across 16 key dimensions. Critical for pilot validation (target: ≥95% completeness on 20+ buildings).

**16 Completeness Dimensions:**
1. Building metadata (address, owner, area, build year, stories) — 20 points max
2. Energy data (CECB, heating degree days, solar potential) — 15 points max
3. Hazardous materials (asbestos, lead, PCB tests) — 20 points max
4. Structural health (sinistralité score, incident history) — 15 points max
5. Environmental exposure (noise, contamination, radon, flood risk) — 15 points max
6. Regulatory compliance (OTConst, CFST, LCI checks) — 20 points max
7. Materials inventory (all building elements documented) — 15 points max
8. Repair/renovation history (past work, quotes) — 10 points max
9. Owner/occupant info (names, contact, lease agreements) — 10 points max
10. Legal documents (property deed, permits, insurance) — 15 points max
11. Photos/evidence (before/after, current state) — 10 points max
12. Field observations (inspector notes, risk flags) — 10 points max
13. Third-party inspections (independent assessments) — 10 points max
14. Remediation plan (contractor proposals, timelines) — 10 points max
15. Post-works documentation (completion certificates, photos) — 10 points max
16. Maintenance/operations manual — 5 points max

**Scoring:**
- Each dimension: 0-100% complete
- Overall score = weighted average of 16 dimensions
- Color code: Green ≥90, Yellow 70-89, Orange 50-69, Red <50

**Model:**
```python
class CompletenessScore(Base):
    building_id: UUID
    dimension: str  # building_metadata, energy_data, hazards, etc
    score: float  # 0-100
    missing_items: JSON  # [{field: "asbestos_test", importance: "critical"}]
    required_actions: JSON  # [{action, priority, effort}]
    updated_at: datetime

class CompletenessReport(Base):
    building_id: UUID
    overall_score: float  # 0-100
    dimension_scores: JSON  # {dimension: score}
    missing_items_count: int
    urgent_actions: int
    recommended_actions: int
    trend: str  # improving, stable, declining
    created_at: datetime
```

**API:**
- `GET /buildings/{id}/completeness` — overall score + breakdown
- `GET /buildings/{id}/completeness/missing-items` — detailed checklist
- `GET /buildings/{id}/completeness/recommended-actions` — next steps
- `GET /buildings?completeness_min=90` — filter buildings by completeness

**Frontend:**
- CompletenessCard (overall % big number + 16 color circles representing dimensions)
- CompletenessBreakdown (expandable list of dimensions with % + missing items)
- MissingItemsChecklist (interactive, user can mark items as "in progress")
- CompletionTrend (sparkline showing progress over weeks)
- IntegrationTo BuildingHome as widget + dedicated page

**Admin Dashboard:**
- PortfolioCompletenessView (scatter: completeness % vs building age, by canton)
- CompletenessLeaderboard (top 10 most complete buildings)
- GapAnalysis (most commonly missing items across portfolio)

## Files to modify
- **Create:** `backend/app/models/completeness_score.py` (25 lines)
- **Create:** `backend/app/models/completeness_report.py` (20 lines)
- **Create:** `backend/app/services/completeness_scorer.py` (150 lines)
- **Create:** `backend/app/schemas/completeness.py` (30 lines)
- **Modify:** `backend/app/api/buildings.py` (add completeness endpoints, 30 lines)
- **Create:** `frontend/src/components/buildings/CompletenessCard.tsx` (120 lines)
- **Create:** `frontend/src/components/buildings/CompletenessBreakdown.tsx` (180 lines)
- **Create:** `frontend/src/components/buildings/MissingItemsChecklist.tsx` (140 lines)
- **Create:** `frontend/src/pages/Building/CompletenessDetail.tsx` (200 lines)
- **Create:** `frontend/src/pages/Admin/CompletenessPortfolio.tsx` (250 lines)
- **Modify:** `frontend/src/pages/Building/BuildingHome.tsx` (integrate card, 10 lines)
- **Create:** `backend/alembic/versions/0XX_add_completeness_tables.py`
- **Create:** `backend/tests/services/test_completeness_scorer.py` (20 tests)
- **Create:** `frontend/src/components/buildings/CompletenessCard.test.tsx` (10 tests)

## Existing patterns to copy

From `backend/app/services/building_passport_service.py`:
```python
async def calculate_scores(building_id: UUID, session) -> dict:
    scores = {}
    for dimension in DIMENSIONS:
        scores[dimension] = await score_dimension(dimension, building_id, session)
    overall = sum(scores.values()) / len(scores)
    return {"dimensions": scores, "overall": overall}
```

From `frontend/src/components/buildings/ReadinessDashboard.tsx`:
```tsx
export const CompletenessCard = memo(({ building_id }: Props) => {
  const { data: completeness } = useQuery({
    queryKey: ["completeness", building_id],
    queryFn: () => api.getCompleteness(building_id),
  });
  
  const color = completeness?.overall_score >= 90 ? "green" : 
                completeness?.overall_score >= 70 ? "yellow" : "red";
  
  return (
    <div className={`p-4 border rounded bg-${color}-50 dark:bg-${color}-900`}>
      <div className="text-4xl font-bold">{Math.round(completeness?.overall_score)}%</div>
      <div className="grid grid-cols-4 gap-2 mt-4">
        {Object.entries(completeness?.dimension_scores || {}).map(([dim, score]) => (
          <Circle key={dim} size={40} fill={scoreToColor(score)} title={dim} />
        ))}
      </div>
    </div>
  );
});
```

## Commit message
feat(programme-i): Completeness measurement dashboard — 16-dimension dossier assessment

## Test command
```bash
cd backend && python -m pytest tests/services/test_completeness_scorer.py -v
cd frontend && npm run validate
```

## Success criteria
- ✅ CompletenessScore + Report models created + migrations run
- ✅ Scorer calculates all 16 dimensions correctly
- ✅ Missing items identified and categorized (critical/important/nice-to-have)
- ✅ Recommended actions suggested based on missing items
- ✅ Overall score = weighted average of 16 dimensions
- ✅ CompletenessCard displays 16 color circles (visual dimension health)
- ✅ CompletenessBreakdown shows each dimension % + missing items
- ✅ MissingItemsChecklist interactive (mark as in_progress)
- ✅ CompletionTrend sparkline shows progress over time
- ✅ Admin PortfolioCompletenessView (scatter plot: completeness vs age, by canton)
- ✅ CompletenessLeaderboard (top 10 most complete)
- ✅ GapAnalysis (most common missing items)
- ✅ 20+ backend tests covering all 16 dimensions + edge cases
- ✅ 10+ frontend tests for card + breakdown + checklist
- ✅ Dark mode support
- ✅ No type errors, no warnings
