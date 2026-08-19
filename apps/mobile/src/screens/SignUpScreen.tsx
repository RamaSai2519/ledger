import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import {authApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'SignUp'>;

export function SignUpScreen({navigation}: Props) {
  const [mobileNumber, setMobileNumber] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const setSession = useAuthStore((s) => s.setSession);

  const mutation = useMutation({
    mutationFn: () => authApi.signup({mobile_number: mobileNumber, password, name}),
    onSuccess: (data) => {
      setSession({
        userId: data.user_id,
        name: data.name,
        householdId: data.household_id ?? null,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });
      navigation.replace('HouseholdCreate');
    },
  });

  return (
    <View style={styles.container}>
      <View style={styles.headerBlock}>
        <Text style={styles.title}>Create your account</Text>
        <Text style={styles.subtitle}>You'll join or start a household next.</Text>
      </View>

      <View style={styles.fields}>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Your name</Text>
          <View style={styles.fieldInput}>
            <TextInput
              style={styles.fieldText}
              value={name}
              onChangeText={setName}
              placeholder="Full name"
              placeholderTextColor={colors.textSecondary}
            />
          </View>
        </View>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Mobile number</Text>
          <View style={[styles.fieldInput, styles.fieldInputFocused]}>
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
          <View style={styles.fieldInput}>
            <TextInput
              style={[styles.fieldTextMono, {flex: 1, letterSpacing: 3}]}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!passwordVisible}
              placeholder="••••••••"
              placeholderTextColor={colors.textSecondary}
            />
            <Pressable onPress={() => setPasswordVisible((v) => !v)} hitSlop={8}>
              <MaterialIcons name={passwordVisible ? 'visibility-off' : 'visibility'} style={styles.eyeGlyph} />
            </Pressable>
          </View>
          <Text style={styles.fieldHint}>At least 8 characters.</Text>
        </View>
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <View style={{paddingTop: spacing.md}}>
        <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending}>
          <Text style={styles.buttonText}>{mutation.isPending ? 'Creating…' : 'Create account'}</Text>
        </Pressable>
      </View>

      <Pressable onPress={() => navigation.replace('Login')}>
        <Text style={styles.link}>
          Already have an account? <Text style={styles.linkAccent}>Log in</Text>
        </Text>
      </Pressable>

      <View style={{flex: 1}} />
      <Text style={styles.legal}>By continuing you agree to the terms and privacy policy.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl},
  headerBlock: {paddingTop: spacing.md},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 27, letterSpacing: -0.6, fontWeight: '600'},
  subtitle: {color: colors.textSecondary, fontSize: 13.5, marginTop: spacing.xs},
  fields: {gap: spacing.md, paddingTop: spacing.xl},
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
  fieldText: {flex: 1, color: colors.textPrimary, fontSize: 14},
  fieldTextMono: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 14},
  fieldPrefix: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 14},
  eyeGlyph: {fontSize: 15},
  fieldHint: {fontSize: 11, color: colors.textSecondary},
  error: {color: colors.negative, marginTop: spacing.sm},
  button: {height: 52, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  link: {textAlign: 'center', color: colors.textSecondary, fontSize: 13, paddingTop: spacing.lg},
  linkAccent: {color: colors.accentOnDark, fontWeight: '600'},
  legal: {fontSize: 11, lineHeight: 16.5, color: '#5A5A66', textAlign: 'center'},
});
