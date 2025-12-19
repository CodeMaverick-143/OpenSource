# Frontend Issues: Maintainer Dashboard

file: `frontend/src/pages/maintainer/index.astro`

## Design Constraint Violations
The current implementation violates the strict "Dark Mode Only" and "No Blue/Purple" rules established in the design system.

- [ ] **Forbidden Color (Blue)**: Lines 69, 94. Uses `bg-blue-100`, `text-blue-800`, `bg-blue-600`, `hover:bg-blue-700`.
- [ ] **Light Mode Backgrounds**: Lines 41, 53, 100. Uses `bg-white`. This breaks the dark theme requirement.
- [ ] **Light Mode Text**: Lines 24, 45, 56. Uses `text-gray-900` (too dark for dark mode) or `text-gray-600` (low contrast on dark).
- [ ] **Status/Tag Colors**: Lines 69, 74-76. Uses light-mode pastel backgrounds (`bg-green-100`, `bg-yellow-100`, etc.) which look jarring in dark mode.

## UI/UX Issues
- [ ] **Card Styling**: Does not use the new `card-premium` class or `var(--color-bg-card)` variables.
- [ ] **Button Styling**: Uses raw Tailwind classes instead of `btn-primary` / `btn-secondary`.
- [ ] **Empty State**: Uses a generic white box instead of a dark, subtle placeholder.
- [ ] **Error Message**: Uses `bg-red-50` (light mode) instead of a dark error distinct style.

## Refactoring Recommendations
1. Replace `bg-white` with `bg-[var(--color-bg-card)]` or `.card-premium`.
2. Replace `text-gray-900` with `text-[var(--color-text-main)]`.
3. Replace Blue buttons with `btn-primary`.
4. Update tags to use `border` + transparent background or deeply muted dark-mode compatible colors (e.g., `bg-green-900/20 text-green-400`).
