import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {householdApi} from '@/api/client';
import {useAuthStore} from '@/state/authStore';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'HouseholdJoin'>;

export function HouseholdJoinScreen({navigation}: Props) {
  const [inviteCode, setInviteCode] = useState('');
  const setHouseholdId = useAuthStore((s) => s.setHouseholdId);

  const mutation = useMutation({
    mutationFn: () => householdApi.join(inviteCode.toUpperCase()),
    onSuccess: (data) => {
      setHouseholdId(data.household_id);
      navigation.replace('Home');
    },
  });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Enter your partner's invite code</Text>
      <TextInput
        style={styles.input}
        value={inviteCode}
        onChangeText={setInviteCode}
        autoCapitalize="characters"
        maxLength={6}
        placeholder="ABC123"
        placeholderTextColor={colors.textSecondary}
      />
      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}
      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Joining…' : 'Join household'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg, justifyContent: 'center'},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600', marginBottom: spacing.lg},
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.md,
    letterSpacing: 4,
    textAlign: 'center',
    fontSize: 20,
  },
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center'},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  error: {color: colors.negative, marginBottom: spacing.sm},
});
