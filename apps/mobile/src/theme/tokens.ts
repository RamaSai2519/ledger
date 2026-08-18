// Dark theme tokens per DESIGN_BRIEF.md §4. Refine against the Claude
// Design project ("Ledger App.dc.html") as screens are actually built —
// these are the starting values, not final.
export const colors = {
  background: '#0B0B12',
  surface: '#16161F',
  accent: '#5B54F9',
  positive: '#2FD988',
  negative: '#FF6B6B',
  textPrimary: '#F5F5F8',
  textSecondary: '#8A8A94',
  border: '#232330',
} as const;

// Dual-identity accent system (DESIGN_BRIEF.md §4 "signature element") —
// each of the two household members gets a distinct accent hue, assigned
// by join order (first = indigo/accent, second = amber).
export const partnerAccents = [colors.accent, '#F5A623'] as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 20,
  pill: 999,
} as const;

// Typography roles per DESIGN_BRIEF.md §"Typography" — display (hero
// numbers/screen titles), body (everything else), monetary (all amounts in
// lists/tables, tabular figures so columns align). No custom font files are
// bundled yet, so display/body use system font weight+size differentiation;
// monetary uses the real `tabular-nums` font-variant feature (supported by
// RN's Text on both platforms) rather than a bespoke face — this can be
// swapped for the design's actual tabular face once it's added as an asset.
export const typography = {
  display: {fontSize: 34, fontWeight: '700', letterSpacing: -0.5} as const,
  body: {fontSize: 15, fontWeight: '400'} as const,
  monetary: {fontVariant: ['tabular-nums'], fontWeight: '600'} as const,
} as const;
