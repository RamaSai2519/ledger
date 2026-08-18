import React from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'HouseholdChoice'>;

export function HouseholdChoiceScreen({navigation}: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Set up your household</Text>
      <Text style={styles.subtitle}>
        A household is the shared ledger you and your partner both see. Create one, or join theirs with an
        invite code.
      </Text>
      <Pressable style={styles.button} onPress={() => navigation.navigate('HouseholdCreate')}>
        <Text style={styles.buttonText}>Create a household</Text>
      </Pressable>
      <Pressable style={styles.buttonSecondary} onPress={() => navigation.navigate('HouseholdJoin')}>
        <Text style={styles.buttonSecondaryText}>Join a household</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg, justifyContent: 'center'},
  title: {color: colors.textPrimary, fontSize: 24, fontWeight: '600', marginBottom: spacing.md},
  subtitle: {color: colors.textSecondary, fontSize: 15, lineHeight: 22, marginBottom: spacing.xl},
  button: {
    backgroundColor: colors.accent,
    borderRadius: radius.pill,
    padding: spacing.md,
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  buttonSecondary: {
    borderRadius: radius.pill,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonSecondaryText: {color: colors.textPrimary, fontWeight: '600'},
});
