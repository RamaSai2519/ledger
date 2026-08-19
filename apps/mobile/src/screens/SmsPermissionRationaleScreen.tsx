import React from 'react';
import {PermissionsAndroid, Platform, Pressable, StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'SmsPermissionRationale'>;

// Plain-language rationale shown before the actual Android permission
// prompt (plan.md §7 step 1, LED-7 mobile scope). The RECEIVE_SMS request
// itself is a core React Native API call; the manifest-registered
// android/.../sms/SmsReceiver.kt BroadcastReceiver is what actually acts on
// the grant (and keeps working even if the app is later backgrounded or
// killed). Returns to Home either way — manual entry always remains
// available (plan.md §7 step 12).
const POINTS: Array<{tone: 'positive' | 'negative'; title: string; body: string}> = [
  {
    tone: 'positive',
    title: 'We read messages from bank senders',
    body: 'Amount, merchant and card digits only, matched on the phone.',
  },
  {
    tone: 'positive',
    title: 'Nothing is saved until you confirm',
    body: 'A dismissed suggestion leaves no record in your book.',
  },
  {
    tone: 'negative',
    title: 'We never read personal messages',
    body: 'Non-bank senders are skipped and never leave the device.',
  },
];

export function SmsPermissionRationaleScreen({navigation}: Props) {
  const requestAccess = async () => {
    if (Platform.OS === 'android') {
      try {
        await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECEIVE_SMS);
      } catch {
        // Permission dialog dismissed/denied — fall through to Home either way,
        // manual entry always remains available (plan.md §7 step 12).
      }
    }
    navigation.navigate('PinSetup');
  };

  return (
    <View style={styles.container}>
      <View style={styles.iconTile}>
        <Text style={styles.iconTileText}>SMS</Text>
      </View>
      <Text style={styles.title}>Let Ledger read{'\n'}bank alerts</Text>
      <Text style={styles.subtitle}>
        On the next screen Android will ask for SMS access. Here is exactly what happens with it.
      </Text>

      <View style={styles.points}>
        {POINTS.map((point) => (
          <View key={point.title} style={styles.pointRow}>
            <Text style={[styles.pointGlyph, point.tone === 'positive' ? styles.pointGlyphPositive : styles.pointGlyphNegative]}>
              {point.tone === 'positive' ? '✓' : '✕'}
            </Text>
            <View style={{flex: 1}}>
              <Text style={styles.pointTitle}>{point.title}</Text>
              <Text style={styles.pointBody}>{point.body}</Text>
            </View>
          </View>
        ))}
      </View>

      <View style={{flex: 1}} />

      <View style={styles.ctaColumn}>
        <Pressable style={styles.primaryCta} onPress={requestAccess}>
          <Text style={styles.primaryCtaText}>Allow SMS access</Text>
        </Pressable>
        <Pressable style={styles.secondaryCta} onPress={() => navigation.navigate('Home')}>
          <Text style={styles.secondaryCtaText}>Not now — I'll add manually</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg, paddingBottom: spacing.xl},
  iconTile: {
    width: 52,
    height: 52,
    borderRadius: radius.row,
    backgroundColor: 'rgba(91,84,249,.14)',
    borderWidth: 1,
    borderColor: 'rgba(91,84,249,.32)',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.sm,
  },
  iconTileText: {color: colors.accentOnDark, fontSize: 12, fontWeight: '700', letterSpacing: 0.5},
  title: {
    color: colors.textPrimary,
    fontFamily: fontFamilies.display,
    fontSize: 27,
    letterSpacing: -0.6,
    lineHeight: 32,
    marginTop: spacing.md,
  },
  subtitle: {color: colors.textSecondary, fontSize: 14, lineHeight: 21.7, marginTop: spacing.sm},
  points: {marginTop: spacing.lg, gap: spacing.sm},
  pointRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: 14,
    borderRadius: radius.row,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pointGlyph: {fontSize: 16, fontWeight: '700', marginTop: 1},
  pointGlyphPositive: {color: colors.positive},
  pointGlyphNegative: {color: colors.negative},
  pointTitle: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  pointBody: {color: colors.textSecondary, fontSize: 11.5, marginTop: 3, lineHeight: 17.25},
  ctaColumn: {gap: spacing.sm},
  primaryCta: {
    height: 52,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryCtaText: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  secondaryCta: {height: 52, alignItems: 'center', justifyContent: 'center'},
  secondaryCtaText: {color: colors.textSecondary, fontSize: 14, fontWeight: '600'},
});
