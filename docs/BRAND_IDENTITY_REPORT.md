# SHIFT brand identity implementation

Implemented 17 October 2026. Frontend presentation only.

## Theme and coverage

`frontend/src/app/globals.css` now centralizes the official charcoal (#101713),
forest surfaces (#19251D / #233228), primary green (#2E6F40), hover (#255A34),
active (#1D492A), sage (#9DD7A9), gold (#D8A45F), ivory (#F2F1E9), muted sage
(#B6C6B8), border (#314137), and disabled surface (#344239). Tailwind v4 semantic
aliases use the same variables. All legacy blue/navy component colors were
replaced with semantic variables, including the code-native machine illustration.
The favicon keeps its existing geometry with the updated palette.

Primary buttons use the exact green interaction colors; small links and focus
rings use lighter sage. Inputs have a separate higher-contrast control border.
Success, amber warning, red rejection/error, and warm neutral informational
statuses remain distinguishable with text labels. Decorative background gradients,
blue glow, and mobile navigation glow were removed. Existing layout breakpoints,
navigation, forms, loading states and workflow structure remain intact.

Coverage: login/authentication, dashboard, machine directory and detail, approved
knowledge library and reader, capture (written/voice/documents), technician
submission history, supervisor review/approval/rejection/revocation, troubleshooting,
shared shell/navigation, error/loading/empty states, status messages and controls.
The official tagline appears in the login and footer; metadata uses the full
product name.

## Logo status

**Missing:** `frontend/public/branding/shift-logo.png`.

`ShiftLogo` provides full and compact variants, accessible image alternative text,
and one centralized image path. The existing plain SHIFT text remains as the
fallback in brand gold. It is not a substitute geometric wordmark. `ShiftBrand`
wraps the compact variant for compatibility; login uses the full variant.

The Next.js configuration detects asset availability at startup/build time,
avoiding broken image requests while it is absent. Supply the official PNG and
restart/rebuild. Natural image proportions are preserved with automatic height;
there is no cropping, filter or recoloring. Inspect the supplied asset for an
artificial checkerboard before integration; transparency and original artwork
cannot be verified until the missing file is supplied.

## Files created

- `frontend/src/components/shift-logo.tsx`
- `frontend/public/branding/README.md`
- `docs/BRAND_IDENTITY_REPORT.md`

## Files modified

- `frontend/src/app/globals.css`
- `frontend/src/app/icon.svg`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/components/app-shell.tsx`
- `frontend/src/components/knowledge-provider.tsx`
- `frontend/src/components/machine-illustration.tsx`
- `frontend/src/components/shift-brand.tsx`
- `frontend/src/components/troubleshooting.tsx`
- `frontend/src/components/ui.tsx`
- `frontend/next.config.ts`
- `README.md`

## Verification

- ESLint, TypeScript validation and Next.js production build passed.
- All 15 existing Playwright workflow tests passed against a production build.
- One temporary additional browser check captured desktop dashboard, capture,
  login and supervisor review screenshots and checked login/supervisor accessibility.
  Total: **16 passed**.
- Existing tests checked axe WCAG A/AA rules across all seven application routes,
  horizontal overflow at 390px and 768px, mobile navigation/focus trapping,
  authenticated capture with attachments, approval/persistence, rejection reasons,
  source withdrawal, audio capture and denial, failed saves, backend recovery,
  retrieval, outcome submission and inference errors.
- Desktop and mobile screenshots were actually inspected. Images are local ignored
  artifacts under `frontend/test-results/brand-*.png` and `shift-mobile.png`.
- Default test startup found ports 3000/8000 already occupied. The successful run
  used temporary copies of the existing suite/config on ports 3001/8001 and a
  temporary database. Existing local servers/data were not stopped or changed.
  Temporary config/test copies were removed after validation; the production
  build was restored to its default API configuration.
- No automated accessibility violations were detected in tested states. Automated
  checks do not establish conformance for every possible state or assistive device.
  The absent official logo remains unverified for transparency and visual fit.

No backend, authentication behavior, API contracts, data models, RAG/inference,
roles, approval rules, field names, validation, submission behavior or demo data
were changed. Changes in the provider and troubleshooting components are confined
to brand presentation, badge styling and formatting.
