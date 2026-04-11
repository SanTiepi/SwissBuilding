# Task I.2 — Expert Review & Override Governance

## What to do
Wire expert review and override capability for automated system decisions (contradictions, risk scores, etc.).

**Currently:**
- System makes autonomous decisions (risk scores, completeness, trust score)
- No way for human expert to override or review
- No audit trail of decisions

**What to build:**
1. Create ExpertReview model with fields:
   - decision_type (contradiction_resolution, risk_score_adjustment, trust_score_correction, etc.)
   - original_value, expert_value
   - expert_notes (explanation for override)
   - expert_approval_status (pending/approved/rejected)
   - expert_timestamp

2. Add ExpertReviewQueue page showing:
   - Flagged decisions needing human review
   - Current system value vs. expert override value
   - Audit trail (who approved, when, why)

3. Wire into key decision points:
   - When contradiction severity is HIGH → requires expert review
   - When trust score < 50 → expert verification required
   - When risk score changes > 10 points → flag for review

4. Add ExpertGate in services:
   - Check if decision has expert override
   - Use override value if exists, otherwise use computed value

5. Create audit log of all expert decisions

## Files to create/modify

**Create:**
- `backend/app/models/expert_review.py` (50 lines)
- `backend/app/services/expert_review_service.py` (100 lines)
- `backend/app/api/expert_reviews.py` (new router, 60 lines)
- `backend/tests/services/test_expert_review_service.py` (8 tests)
- `frontend/src/pages/ExpertReviewQueue.tsx` (200 lines)
- `frontend/src/components/ExpertDecisionCard.tsx` (100 lines)
- `frontend/src/components/__tests__/ExpertDecisionCard.test.tsx` (6 tests)

**Modify:**
- `backend/app/models/__init__.py` - import ExpertReview
- `backend/app/services/contradiction_detection_service.py` - check for expert override before returning
- `backend/app/services/trust_score_service.py` - check for expert override
- `backend/app/api/buildings.py` - integrate expert gate in risk score endpoint
- `frontend/src/App.tsx` - add ExpertReviewQueue route (only for admin users)

## ExpertReview model
```python
# backend/app/models/expert_review.py
from sqlalchemy import Column, String, UUID, DateTime, Enum, Text, JSON, ForeignKey
from enum import Enum as PyEnum

class DecisionType(PyEnum):
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    RISK_SCORE_ADJUSTMENT = "risk_score_adjustment"
    TRUST_SCORE_CORRECTION = "trust_score_correction"
    MATERIAL_RECLASSIFICATION = "material_reclassification"
    DIAGNOSTIC_OVERRIDE = "diagnostic_override"
    COMPLETENESS_WAIVER = "completeness_waiver"

class ReviewStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ExpertReview(Base):
    __tablename__ = "expert_reviews"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    building_id: UUID = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    
    decision_type: DecisionType = Column(Enum(DecisionType), nullable=False)
    
    # What triggered the review
    subject_id: str = Column(String)  # ID of the object being reviewed (contradiction_id, etc.)
    system_value: str = Column(String)  # Original system-computed value
    system_reasoning: str = Column(Text)  # Why the system made this decision
    
    # Expert override
    expert_value: str = Column(String, nullable=True)  # What expert decided instead
    expert_notes: str = Column(Text)  # Expert explanation for override
    expert_id: UUID = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Who approved
    
    review_status: ReviewStatus = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING)
    priority: str = Column(String(10), default="normal")  # high, normal, low
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    reviewed_at: datetime = Column(DateTime, nullable=True)
    
    # Metadata
    metadata: dict = Column(JSON, default=dict)  # Extra context

class ExpertAuditLog(Base):
    """Track all expert decisions for compliance."""
    __tablename__ = "expert_audit_logs"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    building_id: UUID = Column(UUID(as_uuid=True), ForeignKey("buildings.id"))
    expert_id: UUID = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    action: str = Column(String)  # "approved_override", "rejected_override"
    decision_type: DecisionType = Column(Enum(DecisionType))
    
    original_value: str = Column(String)
    new_value: str = Column(String)
    reasoning: str = Column(Text)
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

## Service logic
```python
# backend/app/services/expert_review_service.py
class ExpertReviewService:
    @staticmethod
    async def flag_for_review(
        db: AsyncSession,
        building_id: UUID,
        decision_type: DecisionType,
        subject_id: str,
        system_value: str,
        system_reasoning: str,
        priority: str = "normal"
    ) -> ExpertReview:
        """Flag a decision for expert review."""
        review = ExpertReview(
            building_id=building_id,
            decision_type=decision_type,
            subject_id=subject_id,
            system_value=system_value,
            system_reasoning=system_reasoning,
            priority=priority
        )
        db.add(review)
        db.commit()
        return review
    
    @staticmethod
    async def get_pending_reviews(db: AsyncSession) -> List[ExpertReview]:
        """Get all pending expert reviews."""
        return await db.execute(
            select(ExpertReview)
            .where(ExpertReview.review_status == ReviewStatus.PENDING)
            .order_by(ExpertReview.priority.desc(), ExpertReview.created_at)
        ).scalars().all()
    
    @staticmethod
    async def approve_override(
        db: AsyncSession,
        review_id: UUID,
        expert_value: str,
        expert_notes: str,
        expert_id: UUID
    ) -> ExpertReview:
        """Expert approves override."""
        review = await db.execute(select(ExpertReview).where(ExpertReview.id == review_id))
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        review.expert_value = expert_value
        review.expert_notes = expert_notes
        review.expert_id = expert_id
        review.review_status = ReviewStatus.APPROVED
        review.reviewed_at = datetime.utcnow()
        
        # Log the decision
        log = ExpertAuditLog(
            building_id=review.building_id,
            expert_id=expert_id,
            action="approved_override",
            decision_type=review.decision_type,
            original_value=review.system_value,
            new_value=expert_value,
            reasoning=expert_notes
        )
        
        db.add(review)
        db.add(log)
        db.commit()
        return review
    
    @staticmethod
    async def get_final_value(db: AsyncSession, building_id: UUID, decision_type: DecisionType, subject_id: str):
        """Get final value for a decision (expert override or system value)."""
        review = await db.execute(
            select(ExpertReview).where(
                ExpertReview.building_id == building_id,
                ExpertReview.decision_type == decision_type,
                ExpertReview.subject_id == subject_id,
                ExpertReview.review_status == ReviewStatus.APPROVED
            )
        ).scalar()
        
        # If expert approved override, use that value
        if review and review.expert_value:
            return {
                "value": review.expert_value,
                "source": "expert_override",
                "expert_id": review.expert_id,
                "reasoning": review.expert_notes
            }
        
        # Otherwise, use system value
        return {
            "value": review.system_value if review else None,
            "source": "system_computed"
        }
