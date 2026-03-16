# Keyboard & Focus Audit Report

> Generated: 2026-03-10 | Scope: main navigation, command palette, header controls, page-level tab order

## 1. Focus Order — Main Navigation

### Sidebar (`frontend/src/components/Sidebar.tsx`)

| Element | Focusable | Notes |
|---------|-----------|-------|
| NavLink items (lines 109-131) | Yes — standard `<a>` via `NavLink` | Natural tab order follows DOM order. Active link announced via `sr-only` text (line 128). |
| Collapse toggle button (lines 139-145) | Yes | `aria-label` toggles between "Expand sidebar" / "Collapse sidebar". |
| Mobile close button (lines 94-100) | Yes | `aria-label` uses `t('form.close')`. |

**Finding S1**: `<nav>` has `aria-label="Navigation principale"` (line 105) — good landmark. However the label is hardcoded in French. Should use `t()` for i18n consistency.

**Finding S2**: No `tabindex="-1"` trap on sidebar boundary — tab can escape sidebar into main content naturally. This is correct behavior for a persistent sidebar.

### Header (`frontend/src/components/Header.tsx`)

| Element | Line | Focusable | aria |
|---------|------|-----------|------|
| Hamburger (Menu) | 66-72 | Yes | `aria-label="Menu"` |
| Desktop search trigger | 79-89 | Yes | `aria-label={t('nav.search')}` |
| Mobile search button | 96-102 | Yes | `aria-label={t('nav.search')}` |
| Dark mode toggle | 106-112 | Yes | `aria-label={t('settings.dark_mode')}` |
| NotificationBell | 115 | Yes (component) | — |
| Language switcher | 119-129 | Yes | `aria-label`, `aria-expanded`, `aria-haspopup` |
| User menu | 162-180 | Yes | `aria-label`, `aria-expanded`, `aria-haspopup` |

**Finding H1**: Language dropdown (line 130-154) and user menu dropdown (line 182-216) open on click but have no keyboard-driven close (Escape key). They close only via outside click (`mousedown` listener, lines 38-48). Keyboard-only users cannot close these dropdowns with Escape.

**Finding H2**: Dropdown items (language options, user menu items) are rendered as `<button>` elements — they receive natural tab focus. However, `role="menu"` on the container (lines 133, 185) implies `role="menuitem"` on children, which is missing.

**Finding H3**: No skip-to-content link exists. The tab order goes: hamburger → page title (not focusable) → search → dark mode → notification → language → user → sidebar links → main content. This is a long journey for keyboard users.

## 2. Command Palette Focus Trap (`frontend/src/components/CommandPalette.tsx`)

**Opening**: Ctrl+K / Cmd+K handled in `Layout.tsx` (line 19). Focus is moved to input via `requestAnimationFrame` (line 183).

**Keyboard handling** (lines 286-361):
- `Escape` → closes palette (line 307, 343)
- `ArrowUp/Down` → navigate results
- `Enter` → select result
- `Tab` → opens quick actions for building results (line 336-339)

**Finding CP1**: The palette uses a custom keyboard handler on the input (line 399 `onKeyDown`). `Tab` is `preventDefault()`-ed (line 335), which means pressing Tab does NOT cycle through interactive elements (close button, filter pills). This creates a **partial focus trap** — the input captures all keyboard navigation. The close button (line 405-410) and filter pill buttons (lines 418-429) are unreachable by keyboard when the palette is open.

**Finding CP2**: No `aria-modal="true"` on the dialog container. The `role="dialog"` exists (line 388) but without `aria-modal`, screen readers may not announce it as a modal overlay.

**Finding CP3**: Backdrop click closes the palette (line 378 `onClick={onClose}`), and Escape closes it. Focus is not explicitly restored to the previously focused element after close.

**Finding CP4**: The result list uses `role="listbox"` (line 483) with `role="option"` and `aria-selected` on items — good ARIA pattern for combobox results.

## 3. Layout & Skip Navigation (`frontend/src/components/Layout.tsx`)

**Finding L1**: No `<a href="#main-content">` skip link exists. The `<main>` element (line 59) has no `id` attribute, so even if a skip link were added, there is no target anchor.

**Finding L2**: The Layout uses semantic `<header>`, `<aside>`, `<main>` elements — screen reader landmark navigation works correctly.

## 4. Page-Level Tab Order

Tab order across the app follows natural DOM order:
1. Header controls (hamburger, search, theme, notifications, language, user)
2. Sidebar navigation links (when visible on desktop)
3. Main content area

This is a reasonable order for an admin dashboard. The sidebar being after the header in DOM means keyboard users go through header controls first, which aligns with the visual layout.

## 5. Summary of Findings

| ID | Severity | Description | File:Line |
|----|----------|-------------|-----------|
| S1 | Low | Sidebar nav `aria-label` hardcoded in French | Sidebar.tsx:105 |
| H1 | Medium | Header dropdowns (lang/user) not closable via Escape key | Header.tsx:130-216 |
| H2 | Low | `role="menu"` without `role="menuitem"` on children | Header.tsx:133,185 |
| H3 | Medium | No skip-to-content link | Layout.tsx |
| CP1 | Medium | Command palette Tab key trapped — close button and filters unreachable by keyboard | CommandPalette.tsx:335 |
| CP2 | Low | Dialog missing `aria-modal="true"` | CommandPalette.tsx:388 |
| CP3 | Low | Focus not restored to trigger element after palette close | CommandPalette.tsx / Layout.tsx |
| L1 | Medium | No skip link target (`id` on `<main>`) | Layout.tsx:59 |

## 6. Reproducibility

All findings reference specific file paths and line numbers in `frontend/src/components/`. Tests in `frontend/e2e/navigation.spec.ts` and `frontend/e2e/pages.spec.ts` cover the deterministic keyboard/focus checks added as part of this audit.
