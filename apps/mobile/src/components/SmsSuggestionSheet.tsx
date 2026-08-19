import React, {useEffect, useRef} from 'react';
import {Animated, Dimensions, Modal, Pressable, StyleSheet, Text, View} from 'react-native';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {SmsInboxSuggestion} from '@/api/client';
import {colors, fontFamilies, motion, radius, spacing} from '@/theme/tokens';

const {height: SCREEN_HEIGHT} = Dimensions.get('window');

// s22 in the design project — the SMS suggestion's "signature moment":
// a bottom sheet that slides up over Home (280ms ease-out, backdrop to 45%
// per tokens.ts's `motion`), rather than the plain inline card. No
// bottom-sheet library is installed, so this is a transparent Modal driving
// its own Animated.Value for the slide/backdrop rather than adding
// @gorhom/bottom-sheet or reanimated for one component.
export function SmsSuggestionSheet({
  visible,
  suggestion,
  canConfirm,
  confirming,
  onConfirm,
  onEdit,
  onDismiss,
  onRequestClose,
}: {
  visible: boolean;
  suggestion: SmsInboxSuggestion | null;
  canConfirm: boolean;
  confirming: boolean;
  onConfirm: () => void;
  onEdit: () => void;
  onDismiss: () => void;
  onRequestClose: () => void;
}) {
  const translateY = useRef(new Animated.Value(SCREEN_HEIGHT)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(translateY, {toValue: 0, duration: motion.smsSheetSlideUpMs, useNativeDriver: true}),
        Animated.timing(backdropOpacity, {
          toValue: motion.smsSheetBackdropOpacity,
          duration: motion.smsSheetSlideUpMs,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      translateY.setValue(SCREEN_HEIGHT);
      backdropOpacity.setValue(0);
    }
  }, [visible, translateY, backdropOpacity]);

  if (!suggestion) return null;

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onRequestClose}>
      <View style={StyleSheet.absoluteFill}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onRequestClose}>
          <Animated.View style={[StyleSheet.absoluteFill, styles.backdrop, {opacity: backdropOpacity}]} />
        </Pressable>
        <Animated.View style={[styles.sheet, {transform: [{translateY}]}]}>
          <View style={styles.handleRow}>
            <View style={styles.handle} />
          </View>
          <View style={styles.header}>
            <MaterialIcons name="sms" style={styles.headerIcon} />
            <Text style={styles.headerLabel}>Detected from SMS</Text>
          </View>
          <Text style={styles.merchant}>{suggestion.parsed_merchant ?? 'a merchant'}</Text>
          <Text style={styles.body}>
            ₹{(suggestion.parsed_amount ?? 0).toFixed(0)} — add as {suggestion.parsed_direction === 'credit' ? 'income' : 'an expense'}?
          </Text>
          <View style={styles.actions}>
            <Pressable
              style={[styles.confirmButton, (!canConfirm || confirming) && {opacity: 0.5}]}
              disabled={!canConfirm || confirming}
              onPress={onConfirm}>
              <Text style={styles.confirmButtonText}>{confirming ? 'Confirming…' : 'Confirm'}</Text>
            </Pressable>
            <Pressable style={styles.editButton} onPress={onEdit}>
              <Text style={styles.editButtonText}>Edit</Text>
            </Pressable>
            <Pressable style={styles.dismissButton} onPress={onDismiss}>
              <Text style={styles.dismissButtonText}>Dismiss</Text>
            </Pressable>
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {backgroundColor: '#000'},
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    borderTopLeftRadius: radius.sheet,
    borderTopRightRadius: radius.sheet,
    backgroundColor: colors.backgroundRaised,
    borderTopWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
  },
  handleRow: {alignItems: 'center', paddingVertical: 10},
  handle: {width: 36, height: 4, borderRadius: 2, backgroundColor: colors.border},
  header: {flexDirection: 'row', alignItems: 'center', gap: spacing.xs, marginTop: spacing.xs},
  headerIcon: {fontSize: 17, color: colors.accentOnDark},
  headerLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.accentOnDark, fontWeight: '600'},
  merchant: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 22, marginTop: spacing.sm},
  body: {color: colors.textSecondary, fontSize: 14, marginTop: 4},
  actions: {flexDirection: 'row', gap: spacing.sm, marginTop: spacing.lg},
  confirmButton: {flex: 1, height: 48, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  confirmButtonText: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  editButton: {height: 48, paddingHorizontal: 18, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center'},
  editButtonText: {color: '#C9C9D2', fontSize: 14, fontWeight: '600'},
  dismissButton: {height: 48, paddingHorizontal: 14, alignItems: 'center', justifyContent: 'center'},
  dismissButtonText: {color: colors.textSecondary, fontSize: 14},
});
