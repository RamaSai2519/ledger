import {partnerAccents} from '@/theme/tokens';
import {useAuthStore} from '@/state/authStore';

// Dual-identity accent system (DESIGN_BRIEF.md "signature element"): each
// partner gets a distinct accent hue on transactions they logged. There's
// no /users endpoint yet to look up true join-order for the household
// (that's outside LED-4's scope), so this assigns by viewer perspective —
// "logged by me" vs "logged by my partner" — which still delivers the
// at-a-glance who-logged-what signal the design calls for. Swap this for a
// join-order-based lookup once a household-members endpoint exists.
export function usePartnerAccent(transactionUserId: string | null | undefined): string {
  const selfUserId = useAuthStore((s) => s.userId);
  if (!transactionUserId || !selfUserId) return partnerAccents[0];
  return transactionUserId === selfUserId ? partnerAccents[0] : partnerAccents[1];
}
