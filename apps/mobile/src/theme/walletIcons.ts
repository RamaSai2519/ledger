import type {WalletType} from '@/api/client';

// Maps a wallet's `type` onto a react-native-vector-icons MaterialIcons
// glyph name — shared between WalletFormScreen's type picker and
// WalletsListScreen's row icons so both render the same glyph per type
// instead of each screen inventing its own (previously a plain letter
// avatar).
export const WALLET_TYPE_ICON: Record<WalletType, string> = {
  bank_account: 'account-balance',
  credit_card: 'credit-card',
  pay_later: 'schedule',
  cash: 'payments',
};
