import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {authApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'SignUp'>;

export function SignUpScreen({navigation}: Props) {
  const [mobileNumber, setMobileNumber] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
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
      navigation.replace('HouseholdChoice');
    },
  });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Create your account</Text>
      <TextInput
        style={styles.input}
        placeholder="Name"
        placeholderTextColor={colors.textSecondary}
        value={name}
        onChangeText={setName}
      />
      <TextInput
        style={styles.input}
        placeholder="Mobile number"
        placeholderTextColor={colors.textSecondary}
        keyboardType="phone-pad"
        value={mobileNumber}
        onChangeText={setMobileNumber}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor={colors.textSecondary}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}
      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Creating…' : 'Sign up'}</Text>
      </Pressable>
      <Pressable onPress={() => navigation.replace('Login')}>
        <Text style={styles.link}>Already have an account? Log in</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg, justifyContent: 'center'},
  title: {color: colors.textPrimary, fontSize: 24, fontWeight: '600', marginBottom: spacing.lg},
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: radius.pill,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  error: {color: colors.negative, marginBottom: spacing.sm},
  link: {color: colors.accent, marginTop: spacing.lg, textAlign: 'center'},
});
