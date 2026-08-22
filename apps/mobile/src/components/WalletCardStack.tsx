import React, {useEffect, useRef, useState} from 'react';
import {Animated, StyleSheet, Text, View} from 'react-native';
import {PanGestureHandler, State, type PanGestureHandlerGestureEvent} from 'react-native-gesture-handler';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type {Wallet} from '@/api/client';
import {colors, fontFamilies, motion, radius} from '@/theme/tokens';
import {GradientCard} from '@/components/GradientCard';

const LIABILITY_TYPES = new Set<Wallet['type']>(['credit_card', 'pay_later']);

// Not a secret — just a UI preference, so plain AsyncStorage is fine here.
const FRONT_WALLET_KEY = 'wallet_card_stack_front_id';

const MAX_VISIBLE = 3;
const CARD_HEIGHT = 108;
const LAYER_OFFSET = 12; // vertical step between stacked layers
const LAYER_SCALE_STEP = 0.045;
const LAYER_OPACITY_STEP = 0.18;
const SWIPE_DISTANCE_THRESHOLD = 60;
const SWIPE_VELOCITY_THRESHOLD = 0.5;

function layerStyleForDepth(depth: number) {
  return {
    translateY: depth * LAYER_OFFSET,
    opacity: Math.max(0, 1 - depth * LAYER_OPACITY_STEP),
    scale: 1 - depth * LAYER_SCALE_STEP,
  };
}

function WalletFace({wallet, isFront}: {wallet: Wallet; isFront: boolean}) {
  const isLiability = LIABILITY_TYPES.has(wallet.type);
  const Container = isFront ? GradientCard : View;
  const containerProps = isFront ? {radius: radius.card} : {};
  return (
    <Container style={styles.card} {...containerProps}>
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
    </Container>
  );
}

