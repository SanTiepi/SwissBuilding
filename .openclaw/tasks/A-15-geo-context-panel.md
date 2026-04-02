# Task A.15 — GeoContextPanel Enrichi (Frontend Display)

## What to do
Enhance the existing `GeoContextPanel.tsx` frontend component to display:
1. The new geo risk score (from A.16 API)
2. Individual component scores (inondation, seismic, grele, contamination, radon)
3. Colored risk indicators (green 0-30, yellow 30-60, red 60-100)
4. Brief interpretation text ("Low risk", "Moderate risk", "High risk")

Component should:
- Fetch `GET /buildings/{building_id}/geo-risk-score` on mount
- Display score as large number + gauge/radial chart (use recharts Radial/Gauge if available)
- Show breakdown bars for each sub-component
- Cache results with React.memo + useCallback

## Files to modify
- **Modify:** `frontend/src/components/buildings/GeoContextPanel.tsx` (~200 lines addition)
- **Create/Modify:** `frontend/src/api/geoContext.ts` - add `fetchGeoRiskScore()` function (15 lines)
- **Modify:** `frontend/src/pages/BuildingHome.tsx` - integrate panel if not already there (5 lines)

## Existing patterns to copy

From `frontend/src/components/buildings/ReadinessDashboard.tsx`:
```tsx
import { Radial, RadialChart, Tooltip } from "recharts";

export const GeoContextPanel = memo(({ building_id }: Props) => {
  const [score, setScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchGeoRiskScore(building_id).then(data => {
      setScore(data.score);
      setLoading(false);
    });
  }, [building_id]);
  
  if (loading) return <div>Loading...</div>;
  
  const color = score < 30 ? "green" : score < 60 ? "yellow" : "red";
  
  return (
    <div className={`p-4 border rounded bg-${color}-50`}>
      <h3>Geo Risk Score</h3>
      <div className="text-4xl font-bold">{score}</div>
    </div>
  );
});
```

From other panels (e.g., `IncidentsPanel.tsx`):
```tsx
const bars = [
  { label: "Inondation", value: data.inondation },
  { label: "Seismic", value: data.seismic },
  // ... etc
];

return <BarChart data={bars} />;
```

## Commit message
```
feat(programme-a): geo context panel with risk score display + sub-component breakdown
```

## Test command
```bash
cd frontend && npm run validate && npm test -- GeoContextPanel
```

## Notes
- Component already likely exists; enrich it
- Use Tailwind dark: classes for dark mode
- Responsive: stack on mobile, horizontal on desktop
- No external geo.admin API calls from frontend — all via backend API
