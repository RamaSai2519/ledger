# Default category name -> icon key. The icon key is a semantic identifier
# (not a specific icon-library glyph name) so the mobile app's icon mapping
# can change library/glyph choices without a data migration — see
# apps/mobile/src/theme/categoryIcons.ts for the icon-key -> glyph mapping.
DEFAULT_EXPENSE_CATEGORIES = [
    ("Food & Dining", "food_dining"),
    ("Groceries", "groceries"),
    ("Transport", "transport"),
    ("Fuel", "fuel"),
    ("Shopping", "shopping"),
    ("Bills & Utilities", "bills_utilities"),
    ("Rent", "rent"),
    ("EMI / Loan Payment", "emi_loan"),
    ("Entertainment", "entertainment"),
    ("Health & Fitness", "health_fitness"),
    ("Subscriptions", "subscriptions"),
    ("Travel", "travel"),
    ("Education", "education"),
    ("Personal Care", "personal_care"),
    ("Gifts & Donations", "gifts_donations"),
    ("Balance Adjustment", "balance_adjustment"),  # system category, hidden from manual picker
    ("Miscellaneous", "miscellaneous"),
]

DEFAULT_INCOME_CATEGORIES = [
    ("Salary", "salary"),
    ("Freelance / Business", "freelance_business"),
    ("Investment Returns", "investment_returns"),
    ("Refunds / Cashback", "refunds_cashback"),
    ("Other Income", "other_income"),
]

SYSTEM_CATEGORY_NAMES = {"Balance Adjustment"}

INVITE_CODE_LENGTH = 6
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity
MAX_HOUSEHOLD_MEMBERS = 2

# Default per-member accent color, assigned by join order (index into
# member_ids) at household create/join time. Mirrors
# apps/mobile/src/theme/tokens.ts's `partnerAccents` tuple — keep both in
# sync if either changes. A user can override their own via PATCH
# /users/profile.
DEFAULT_ACCENT_PALETTE = ["#5B54F9", "#E8A33D"]
