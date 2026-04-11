# Task G.1 — Trust Score Visibility (Building Passport Enhancement)

## What to do
Make the building trust score explicitly visible and actionable in the BuildingHome page.

**Currently:**
- `trust_score` field exists in Building model (0-100)
- No frontend display
- No breakdown of what drives the score

**What to build:**
1. Add TrustScorePanel component to BuildingHome (similar to ReadinessDashboard)
2. Display trust score as large number + 3-tier indicators: Low (<40), Medium (40-70), High (70-100)
3. Show breakdown: "What improves trust?"
   - Diagnostic source reliability (certified vs self-report) → +weight
   - Recency of diagnostics (< 5 years) → +weight
   - Data contradiction count → -weight
   - Field observation count (ground truth) → +weight
4. Show score history (last 6 months) as sparkline
5. Color code: red (0-40), amber (40-70), green (70-100)
6. Explain each component in a tooltip

## Files to modify
- **Create:** `frontend/src/components/buildings/TrustScorePanel.tsx` (120 lines)
- **Create:** `frontend/src/hooks/useTrustScore.ts` (30 lines, fetch + format)
- **Modify:** `frontend/src/pages/BuildingHome.tsx` - integrate TrustScorePanel (5 lines)
- **Create:** `frontend/src/components/buildings/__tests__/TrustScorePanel.test.tsx` (8 tests)

## Existing patterns to copy

From `frontend/src/components/buildings/ReadinessDashboard.tsx`:
```tsx
import React, { memo } from 'react';
import { Building, cn } from '@/lib/types';

export const TrustScorePanel = memo(({ building }: { building: Building }) => {
  const { score, breakdown, history } = useTrustScore(building.id);

  const getTrustColor = (score: number) => {
    if (score < 40) return 'from-red-100 to-red-50 border-red-200';
    if (score < 70) return 'from-amber-100 to-amber-50 border-amber-200';
    return 'from-green-100 to-green-50 border-green-200';
  };

  const getTrustTextColor = (score: number) => {
    if (score < 40) return 'text-red-700';
    if (score < 70) return 'text-amber-700';
    return 'text-green-700';
  };

  return (
    <div className={cn('p-6 rounded-lg border', getTrustColor(score))}>
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
        Dossier Confiance
      </h3>
      <div className={cn('text-5xl font-bold mb-4', getTrustTextColor(score))}>
        {Math.round(score)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        {score < 40 && '❌ Trust bas — preuves insuffisantes'}
        {score >= 40 && score < 70 && '⚠️ Trust modéré — manquent données'}
        {score >= 70 && '✅ Trust élevé — dossier fiable'}
      </div>
      <div className="space-y-2">
        {breakdown.map((item) => (
          <div key={item.label} className="flex justify-between text-xs">
            <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
            <span className="text-gray-900 dark:text-gray-100 font-semibold">{item.value}</span>
          </div>
        ))}
      </div>
      {history && (
        <div className="mt-4 h-12 bg-white dark:bg-gray-800 rounded p-2">
          <Sparkline data={history} />
        </div>
      )}
    </div>
  );
});
```

## API response (GET /buildings/{building_id}/trust-score)
```json
{
  "score": 78,
  "breakdown": [
    {"label": "Source fiabilité", "value": 25, "max": 30},
    {"label": "Récence donnees", "value": 20, "max": 25},
    {"label": "Observations terrain", "value": 18, "max": 25},
    {"label": "Contradictions", "value": 15, "max": 20}
  ],
  "history": [72, 74, 75, 77, 78],
  "trend": "↑ +6 pts en 30 jours"
}
```

## Commit message
```
feat(programme-g): trust score visibility in building home — breakdown + history
```

## Test command
```bash
cd frontend && npm run validate && npm test -- TrustScorePanel
```

## Notes
- Component should be responsive (stack on mobile)
- No backend changes needed (score computation already exists)
- Use dark mode classes
- Position: right-hand panel, below ReadinessDashboard
