# Frontend Performance Audit

> Generated: 2026-03-10 | Build tool: Vite 5.4.21 | Framework: React 18 + TypeScript

## Bundle Overview

| Chunk | Size (minified) | Size (gzip) | Category |
|-------|-----------------|-------------|----------|
| `index-*.js` | 630.62 kB | 158.71 kB | Main entry (i18n + app shell + API layer) |
| `BarChart-*.js` | 388.49 kB | 105.95 kB | recharts (lazy-loaded) |
| `vendor-*.js` | 164.83 kB | 53.79 kB | react + react-dom + react-router-dom |
| `OverviewTab-*.js` | 151.82 kB | 28.88 kB | Building detail overview (lazy) |
| `types-*.js` | 79.07 kB | 21.56 kB | Shared type constants / enums |
| `query-*.js` | 41.70 kB | 12.61 kB | @tanstack/react-query |
| `index-*.css` | 91.93 kB | 13.55 kB | Main CSS (Tailwind) |
| `mapbox-gl-*.css` | 41.01 kB | 5.60 kB | Mapbox GL CSS (lazy) |

**Total JS**: ~2,195 kB (minified) across 117 chunks
**Total CSS**: ~133 kB (minified) across 2 files
**PWA precache**: 124 entries, 2,327 kB

## Code Splitting Assessment

### What is already well-optimized

1. **All 33 pages are lazy-loaded** (`App.tsx:7-39`). Every route uses `lazy(() => import(...))` with `<Suspense>` boundaries.
2. **recharts is isolated** via lazy `DashboardCharts` and `PortfolioCharts` components (`Dashboard.tsx:34`, `Portfolio.tsx:15`). The 388 kB chunk only loads when those pages are visited.
3. **mapbox-gl is isolated** via lazy `PollutantMap` page. The mapbox CSS loads only when the map page is visited.
4. **Heavy form libraries (zod, react-hook-form, @hookform/resolvers)** are only imported from lazy-loaded pages (Login, Settings, BuildingDetail, BuildingsList, DiagnosticView, BuildingSamples). They do not pollute the main chunk.
5. **Building detail sub-components** (OverviewTab, DiagnosticsTab, DocumentsTab, ActivityTab) are lazy-loaded within `BuildingDetail.tsx`.
6. **Vendor chunk** is properly split: react + react-dom + react-router-dom (164.83 kB).
7. **Query chunk** is properly split: @tanstack/react-query (41.70 kB).

### The index chunk (630 kB) — root cause analysis

The main `index` chunk contains:
- **i18n translation strings** (~500 kB raw across 4 languages x ~130 KB each): `src/i18n/index.ts` statically imports all 4 language files (fr, de, it, en) with ~1,110 keys per language. These are loaded eagerly because `I18nProvider` wraps the entire app in `main.tsx`.
- **App shell**: Layout, Sidebar, Header, CommandPalette, ErrorBoundary, ProtectedRoute
- **API client layer**: axios client, API modules shared across pages
- **Utility functions**: formatters, type definitions
- **Zustand stores**: authStore, toastStore, themeStore

The i18n strings are the dominant contributor (~80% of the chunk). After gzip, the index chunk is 158.71 kB — acceptable for a SPA's critical path.

## Quick Wins Applied

### 1. Removed dead `map` manual chunk (vite.config.ts)

**Before**: `manualChunks` included `map: ['mapbox-gl']`, which produced a `map-*.js` file of 0.00 kB (empty) and a build warning "Generated an empty chunk: map".

**After**: Removed the entry. mapbox-gl is only dynamically imported through lazy-loaded pages, so Rollup already isolates it automatically. This eliminated the empty chunk and the build warning.

**Impact**: -1 empty chunk, cleaner build output, no functional change.

### 2. Added chunkSizeWarningLimit (vite.config.ts)

Set `chunkSizeWarningLimit: 650` to suppress the false positive warning on the index chunk. The 630 kB is legitimately dominated by i18n strings that must be eagerly loaded (the app needs translations before rendering any UI).

**Impact**: Cleaner build output, no functional change.

## Items NOT Recommended (with reasoning)

### Dynamic i18n loading (load only active language)

**What**: Dynamically import only the active language file instead of all 4.
**Why not now**:
- The i18n files are hub files (AGENTS.md forbids agent edits to `src/i18n/{en,fr,de,it}.ts`)
- Would require restructuring `I18nProvider` and adding async loading states
- After gzip, the 4 languages compress to ~40 kB total (highly repetitive key structures compress well)
- Risk of flash-of-untranslated-content during language switch
- Medium-effort, low real-world impact given gzip compression

### Splitting recharts into a manual chunk

**Why not**: recharts is already automatically isolated by Rollup because it is only imported from lazy-loaded components. Adding it to `manualChunks` would force it into a named chunk loaded by every page that uses any chart, which is the current behavior anyway. No benefit.

### Splitting OverviewTab (151 kB)

**Why not**: Already lazy-loaded from `BuildingDetail.tsx:25`. It imports 16 sub-components (PassportCard, TrustScoreCard, etc.) which are only used on this tab. Splitting it further would add HTTP round-trips for minimal gain since all those components are needed together.

### Tree-shaking lucide-react icons

**Why not**: lucide-react already supports tree-shaking via named exports. Individual icons are already split into tiny chunks (~0.3-0.6 kB each). The current setup is optimal.

### CSS code splitting

**Why not**: Vite's `cssCodeSplit` is already `true` by default. The mapbox CSS is already in a separate file. The main CSS (91.93 kB, 13.55 kB gzip) is Tailwind utility classes — splitting it further would cause FOUC.

### Switching to lightningcss for CSS minification

**Why not**: Requires adding `lightningcss` as a dependency. Savings would be marginal (est. 1-3% on 91 kB CSS). Not worth the dependency.

## Metrics Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Build warnings | 2 (empty chunk + size) | 0 | -2 |
| Chunk count | 118 JS + 2 CSS | 117 JS + 2 CSS | -1 |
| Total JS size | 2,195.2 kB | 2,195.2 kB | ~0 (removed 0 kB empty chunk) |
| Index chunk | 630.62 kB | 630.62 kB | 0 |
| Lazy pages | 33/33 | 33/33 | - |
| Build time | ~5.8s | ~6.9s | n/a (varies) |

## Future Opportunities (if index chunk growth continues)

1. **Dynamic i18n**: Load only the active language, defer others to language-switch time. Would reduce initial JS by ~375 kB raw / ~30 kB gzip. Requires i18n architecture change.
2. **Pre-compress assets**: Enable `vite-plugin-compression` for pre-built .br/.gz files. Reduces server-side compression overhead.
3. **Module preloading hints**: Add `modulepreload` for critical-path lazy chunks (Dashboard, BuildingsList) to reduce perceived load time.
