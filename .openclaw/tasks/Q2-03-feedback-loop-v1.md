# Task Q2.03 — AI Feedback Loop v1 (Data Flywheel)

## What to do
Implement user corrections → AI learning feedback mechanism. When users correct AI-extracted data (e.g., "this is not asbestos, it's concrete"), store correction as training signal to improve future extractions.

**Mechanism:**
1. Flag all AI-generated data with `ai_generated=True` and `ai_version=<model_version>`
2. On every edit by human, create `ai_feedback` record: {field_name, original_value, corrected_value, confidence_delta}
3. Service aggregates feedback: "asbestos extraction had 3 false positives in same building type → adjust threshold"
4. Confidence scores are reduced on re-extraction if previous corrections found

**Models:**
```python
class AIFeedback(Base):
    id: UUID
    entity_type: str  # diagnostic, material, sample, etc
    entity_id: UUID
    field_name: str  # e.g., "material_type", "hazard_level"
    original_value: str  # AI extracted value
    corrected_value: str  # human correction
    confidence_delta: float  # -0.15 if correction was wrong
    user_id: UUID
    model_version: str  # which model generated original
    created_at: datetime

class AIMetrics(Base):
    id: UUID
    entity_type: str
    field_name: str
    total_extractions: int
    total_corrections: int
    error_rate: float  # corrections / total_extractions
    common_errors: JSON  # [{original, corrected, count}]
    updated_at: datetime
```

**Workflow:**
1. When user edits diagnostic.material_type, capture before/after
2. Call `record_ai_feedback(entity_id, field_name, old, new, confidence_score)`
3. Aggregator updates AIMetrics (error_rate, common_errors)
4. Dashboard shows: "Material extraction: 92% accuracy, 3 corrections this week"

**API:**
- `POST /diagnostics/{id}/feedback` — record correction
- `GET /analytics/ai-metrics` — accuracy by entity_type + field_name

**Frontend:**
- "Edit" buttons on AI-extracted fields now include: "This is wrong? Tell us" link
- Quick correction modal (shows original + lets user correct + records feedback)
- Learning dashboard (admin view): top errors, accuracy trends

## Files to modify
- **Create:** `backend/app/models/ai_feedback.py` (25 lines)
- **Create:** `backend/app/models/ai_metrics.py` (20 lines)
- **Create:** `backend/app/services/ai_feedback_service.py` (60 lines)
- **Create:** `backend/app/schemas/ai_feedback.py` (20 lines)
- **Modify:** `backend/app/api/diagnostics.py` (add feedback endpoint, 15 lines)
- **Modify:** `backend/app/models/diagnostic.py` (add ai_version field, 2 lines)
- **Modify:** `backend/app/models/material.py` (add ai_version field, 2 lines)
- **Create:** `frontend/src/components/AIFeedbackModal.tsx` (80 lines)
- **Modify:** `frontend/src/components/fields/EditableField.tsx` (add feedback trigger, 10 lines)
- **Create:** `frontend/src/pages/Admin/AIMetricsBoard.tsx` (120 lines)
- **Create:** `backend/alembic/versions/0XX_add_ai_feedback_tables.py`
- **Create:** `backend/tests/services/test_ai_feedback_service.py` (10 tests)

## Existing patterns to copy

From `backend/app/models/diagnostic.py`:
```python
class Diagnostic(Base):
    __tablename__ = "diagnostics"
    ai_generated: bool = Column(Boolean, default=False)
    ai_generated_fields: JSON = Column(JSON, default={})  # {field: confidence}
```

From `frontend/src/components/editable/EditableField.tsx`:
```tsx
export const EditableField = memo(({ value, onChange, aiGenerated }: Props) => {
  const [isEditing, setIsEditing] = useState(false);
  
  const handleSave = async (newValue: string) => {
    if (aiGenerated) {
      // Record feedback
      await api.recordFeedback(entityId, fieldName, value, newValue);
    }
    onChange(newValue);
  };
  
  return (
    <div>
      {isEditing ? (
        <input value={value} onChange={e => handleSave(e.target.value)} />
      ) : (
        <div>
          {value}
          {aiGenerated && <button onClick={() => setIsEditing(true)}>Edit</button>}
        </div>
      )}
    </div>
  );
});
```

## Commit message
feat(programme-i): AI feedback loop v1 — track corrections, improve extraction accuracy

## Test command
```bash
cd backend && python -m pytest tests/services/test_ai_feedback_service.py -v
cd frontend && npm run validate
```

## Success criteria
- ✅ AIFeedback + AIMetrics models created + migrations run
- ✅ ai_generated flag added to diagnostic + material models
- ✅ Recording feedback captures original, correction, confidence
- ✅ Aggregator calculates error_rate correctly
- ✅ Common_errors JSON tracks top mistakes
- ✅ API endpoint POST /diagnostics/{id}/feedback working
- ✅ AIFeedbackModal shows on edit with "record feedback" option
- ✅ AIMetricsBoard displays accuracy trends + top errors
- ✅ 10+ tests covering feedback recording + aggregation
- ✅ Dark mode support
- ✅ No type errors, no warnings
