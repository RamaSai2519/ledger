import React, {useState} from 'react';
import {FlatList, Modal, Pressable, StyleSheet, Text, View} from 'react-native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import type {Category} from '@/api/client';
import {colors, radius, spacing} from '@/theme/tokens';
import {glyphForCategoryIcon} from '@/theme/categoryIcons';

type Props = {
  label: string;
  categories: Category[];
  value: string | null;
  onChange: (value: string) => void;
};

// LED-10: dedicated icon-grid category picker (design project's #s16),
// replacing the generic PickerField list specifically for category
// selection — a materially different, higher-fidelity picking experience
// than the plain text-list modal PickerField still uses for wallets.
export function CategoryIconGridField({label, categories, value, onChange}: Props) {
  const [open, setOpen] = useState(false);
  const selected = categories.find((c) => c.id === value);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={styles.field} onPress={() => setOpen(true)}>
        {selected ? (
          <View style={styles.selectedRow}>
            <View
              style={[
                styles.selectedIconTile,
                {backgroundColor: `${selected.color ?? colors.accent}24`, borderColor: selected.color ?? colors.accent},
              ]}>
              <MaterialCommunityIcons
                name={glyphForCategoryIcon(selected.icon)}
                size={17}
                color={selected.color ?? colors.accent}
              />
            </View>
            <Text style={styles.fieldText}>{selected.name}</Text>
          </View>
        ) : (
          <Text style={styles.placeholderText}>Select a category…</Text>
        )}
      </Pressable>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
            <Text style={styles.sheetTitle}>{label}</Text>
            <FlatList
              data={categories}
              keyExtractor={(item) => item.id}
              numColumns={4}
              columnWrapperStyle={styles.gridRow}
              contentContainerStyle={styles.gridContent}
              renderItem={({item}) => {
                const isSelected = item.id === value;
                const color = item.color ?? colors.accent;
                return (
                  <Pressable
                    style={styles.gridItem}
                    onPress={() => {
                      onChange(item.id);
                      setOpen(false);
                    }}>
                    <View
                      style={[
                        styles.gridIconTile,
                        {backgroundColor: `${color}1F`, borderColor: isSelected ? color : colors.border},
                        isSelected && styles.gridIconTileSelected,
                      ]}>
                      <MaterialCommunityIcons name={glyphForCategoryIcon(item.icon)} size={22} color={color} />
                      {isSelected && (
                        <View style={[styles.checkBadge, {backgroundColor: color}]}>
                          <MaterialCommunityIcons name="check" style={styles.checkBadgeText} />
                        </View>
                      )}
                    </View>
                    <Text style={styles.gridItemLabel} numberOfLines={1}>
                      {item.name}
                    </Text>
                  </Pressable>
                );
              }}
              ListEmptyComponent={<Text style={styles.emptyText}>No categories yet.</Text>}
            />
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {marginBottom: spacing.md},
  label: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs},
  field: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
  },
  selectedRow: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm},
  selectedIconTile: {width: 34, height: 34, borderRadius: 12, borderWidth: 1, alignItems: 'center', justifyContent: 'center'},
  fieldText: {color: colors.textPrimary, fontSize: 15},
  placeholderText: {color: colors.textSecondary, fontSize: 15, paddingVertical: spacing.xs},
  backdrop: {flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end'},
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.lg,
    maxHeight: '70%',
  },
  sheetTitle: {color: colors.textPrimary, fontSize: 17, fontWeight: '600', marginBottom: spacing.md},
  gridContent: {gap: spacing.md, paddingBottom: spacing.sm},
  gridRow: {gap: spacing.md},
  gridItem: {flex: 1, alignItems: 'center', gap: 6},
  gridIconTile: {
    width: 56,
    height: 56,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  gridIconTileSelected: {borderWidth: 2},
  checkBadge: {position: 'absolute', bottom: -3, right: -3, width: 16, height: 16, borderRadius: 8, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: colors.surface},
  checkBadgeText: {color: colors.textPrimary, fontSize: 9, fontWeight: '700'},
  gridItemLabel: {color: colors.textSecondary, fontSize: 10.5, textAlign: 'center'},
  emptyText: {color: colors.textSecondary, textAlign: 'center', padding: spacing.lg},
});