// Swipeable stack of every wallet — the front card can be dragged/swiped
// up, at which point it settles behind the stack while the other layers
// step forward, cycling it to the back. Up to MAX_VISIBLE cards are
// rendered at once (peeking behind the front card) so it always reads as a
// stack even with just 2 wallets.
export function WalletCardStack({wallets}: {wallets: Wallet[]}) {
  const [order, setOrder] = useState<number[]>(() => wallets.map((_, i) => i));
  const [cycling, setCycling] = useState(false);
  // `drag` follows the finger for the live swipe gesture on the front card;
  // `restack` is the 0→1 progress of the settle animation once a swipe is
  // released past threshold, driving every visible layer's transition to
  // its new depth (front card tucking behind, others stepping forward) at
  // once instead of the old fly-off-then-instant-reorder jump cut.
  const drag = useRef(new Animated.ValueXY({x: 0, y: 0})).current;
  const restack = useRef(new Animated.Value(0)).current;

  // PanResponder.create() only runs once (useRef's initializer is only
  // evaluated on mount), so any closure inside it over `wallets` would be
  // permanently stuck on whatever `wallets` was on the very first render —
  // typically `[]`, before the wallets query resolves. Route through this
  // ref (reassigned every render, synchronously) instead so the gesture
  // handlers always see the current wallet list.
  const walletsRef = useRef(wallets);
  walletsRef.current = wallets;

  useEffect(() => {
    setOrder((prev) => (prev.length === wallets.length ? prev : wallets.map((_, i) => i)));
  }, [wallets.length]);

  // Restore whichever wallet the user last left on top, once, the first
  // time wallets are available — matched by id (not index) since the
  // wallet list's order can shift between sessions. Later swipes update
  // the stored id directly in cycleToBack rather than re-running this.
  const restoredRef = useRef(false);
  useEffect(() => {
    if (restoredRef.current || wallets.length === 0) return;
    restoredRef.current = true;
    AsyncStorage.getItem(FRONT_WALLET_KEY)
      .then((id) => {
        if (!id) return;
        const walletIndex = wallets.findIndex((w) => w.id === id);
        if (walletIndex < 0) return;
        setOrder((prev) => {
          const pos = prev.indexOf(walletIndex);
          if (pos <= 0) return prev;
          return [...prev.slice(pos), ...prev.slice(0, pos)];
        });
      })
      .catch(() => {});
  }, [wallets]);

  const visibleCount = Math.min(MAX_VISIBLE, wallets.length);

  const cycleToBack = () => {
    setCycling(true);
    Animated.parallel([
      Animated.timing(restack, {toValue: 1, duration: motion.walletCardRestackMs, useNativeDriver: true}),
      Animated.timing(drag, {toValue: {x: 0, y: 0}, duration: motion.walletCardRestackMs, useNativeDriver: true}),
    ]).start(() => {
      restack.setValue(0);
      drag.setValue({x: 0, y: 0});
      setOrder((prev) => {
        const next = [...prev.slice(1), prev[0]];
        const newFront = walletsRef.current[next[0]];
        if (newFront) AsyncStorage.setItem(FRONT_WALLET_KEY, newFront.id).catch(() => {});
        return next;
      });
      setCycling(false);
    });
  };

  const resetPosition = () => {
    Animated.spring(drag, {toValue: {x: 0, y: 0}, useNativeDriver: true, friction: 7}).start();
  };

  // Plain core PanResponder can't coordinate with the page's ScrollView —
  // once the page has enough content to actually scroll, the native scroll
  // responder claims the vertical touch stream before the JS-thread
  // PanResponder ever sees it, so the swipe stopped firing. PanGestureHandler
  // (from react-native-gesture-handler, which HomeScreen's ScrollView is
  // also built on) recognizes gestures on the native side, so a tightly
  // scoped nested handler like this one reliably wins the touch over its
  // ancestor ScrollView.
  const onGestureEvent = (event: PanGestureHandlerGestureEvent) => {
    const {translationX, translationY} = event.nativeEvent;
    // Only let the drag travel upward — this is a swipe-to-cycle gesture,
    // not a free-drag card.
    drag.setValue({x: translationX * 0.3, y: Math.min(0, translationY)});
  };

  const onHandlerStateChange = (event: PanGestureHandlerGestureEvent) => {
    const {state, translationY, velocityY} = event.nativeEvent;
    if (state !== State.END && state !== State.CANCELLED && state !== State.FAILED) return;
    const crossedThreshold = translationY < -SWIPE_DISTANCE_THRESHOLD || velocityY < -SWIPE_VELOCITY_THRESHOLD * 1000;
    if (state === State.END && walletsRef.current.length > 1 && crossedThreshold) {
      cycleToBack();
    } else {
      resetPosition();
    }
  };

  if (wallets.length === 0) return null;

  // While idle this is just the visible slice. While cycling, also include
  // the card waiting behind the stack (if any) so it can animate into the
  // back visible layer instead of popping in once the rotation commits.
  const enteringIndex = cycling && visibleCount < order.length ? order[visibleCount] : null;
  const slots = order
    .slice(0, visibleCount)
    .map((walletIndex, depth) => ({walletIndex, depth}))
    .concat(enteringIndex !== null ? [{walletIndex: enteringIndex, depth: visibleCount}] : []);

  return (
    <View style={styles.stackWrap}>
      {slots
        .slice()
        .reverse()
        .map(({walletIndex, depth}) => {
          const wallet = wallets[walletIndex];
          const isFront = depth === 0;
          const isEntering = depth === visibleCount;
          const from = isEntering ? {...layerStyleForDepth(depth), opacity: 0} : layerStyleForDepth(depth);
          const to = layerStyleForDepth(isFront ? visibleCount : depth - 1);
          const targetOpacity = isFront ? 0 : to.opacity;

          const translateY = restack.interpolate({inputRange: [0, 1], outputRange: [from.translateY, to.translateY]});
          const opacity = restack.interpolate({inputRange: [0, 1], outputRange: [from.opacity, targetOpacity]});
          const scale = restack.interpolate({inputRange: [0, 1], outputRange: [from.scale, to.scale]});

          const layer = (
            <Animated.View
              key={wallet.id}
              style={[
                styles.cardLayer,
                {
                  opacity,
                  // The outgoing front card drops behind every other layer
                  // the instant the settle animation starts, so it reads as
                  // tucking behind the stack rather than sliding over it.
                  zIndex: isFront ? (cycling ? 0 : MAX_VISIBLE + 1) : MAX_VISIBLE - depth,
                  transform: [{translateY}, {scale}, ...(isFront ? [{translateX: drag.x}, {translateY: drag.y}] : [])],
                },
              ]}>
              <WalletFace wallet={wallet} isFront={isFront} />
            </Animated.View>
          );

          if (!isFront || cycling) return layer;

          return (
            <PanGestureHandler
              key={wallet.id}
              activeOffsetY={[-8, 8]}
              failOffsetX={[-15, 15]}
              onGestureEvent={onGestureEvent}
              onHandlerStateChange={onHandlerStateChange}>
              {layer}
            </PanGestureHandler>
          );
        })}
    </View>
  );
}

const styles = StyleSheet.create({
  stackWrap: {height: CARD_HEIGHT + (MAX_VISIBLE - 1) * LAYER_OFFSET + 14, marginTop: 14, marginHorizontal: 20},
  cardLayer: {position: 'absolute', top: 0, left: 0, right: 0},
  card: {padding: 16, borderRadius: radius.card, backgroundColor: colors.accent, minHeight: CARD_HEIGHT},
  cardHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  cardName: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600', flexShrink: 1, marginRight: 8},
  badge: {paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,.16)'},
  badgeText: {color: colors.textPrimary, fontSize: 10},
  cardDigits: {color: 'rgba(255,255,255,.72)', fontFamily: fontFamilies.monetary, fontSize: 13, letterSpacing: 2.5, marginTop: 14},
  cardFooter: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: 9},
  cardLabel: {color: 'rgba(255,255,255,.62)', fontSize: 10},
  cardAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetaryMedium, fontSize: 18},
});
