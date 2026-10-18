# Official SHIFT wordmark

Source of truth: the supplied `Futuristic Gold SHIFT Wordmark (1).png`, preserved
byte-for-byte as `shift-reference.png`. It is an opaque 2098 × 749 PNG, not a
transparent image. No checkerboard was present.

Production assets:

- `shift-logo.svg`: transparent champagne gold, from the `--gold` theme token.
- `shift-logo-light.svg`: identical lettering in forest green, from `--primary-active`,
  for light/ivory backgrounds.
- `shift-logo.manifest.json`: intrinsic dimensions, asset paths, source checksum
  and conversion evidence.

The five original letter silhouettes were traced directly from the reference's
pixel edges. No generated/retyped/rearranged lettering, generic icon, stretching,
letter cropping, shadow or glow was added. The new vector canvas includes 16 source
pixels of clear space around all lettering; the original reference/canvas is retained
unchanged. The dark backdrop and its empty margins are not part of the transparent
wordmark. Color is intentionally flat to match SHIFT's semantic palette.

`src/components/shift-logo.tsx` is the only production asset entry point. It supports
`full`, `compact` and `footer` sizes, plus `surface="dark"` (default) and
`surface="light"`. The surface prop describes the actual background; OS theme does
not override the application's dark theme. Intrinsic dimensions and reserved
placement heights prevent logo-loading shifts.

Reproduce the conversion with the existing Next.js sharp dependency, from frontend/:

```sh
node scripts/prepare-shift-logo.mjs public/branding/shift-reference.png
```

The generator reads colors from centralized CSS tokens and refuses to publish if
five closed source contours or the source/vector silhouette comparison fail.
The recorded original-resolution silhouette overlap is approximately 99.46%.
Both variants share exactly the same geometry; only the palette fill differs.
