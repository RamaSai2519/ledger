import React, {useState} from 'react';
import {FlatList, Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {CategoryType} from '@/api/client';
import {categoriesApi} from '@/api/client';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Categories'>;

const SWATCHES = ['#E8A33D', '#8FB4FF', '#7FE3B8', '#D4A5FF', '#FFB4B4', '#9BE0FF'];

export function CategoriesScreen({}: Props) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<CategoryType>('expense');
  const [editing, setEditing] = useState<{id: string | null; name: string; color: string} | null>(null);

  const query = useQuery({queryKey: ['categories', 'manage', tab], queryFn: () => categoriesApi.list({type: tab})});
  const archivedQuery = useQuery({
    queryKey: ['categories', 'manage', tab, 'archived'],
    queryFn: () => categoriesApi.list({type: tab, include_archived: true}),
  });

  const invalidate = () => queryClient.invalidateQueries({queryKey: ['categories']});

  const createMutation = useMutation({
    mutationFn: (vars: {name: string; color: string}) => categoriesApi.create({name: vars.name, type: tab, color: vars.color}),
    onSuccess: () => {
      setEditing(null);
      invalidate();
    },
  });
  const updateMutation = useMutation({
    mutationFn: (vars: {id: string; name: string; color: string}) => categoriesApi.update(vars.id, {name: vars.name, color: vars.color}),
    onSuccess: () => {
      setEditing(null);
      invalidate();
    },
  });
  const archiveMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.remove(id),
    onSuccess: () => {
      setEditing(null);
      invalidate();
    },
  });
  const unarchiveMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.update(id, {is_archived: false}),
    onSuccess: invalidate,
  });

  const categories = query.data?.categories ?? [];
  const archived = (archivedQuery.data?.categories ?? []).filter((c) => c.is_archived);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Categories</Text>
        <Pressable onPress={() => setEditing({id: null, name: '', color: SWATCHES[0]})} hitSlop={8}>
          <Text style={styles.addGlyph}>+</Text>
        </Pressable>
      </View>

      <View style={styles.tabRow}>
        {(['expense', 'income'] as CategoryType[]).map((t) => (
          <Pressable key={t} style={[styles.tab, tab === t && styles.tabSelected]} onPress={() => setTab(t)}>
            <Text style={tab === t ? styles.tabTextSelected : styles.tabText}>{t === 'expense' ? 'Expense' : 'Income'}</Text>
          </Pressable>
        ))}
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading categories…</Text>}
      {query.isError && (
        <View style={styles.errorBlock}>
          <Text style={styles.errorTitle}>Categories didn't load</Text>
          <Pressable onPress={() => query.refetch()}>
            <Text style={styles.errorRetry}>Try again</Text>
          </Pressable>
        </View>
      )}
      {query.isSuccess && categories.length === 0 && archived.length === 0 && !editing && (
        <View style={styles.emptyBlock}>
          <Text style={styles.emptyTitle}>No {tab} categories yet</Text>
          <Pressable style={styles.emptyOption} onPress={() => setEditing({id: null, name: '', color: SWATCHES[0]})}>
            <Text style={styles.emptyOptionText}>Add your first {tab} category</Text>
            <Text style={styles.emptyOptionChevron}>›</Text>
          </Pressable>
        </View>
      )}

      <FlatList
        data={[...categories.map((c) => ({...c, archived: false})), ...archived.map((c) => ({...c, archived: true}))]}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{paddingHorizontal: spacing.lg, paddingTop: spacing.sm}}
        ListFooterComponent={
          editing ? (
            <View style={styles.editPanel}>
              <Text style={styles.editPanelLabel}>{editing.id ? 'Editing a category' : 'New category'}</Text>
              <View style={styles.editPanelRow}>
                <View style={[styles.editIconTile, {backgroundColor: `${editing.color}24`, borderColor: editing.color}]}>
                  <Text style={[styles.editIconGlyph, {color: editing.color}]}>{(editing.name || '?').charAt(0).toUpperCase()}</Text>
                </View>
                <TextInput
                  style={styles.editNameInput}
                  value={editing.name}
                  onChangeText={(t) => setEditing((e) => e && {...e, name: t})}
                  placeholder="Category name"
                  placeholderTextColor={colors.textSecondary}
                  autoFocus
                />
              </View>
              <View style={styles.swatchRow}>
                {SWATCHES.map((c) => (
                  <Pressable
                    key={c}
                    style={[styles.swatch, {backgroundColor: c}, editing.color === c && styles.swatchSelected]}
                    onPress={() => setEditing((e) => e && {...e, color: c})}
                  />
                ))}
              </View>
              <View style={styles.editActions}>
                <Pressable
                  style={styles.saveButton}
                  disabled={!editing.name.trim()}
                  onPress={() =>
                    editing.id
                      ? updateMutation.mutate({id: editing.id, name: editing.name.trim(), color: editing.color})
                      : createMutation.mutate({name: editing.name.trim(), color: editing.color})
                  }>
                  <Text style={styles.saveButtonText}>Save category</Text>
                </Pressable>
                <Pressable style={styles.cancelButton} onPress={() => setEditing(null)}>
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </Pressable>
                {editing.id && (
                  <Pressable style={styles.cancelButton} onPress={() => archiveMutation.mutate(editing.id!)}>
                    <Text style={styles.cancelButtonText}>Archive</Text>
                  </Pressable>
                )}
              </View>
            </View>
          ) : null
        }
        renderItem={({item}) => {
          const isSystem = item.name === 'Balance Adjustment';
          return (
            <Pressable
              style={[styles.row, item.archived && {opacity: 0.55}]}
              disabled={isSystem}
              onPress={() =>
                item.archived
                  ? unarchiveMutation.mutate(item.id)
                  : setEditing({id: item.id, name: item.name, color: item.color ?? SWATCHES[0]})
              }>
              <View style={[styles.rowIcon, !item.archived && {backgroundColor: `${item.color ?? colors.accent}1F`, borderColor: item.color ?? colors.accent}]}>
                <Text style={[styles.rowIconGlyph, {color: item.archived ? colors.textSecondary : item.color ?? colors.accent}]}>
                  {item.name.charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={{flex: 1}}>
                <Text style={styles.rowName}>{item.name}</Text>
                <Text style={styles.rowMeta}>
                  {item.archived ? 'Archived · kept on old entries' : item.is_default ? 'Default category' : 'Custom category'}
                </Text>
              </View>
              {!isSystem && (
                <Text style={styles.rowChevron}>{item.archived ? '↺' : '⋮'}</Text>
              )}
            </Pressable>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  header: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 18, fontWeight: '600'},
  addGlyph: {color: colors.accentOnDark, fontSize: 22},
  tabRow: {flexDirection: 'row', gap: 6, marginHorizontal: spacing.lg, marginTop: spacing.md, padding: 3, borderRadius: radius.pill, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  tab: {flex: 1, paddingVertical: 8, borderRadius: radius.pill, alignItems: 'center'},
  tabSelected: {backgroundColor: colors.border},
  tabText: {color: colors.textSecondary, fontSize: 12.5},
  tabTextSelected: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600'},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.lg, paddingHorizontal: spacing.lg},
  errorBlock: {alignItems: 'center', marginTop: spacing.lg, gap: spacing.sm},
  errorTitle: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  errorRetry: {color: colors.accentOnDark, fontSize: 12.5, fontWeight: '600'},
  emptyBlock: {marginHorizontal: spacing.lg, marginTop: spacing.md, gap: spacing.sm},
  emptyTitle: {color: colors.textPrimary, fontSize: 15, fontWeight: '600', marginBottom: spacing.xs},
  emptyOption: {flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  emptyOptionText: {flex: 1, color: colors.textPrimary, fontSize: 13},
  emptyOptionChevron: {color: colors.textSecondary, fontSize: 18},
  row: {flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#17171F'},
  rowIcon: {width: 38, height: 38, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center'},
  rowIconGlyph: {fontWeight: '700', fontSize: 14},
  rowName: {color: colors.textPrimary, fontSize: 13.5, fontWeight: '600'},
  rowMeta: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 11, marginTop: 2},
  rowChevron: {color: '#5A5A66', fontSize: 18},
  editPanel: {marginTop: spacing.md, marginBottom: spacing.xl, padding: 16, borderRadius: radius.card - 2, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  editPanelLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66'},
  editPanelRow: {flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: spacing.sm},
  editIconTile: {width: 48, height: 48, borderRadius: 16, borderWidth: 1, alignItems: 'center', justifyContent: 'center'},
  editIconGlyph: {fontSize: 20, fontWeight: '700'},
  editNameInput: {flex: 1, height: 44, borderRadius: 12, backgroundColor: colors.backgroundRaised, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, color: colors.textPrimary, fontSize: 13.5},
  swatchRow: {flexDirection: 'row', gap: 9, marginTop: spacing.md},
  swatch: {width: 26, height: 26, borderRadius: 13},
  swatchSelected: {borderWidth: 2, borderColor: colors.background, shadowColor: '#000'},
  editActions: {flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md},
  saveButton: {flex: 1, height: 42, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  saveButtonText: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600'},
  cancelButton: {height: 42, paddingHorizontal: 16, borderRadius: radius.pill, borderWidth: 1, borderColor: '#2A2A38', alignItems: 'center', justifyContent: 'center'},
  cancelButtonText: {color: colors.textSecondary, fontSize: 12.5},
});
