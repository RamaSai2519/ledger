import React, {useState} from 'react';
import {Pressable, Share, StyleSheet, Text, TextInput, View} from 'react-native';
import Clipboard from '@react-native-clipboard/clipboard';
import {useMutation} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import {householdApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';
import {HouseholdTabs} from '@/components/HouseholdTabs';

type Props = NativeStackScreenProps<RootStackParamList, 'HouseholdCreate'>;

// s06 in the design project. The mockup shows the invite code already
// generated with Share/Continue actions — here the household is created as
// soon as a name is entered and confirmed, then this same screen flips to
// showing the code, matching that same layout.
export function HouseholdCreateScreen({navigation}: Props) {
  const [name, setName] = useState('Our Home');
  const setHouseholdId = useAuthStore((s) => s.setHouseholdId);

  const mutation = useMutation({
    mutationFn: () => householdApi.create(name),
    onSuccess: (data) => setHouseholdId(data.household_id, data.name),
  });

  if (mutation.isSuccess) {
    return (
      <View style={styles.container}>
        <View style={styles.headerBlock}>
          <Text style={styles.title}>Your household</Text>
          <Text style={styles.subtitle}>One household, two accounts, one shared book.</Text>
        </View>
        <HouseholdTabs active="create" onSelectJoin={() => navigation.replace('HouseholdJoin')} />

        <View style={styles.codeCard}>
          <Text style={styles.fieldLabel}>Household name</Text>
          <Text style={styles.householdName}>{mutation.data.name}</Text>
          <View style={styles.divider} />
          <View style={styles.codeRow}>
            <View>
              <Text style={styles.fieldLabel}>Invite code</Text>
              <Text style={styles.code}>{mutation.data.invite_code}</Text>
            </View>
            <View style={styles.codeActions}>
              <Pressable style={styles.codeActionButton} onPress={() => Clipboard.setString(mutation.data.invite_code)} hitSlop={8}>
                <MaterialIcons name="content-copy" style={styles.codeActionIcon} />
              </Pressable>
              <Pressable
                style={styles.codeActionButton}
                onPress={() => Share.share({message: `Join our Ledger household with code ${mutation.data.invite_code}`})}
                hitSlop={8}>
                <MaterialIcons name="share" style={styles.codeActionIcon} />
              </Pressable>
            </View>
          </View>
          <Text style={styles.codeHint}>Share this with your partner. It works once, and expires in 24 hours.</Text>
        </View>

        <View style={styles.waitingBanner}>
          <Text style={styles.waitingText}>Waiting for your partner to join. You can start adding wallets now.</Text>
        </View>

        <View style={{flex: 1}} />
        <Pressable style={styles.button} onPress={() => navigation.replace('SmsPermissionRationale')}>
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerBlock}>
        <Text style={styles.title}>Your household</Text>
        <Text style={styles.subtitle}>One household, two accounts, one shared book.</Text>
      </View>
      <HouseholdTabs active="create" onSelectJoin={() => navigation.replace('HouseholdJoin')} />

      <View style={styles.field}>
        <Text style={styles.fieldLabel}>Household name</Text>
        <TextInput style={styles.input} value={name} onChangeText={setName} placeholderTextColor={colors.textSecondary} />
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <View style={{flex: 1}} />
      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Creating…' : 'Create household'}</Text>
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
  input: {
    marginTop: spacing.xs,
    height: 50,
    borderRadius: radius.input,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    paddingHorizontal: 14,
    fontSize: 15,
  },
  codeCard: {
    marginTop: spacing.lg,
    padding: 20,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  householdName: {color: colors.textPrimary, fontSize: 16, fontWeight: '600', marginTop: spacing.xs},
  divider: {height: 1, backgroundColor: colors.border, marginVertical: 18},
  code: {color: colors.accentOnDark, fontFamily: fontFamilies.monetary, fontSize: 30, letterSpacing: 6, marginTop: 10},
  codeRow: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between'},
  codeActions: {flexDirection: 'row', gap: spacing.sm},
  codeActionButton: {
    width: 38,
    height: 38,
    borderRadius: radius.iconTile,
    backgroundColor: colors.backgroundRaised,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  codeActionIcon: {color: colors.accentOnDark, fontSize: 18},
  codeHint: {fontSize: 12, color: colors.textSecondary, marginTop: spacing.xs, lineHeight: 18},
  waitingBanner: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
    padding: 14,
    borderRadius: radius.row,
    backgroundColor: 'rgba(91,84,249,.08)',
    borderWidth: 1,
    borderColor: 'rgba(91,84,249,.28)',
  },
  waitingText: {flex: 1, fontSize: 12.5, color: '#C9C9D2'},
  error: {color: colors.negative, marginTop: spacing.sm},
  button: {height: 52, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
});
