# Official SHIFT logo integration

The supplied `Futuristic Gold SHIFT Wordmark (1).png` is the source of truth.
Its original bytes are preserved in `frontend/public/branding/shift-reference.png`.
The source is opaque, so the production SVGs trace its five letter silhouettes
and provide transparency without the black rectangular backdrop. Letter geometry,
spacing and proportions are preserved; no replacement typeface or icon was used.
The original-resolution binary silhouette overlap is 99.46% (details/checksum in
`shift-logo.manifest.json`). Empty background margins become consistent clear space;
no lettering is clipped. Flat colors replace the source's gold texture to match
existing semantic tokens. Each production SVG is approximately 3.3 KB.

Gold (`--gold`, #d8a45f) is used on existing dark surfaces. Forest green
(`--primary-active`, #1d492a) is available via `surface="light"` for light surfaces.
Measured contrast: gold/background 8.14:1, gold/sidebar 7.10:1,
forest/ivory 9.09:1 and forest/white 10.30:1.

The shared ShiftLogo component supplies login, sidebar/navigation and footer
placements. Dimensions, object-fit and centralized size tokens preserve aspect
ratio and reserve space while loading. Existing mobile navigation contains the
same component. There is no separate light application theme; explicit surface
selection makes the appropriate variant available without changing theme behavior.

## Files changed for this request

- `frontend/src/components/shift-logo.tsx`: official asset and variant selection.
- `frontend/src/components/app-shell.tsx`: shared logo in existing footer.
- `frontend/src/app/globals.css`: centralized logo sizing and placement styles.
- `frontend/next.config.ts`: remove obsolete optional-asset/fallback flag.
- `frontend/public/branding/shift-reference.png`: original reference, unchanged.
- `frontend/public/branding/shift-logo.svg`: transparent gold wordmark.
- `frontend/public/branding/shift-logo-light.svg`: transparent forest wordmark.
- `frontend/public/branding/shift-logo.manifest.json`: dimensions and provenance.
- `frontend/public/branding/README.md`: asset and regeneration instructions.
- `frontend/scripts/prepare-shift-logo.mjs`: deterministic source contour conversion.
- `README.md`: replace obsolete missing-logo documentation.
- `docs/LOGO_IMPLEMENTATION_REPORT.md`: this report.

Earlier uncommitted feature changes were retained. This request changed no backend,
authentication, AMD/Gemma, voice capture, RAG or approval behavior.

## Validation

- Frontend ESLint, TypeScript and normal production build passed.
- All 29 existing browser workflow tests passed using the isolated test backend
  and mocked AI/speech providers; no live inference or API credits were used.
- Three additional temporary branding checks passed: real asset loading across all
  seven main routes, login widths 320/390/768/1440 and application widths
  390/768/1440; no horizontal overflow or broken branding requests; dark/light
  variant rendering; logo loading preserves its reserved geometry; mobile image
  proportions and sidebar containment.
- Screenshots inspected: desktop dashboard, login, variant comparison and mobile
  navigation. The mobile sidebar animates into view; final containment is checked
  after its transition completes.
- Existing workflow tests also cover all-view automated accessibility, mobile
  navigation, technician capture, supervisor review and permission behavior.
- Temporary test configurations were removed. The final mobile screenshot is retained locally at
  `frontend/test-results/logo-mobile.png`; other review screenshots were temporary.

To review: open login, sign in and visit Overview, Machines, a machine detail,
Knowledge Library, Capture Knowledge, Approvals and Troubleshoot. On a phone,
open navigation to see the compact wordmark. Both color variants are available in `frontend/public/branding/`.
