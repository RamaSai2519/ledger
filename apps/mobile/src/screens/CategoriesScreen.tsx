import React, {useState} from 'react';
import {FlatList, Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Category, CategoryType} from '@/api/client';
import {categoriesApi} from '@/api/client';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Categories'>;

export function CategoriesScreen({}: Props) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<CategoryType>('expense');
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const query = useQuery({
    queryKey: ['categories', 'manage', tab],
    queryFn: () => categoriesApi.list({type: tab}),
  });

  const invalidate = () => queryClient.invalidateQueries({queryKey: ['categories']});

  const createMutation = useMutation({
    mutationFn: () => categoriesApi.create({name: newName.trim(), type: tab}),
    onSuccess: () => {
      setNewName('');
      invalidate();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: {id: string; name: string}) => categoriesApi.update(vars.id, {name: vars.name}),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.remove(id),
    onSuccess: invalidate,
  });

  const categories = query.data?.categories ?? [];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Categories</Text>

      <View style={styles.tabRow}>
        {(['expense', 'income'] as CategoryType[]).map((t) => (
          <Pressable key={t} style={[styles.tab, tab === t && styles.tabSelected]} onPress={() => setTab(t)}>
            <Text style={tab === t ? styles.tabTextSelected : styles.tabText}>
              {t === 'expense' ? 'Expense' : 'Income'}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.addRow}>
        <TextInput
          style={styles.addInput}
          value={newName}
          onChangeText={setNewName}
          placeholder="New category name"
          placeholderTextColor={colors.textSecondary}
        />
        <Pressable
          style={styles.addButton}
          disabled={!newName.trim() || createMutation.isPending}
          onPress={() => createMutation.mutate()}>
          <Text style={styles.addButtonText}>Add</Text>
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}

      <FlatList
        data={categories}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{gap: spacing.xs}}
        renderItem={({item}: {item: Category}) => {
          const isSystem = item.name === 'Balance Adjustment';
          const isEditing = editingId === item.id;
          return (
            <View style={styles.row}>
              {isEditing ? (
                <TextInput
                  style={styles.editInput}
                  value={editingName}
                  onChangeText={setEditingName}
                  autoFocus
                  onSubmitEditing={() => updateMutation.mutate({id: item.id, name: editingName})}
                />
              ) : (
                <Text style={styles.rowText}>
                  {item.name}
                  {item.is_default ? ' · default' : ''}
                </Text>
              )}

              {!isSystem && !isEditing && (
                <View style={styles.rowActions}>
                  <Pressable
                    onPress={() => {
                      setEditingId(item.id);
                      setEditingName(item.name);
                    }}>
                    <Text style={styles.rowAction}>Edit</Text>
                  </Pressable>
                  <Pressable onPress={() => archiveMutation.mutate(item.id)}>
                    <Text style={[styles.rowAction, {color: colors.negative}]}>Remove</Text>
                  </Pressable>
                </View>
              )}
              {isEditing && (
                <Pressable onPress={() => updateMutation.mutate({id: item.id, name: editingName})}>
                  <Text style={styles.rowAction}>Save</Text>
                </Pressable>
              )}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600', marginBottom: spacing.md},
  tabRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md},
  tab: {flex: 1, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingVertical: spacing.sm, alignItems: 'center'},
  tabSelected: {backgroundColor: colors.accent, borderColor: colors.accent},
  tabText: {color: colors.textSecondary, fontSize: 13},
  tabTextSelected: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  addRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md},
  addInput: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.sm,
  },
  addButton: {backgroundColor: colors.accent, borderRadius: radius.pill, paddingHorizontal: spacing.md, justifyContent: 'center'},
  addButtonText: {color: colors.textPrimary, fontWeight: '600'},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.lg},
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
  },
  rowText: {color: colors.textPrimary, fontSize: 14, flex: 1},
  editInput: {
    flex: 1,
    color: colors.textPrimary,
    borderBottomWidth: 1,
    borderBottomColor: colors.accent,
    paddingVertical: 2,
  },
  rowActions: {flexDirection: 'row', gap: spacing.md},
  rowAction: {color: colors.accent, fontSize: 13, fontWeight: '600'},
});
