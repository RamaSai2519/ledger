// Maps a Category.icon key (a semantic identifier the backend seeds — see
// services/api/src/shared/constants.py's DEFAULT_EXPENSE_CATEGORIES/
// DEFAULT_INCOME_CATEGORIES) onto a react-native-vector-icons
// MaterialCommunityIcons glyph name. Kept as its own indirection layer so
// swapping icon libraries or individual glyphs later never needs a data
// migration — only this map changes.
export const CATEGORY_ICON_MAP: Record<string, string> = {
  food_dining: 'silverware-fork-knife',
  groceries: 'cart-outline',
  transport: 'bus',
  fuel: 'gas-station-outline',
  shopping: 'shopping-outline',
  bills_utilities: 'flash-outline',
  rent: 'home-city-outline',
  emi_loan: 'bank-outline',
  entertainment: 'movie-open-outline',
  health_fitness: 'heart-pulse',
  subscriptions: 'autorenew',
  travel: 'airplane',
  education: 'school-outline',
  personal_care: 'flower-outline',
  gifts_donations: 'gift-outline',
  balance_adjustment: 'scale-balance',
  miscellaneous: 'shape-outline',
  salary: 'cash-multiple',
  freelance_business: 'briefcase-outline',
  investment_returns: 'chart-line',
  refunds_cashback: 'cash-refund',
  other_income: 'wallet-outline',
};

// Custom (non-default) categories don't have a recognized icon key — this
// is the glyph shown for those instead of falling back to a first-letter.
export const CATEGORY_ICON_FALLBACK = 'shape-outline';

export function glyphForCategoryIcon(icon: string | null | undefined): string {
  return (icon && CATEGORY_ICON_MAP[icon]) || CATEGORY_ICON_FALLBACK;
}
