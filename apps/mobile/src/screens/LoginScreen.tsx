import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {authApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export function LoginScreen({navigation}: Props) {
  const [mobileNumber, setMobileNumber] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const setSession = useAuthStore((s) => s.setSession);

  const mutation = useMutation({
    mutationFn: () => authApi.login({mobile_number: mobileNumber, password}),
    onSuccess: (data) => {
      setSession({
        userId: data.user_id,
        name: data.name,
        householdId: data.household_id ?? null,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });
      navigation.replace(data.household_id ? 'Home' : 'HouseholdCreate');
    },
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.mark}>
          <Text style={styles.markText}>L</Text>
        </View>
        <Text style={styles.title}>Welcome back</Text>
      </View>

      <View style={styles.fields}>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Mobile number</Text>
          <View style={styles.fieldInput}>
            <Text style={styles.fieldPrefix}>+91</Text>
            <TextInput
              style={styles.fieldTextMono}
              value={mobileNumber}
              onChangeText={setMobileNumber}
              keyboardType="phone-pad"
              placeholder="98765 43210"
              placeholderTextColor={colors.textSecondary}
            />
          </View>
        </View>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Password</Text>
          <View style={[styles.fieldInput, styles.fieldInputFocused]}>
            <TextInput
              style={[styles.fieldTextMono, {flex: 1, letterSpacing: 3}]}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!passwordVisible}
              placeholder="••••••"
              placeholderTextColor={colors.textSecondary}
            />
            <Pressable onPress={() => setPasswordVisible((v) => !v)} hitSlop={8}>
              <Text style={styles.eyeGlyph}>{passwordVisible ? '🙈' : '👁'}</Text>
            </Pressable>
          </View>
        </View>
        <Text style={styles.forgot}>Forgot password?</Text>
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <View style={{paddingTop: spacing.md}}>
        <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending}>
          <Text style={styles.buttonText}>{mutation.isPending ? 'Logging in…' : 'Log in'}</Text>
        </Pressable>
      </View>

      <View style={styles.dividerRow}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>OR</Text>
        <View style={styles.dividerLine} />
      </View>

      <View style={styles.biometricButton}>
        <Text style={styles.biometricGlyph}>⚷</Text>
        <Text style={styles.biometricText}>Use fingerprint</Text>
      </View>

      <View style={{flex: 1}} />
      <Pressable onPress={() => navigation.replace('SignUp')}>
        <Text style={styles.link}>
          New here? <Text style={styles.linkAccent}>Create an account</Text>
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl},
  header: {alignItems: 'center', gap: spacing.sm, paddingTop: 56},
  mark: {width: 56, height: 56, borderRadius: radius.card - 2, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  markText: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 28, fontWeight: '600'},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 24, letterSpacing: -0.4, fontWeight: '600'},
  fields: {gap: spacing.md, paddingTop: 38},
  field: {gap: spacing.xs},
  fieldLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.textSecondary},
  fieldInput: {
    height: 50,
    borderRadius: radius.input,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: 14,
  },
  fieldInputFocused: {borderColor: colors.accent},
  fieldTextMono: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 14},
  fieldPrefix: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 14},
  eyeGlyph: {fontSize: 15},
  forgot: {textAlign: 'right', color: colors.accentOnDark, fontSize: 12.5},
  error: {color: colors.negative, marginTop: spacing.sm},
  button: {height: 52, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  dividerRow: {flexDirection: 'row', alignItems: 'center', gap: 10, paddingTop: spacing.lg},
  dividerLine: {flex: 1, height: 1, backgroundColor: colors.border},
  dividerText: {fontSize: 11, color: '#5A5A66'},
  biometricButton: {
    marginTop: spacing.md,
    height: 52,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
  },
  biometricGlyph: {fontSize: 16, color: colors.accentOnDark},
  biometricText: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  link: {textAlign: 'center', color: colors.textSecondary, fontSize: 13, paddingBottom: spacing.sm},
  linkAccent: {color: colors.accentOnDark, fontWeight: '600'},
});
