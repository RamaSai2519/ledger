// Dark theme tokens — pulled directly from the Claude Design project's
// "Final tokens" spec screen (Khaata App.dc.html#spec1), not re-derived.
export const colors = {
  background: '#0B0B12', // bg base
  backgroundRaised: '#0F0F17', // bg raised (nav, keypad)
  surface: '#16161F',
  border: '#232330', // border / track
  accent: '#5B54F9', // primary · Ishaan (first household member)
  accentOnDark: '#B9B6FF', // indigo on dark (links, icons)
  positive: '#2FD988', // income / under budget
  negative: '#FF6B6B', // owe / over / error
  textPrimary: '#F5F5F8',
  textSecondary: '#8A8A94',
} as const;

// Hero/card gradient, 145deg — used behind hero numbers and the SMS
// suggestion card. React Native has no CSS gradients built in; consumers
// use these two stops with react-native-linear-gradient (or an
// approximation) rather than a flat fill.
export const heroGradient = ['#6A62FF', '#3F38D4'] as const;
export const heroGradientAngle = 145;

// Dual-identity accent system (DESIGN_BRIEF.md §4 "signature element") —
// each of the two household members gets a distinct accent hue, assigned
// by join order. First member = accent (indigo), second = Meera's amber
// from the design spec.
export const partnerAccents = [colors.accent, '#E8A33D'] as const;

// Category icon tints (icon glyph color only, never used as a fill) —
// spec1: "Category hues (icon tints only, never fills)".
export const categoryHues = {
  food: '#E8A33D',
  travel: '#8FB4FF',
  groceries: '#7FE3B8',
  rent: '#D4A5FF',
  bills: '#FFB4B4',
  health: '#FFD59B',
  fun: '#9BE0FF',
} as const;

// space 4 · 6 · 8 · 10 · 14 · 16 · 20 · 26 (spec1). Named steps map onto
// the closest spec value; screens needing an exact spec value (e.g. 10, 14,
// 26) should use the numeric literal directly rather than force-fitting one
// of these names.
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 20, // screen padding (spec1: "screen padding 20, 16 for full-width cards")
  xl: 26,
} as const;

// radius 12 icon-tile · 14 input/keypad · 16 row · 18–20 card · 22 hero ·
// 26 sheet · 100 pill (spec1). `sm`/`md`/`lg` are back-compat aliases onto
// the closest spec value, kept so pre-existing screens (built before this
// spec was pulled) don't all need a call-site rewrite in the same pass —
// new/redesigned screens should reach for the named spec keys directly.
export const radius = {
  iconTile: 12,
  input: 14,
  row: 16,
  card: 20,
  hero: 22,
  sheet: 26,
  pill: 100,
  sm: 12,
  md: 16,
  lg: 20,
} as const;

// hit targets ≥44 · keypad key 52 · FAB 56 · PIN key 64 (spec1).
export const hitTargets = {
  min: 44,
  keypadKey: 52,
  fab: 56,
  pinKey: 64,
} as const;

// Typography roles per spec1's "Type" section. Real .ttf faces are bundled
// under src/assets/fonts and linked into android/app/src/main/assets/fonts
// via react-native.config.js + `npx react-native-asset`. Android's Typeface
// loader has no notion of a single family with multiple weights the way iOS
// does — each weight actually used by a screen is its own named family here
// (mirroring the bundled filenames); `fontWeight` in a screen's style is
// mostly redundant once the right family is picked, but harmless to leave.
export const fontFamilies = {
  display: 'SpaceGrotesk-SemiBold', // hero figures, screen titles — weight 600 (the spec's only display weight)
  displayBold: 'SpaceGrotesk-Bold', // the one weight-700 use (Splash/Home brand mark)
  body: 'InstrumentSans-Regular', // body/meta/labels default — applied globally, see applyFontDefaults.ts
  bodyMedium: 'InstrumentSans-Medium',
  bodySemiBold: 'InstrumentSans-SemiBold',
  monetary: 'IBMPlexMono-Regular', // every ₹ amount, masked digits, PIN, list dates
  monetaryMedium: 'IBMPlexMono-Medium',
} as const;

export const typography = {
  heroDisplay: {fontSize: 46, fontWeight: '600' as const, letterSpacing: -0.5},
  screenTitle: {fontSize: 20, fontWeight: '600' as const, letterSpacing: -0.4},
  display: {fontSize: 34, fontWeight: '600' as const, letterSpacing: -0.5},
  body: {fontSize: 15, fontWeight: '400' as const},
  bodyMedium: {fontSize: 14, fontWeight: '500' as const},
  meta: {fontSize: 11.5, fontWeight: '400' as const},
  labelCaps: {fontSize: 11, fontWeight: '600' as const, letterSpacing: 0.5, textTransform: 'uppercase' as const},
  monetary: {fontVariant: ['tabular-nums'] as const, fontWeight: '500' as const},
} as const;

// Motion timings (spec1 "Motion") — for screens implementing the SMS
// suggestion sheet, confirm-collapse, chart scrub, skeleton shimmer, and
// budget bar fill, so every implementation uses the same numbers instead of
// picking ad hoc durations.
export const motion = {
  smsSheetSlideUpMs: 280,
  smsSheetBackdropOpacity: 0.45,
  smsSheetAmountFadeDelayMs: 60,
  confirmCollapseMs: 200,
  chartGuideFadeMs: 120,
  skeletonShimmerMs: 1600,
  walletCardRestackMs: 240,
  budgetBarFillMs: 400,
} as const;
