import React from 'react';
import type {StyleProp, ViewStyle} from 'react-native';
import {StyleSheet, View} from 'react-native';
import Svg, {Defs, LinearGradient, Rect, Stop} from 'react-native-svg';
import {heroGradient, heroGradientAngle} from '@/theme/tokens';

// CSS's `linear-gradient(145deg, ...)` measures its angle clockwise from
// the top (0deg = pointing up), while SVG gradients are plotted as a
// literal (x1,y1)-(x2,y2) vector across a 0..1 box — this converts one to
// the other so `heroGradientAngle` (145, from the design spec) reproduces
// the same visual direction here.
function angleToVector(angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  const dx = Math.cos(rad) / 2;
  const dy = Math.sin(rad) / 2;
  return {x1: 0.5 - dx, y1: 0.5 - dy, x2: 0.5 + dx, y2: 0.5 + dy};
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
  const vector = angleToVector(heroGradientAngle);
  return (
    <View style={[styles.wrap, {borderRadius: radius}, style]}>
      <Svg style={StyleSheet.absoluteFill} width="100%" height="100%">
        <Defs>
          <LinearGradient id="grad" x1={vector.x1} y1={vector.y1} x2={vector.x2} y2={vector.y2}>
            <Stop offset="0" stopColor={heroGradient[0]} stopOpacity={1} />
            <Stop offset="1" stopColor={heroGradient[1]} stopOpacity={1} />
          </LinearGradient>
        </Defs>
        <Rect x={0} y={0} width="100%" height="100%" fill="url(#grad)" />
      </Svg>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {overflow: 'hidden'},
});
