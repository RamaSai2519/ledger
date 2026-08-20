import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {householdApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';
import {HouseholdTabs} from '@/components/HouseholdTabs';

type Props = NativeStackScreenProps<RootStackParamList, 'HouseholdJoin'>;

export function HouseholdJoinScreen({navigation}: Props) {
  const [inviteCode, setInviteCode] = useState('');
  const [step, setStep] = useState<'code' | 'preview'>('code');
  const setHouseholdId = useAuthStore((s) => s.setHouseholdId);

  const previewQuery = useQuery({
    queryKey: ['householdPreview', inviteCode],
    queryFn: () => householdApi.preview(inviteCode),
    enabled: false,
    retry: false,
  });

  const joinMutation = useMutation({
    mutationFn: () => householdApi.join(inviteCode),
    onSuccess: (data) => {
      setHouseholdId(data.household_id, data.name);
      navigation.replace('SmsPermissionRationale');
    },
  });

  const handleCodeChange = (t: string) => {
    setInviteCode(t.toUpperCase().slice(0, 6));
    if (step === 'preview') setStep('code');
  };

  const handleContinue = async () => {
    const result = await previewQuery.refetch();
    if (result.data) setStep('preview');
  };

  const handleBack = () => setStep('code');

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
          onChangeText={handleCodeChange}
          autoCapitalize="characters"
          maxLength={6}
          autoFocus
          editable={step === 'code'}
        />
        <Text style={styles.hint}>Ask your partner to send it from Settings → Household.</Text>
      </View>

      {previewQuery.isError && step === 'code' && (
        <Text style={styles.error}>{(previewQuery.error as Error).message}</Text>
      )}

      {step === 'preview' && previewQuery.data && (
        <View style={styles.previewCard}>
          <View style={styles.previewAvatar}>
            <Text style={styles.previewAvatarText}>{previewQuery.data.name.trim().charAt(0).toUpperCase()}</Text>
          </View>
          <View style={{flex: 1}}>
            <Text style={styles.previewName}>{previewQuery.data.name}</Text>
            <Text style={styles.previewMeta}>
              {previewQuery.data.member_count} member{previewQuery.data.member_count === 1 ? '' : 's'} already in
            </Text>
          </View>
        </View>
      )}

      {joinMutation.isError && <Text style={styles.error}>{(joinMutation.error as Error).message}</Text>}

      <View style={{flex: 1}} />

      {step === 'code' ? (
        <Pressable
          style={styles.button}
          onPress={handleContinue}
          disabled={previewQuery.isFetching || inviteCode.length < 6}
        >
          <Text style={styles.buttonText}>{previewQuery.isFetching ? 'Looking up…' : 'Continue'}</Text>
        </Pressable>
      ) : (
        <>
          <Pressable style={styles.backButton} onPress={handleBack} disabled={joinMutation.isPending}>
            <Text style={styles.backButtonText}>Change code</Text>
          </Pressable>
          <Pressable style={styles.button} onPress={() => joinMutation.mutate()} disabled={joinMutation.isPending}>
            <Text style={styles.buttonText}>{joinMutation.isPending ? 'Joining…' : 'Join household'}</Text>
          </Pressable>
        </>
      )}
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
  previewCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.lg,
    padding: spacing.md,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  previewAvatar: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  previewAvatarText: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 18, fontWeight: '600'},
  previewName: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 17, fontWeight: '600'},
  previewMeta: {color: colors.textSecondary, fontSize: 13, marginTop: 2},
  backButton: {height: 44, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.sm},
  backButtonText: {color: colors.textSecondary, fontSize: 13.5, fontWeight: '600'},
  button: {height: 52, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
});
