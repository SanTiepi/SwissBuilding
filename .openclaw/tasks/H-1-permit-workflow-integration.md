# Task H.1 — Permit Workflow Integration (Public Funding Track)

## What to do
Wire permit workflow into the application: track renovation permits, deadlines, approval status, and linked public funding applications.

**Currently:**
- No permit tracking
- No deadline management for permits
- No link between permit status and subsidy eligibility

**What to build:**
1. Create Permit model with fields:
   - permit_number, permit_type (renovation/demolition/construction)
   - authority (cantonal/communal)
   - submission_date, approval_date, expiry_date
   - status (draft/submitted/approved/rejected/expired)
   - linked_subsidy_ids (reference to subsidy applications)

2. Add API endpoints:
   - POST /buildings/{building_id}/permits (create)
   - GET /buildings/{building_id}/permits (list)
   - PATCH /buildings/{building_id}/permits/{permit_id} (update status)
   - GET /buildings/{building_id}/permits/{permit_id}/deadline-alerts (upcoming expirations)

3. Add PermitManagementPanel in BuildingHome showing:
   - Active permits with status badges
   - Expiry dates (red if < 30 days)
   - Linked subsidies (show subsidy amount + deadline)
   - Upload permit document

4. Add permit deadline alerts to notification system
   - "Permit expires in 30 days"
   - "Subsidy deadline approaching for permit #xxx"

## Files to create/modify

**Create:**
- `backend/app/models/permit.py` (permit model, 50 lines)
- `backend/app/services/permit_service.py` (100 lines, CRUD + deadline logic)
- `backend/app/api/permits.py` (new router, 50 lines)
- `backend/tests/services/test_permit_service.py` (10 tests)
- `frontend/src/components/buildings/PermitManagementPanel.tsx` (160 lines)
- `frontend/src/hooks/usePermits.ts` (40 lines)
- `frontend/src/components/buildings/__tests__/PermitManagementPanel.test.tsx` (8 tests)

**Modify:**
- `backend/app/models/__init__.py` - import Permit model
- `backend/app/models/building.py` - add relationship to permits (2 lines)
- `backend/alembic/versions/` - create migration
- `frontend/src/pages/BuildingHome.tsx` - integrate PermitManagementPanel (5 lines)
- `backend/app/services/notification_service.py` - add permit deadline alert trigger (10 lines)

## Permit model
```python
# backend/app/models/permit.py
from sqlalchemy import Column, String, UUID, DateTime, Enum, ForeignKey, Text
from enum import Enum as PyEnum
from datetime import datetime

class PermitType(PyEnum):
    RENOVATION = "renovation"
    DEMOLITION = "demolition"
    CONSTRUCTION = "construction"
    MODIFICATION = "modification"

class PermitStatus(PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class Permit(Base):
    __tablename__ = "permits"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    building_id: UUID = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    
    permit_number: str = Column(String(50), nullable=True)
    permit_type: PermitType = Column(Enum(PermitType), nullable=False)
    authority: str = Column(String(100))  # e.g., "Service de l'environnement VD"
    
    submission_date: datetime = Column(DateTime)
    approval_date: datetime = Column(DateTime, nullable=True)
    expiry_date: datetime = Column(DateTime)  # When permit expires
    
    status: PermitStatus = Column(Enum(PermitStatus), default=PermitStatus.DRAFT)
    notes: str = Column(Text, nullable=True)
    
    # Linked subsidies (JSON array of subsidy_ids)
    linked_subsidy_ids: List[UUID] = Column(JSON, default=list)
    
    # Document storage
    permit_document_url: str = Column(String, nullable=True)
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Service logic
```python
# backend/app/services/permit_service.py
from app.models import Permit, Building
from app.schemas import PermitCreate, PermitUpdate
from datetime import datetime, timedelta

