# Task G.3 — Contradiction Detection Visible in Dossier

## What to do
Detect and surface data contradictions (conflicting diagnostics, observations, test results) explicitly in the Building Home.

**Examples of contradictions:**
- Diagnostic A says "asbestos negative" but Diagnostic B says "asbestos positive" → 🚩 conflict
- Field observation says "roof in good condition" but 3 months later "roof damaged" → 🚩 timeline problem
- Material inventory says "PVC tiles 1975" but diagnostic says "asbestos tiles detected" → 🚩 mismatch
- Lab report says "lead positive" but visual inspection says "no lead" → 🚩 needs investigation

**What to build:**
1. Create contradiction detection service that compares:
   - Diagnostic results (asbestos, lead, PCB, radon)
   - Field observations (material type, condition)
   - Material inventory (recorded vs actual)
   - Timeline (ordering of events)
2. Store detected contradictions in `Contradiction` model (create if needed)
3. Display in a ContradictionPanel with:
   - Source 1 vs Source 2 comparison
   - Severity (high = safety risk, low = cosmetic)
   - Recommended resolution (lab retest, expert visit, acknowledge gap)
4. Show contradiction count in header (badge)
5. Allow marking as "resolved", "acknowledged", or "pending review"

## Files to create/modify

**Create:**
- `backend/app/services/contradiction_detection_service.py` (120 lines)
- `backend/app/models/contradiction.py` (model definition, 40 lines)
- `backend/tests/services/test_contradiction_detection_service.py` (10 tests)
- `frontend/src/components/buildings/ContradictionPanel.tsx` (150 lines)
- `frontend/src/components/buildings/__tests__/ContradictionPanel.test.tsx` (8 tests)

**Modify:**
- `backend/app/models/__init__.py` - import Contradiction model
- `backend/app/api/buildings.py` - add GET route for contradictions (15 lines)
- `backend/app/models/building.py` - add relationship to contradictions (2 lines)
- `frontend/src/pages/BuildingHome.tsx` - integrate panel (5 lines)

## Contradiction model
```python
# backend/app/models/contradiction.py
from sqlalchemy import Column, String, UUID, DateTime, Enum
from enum import Enum as PyEnum

class ContradictionSeverity(PyEnum):
    HIGH = "high"      # Safety risk
    MEDIUM = "medium"  # Data quality issue
    LOW = "low"        # Cosmetic, informational

class Contradiction(Base):
    __tablename__ = "contradictions"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    building_id: UUID = Column(UUID(as_uuid=True), ForeignKey("buildings.id"))
    
    # What's contradicting
    field: str = Column(String(100))  # e.g., "asbestos", "roof_condition", "material_type"
    source_1: str = Column(String)    # e.g., "diagnostic_2023"
    source_1_value: str = Column(String)
    source_1_date: datetime = Column(DateTime)
    
    source_2: str = Column(String)    # e.g., "observation_2023"
    source_2_value: str = Column(String)
    source_2_date: datetime = Column(DateTime)
    
    severity: ContradictionSeverity = Column(Enum(ContradictionSeverity), default=ContradictionSeverity.MEDIUM)
    
    # Resolution
    status: str = Column(String(20), default="pending")  # pending | acknowledged | resolved
    resolution_note: str = Column(String, nullable=True)
    resolved_by_user_id: UUID = Column(UUID(as_uuid=True), nullable=True)
    resolved_at: datetime = Column(DateTime, nullable=True)
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Service logic
```python
# backend/app/services/contradiction_detection_service.py
from app.models import Contradiction, Diagnostic, FieldObservation, Material

