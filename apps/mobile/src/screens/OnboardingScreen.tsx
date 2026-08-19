import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {colors, fontFamilies, partnerAccents, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Onboarding'>;

// s02/s03 in the design project — a 2-page pager introducing the shared
// ledger and the SMS auto-detect feature. No pager/carousel library is
// installed, so this is a local page-index toggle rather than a swipeable
// view; the dot indicator + Next/Get started CTA still drive the same flow.
export function OnboardingScreen({navigation}: Props) {
  const [page, setPage] = useState<0 | 1>(0);

  const finish = () => navigation.replace('Login');

  return (
    <View style={styles.container}>
      <Pressable style={styles.skip} onPress={finish}>
        <Text style={styles.skipText}>Skip</Text>
      </Pressable>

      {page === 0 ? (
        <View style={styles.visual}>
          <View style={styles.visualBackdrop} />
          <View style={[styles.card, styles.cardLeft]}>
            <View style={styles.cardHeader}>
              <View style={[styles.avatar, {borderColor: partnerAccents[0]}]}>
                <Text style={[styles.avatarText, {color: partnerAccents[0]}]}>I</Text>
              </View>
              <Text style={styles.cardAuthor}>Ishaan added</Text>
            </View>
            <View style={styles.cardRow}>
              <Text style={styles.cardMerchant}>HP Petrol</Text>
              <Text style={styles.cardAmount}>−₹2,100</Text>
            </View>
          </View>
          <View style={[styles.card, styles.cardRight]}>
            <View style={styles.cardHeader}>
              <View style={[styles.avatar, {borderColor: partnerAccents[1]}]}>
                <Text style={[styles.avatarText, {color: partnerAccents[1]}]}>M</Text>
              </View>
              <Text style={[styles.cardAuthor, {color: 'rgba(255,255,255,.72)'}]}>Meera added</Text>
            </View>
            <View style={styles.cardRow}>
              <Text style={[styles.cardMerchant, {color: '#fff'}]}>Swiggy</Text>
              <Text style={[styles.cardAmount, {color: '#fff'}]}>−₹450</Text>
            </View>
          </View>
        </View>
      ) : (
        <View style={styles.visual}>
          <View style={styles.smsBubble}>
            <Text style={styles.smsMeta}>HDFCBK · now</Text>
            <Text style={styles.smsBody}>Rs.450.00 spent on HDFC Card x4821 at SWIGGY on 18-08-26.</Text>
          </View>
          <Text style={styles.arrow}>↓</Text>
          <View style={styles.suggestionBubble}>
            <Text style={styles.suggestionLabel}>Add this expense?</Text>
            <Text style={styles.suggestionTitle}>₹450 at Swiggy · Food</Text>
            <View style={styles.suggestionActions}>
              <View style={styles.suggestionConfirm}>
                <Text style={styles.suggestionConfirmText}>Confirm</Text>
              </View>
              <View style={styles.suggestionEdit}>
                <Text style={styles.suggestionEditText}>Edit</Text>
              </View>
            </View>
          </View>
        </View>
      )}

      <View style={styles.copy}>
        <Text style={styles.title}>{page === 0 ? 'Both of you write in\nthe same book' : 'Your bank SMS\ndoes the typing'}</Text>
        <Text style={styles.subtitle}>
          {page === 0
            ? 'Every wallet, expense and budget is shared. No splitting, no settling up — just one household ledger, seen from two accounts.'
            : 'Ledger reads bank alerts on this phone and offers the transaction, already filled in. You confirm, edit or dismiss.'}
        </Text>
      </View>

      <View style={{flex: 1}} />

      <View style={styles.footer}>
        <View style={styles.dots}>
          <View style={[styles.dot, page === 0 && styles.dotActive]} />
          <View style={[styles.dot, page === 1 && styles.dotActive]} />
        </View>
        <Pressable style={styles.cta} onPress={() => (page === 0 ? setPage(1) : finish())}>
          <Text style={styles.ctaText}>{page === 0 ? 'Next' : 'Get started'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  skip: {alignSelf: 'flex-end', padding: spacing.lg, paddingBottom: 0},
  skipText: {color: colors.textSecondary, fontSize: 12.5},
  visual: {height: 260, marginTop: spacing.md, paddingHorizontal: spacing.lg, justifyContent: 'center'},
  visualBackdrop: {
    position: 'absolute',
    alignSelf: 'center',
    top: 20,
    width: 210,
    height: 210,
    borderRadius: 60,
    backgroundColor: '#15142B',
  },
  card: {
    position: 'absolute',
    width: 200,
    padding: 14,
    borderRadius: radius.card - 2,
    backgroundColor: colors.backgroundRaised,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardLeft: {left: 16, top: 32, transform: [{rotate: '-7deg'}]},
  cardRight: {
    right: 8,
    top: 130,
    transform: [{rotate: '5deg'}],
    backgroundColor: colors.accent,
    borderWidth: 0,
  },
  cardHeader: {flexDirection: 'row', alignItems: 'center', gap: spacing.xs},
  avatar: {width: 22, height: 22, borderRadius: 11, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center'},
  avatarText: {fontSize: 9, fontWeight: '700'},
  cardAuthor: {fontSize: 11, color: colors.textSecondary},
  cardRow: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: spacing.sm},
  cardMerchant: {fontSize: 12.5, fontWeight: '600', color: colors.textPrimary},
  cardAmount: {fontFamily: fontFamilies.monetary, fontSize: 13, color: colors.textPrimary},
  smsBubble: {padding: 14, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  smsMeta: {fontSize: 10.5, color: colors.textSecondary},
  smsBody: {fontSize: 12.5, lineHeight: 18.75, marginTop: 6, color: '#C9C9D2'},
  arrow: {textAlign: 'center', fontSize: 22, color: colors.accent, paddingVertical: 14},
  suggestionBubble: {padding: 16, borderRadius: radius.card - 2, backgroundColor: colors.accent},
  suggestionLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: 'rgba(255,255,255,.75)'},
  suggestionTitle: {fontSize: 15, fontWeight: '600', color: colors.textPrimary, marginTop: 8},
  suggestionActions: {flexDirection: 'row', gap: spacing.xs, marginTop: 14},
  suggestionConfirm: {
    flex: 1,
    height: 36,
    borderRadius: radius.pill,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  suggestionConfirmText: {fontSize: 12.5, fontWeight: '600', color: colors.background},
  suggestionEdit: {
    height: 36,
    paddingHorizontal: 16,
    borderRadius: radius.pill,
    backgroundColor: 'rgba(255,255,255,.16)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  suggestionEditText: {fontSize: 12.5, color: colors.textPrimary},
  copy: {paddingHorizontal: spacing.lg},
  title: {
    color: colors.textPrimary,
    fontFamily: fontFamilies.display,
    fontSize: 29,
    lineHeight: 33.35,
    letterSpacing: -0.8,
    fontWeight: '600',
  },
  subtitle: {color: colors.textSecondary, fontSize: 14, lineHeight: 21.7, marginTop: spacing.sm},
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
  },
  dots: {flexDirection: 'row', gap: 6},
  dot: {width: 5, height: 5, borderRadius: 3, backgroundColor: colors.border},
  dotActive: {width: 18, backgroundColor: colors.accent},
  cta: {height: 52, paddingHorizontal: 26, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  ctaText: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
});
