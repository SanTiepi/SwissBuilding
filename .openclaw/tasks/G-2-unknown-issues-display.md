# Task G.2 — Unknown Issues Explicit Display

## What to do
Make unknown/unresolved dossier gaps explicitly visible to users in the Building Home.

**Currently:**
- Completeness checker detects gaps (missing diagnostics, etc.)
- No dedicated display → users don't see what's uncertain
- No path to resolve gaps

**What to build:**
1. Create UnknownIssuesPanel component (similar to IncidentsPanel)
2. Query for incompleteness: missing layers, missing diagnostics, field observations needed
3. Display as prioritized list:
   - "🔴 CRITICAL: No asbestos diagnostic (>30 years old)"
   - "🟡 IMPORTANT: No lead test (pre-1970 property)"
   - "🟢 LOW: Radon measurement unknown (can be estimated)"
4. Each issue has:
   - Severity (red/amber/green)
   - Actionable next step ("Get diagnostic", "Field observe", "Accept estimate")
   - Estimated cost (if applicable)
   - Impact on trust score (if resolved)
5. Allow bulk actions: "Request all missing diagnostics" → generates task list

## Files to modify
- **Create:** `frontend/src/components/buildings/UnknownIssuesPanel.tsx` (140 lines)
- **Create:** `backend/app/services/unknown_issues_service.py` (80 lines)
- **Modify:** `backend/app/api/buildings.py` - add GET route for unknown issues (15 lines)
- **Create:** `backend/tests/services/test_unknown_issues_service.py` (8 tests)
- **Modify:** `frontend/src/pages/BuildingHome.tsx` - integrate panel (5 lines)
- **Create:** `frontend/src/components/buildings/__tests__/UnknownIssuesPanel.test.tsx` (6 tests)

## Service logic (backend)

```python
# backend/app/services/unknown_issues_service.py
from enum import Enum
from app.models import Building

class IssueSeverity(Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    LOW = "low"

class UnknownIssue:
    def __init__(self, label: str, severity: IssueSeverity, action: str, cost_estimate: float = None):
        self.label = label
        self.severity = severity
        self.action = action
        self.cost_estimate = cost_estimate

async def get_unknown_issues(db: AsyncSession, building_id: UUID) -> List[UnknownIssue]:
    """Detect gaps in building intelligence."""
    building = await db.execute(select(Building).where(Building.id == building_id))
    if not building:
        raise ValueError(f"Building {building_id} not found")

    issues = []

    # Check asbestos diagnostic (critical if >30 years old)
    if not building.has_asbestos_diagnostic and building.age_years > 30:
        issues.append(UnknownIssue(
            "No asbestos diagnostic on record",
            IssueSeverity.CRITICAL,
            "Order asbestos survey",
            cost_estimate=2000.0
        ))

    # Check lead (critical if pre-1970)
    if not building.has_lead_diagnostic and building.construction_year < 1970:
        issues.append(UnknownIssue(
            "Lead paint survey missing (pre-1970 property)",
            IssueSeverity.CRITICAL,
            "Order lead survey",
            cost_estimate=1500.0
        ))

    # Check radon (estimate possible but measurement better)
    if building.radon_zone == "high" and not building.radon_measurement:
        issues.append(UnknownIssue(
            "High radon zone — measurement recommended",
            IssueSeverity.IMPORTANT,
            "Order radon test or accept geological estimate",
            cost_estimate=300.0
        ))

    # Check field observations (low priority but improves trust)
    observation_count = await db.execute(
        select(FieldObservation).where(FieldObservation.building_id == building_id)
    )
    if observation_count.scalar() < 3:
        issues.append(UnknownIssue(
            "Field observations low — ground truth missing",
            IssueSeverity.LOW,
            "Schedule site visit",
            cost_estimate=500.0
        ))

    return sorted(issues, key=lambda x: ["critical", "important", "low"].index(x.severity.value))
```

## API endpoint
```python
@router.get("/{building_id}/unknown-issues")
async def get_unknown_issues(
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("buildings", "read")),
):
    return await unknown_issues_service.get_unknown_issues(db, building_id)
```

## Frontend component snippet
```tsx
export const UnknownIssuesPanel = memo(({ building_id }: Props) => {
  const { issues, loading } = useUnknownIssues(building_id);

  if (loading) return <div>Loading issues...</div>;
  if (issues.length === 0) return <div className="p-4 text-green-700">✅ Dossier complet!</div>;

  return (
    <div className="p-6 border rounded-lg bg-gray-50 dark:bg-gray-800">
      <h3 className="text-lg font-semibold mb-4">Lacunes à traiter</h3>
      <div className="space-y-3">
        {issues.map((issue, idx) => (
          <div key={idx} className={cn(
            "p-3 rounded border-l-4",
            issue.severity === "critical" ? "bg-red-50 border-red-400" :
            issue.severity === "important" ? "bg-amber-50 border-amber-400" :
            "bg-green-50 border-green-400"
          )}>
            <div className="font-semibold text-sm">{issue.label}</div>
            <div className="text-xs text-gray-600 mt-1">Recommandation: {issue.action}</div>
            {issue.cost_estimate && (
              <div className="text-xs text-gray-600">Coût estimé: CHF {issue.cost_estimate}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
});
```

## Commit message
```
feat(programme-g): unknown issues panel — explicit gaps + actionable next steps
```

## Test command
```bash
cd backend && python -m pytest tests/services/test_unknown_issues_service.py -v
cd frontend && npm run validate && npm test -- UnknownIssuesPanel
```

## Notes
- Use color coding: red (critical), amber (important), green (low)
- "Request diagnostics" button should link to task creation workflow
- This is a TRUST BUILDER — showing what you don't know is honesty
- Estimated cost helps users prioritize
