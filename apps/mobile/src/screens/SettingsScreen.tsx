import React, {useEffect, useState} from 'react';
import {Linking, PermissionsAndroid, Platform, Pressable, ScrollView, Share, StyleSheet, Text, View} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import Clipboard from '@react-native-clipboard/clipboard';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import {householdApi} from '@/api/client';
import {BottomNavBar} from '@/components/BottomNavBar';
import {isBiometricSensorAvailable} from '@/native/biometrics';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Settings'>;

function Toggle({on}: {on: boolean}) {
  return (
    <View style={[styles.toggleTrack, on && styles.toggleTrackOn]}>
      <View style={styles.toggleThumb} />
    </View>
  );
}

function Row({glyph, title, subtitle, onPress, right}: {glyph: string; title: string; subtitle?: string; onPress?: () => void; right?: React.ReactNode}) {
  return (
    <Pressable style={styles.row} onPress={onPress} disabled={!onPress}>
      <View style={styles.rowIcon}>
        <MaterialIcons name={glyph} style={styles.rowIconGlyph} />
      </View>
      <View style={{flex: 1}}>
        <Text style={styles.rowTitle}>{title}</Text>
        {!!subtitle && <Text style={styles.rowSubtitle}>{subtitle}</Text>}
      </View>
      {right ?? <MaterialIcons name="chevron-right" style={styles.chevron} />}
    </Pressable>
  );
}