async def detect_contradictions(db: AsyncSession, building_id: UUID) -> List[Contradiction]:
    """Detect conflicting data in building dossier."""
    
    building = await db.execute(select(Building).where(Building.id == building_id))
    if not building:
        raise ValueError(f"Building {building_id} not found")
    
    contradictions = []
    
    # 1. Asbestos contradictions (diagnostic A vs B)
    asbestos_diags = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.type == "asbestos"
        ).order_by(Diagnostic.date)
    )
    asbestos_results = asbestos_diags.scalars().all()
    
    for i in range(len(asbestos_results) - 1):
        d1, d2 = asbestos_results[i], asbestos_results[i + 1]
        if d1.result != d2.result:  # e.g., "positive" vs "negative"
            contradictions.append(Contradiction(
                building_id=building_id,
                field="asbestos",
                source_1=f"diagnostic_{d1.id}",
                source_1_value=d1.result,
                source_1_date=d1.date,
                source_2=f"diagnostic_{d2.id}",
                source_2_value=d2.result,
                source_2_date=d2.date,
                severity=ContradictionSeverity.HIGH if "positive" in [d1.result, d2.result] else ContradictionSeverity.MEDIUM
            ))
    
    # 2. Material type contradictions (inventory vs observation)
    materials = await db.execute(
        select(Material).where(Material.building_id == building_id)
    )
    
    for material in materials.scalars().all():
        observations = await db.execute(
            select(FieldObservation).where(
                FieldObservation.building_id == building_id,
                FieldObservation.zone == material.zone
            )
        )
        
        for obs in observations.scalars().all():
            if obs.observed_material_type != material.type:
                contradictions.append(Contradiction(
                    building_id=building_id,
                    field="material_type",
                    source_1=f"inventory_{material.id}",
                    source_1_value=material.type,
                    source_1_date=material.created_at,
                    source_2=f"observation_{obs.id}",
                    source_2_value=obs.observed_material_type,
                    source_2_date=obs.observation_date,
                    severity=ContradictionSeverity.HIGH
                ))
    
    # 3. Timeline contradictions (condition degradation too fast)
    # If roof is "good" at time A and "damaged" at time B within 6 months → suspicious
    # (Could be real if there was a storm, but flag it)
    
    db.add_all(contradictions)
    db.commit()
    
    return contradictions
```

## Frontend display
```tsx
export const ContradictionPanel = memo(({ building_id }: Props) => {
  const { contradictions, loading } = useContradictions(building_id);

  if (loading) return <div>Analyzing dossier...</div>;
  if (contradictions.length === 0) return <div className="p-4 text-green-700">✅ Dossier cohérent</div>;

  return (
    <div className="p-6 border rounded-lg bg-white dark:bg-gray-900">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Incohérences détectées</h3>
        <span className="bg-red-500 text-white rounded-full px-2 py-1 text-xs font-bold">
          {contradictions.length}
        </span>
      </div>
      
      <div className="space-y-4">
        {contradictions.map((c) => (
          <div key={c.id} className={cn(
            "p-4 rounded border-l-4",
            c.severity === "high" ? "bg-red-50 border-red-500" :
            c.severity === "medium" ? "bg-amber-50 border-amber-500" :
            "bg-blue-50 border-blue-500"
          )}>
            <div className="font-semibold text-sm mb-2">{c.field.replace(/_/g, ' ').toUpperCase()}</div>
            
            <div className="flex items-center gap-2 text-xs mb-3">
              <div className="flex-1">
                <div className="text-gray-500">Source 1</div>
                <div className="font-semibold text-gray-800">{c.source_1_value}</div>
                <div className="text-gray-500 text-xs">{c.source_1} • {format(c.source_1_date)}</div>
              </div>
              <div className="px-2 text-gray-400">≠</div>
              <div className="flex-1">
                <div className="text-gray-500">Source 2</div>
                <div className="font-semibold text-gray-800">{c.source_2_value}</div>
                <div className="text-gray-500 text-xs">{c.source_2} • {format(c.source_2_date)}</div>
              </div>
            </div>
            
            <select 
              value={c.status}
              onChange={(e) => updateContradictionStatus(c.id, e.target.value)}
              className="text-xs p-1 border rounded"
            >
              <option value="pending">Pending Review</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        ))}
      </div>
    </div>
  );
});
```

## Commit message
```
feat(programme-g): contradiction detection — surface data conflicts explicitly
```

## Test command
```bash
cd backend && python -m pytest tests/services/test_contradiction_detection_service.py -v
cd frontend && npm run validate && npm test -- ContradictionPanel
```

## Notes
- This is **trust-building** work: "we found a problem" is better than silent inconsistency
- Mark contradictions with high severity (safety risk) in red
- Include timeline logic: if two events are very close in time, flag as suspicious
- Allow users to acknowledge contradictions they're aware of ("we redid the test")
