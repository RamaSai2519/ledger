import React from 'react';
import type {LayoutChangeEvent, StyleProp, ViewStyle} from 'react-native';
import {StyleSheet, View} from 'react-native';
import Svg, {Defs, LinearGradient, Rect, Stop} from 'react-native-svg';
import {heroGradient, heroGradientAngle} from '@/theme/tokens';

// CSS's `linear-gradient(145deg, ...)` measures its angle clockwise from
// the top (0deg = pointing up) and keeps that angle regardless of the
// box's aspect ratio. SVG's default gradientUnits ("objectBoundingBox")
// instead normalizes the vector into a 0..1 box and stretches each axis
// independently by the element's own width/height — on a wide, short box
// like these cards (~3:1) that distorts a 145° diagonal into a much
// steeper transition, which reads as a hard seam rather than a smooth
// gradient. Computing the vector in real pixel space (gradientUnits=
// "userSpaceOnUse", sized via onLayout) preserves the true angle instead.
function angleToVector(angleDeg: number, width: number, height: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  const dx = Math.cos(rad);
  const dy = Math.sin(rad);
  // Half-length of the gradient line so it spans corner-to-corner of the
  // box along this angle, same formula CSS uses for `linear-gradient`.
  const half = (Math.abs(dx) * width + Math.abs(dy) * height) / 2;
  const cx = width / 2;
  const cy = height / 2;
  return {x1: cx - dx * half, y1: cy - dy * half, x2: cx + dx * half, y2: cy + dy * half};
}

// Hero/card gradient fill (spec1: "hero / card gradient 145°") — used
// behind hero numbers, wallet-stack cards, and the SMS suggestion sheet.
// react-native-svg is already a dependency (charts), so this reuses its
// <LinearGradient> instead of adding react-native-linear-gradient.
export function GradientCard({
  style,
  radius = 0,
  children,
}: {
  style?: StyleProp<ViewStyle>;
  radius?: number;
  children?: React.ReactNode;
}) {
  const [size, setSize] = React.useState({width: 0, height: 0});
  const onLayout = (e: LayoutChangeEvent) => {
    const {width, height} = e.nativeEvent.layout;
    setSize((prev) => (prev.width === width && prev.height === height ? prev : {width, height}));
  };
  const vector = angleToVector(heroGradientAngle, size.width, size.height);
  return (
    <View style={[styles.wrap, {borderRadius: radius}, style]} onLayout={onLayout}>
      {size.width > 0 && size.height > 0 && (
        <Svg style={StyleSheet.absoluteFill} width={size.width} height={size.height}>
          <Defs>
            <LinearGradient id="grad" gradientUnits="userSpaceOnUse" x1={vector.x1} y1={vector.y1} x2={vector.x2} y2={vector.y2}>
              <Stop offset="0" stopColor={heroGradient[0]} stopOpacity={1} />
              <Stop offset="1" stopColor={heroGradient[1]} stopOpacity={1} />
            </LinearGradient>
          </Defs>
          <Rect x={0} y={0} width={size.width} height={size.height} fill="url(#grad)" />
        </Svg>
      )}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {overflow: 'hidden'},
});