```

## API endpoints
```python
@router.get("/expert-reviews/pending")
async def get_pending_reviews(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("admin", "review"))
):
    """Get pending expert reviews (admin only)."""
    return await ExpertReviewService.get_pending_reviews(db)

@router.patch("/expert-reviews/{review_id}/approve")
async def approve_expert_override(
    review_id: UUID,
    override_data: ExpertOverrideData,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("admin", "review"))
):
    """Expert approves a system decision override."""
    return await ExpertReviewService.approve_override(
        db,
        review_id,
        override_data.expert_value,
        override_data.expert_notes,
        user.id
    )
```

## Integration in contradiction service
```python
# In contradiction_detection_service.py
async def detect_contradictions(db: AsyncSession, building_id: UUID):
    contradictions = []
    # ... detection logic ...
    
    for contradiction in contradictions:
        # High-severity contradictions require expert review
        if contradiction.severity == ContradictionSeverity.HIGH:
            await ExpertReviewService.flag_for_review(
                db,
                building_id,
                DecisionType.CONTRADICTION_RESOLUTION,
                str(contradiction.id),
                f"{contradiction.source_1_value} vs {contradiction.source_2_value}",
                f"Data contradiction detected in {contradiction.field}",
                priority="high"
            )
    
    return contradictions
```

## Frontend page
```tsx
export const ExpertReviewQueue = () => {
  const { reviews, loading } = useExpertReviews();

  if (loading) return <div>Loading reviews...</div>;

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Expert Review Queue</h1>
      
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-red-50 rounded">
          <div className="text-2xl font-bold text-red-700">{reviews.filter(r => r.priority === 'high').length}</div>
          <div className="text-xs text-red-600">High Priority</div>
        </div>
        <div className="p-4 bg-amber-50 rounded">
          <div className="text-2xl font-bold text-amber-700">{reviews.filter(r => r.priority === 'normal').length}</div>
          <div className="text-xs text-amber-600">Normal Priority</div>
        </div>
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-2xl font-bold text-blue-700">{reviews.filter(r => r.priority === 'low').length}</div>
          <div className="text-xs text-blue-600">Low Priority</div>
        </div>
      </div>

      <div className="space-y-4">
        {reviews.map((review) => (
          <ExpertDecisionCard key={review.id} review={review} />
        ))}
      </div>
    </div>
  );
};
```

## Commit message
```
feat(programme-i): expert review & override governance — audit trail for critical decisions
```

## Test command
```bash
cd backend && python -m pytest tests/services/test_expert_review_service.py -v
cd frontend && npm run validate && npm test -- ExpertReviewQueue
```

## Notes
- Expert review is **gated access** (admin/expert role only)
- Every override creates immutable audit log for compliance
- Flag contradictions, risk scores, completeness decisions automatically
- Reviewers can approve override or reject (use system value)
- This is essential for **legal-grade proof** requirements
