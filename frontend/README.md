# PartVault frontend

Phase 2 provides a Vue 3 / TypeScript / Quasar shell at `/app/`. Items, Collections
and account links currently open the working Django pages. The item browser is
Phase 3; this shell does not claim workflow parity.

## Local setup

Use Node **24.x** and npm (the committed `package-lock.json` is authoritative).
`.nvmrc` selects Node 24. Node is needed for development/builds, not Django runtime.

From the repository root:

```sh
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
cd ..
uv run manage.py runserver
```

Open `http://127.0.0.1:8000/app/`. The compiled shell is served by Django and
Django's development static handler. No frontend dev server is needed in this mode.
A missing/invalid manifest returns an accessible 503 page with legacy navigation;
rebuild the frontend. JavaScript-disabled users also get legacy links.

For hot reload, run Django on `127.0.0.1:8000`, then `npm run dev` in `frontend/`.
Open `http://127.0.0.1:5173/app/`. Vite proxies API and explicit legacy route prefixes
(including auth/media) to Django. Use the same hostname for both servers. In ignored
`config/local_settings.py`, allow the local Vite origin for Django's CSRF check:

```python
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:5173"]
```

Merge this with any existing local trusted origins. If using `localhost`, use
`http://localhost:5173` consistently instead. No CORS is needed. The proxy preserves
Origin/Host; it does not disable Django CSRF protection. Add only your local origin,
not a wildcard or a public dev-server host.

The development-only component preview is `/app/__preview/` on Vite. It contains
local controls, loading/empty/error feedback, validation and a dialog. It performs
no inventory writes and is omitted from compiled builds and product navigation.
All shell sessions still use the real anonymous/session API; no fixtures or automated
validation infrastructure is included.

## Build and Django integration

`npm run build` generates:

- `partvault/static/partvault/frontend/manifest.json` with entry `src/main.ts`.
- Content-hashed JS/CSS/font assets under `partvault/static/partvault/frontend/assets/`.

The generated directory and node_modules are ignored. The build empties only this
dedicated generated directory. Django reads the source manifest from
`FRONTEND_MANIFEST_PATH`, renders stylesheet/script/preload URLs with staticfiles,
and returns private/no-store shell responses. Only `/app/` page paths use the shell;
unknown app paths return the client unavailable view with HTTP 404. Reserved
`/app/api`, `/app/static`, `/app/media`, `/app/admin`, image/document/assets prefixes
and filename paths get a server 404, never a shell. Other API/admin/static/media/QR
routes continue to use their existing handlers. Unsafe shell methods return 405.

The asset base is `/static/partvault/frontend/`; the router base is `/app/`.
There is no SSR or primary-route switch. The app title comes from Django `SITE_TITLE`
through `json_script`; direct Vite development defaults to PartVault. Public legacy
item metadata remains served by its existing Django detail route.

For the existing operator-managed deployment, compile **in the mounted application
tree** before `collectstatic`, then start/restart Django with those files available.
Image-only output under `/app` would be hidden by the application bind mount.
`STATIC_ROOT` defaults to `<repository>/static`, which becomes `/app/static` in the
container and matches the documented nginx `/static/` alias. Effective production
local overrides must agree. Keep the source manifest in the mounted tree: copying
only collected assets is insufficient for the Django shell loader.

The operator installs the locked Python dependencies, applies any applicable
migrations (none added in Phase 2), builds frontend assets, collects static files,
and then starts the updated app. An external build machine/CI may compile into the
same deployable tree; no production Node service is required. Remove nginx's direct
`/media/` alias so Django can authorize media. Verify actual static, media, proxy
and CSRF behavior in production. No production commands were executed here.

## Shared frontend modules

- `api/client.ts`: same-origin `/api/v1/` requests, AbortSignal support, typed errors,
  JSON/multipart bodies and binary API downloads. Unsafe requests require the masked
  bootstrap CSRF token. Reject external URLs and redirects; parse HTTP/proxy errors
  before accepting a body. Cancellation remains an AbortError. There is no retry.
- `api/auth.ts`: local login/signup links with validated `/app/` return paths.
  Login/logout use Django return handling. Legacy signup still returns to its legacy
  destination; preserving signup return context belongs to the account phase.
