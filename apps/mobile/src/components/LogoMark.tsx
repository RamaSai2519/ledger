import React from 'react';
import Svg, {Circle} from 'react-native-svg';
import {colors, partnerAccents} from '@/theme/tokens';

// The Ledger logo mark — two overlapping circles, one per household
// partner's dual-identity accent hue, meeting in a shared middle (design
// project "Logo design iteration", option 1a). Vector source of truth is
// assets/brand/logo-mark.svg; keep this in sync if that file changes.
export function LogoMark({size = 84, mono = false}: {size?: number; mono?: boolean}) {
  const [primary, secondary] = mono
    ? [colors.background, colors.background]
    : [partnerAccents[0], partnerAccents[1]];
  const secondaryOpacity = mono ? 0.6 : 0.85;
  const primaryOpacity = mono ? 0.85 : 1;

  return (
    <Svg width={size} height={size} viewBox="0 0 84 84">
      <Circle cx={30} cy={40} r={30} fill={primary} fillOpacity={primaryOpacity} />
      <Circle cx={54} cy={40} r={30} fill={secondary} fillOpacity={secondaryOpacity} />
    </Svg>
  );
}
