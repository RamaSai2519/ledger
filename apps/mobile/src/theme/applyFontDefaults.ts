import {Text, TextInput} from 'react-native';
import {fontFamilies} from '@/theme/tokens';

// Instrument Sans is the spec's body/meta/label face (spec1 "Type") but is
// never referenced explicitly per-screen — screens only ever opt into the
// display (Space Grotesk) or monetary (IBM Plex Mono) faces on top of
// whatever the default is. Rather than touching every body Text style in
// every screen, this sets it once as the default for every <Text>/
// <TextInput> in the tree; a screen's own `fontFamily` in its style array
// still wins since RN merges defaultProps.style before the component's own
// style prop.
export function applyFontDefaults() {
  const TextAny = Text as unknown as {defaultProps?: {style?: unknown}};
  TextAny.defaultProps = TextAny.defaultProps || {};
  TextAny.defaultProps.style = [{fontFamily: fontFamilies.body}, TextAny.defaultProps.style];

  const TextInputAny = TextInput as unknown as {defaultProps?: {style?: unknown}};
  TextInputAny.defaultProps = TextInputAny.defaultProps || {};
  TextInputAny.defaultProps.style = [{fontFamily: fontFamilies.body}, TextInputAny.defaultProps.style];
}
