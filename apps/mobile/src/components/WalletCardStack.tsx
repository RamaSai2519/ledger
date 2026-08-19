import React, {useEffect, useRef, useState} from 'react';
import {Animated, PanResponder, StyleSheet, Text, View} from 'react-native';
import type {Wallet} from '@/api/client';
import {colors, fontFamilies, motion, radius} from '@/theme/tokens';

const LIABILITY_TYPES = new Set<Wallet['type']>(['credit_card', 'pay_later', 'loan']);

const MAX_VISIBLE = 3;
const CARD_HEIGHT = 108;
const LAYER_OFFSET = 12; // vertical step between stacked layers
const LAYER_SCALE_STEP = 0.045;
const SWIPE_DISTANCE_THRESHOLD = 60;
const SWIPE_VELOCITY_THRESHOLD = 0.5;
const OFFSCREEN_Y = -260;

function WalletFace({wallet}: {wallet: Wallet}) {
  const isLiability = LIABILITY_TYPES.has(wallet.type);
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardName} numberOfLines={1}>
          {wallet.name}
        </Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{isLiability ? 'Owe' : 'Have'}</Text>
        </View>
      </View>
      {!!wallet.account_last4 && <Text style={styles.cardDigits}>•••• •••• {wallet.account_last4}</Text>}
      <View style={styles.cardFooter}>
        <View>
          <Text style={styles.cardLabel}>{isLiability ? 'Outstanding' : 'Balance'}</Text>
          <Text style={styles.cardAmount}>₹{Math.abs(wallet.current_balance).toLocaleString('en-IN')}</Text>
        </View>
        {isLiability && wallet.credit_card_details?.credit_limit != null && (
          <View style={{alignItems: 'flex-end'}}>
            <Text style={styles.cardLabel}>Limit left</Text>
            <Text style={[styles.cardAmount, {fontSize: 12, color: '#DFFCEB'}]}>
              ₹{Math.max(0, wallet.credit_card_details.credit_limit - wallet.current_balance).toLocaleString('en-IN')}
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

// Swipeable stack of every wallet — the front card can be dragged/swiped
// up, at which point it animates off-screen and cycles to the back of the
// stack, bringing the next wallet to the front. Up to MAX_VISIBLE cards are
// rendered at once (peeking behind the front card) so it always reads as a
// stack even with just 2 wallets.
export function WalletCardStack({wallets}: {wallets: Wallet[]}) {
  const [order, setOrder] = useState<number[]>(() => wallets.map((_, i) => i));
  const translate = useRef(new Animated.ValueXY({x: 0, y: 0})).current;

  useEffect(() => {
    setOrder((prev) => (prev.length === wallets.length ? prev : wallets.map((_, i) => i)));
  }, [wallets.length]);

  const cycleToBack = () => {
    Animated.timing(translate, {
      toValue: {x: 0, y: OFFSCREEN_Y},
      duration: motion.walletCardRestackMs,
      useNativeDriver: true,
    }).start(() => {
      translate.setValue({x: 0, y: 0});
      setOrder((prev) => [...prev.slice(1), prev[0]]);
    });
  };

  const resetPosition = () => {
    Animated.spring(translate, {toValue: {x: 0, y: 0}, useNativeDriver: true, friction: 7}).start();
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponderCapture: (_, gesture) => Math.abs(gesture.dy) > 6 && Math.abs(gesture.dy) > Math.abs(gesture.dx),
      onPanResponderMove: (_, gesture) => {
        // Only let the drag travel upward — this is a swipe-to-cycle
        // gesture, not a free-drag card.
        translate.setValue({x: gesture.dx * 0.3, y: Math.min(0, gesture.dy)});
      },
      onPanResponderRelease: (_, gesture) => {
        if (gesture.dy < -SWIPE_DISTANCE_THRESHOLD || gesture.vy < -SWIPE_VELOCITY_THRESHOLD) {
          cycleToBack();
        } else {
          resetPosition();
        }
      },
      onPanResponderTerminate: resetPosition,
    }),
  ).current;

  if (wallets.length === 0) return null;

  const visible = order.slice(0, MAX_VISIBLE);

  return (
    <View style={styles.stackWrap}>
      {visible
        .map((walletIndex, depth) => ({walletIndex, depth}))
        .reverse()
        .map(({walletIndex, depth}) => {
          const wallet = wallets[walletIndex];
          const isFront = depth === 0;
          const layerStyle = {
            top: depth * LAYER_OFFSET,
            zIndex: MAX_VISIBLE - depth,
            opacity: 1 - depth * 0.18,
            transform: [{scale: 1 - depth * LAYER_SCALE_STEP}],
          };

          if (!isFront) {
            return (
              <View key={wallet.id} style={[styles.cardLayer, layerStyle]}>
                <WalletFace wallet={wallet} />
              </View>
            );
          }

          return (
            <Animated.View
              key={wallet.id}
              style={[
                styles.cardLayer,
                layerStyle,
                {transform: [...layerStyle.transform, {translateX: translate.x}, {translateY: translate.y}]},
              ]}
              {...panResponder.panHandlers}>
              <WalletFace wallet={wallet} />
            </Animated.View>
          );
        })}
    </View>
  );
}

const styles = StyleSheet.create({
  stackWrap: {height: CARD_HEIGHT + (MAX_VISIBLE - 1) * LAYER_OFFSET + 14, marginTop: 14, marginHorizontal: 20},
  cardLayer: {position: 'absolute', left: 0, right: 0},
  card: {padding: 16, borderRadius: radius.card, backgroundColor: colors.accent, minHeight: CARD_HEIGHT},
  cardHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  cardName: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600', flexShrink: 1, marginRight: 8},
  badge: {paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,.16)'},
  badgeText: {color: colors.textPrimary, fontSize: 10},
  cardDigits: {color: 'rgba(255,255,255,.72)', fontFamily: fontFamilies.monetary, fontSize: 13, letterSpacing: 2.5, marginTop: 14},
  cardFooter: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: 9},
  cardLabel: {color: 'rgba(255,255,255,.62)', fontSize: 10},
  cardAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 18, fontWeight: '500'},
});
