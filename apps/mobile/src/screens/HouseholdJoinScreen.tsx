import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {householdApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';
import {HouseholdTabs} from '@/components/HouseholdTabs';

type Props = NativeStackScreenProps<RootStackParamList, 'HouseholdJoin'>;

export function HouseholdJoinScreen({navigation}: Props) {
  const [inviteCode, setInviteCode] = useState('');
  const setHouseholdId = useAuthStore((s) => s.setHouseholdId);

  const mutation = useMutation({
    mutationFn: () => householdApi.join(inviteCode.toUpperCase()),
    onSuccess: (data) => {
      setHouseholdId(data.household_id, data.name);
      navigation.replace('SmsPermissionRationale');
    },
  });

  const codeChars = inviteCode.toUpperCase().padEnd(6, ' ').split('');

  return (
    <View style={styles.container}>
      <View style={styles.headerBlock}>
        <Text style={styles.title}>Your household</Text>
        <Text style={styles.subtitle}>One household, two accounts, one shared book.</Text>
      </View>
      <HouseholdTabs active="join" onSelectCreate={() => navigation.replace('HouseholdCreate')} />

      <View style={styles.field}>
        <Text style={styles.fieldLabel}>Enter your partner's code</Text>
        <View style={styles.codeRow}>
          {codeChars.map((ch, i) => (
            <View key={i} style={[styles.codeBox, i === inviteCode.length && styles.codeBoxFocused]}>
              <Text style={styles.codeChar}>{ch.trim()}</Text>
            </View>
          ))}
        </View>
        {/* Real keyboard input, visually hidden behind the code boxes above */}
        <TextInput
          style={styles.hiddenInput}
          value={inviteCode}
          onChangeText={(t) => setInviteCode(t.toUpperCase().slice(0, 6))}
          autoCapitalize="characters"
          maxLength={6}
          autoFocus
        />
        <Text style={styles.hint}>Ask your partner to send it from Settings → Household.</Text>
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <View style={{flex: 1}} />
      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending || inviteCode.length < 6}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Joining…' : 'Join household'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl},
  headerBlock: {paddingTop: spacing.sm},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 27, letterSpacing: -0.6, fontWeight: '600'},
  subtitle: {color: colors.textSecondary, fontSize: 13.5, marginTop: spacing.xs},
  field: {marginTop: spacing.lg},
  fieldLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.textSecondary},
  codeRow: {flexDirection: 'row', gap: spacing.xs, marginTop: spacing.sm},
  codeBox: {
    flex: 1,
    height: 58,
    borderRadius: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  codeBoxFocused: {borderColor: colors.accent},
  codeChar: {color: colors.accentOnDark, fontFamily: fontFamilies.monetary, fontSize: 22},
  hiddenInput: {position: 'absolute', opacity: 0, height: 1, width: 1},
  hint: {fontSize: 12, color: colors.textSecondary, marginTop: spacing.sm},
  error: {color: colors.negative, marginTop: spacing.sm},
  button: {height: 52, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
});