class PermitService:
    @staticmethod
    async def create_permit(db: AsyncSession, building_id: UUID, permit_data: PermitCreate) -> Permit:
        """Create a new permit for a building."""
        building = await db.execute(select(Building).where(Building.id == building_id))
        if not building:
            raise ValueError(f"Building {building_id} not found")
        
        permit = Permit(
            building_id=building_id,
            permit_type=permit_data.permit_type,
            authority=permit_data.authority,
            submission_date=permit_data.submission_date,
            expiry_date=permit_data.expiry_date,
            status=PermitStatus.DRAFT
        )
        
        db.add(permit)
        db.commit()
        return permit
    
    @staticmethod
    async def get_deadline_alerts(db: AsyncSession, building_id: UUID) -> List[dict]:
        """Get permits expiring soon."""
        permits = await db.execute(
            select(Permit).where(
                Permit.building_id == building_id,
                Permit.status != PermitStatus.EXPIRED
            )
        )
        
        alerts = []
        now = datetime.utcnow()
        thirty_days = now + timedelta(days=30)
        
        for permit in permits.scalars().all():
            if permit.expiry_date < thirty_days:
                days_left = (permit.expiry_date - now).days
                alerts.append({
                    "permit_id": permit.id,
                    "type": "permit_expiry",
                    "severity": "critical" if days_left < 7 else "warning",
                    "message": f"Permit {permit.permit_number} expires in {days_left} days",
                    "action": "Renew permit"
                })
        
        return sorted(alerts, key=lambda x: x["severity"])
    
    @staticmethod
    async def update_permit_status(db: AsyncSession, permit_id: UUID, new_status: PermitStatus) -> Permit:
        """Update permit status (e.g., submitted → approved)."""
        permit = await db.execute(select(Permit).where(Permit.id == permit_id))
        if not permit:
            raise ValueError(f"Permit {permit_id} not found")
        
        permit.status = new_status
        if new_status == PermitStatus.APPROVED:
            permit.approval_date = datetime.utcnow()
        
        db.add(permit)
        db.commit()
        return permit
```

## API endpoints
```python
# backend/app/api/permits.py
@router.post("/{building_id}/permits")
async def create_permit(
    building_id: UUID,
    permit_data: PermitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("buildings", "edit"))
):
    """Create a new permit."""
    return await PermitService.create_permit(db, building_id, permit_data)

@router.get("/{building_id}/permits")
async def list_permits(
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("buildings", "read"))
):
    """List all permits for a building."""
    permits = await db.execute(
        select(Permit).where(Permit.building_id == building_id).order_by(Permit.expiry_date)
    )
    return permits.scalars().all()

@router.patch("/{building_id}/permits/{permit_id}")
async def update_permit(
    building_id: UUID,
    permit_id: UUID,
    permit_update: PermitUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("buildings", "edit"))
):
    """Update permit status."""
    return await PermitService.update_permit_status(db, permit_id, permit_update.status)

@router.get("/{building_id}/permits/deadline-alerts")
async def get_permit_alerts(
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("buildings", "read"))
):
    """Get deadline alerts for permits."""
    return await PermitService.get_deadline_alerts(db, building_id)
```

## Frontend component
```tsx
export const PermitManagementPanel = memo(({ building_id }: Props) => {
  const { permits, alerts, loading } = usePermits(building_id);

  if (loading) return <div>Loading permits...</div>;

  return (
    <div className="p-6 border rounded-lg bg-white dark:bg-gray-900">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Permis & Deadlines</h3>
        <button className="bg-blue-500 text-white px-4 py-2 rounded text-sm">
          + Ajouter permis
        </button>
      </div>

      {alerts.length > 0 && (
        <div className="mb-4 space-y-2">
          {alerts.map((alert) => (
            <div key={alert.permit_id} className={cn(
              "p-2 text-xs rounded",
              alert.severity === "critical" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
            )}>
              ⚠️ {alert.message} → {alert.action}
            </div>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {permits.map((permit) => (
          <div key={permit.id} className="p-3 border rounded bg-gray-50 dark:bg-gray-800">
            <div className="flex justify-between items-start mb-2">
              <div>
                <div className="font-semibold text-sm">{permit.permit_type} — {permit.permit_number}</div>
                <div className="text-xs text-gray-600">{permit.authority}</div>
              </div>
              <span className={cn("text-xs font-bold px-2 py-1 rounded",
                permit.status === "approved" ? "bg-green-100 text-green-700" :
                permit.status === "submitted" ? "bg-blue-100 text-blue-700" :
                permit.status === "rejected" ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-700"
              )}>
                {permit.status}
              </span>
            </div>
            
            <div className="text-xs text-gray-600 mb-2">
              Expiry: {format(permit.expiry_date, 'dd.MM.yyyy')} 
              {isWithin30Days(permit.expiry_date) && " 🚩"}
            </div>
            
            {permit.linked_subsidy_ids.length > 0 && (
              <div className="text-xs text-blue-600 mb-2">
                🔗 Linked to {permit.linked_subsidy_ids.length} subsidy application(s)
              </div>
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
feat(programme-h): permit workflow integration — track permits, deadlines, linked subsidies
```

## Test command
```bash
cd backend && python -m pytest tests/services/test_permit_service.py -v
cd frontend && npm run validate && npm test -- PermitManagementPanel
```

## Notes
- Permits expire after expiry_date — auto-mark as EXPIRED via cron job
- Permit expiry should trigger notification 30, 14, 7 days before
- Permits can be linked to subsidies for unified deadline tracking
- Upload permit documents for record-keeping