- `composables/useSession.ts`: shared session, identity, active collection and refresh.
  New reads cancel stale bootstrap calls; only the newest response publishes its CSRF
  token. Refresh on initial mount, visibility/focus and history-cache restoration.
  Failed refresh preserves prior data but hides account mutations and active context.
  `activateCollection` guards duplicate writes and reconciles via bootstrap; it never
  replays an ambiguous activation. Collection selection remains on the legacy page
  until its replacement phase.
- `components/common`: loading, error/retry, empty and form-error primitives.
- `styles`: centralized Sass/Quasar tokens, CSS tokens and stored-status color mapping.

Logout is a native same-origin CSRF-protected POST with a validated return path and
submission guard. A Django CSRF failure displays its existing error page; it is not
silently replayed. API 403 errors distinguish recognized CSRF/authentication messages
from other permission failures; they never automatically redirect away from edits.

## Design and dependencies

The user authorized a new palette and typography on 2026-10-04. The shell uses
mineral neutrals, deep green and IBM Plex Sans / Mono. The interface is dense and
functional: light surfaces, flat grouping, 28px desktop titles, 24px mobile titles,
8px control radii, 12px panel radii, 4/8/12/16/24/32 spacing, and reduced-motion support.
The legal GPL footer and navigation meanings remain. Legacy styling is unchanged.

| Packages | Purpose | License |
| --- | --- | --- |
| Vue, Vue Router | Composition API and history routing | MIT |
| Quasar, its Vite plugin | Shared component system, tree-shaken integration and Sass tokens | MIT |
| Quasar Extras | One MDI v7 SVG icon family; no icon webfont | MIT package; bundled MDI icons Apache-2.0 |
| Fontsource IBM Plex Sans/Mono | Self-hosted Latin fonts; system fallback for other glyphs | MIT packaging; fonts SIL OFL-1.1 |
| Vite, Vue plugin, Sass Embedded | Local build/compiler pipeline | MIT |
| TypeScript, vue-tsc | Strict typed Vue implementation checks | Apache-2.0 / MIT |
| ESLint 10, Vue/TypeScript plugins, globals | Source lint checks | MIT |
| Node type definitions | Typed build configuration | MIT |

IBM Plex's OFL notice is included in `licenses/OFL-IBM-Plex.txt`. No remote fonts,
Bootstrap/React/HTMX additions, store, test runner or browser harness are included.
The dependency versions are pinned by the lockfile; ESLint 10 was selected after
ESLint 9 reported end of support. Installation reported a pending optional native
`@parcel/watcher` build script; it was not approved or run, and the required checks
and build passed without it.

Implementation references: [Quasar Vite plugin](https://quasar.dev/start/vite-plugin/),
[Vite backend integration](https://vite.dev/guide/backend-integration),
[Vue Router history mode](https://router.vuejs.org/guide/essentials/history-mode.html),
[Fontsource installation](https://fontsource.org/docs/getting-started/install).

## Validation handoff

User acceptance remains pending. No automated tests were run. Partial anonymous
manual Chrome DevTools review and screenshots were recorded on 2026-10-04; the
phase record lists findings and unreviewed scenarios. For future rendered checks,
follow [the local browser review workflow](../browser-review.md), including DevTools
discovery, responsive/focus review and screenshot storage under ignored `.artifacts/`.
Use isolated data for session/account scenarios, never live inventory as fixtures.

- [ ] Open the built `/app/` shell and a deep unknown app URL; refresh both. Confirm
  legacy routes and missing API/static/media/admin paths do not return the shell.
- [ ] Check anonymous navigation and login; check signed-in identity, no active
  collection, active context and missing Profile. Check logout and tab/history-cache
  session refresh. A failed refresh must not expose active-context mutation controls.
- [ ] Check keyboard skip link, drawer opening/focus/Escape/Tab loop/focus return,
  account links and logout. Check dialog focus, field labels/errors and retry in the
  development component preview.
- [ ] Review 1440px, 768px and 360px, 200% zoom, long names, touch targets and reduced
  motion. Confirm no overflow, obscured labels or duplicate mobile/desktop navigation.
- [ ] Check session network/server failures, proxy HTML errors, expired sessions and
  CSRF failures. No unsafe write may replay automatically.
- [ ] Confirm generated JS/CSS/fonts are available through the operator's actual
  static host and source manifest path; record production media/proxy checks separately.
