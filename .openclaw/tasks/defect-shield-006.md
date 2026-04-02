# Task: DefectShield — Frontend widget + badge

## Commit message
feat(defect-shield): add frontend widget + urgency badge to Building Home

## What to do
Ensure the DefectTimelineWidget (which already exists) is wired into the Building Home / Overview page, showing a list of active/notified defects with urgency badges (red <15 days, orange 15-30, yellow 30-45, green >45), status colors, timeline info, and action buttons (create new defect, update status, generate PDF letter). Widget should be responsive, support dark mode, and use existing AsyncStateWrapper patterns for loading/error states.

## Files to modify
- `frontend/src/components/building-detail/DefectTimelineWidget.tsx` (verify complete; should have: list defects, status badges, urgency colors, create modal, action buttons, dark mode)
- `frontend/src/components/building-detail/BuildingHomeView.tsx` (integrate DefectTimelineWidget if not already present)
- `frontend/src/api/defectTimeline.ts` (verify hooks: useListDefects, useCreateDefect, useUpdateDefect, useDeleteDefect, useGenerateLetter)
- `frontend/tests/DefectTimelineWidget.test.tsx` (add tests: render list, click create, update status, generate PDF)

## Existing patterns to follow

From `DefectTimelineWidget.tsx` (component structure):
```tsx
export function DefectTimelineWidget({ buildingId }: Props) {
  const { t } = useTranslation();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { data, isLoading, error } = useQuery(...); // list defects

  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-lg">
      <h3>{t('defects.title')}</h3>
      <AsyncStateWrapper loading={isLoading} error={error}>
        {data?.map(timeline => (
          <DefectCard key={timeline.id} timeline={timeline} />
        ))}
      </AsyncStateWrapper>
      <Button onClick={() => setShowCreateModal(true)}>+ Add Defect</Button>
      {showCreateModal && <DefectCreateModal onClose={...} onSuccess={...} />}
    </div>
  );
}

// Status badge with color: active (blue), notified (green), expired (gray), resolved (green)
// Urgency dot + text: red/orange/yellow/green based on days_remaining
```

From existing BuildingHomeView patterns:
```tsx
<Section title="Building Overview">
  <DefectTimelineWidget buildingId={building.id} />
  {/* other widgets */}
</Section>
```

## Acceptance criteria
- [ ] Widget displays list of defects with status, urgency, discovery date, deadline
- [ ] Urgency colors work (red <15, orange 15-30, yellow 30-45, green >45 days)
- [ ] Status badges show active/notified/expired/resolved with correct colors
- [ ] Create button opens modal with form (discovery_date, defect_type, description)
- [ ] Update status dropdown (active→notified, notified→resolved, expired→resolved)
- [ ] Generate PDF button calls backend endpoint and downloads file
- [ ] Delete button soft-deletes with confirmation
- [ ] Dark mode classes (dark:) applied to all elements
- [ ] AsyncStateWrapper handles loading/error/empty states
- [ ] Widget integrated into Building Home view
- [ ] Tests pass for all interactions
- [ ] No regression in existing building tests

## Test command
cd frontend && npm test -- DefectTimelineWidget && npm test -- BuildingHomeView

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Follow existing dark mode pattern (dark: classes + cn() for conditionals)
- Commit with the message above if tests pass
