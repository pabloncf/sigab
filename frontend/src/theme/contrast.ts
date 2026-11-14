function luminance(hex: string) {
  const expanded = hex.length === 4 ? hex.slice(1).split("").map((part) => part + part).join("") : hex.slice(1);
  const rgb = [0, 2, 4].map((offset) => {
    const value = parseInt(expanded.slice(offset, offset + 2), 16) / 255;
    return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
  });
  return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
}

/** Pick the higher-contrast foreground for an installation's primary button. */
export function readableForeground(background: string) {
  return luminance(background) > .179 ? "#000000" : "#ffffff";
}
