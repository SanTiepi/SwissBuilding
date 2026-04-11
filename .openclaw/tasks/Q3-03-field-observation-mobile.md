# Task Q3.03 — Field Observation v1 (Mobile-Friendly)

## What to do
Implement mobile-friendly field observation form for on-site inspectors. Allows quick capture of structural/material observations without full diagnostic workflow.

**Observation form includes:**
1. Building element selection (roof, walls, basement, etc)
2. Photo capture (multiple angles)
3. Condition assessment (good/fair/poor/critical)
4. Risk flags (water stain, crack, mold visible, etc)
5. Notes (voice-to-text or text)
6. Location tagging (GPS + building element visual selector)
7. Contractor/inspector sign-off

**Data model:**
```python
class FieldObservation(Base):
    id: UUID
    building_id: UUID
    building_element_id: UUID
    observer_name: str
    observer_id: UUID
    observation_date: datetime
    photos: JSON  # [{uri, element_part, timestamp}]
    condition_assessment: str  # good/fair/poor/critical
    risk_flags: JSON  # [water_stain, crack, mold, rust, deformation]
    notes: str
    gps_lat: float
    gps_lon: float
    compass_direction: Optional[str]  # north/south/east/west
    inspection_duration_minutes: int
    ai_observation_summary: Optional[str]  # Claude Vision summary
    ai_generated: bool = True
    created_at: datetime

class ObservationRiskScore(Base):
    field_observation_id: UUID
    building_id: UUID
    risk_score: float  # 0-100 based on flags + condition
    recommended_action: str  # investigate_further, monitor, urgent_diagnosis
    urgency_level: str  # low/medium/high/critical
```

**API:**
- `POST /buildings/{id}/field-observations` — create observation
- `GET /buildings/{id}/field-observations` — list observations
- `GET /buildings/{id}/field-observations/{id}` — detail + risk assessment

**Frontend (mobile-first):**
- ObservationForm component (big buttons, vertical layout for phone)
- Building element selector (visual grid + touch-friendly buttons)
- PhotoCapture widget (camera integration, batch upload)
- ConditionPicker (A/B/C/D difficulty picker style)
- RiskFlagCheckboxes (large touch targets)
- VoiceToText input for notes
- PreviewScreen (review before submission)
- ConfirmationScreen (submitted ✓, next steps)

## Files to modify
- **Create:** `backend/app/models/field_observation.py` (35 lines)
- **Create:** `backend/app/models/observation_risk_score.py` (20 lines)
- **Create:** `backend/app/services/observation_risk_scorer.py` (60 lines)
- **Create:** `backend/app/schemas/field_observation.py` (30 lines)
- **Modify:** `backend/app/api/buildings.py` (add observation endpoints, 25 lines)
- **Create:** `frontend/src/pages/FieldObservation/ObservationForm.tsx` (300 lines, mobile-first)
- **Create:** `frontend/src/components/observation/BuildingElementSelector.tsx` (150 lines)
- **Create:** `frontend/src/components/observation/PhotoCaptureWidget.tsx` (120 lines)
- **Create:** `frontend/src/components/observation/ConditionPicker.tsx` (80 lines)
- **Create:** `frontend/src/components/observation/RiskFlagCheckboxes.tsx` (60 lines)
- **Create:** `frontend/src/components/observation/VoiceInput.tsx` (60 lines)
- **Modify:** `frontend/src/pages/Building/BuildingHome.tsx` (link to observations, 5 lines)
- **Create:** `backend/alembic/versions/0XX_add_field_observations.py`
- **Create:** `backend/tests/services/test_observation_risk_scorer.py` (10 tests)
- **Create:** `frontend/src/pages/FieldObservation/ObservationForm.test.tsx` (12 tests)

## Existing patterns to copy

From `frontend/src/pages/Contractor/MaterialPhotoCapture.tsx`:
```tsx
const PhotoCaptureWidget = memo(({ onCapture }: Props) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const capturePhoto = async () => {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    ctx?.drawImage(videoRef.current!, 0, 0);
    const blob = await new Promise(r => canvas.toBlob(r));
    onCapture(blob);
  };
  
  return (
    <div>
      <video ref={videoRef} autoPlay playsInline />
      <button onClick={capturePhoto}>Capture</button>
    </div>
  );
});
```

From `backend/app/services/geo_context_service.py` (risk scoring pattern):
```python
async def calculate_risk_score(observation: FieldObservation) -> float:
    base_score = CONDITION_SCORES[observation.condition_assessment]
    risk_multipliers = {
        "water_stain": 1.3,
        "crack": 1.25,
        "mold": 1.4,
    }
    for flag in observation.risk_flags:
        base_score *= risk_multipliers.get(flag, 1.0)
    return min(base_score, 100)
```

## Commit message
feat(programme-g): Field observation v1 — mobile-friendly on-site inspection capture

## Test command
```bash
cd backend && python -m pytest tests/services/test_observation_risk_scorer.py -v
cd frontend && npm run validate
npm run test:e2e  # mobile form flow
```

## Success criteria
- ✅ FieldObservation + ObservationRiskScore models created + migrations run
- ✅ Mobile form responsive on viewport widths 320px+ (phone-first)
- ✅ Photo capture working (camera access via getUserMedia)
- ✅ Building element selector visual (icons + labels)
- ✅ Condition picker easy to use (A-D large buttons)
- ✅ Risk flags with checkboxes (multiple selection)
- ✅ Voice-to-text working (Web Speech API)
- ✅ GPS location captured if available
- ✅ Risk score calculated from condition + risk_flags
- ✅ Recommended actions clear (investigate_further, monitor, urgent)
- ✅ API endpoints POST/GET working
- ✅ 10+ backend tests for risk scoring
- ✅ 12+ frontend tests for form submission + photo upload
- ✅ Dark mode support on mobile form
- ✅ No type errors, no warnings
- ✅ Fast load time on mobile (lazy load media)