export function SettingsScreen({navigation}: Props) {
  const name = useAuthStore((s) => s.name);
  const householdName = useAuthStore((s) => s.householdName);
  const clearSession = useAuthStore((s) => s.clearSession);
  const biometricEnabled = useAuthStore((s) => s.biometricEnabled);
  const setBiometricEnabled = useAuthStore((s) => s.setBiometricEnabled);

  const [smsDetectionOn, setSmsDetectionOn] = useState(false);
  const [biometricAvailable, setBiometricAvailable] = useState(false);

  useEffect(() => {
    if (Platform.OS !== 'android') return;
    PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.RECEIVE_SMS).then(setSmsDetectionOn);
    isBiometricSensorAvailable().then(setBiometricAvailable);
  }, []);

  const inviteCodeQuery = useQuery({queryKey: ['household', 'invite-code'], queryFn: () => householdApi.inviteCode()});

  const onToggleSms = async () => {
    if (smsDetectionOn) {
      // Android doesn't let an app revoke its own granted permission —
      // send the user to system settings, same pattern as most apps use
      // for a "turn this off" toggle on an already-granted permission.
      Linking.openSettings();
      return;
    }
    const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECEIVE_SMS);
    setSmsDetectionOn(granted === PermissionsAndroid.RESULTS.GRANTED);
  };

  const onToggleBiometric = () => {
    if (!biometricAvailable) return;
    setBiometricEnabled(!biometricEnabled);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={{paddingBottom: spacing.xl}}>
        <Text style={styles.title}>Settings</Text>

        <View style={styles.profileRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{(name ?? '?').charAt(0).toUpperCase()}</Text>
          </View>
          <View style={{flex: 1}}>
            <Text style={styles.profileName}>{name}</Text>
          </View>
          <Text style={styles.chevron}>›</Text>
        </View>

        <Text style={styles.sectionLabel}>Household</Text>
        <View style={styles.householdCard}>
          <View style={styles.householdRow}>
            <View style={styles.avatarStack}>
              <View style={[styles.stackAvatar, {borderColor: colors.accentOnDark}]}>
                <Text style={[styles.stackAvatarText, {color: colors.accentOnDark}]}>{(name ?? '?').charAt(0).toUpperCase()}</Text>
              </View>
              <View style={[styles.stackAvatar, styles.stackAvatarOffset, {borderColor: '#F1CB8E'}]}>
                <Text style={[styles.stackAvatarText, {color: '#F1CB8E'}]}>+</Text>
              </View>
            </View>
            <Text style={styles.householdNameText}>{householdName ?? 'Your household'}</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.inviteRow}>
            <View>
              <Text style={styles.inviteLabel}>Invite code</Text>
              <Text style={styles.inviteCode}>{inviteCodeQuery.data?.invite_code ?? '······'}</Text>
            </View>
            {!!inviteCodeQuery.data?.invite_code && (
              <View style={styles.inviteActions}>
                <Pressable
                  style={styles.inviteActionButton}
                  onPress={() => Clipboard.setString(inviteCodeQuery.data!.invite_code)}
                  hitSlop={8}>
                  <MaterialIcons name="content-copy" style={styles.inviteActionIcon} />
                </Pressable>
                <Pressable
                  style={styles.inviteActionButton}
                  onPress={() => Share.share({message: `Join our Ledger household with code ${inviteCodeQuery.data!.invite_code}`})}
                  hitSlop={8}>
                  <MaterialIcons name="share" style={styles.inviteActionIcon} />
                </Pressable>
              </View>
            )}
          </View>
        </View>

        <Text style={styles.sectionLabel}>Book</Text>
        <View style={styles.section}>
          <Row glyph="category" title="Manage categories" onPress={() => navigation.navigate('Categories')} />
          <Row glyph="account-balance-wallet" title="Manage wallets" onPress={() => navigation.navigate('WalletsList')} />
          <Row glyph="autorenew" title="Recurring transactions" onPress={() => navigation.navigate('RecurringRulesList')} />
          <Row glyph="account-balance" title="Loans" onPress={() => navigation.navigate('LoansList')} />
          <Row
            glyph="sms"
            title="SMS detection"
            subtitle={smsDetectionOn ? 'On' : 'Off — tap to allow'}
            onPress={onToggleSms}
            right={<Toggle on={smsDetectionOn} />}
          />
        </View>

        <Text style={styles.sectionLabel}>Security</Text>
        <View style={styles.section}>
          <Row glyph="lock" title="Change PIN" onPress={() => navigation.navigate('PinSetup')} />
          <Row
            glyph="fingerprint"
            title="Unlock with fingerprint"
            subtitle={biometricAvailable ? undefined : 'No fingerprint sensor on this device'}
            onPress={biometricAvailable ? onToggleBiometric : undefined}
            right={<Toggle on={biometricEnabled} />}
          />
        </View>

        <Pressable
          style={styles.logoutButton}
          onPress={() => {
            clearSession();
            navigation.reset({index: 0, routes: [{name: 'Login'}]});
          }}>
          <Text style={styles.logoutButtonText}>Log out</Text>
        </Pressable>
      </ScrollView>
      <BottomNavBar active="settings" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 20, fontWeight: '600', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    padding: 13,
    borderRadius: radius.card - 2,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  avatar: {width: 44, height: 44, borderRadius: 22, backgroundColor: colors.background, borderWidth: 2, borderColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  avatarText: {color: colors.accentOnDark, fontSize: 16, fontWeight: '600'},
  profileName: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  chevron: {color: colors.textSecondary, fontSize: 19},
  sectionLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: 4},
  householdCard: {marginHorizontal: spacing.lg, padding: 16, borderRadius: radius.card - 2, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  householdRow: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm},
  avatarStack: {flexDirection: 'row'},
  stackAvatar: {width: 28, height: 28, borderRadius: 14, backgroundColor: colors.background, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center'},
  stackAvatarOffset: {marginLeft: -7},
  stackAvatarText: {fontSize: 10.5, fontWeight: '600'},
  householdNameText: {flex: 1, fontSize: 12.5, color: colors.textPrimary},
  divider: {height: 1, backgroundColor: colors.border, marginVertical: 11},
  inviteRow: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  inviteLabel: {fontSize: 11, color: colors.textSecondary},
  inviteCode: {fontFamily: fontFamilies.monetary, fontSize: 17, letterSpacing: 4, color: colors.accentOnDark, marginTop: 3},
  inviteActions: {flexDirection: 'row', gap: spacing.sm},
  inviteActionButton: {
    width: 36,
    height: 36,
    borderRadius: radius.iconTile,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inviteActionIcon: {color: colors.accentOnDark, fontSize: 17},
  section: {marginHorizontal: spacing.lg},
  row: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingVertical: 11, borderBottomWidth: 1, borderBottomColor: '#17171F'},
  rowIcon: {width: 36, height: 36, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center'},
  rowIconGlyph: {color: '#C9C9D2', fontSize: 15},
  rowTitle: {color: colors.textPrimary, fontSize: 13},
  rowSubtitle: {color: colors.textSecondary, fontSize: 11, marginTop: 2},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, backgroundColor: colors.border, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  logoutButton: {marginHorizontal: spacing.lg, marginTop: spacing.lg, height: 46, borderRadius: radius.pill, borderWidth: 1, borderColor: 'rgba(255,107,107,.35)', alignItems: 'center', justifyContent: 'center'},
  logoutButtonText: {color: '#FF9B9B', fontSize: 14, fontWeight: '600'},
});
