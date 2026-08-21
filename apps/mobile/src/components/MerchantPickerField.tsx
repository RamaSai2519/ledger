import React, {useState} from 'react';
import {FlatList, Modal, Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import {merchantsApi} from '@/api/client';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = {
  label: string;
  placeholder?: string;
  value: string | null;
  onChange: (name: string) => void;
  autoOpen?: boolean;
};

// LED-28: search-or-create merchant picker for the SMS suggestion edit
// screen — lets the household pick a previously-seen canonical merchant
// name or type a brand new one, distinct from PickerField (which only ever
// selects from a fixed list, never creates). Selecting/typing a name here
// is what teaches the backend's merchant_aliases mapping for next time
// (see SmsSuggestionAcceptInput.merchant_name).
export function MerchantPickerField({label, placeholder = 'Select or type a merchant…', value, onChange, autoOpen = false}: Props) {
  const [open, setOpen] = useState(autoOpen);
  const [query, setQuery] = useState('');

  const merchantsQuery = useQuery({
    queryKey: ['merchants', query],
    queryFn: () => merchantsApi.list(query.trim() ? {q: query.trim()} : undefined),
    enabled: open,
  });

  const names = merchantsQuery.data?.merchants ?? [];
  const trimmedQuery = query.trim();
  const exactMatch = names.some((n) => n.toLowerCase() === trimmedQuery.toLowerCase());

  const select = (name: string) => {
    onChange(name);
    setQuery('');
    setOpen(false);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={styles.field} onPress={() => setOpen(true)}>
        <Text style={value ? styles.fieldText : styles.placeholderText}>{value ?? placeholder}</Text>
      </Pressable>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
            <Text style={styles.sheetTitle}>{label}</Text>
            <TextInput
              style={styles.searchInput}
              value={query}
              onChangeText={setQuery}
              placeholder="Search or type a new merchant"
              placeholderTextColor={colors.textSecondary}
              autoFocus
            />
            <FlatList
              data={names}
              keyExtractor={(item) => item}
              keyboardShouldPersistTaps="handled"
              ListHeaderComponent={
                trimmedQuery && !exactMatch ? (
                  <Pressable style={styles.createOption} onPress={() => select(trimmedQuery)}>
                    <MaterialIcons name="add-circle-outline" style={styles.createIcon} />
                    <Text style={styles.createText}>Create "{trimmedQuery}"</Text>
                  </Pressable>
                ) : null
              }
              renderItem={({item}) => (
                <Pressable style={styles.option} onPress={() => select(item)}>
                  <Text style={styles.optionText}>{item}</Text>
                  {item === value && <MaterialIcons name="check" style={styles.checkmark} />}
                </Pressable>
              )}
              ListEmptyComponent={
                !trimmedQuery ? <Text style={styles.emptyText}>Start typing to search or create a merchant.</Text> : null
              }
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
    padding: spacing.md,
  },
  fieldText: {color: colors.textPrimary, fontSize: 15},
  placeholderText: {color: colors.textSecondary, fontSize: 15},
  backdrop: {flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end'},
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.lg,
    maxHeight: '75%',
  },
  sheetTitle: {color: colors.textPrimary, fontSize: 17, fontWeight: '600', marginBottom: spacing.md},
  searchInput: {
    backgroundColor: colors.backgroundRaised,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: 15,
    marginBottom: spacing.sm,
  },
  createOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  createIcon: {color: colors.accent, fontSize: 18},
  createText: {color: colors.accent, fontSize: 15, fontWeight: '600'},
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  optionText: {color: colors.textPrimary, fontSize: 15},
  checkmark: {color: colors.accent, fontSize: 16, fontWeight: '700'},
  emptyText: {color: colors.textSecondary, textAlign: 'center', padding: spacing.lg},
});
