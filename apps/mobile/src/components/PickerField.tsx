import React, {useState} from 'react';
import {FlatList, Modal, Pressable, StyleSheet, Text, View} from 'react-native';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import {colors, radius, spacing} from '@/theme/tokens';

export type PickerOption = {label: string; value: string; sublabel?: string; tint?: string};

type Props = {
  label: string;
  placeholder?: string;
  options: PickerOption[];
  value: string | null;
  onChange: (value: string) => void;
  // LED-19: SmsSuggestionEditScreen sets this for a null/low-confidence
  // prefill so the picker sheet opens on its own rather than waiting for a
  // tap — the field the household is least likely to have gotten "for free"
  // is the one that should ask for their input first.
  autoOpen?: boolean;
};

// A lightweight modal picker used for wallet/category selection in the
// transaction and wallet forms. No native picker/select library is in the
// dependency tree yet (would need native linking we can't verify here), so
// this stays pure-JS/RN — a Pressable that opens a full list in a Modal.
export function PickerField({label, placeholder = 'Select…', options, value, onChange, autoOpen = false}: Props) {
  const [open, setOpen] = useState(autoOpen);
  const selected = options.find((o) => o.value === value);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={styles.field} onPress={() => setOpen(true)}>
        <Text style={selected ? styles.fieldText : styles.placeholderText}>
          {selected ? selected.label : placeholder}
        </Text>
      </Pressable>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.sheet}>
            <Text style={styles.sheetTitle}>{label}</Text>
            <FlatList
              data={options}
              keyExtractor={(item) => item.value}
              renderItem={({item}) => (
                <Pressable
                  style={styles.option}
                  onPress={() => {
                    onChange(item.value);
                    setOpen(false);
                  }}>
                  {item.tint && <View style={[styles.tintDot, {backgroundColor: item.tint}]} />}
                  <View style={{flex: 1}}>
                    <Text style={styles.optionText}>{item.label}</Text>
                    {item.sublabel && <Text style={styles.optionSublabel}>{item.sublabel}</Text>}
                  </View>
                  {item.value === value && <MaterialIcons name="check" style={styles.checkmark} />}
                </Pressable>
              )}
              ListEmptyComponent={<Text style={styles.emptyText}>Nothing to pick from yet.</Text>}
            />
          </View>
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
    maxHeight: '70%',
  },
  sheetTitle: {color: colors.textPrimary, fontSize: 17, fontWeight: '600', marginBottom: spacing.md},
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tintDot: {width: 10, height: 10, borderRadius: 5, marginRight: spacing.sm},
  optionText: {color: colors.textPrimary, fontSize: 15},
  optionSublabel: {color: colors.textSecondary, fontSize: 12, marginTop: 2},
  checkmark: {color: colors.accent, fontSize: 16, fontWeight: '700'},
  emptyText: {color: colors.textSecondary, textAlign: 'center', padding: spacing.lg},
});
