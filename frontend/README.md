# PartVault frontend

Phases 2–6 provide a Vue 3 / TypeScript / Quasar shell at `/app/` and item browser
at `/app/items/` and `/app/items/{collection_id}/`. Read-only item detail is at `/app/item/{item_id}/`. Metadata create/edit lives at `/app/items/new/` and `/app/item/{item_id}/edit/`. Collections, account and
attachment-management links open the working Django pages. User acceptance and
legacy/API parity remain pending.

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

## Phase 3 item browser

Open `http://127.0.0.1:8000/app/items/` after the local build/server steps above.
The local SQLite database contains user-confirmed test data; the manual browser
account is documented in the local `AGENTS.md`. No automated tests or harness
were added or run.

- Desktop uses server-backed QTable; below 1024px a thumbnail-led list replaces
  the table. Both share the same filters, sort, page and page-size state.
- URL keys: `search` (legacy `q` is accepted), `collection`, `category`,
  `manufacturer`, repeated `tag` (AND), `ordering`, `page`, `page_size`.
  Defaults: `-updated_at`, page 1, 50 items; page size supports 1–100.
  `/app/items/{collection_id}/` takes precedence over query `collection`.
  Empty optional values use defaults; invalid IDs/repeated singletons/sorts show
  an error instead of issuing a broader item read. Unrelated query keys are not
  forwarded to the API. Editing search writes `search` and removes legacy `q`.
- Search debounces 300ms and Enter submits immediately. Each settled edit pushes
  history; Back/Forward restores URL state. Filter, sort and page-size changes
  reset page 1. Other controls commit any pending search draft before navigation.
  Superseded item/context/facet reads are cancelled and generation-guarded.
  Query-only navigation preserves keyboard focus; page navigation focuses title.
- Collection choices use paginated `collections/` and include empty collections.
  Category/manufacturer/tag selectors use paginated visible-record facets, omit
  their own filter to offer alternatives, support text search and Load more.
  No editor catalog or whole-inventory fetch is used. Selected labels come from
  returned items/choices or collection detail; unmatched bookmarked IDs display
  explicit `Category #id` / `Tags (match all) #id` fallback labels.
- Columns are configurable locally in `partvault.items.columns.v1` storage;
  Name is required. Storage failure falls back to defaults. No identity,
  credentials or authoritative inventory is kept in that preference.
- Browsing a collection does not activate it. Make active collection is an
  explicit owner-only CSRF-protected POST using the existing guarded helper.
  Phase 6 opens New/Edit in the SPA; an owned collection context is explicitly preselected in New, without activation. Detail/New/Edit retain browser return context.
- Empty inventory, no matches, stable loading, retryable API/session errors and
  unavailable pages have distinct feedback. No automatic unsafe retry is added.

### Phase 3 user-validation checklist

All results are pending. Use disposable/test data and record dated role/context
and outcomes in [the Phase 3 record](../ui-migrate-phase-3.md#completion-record).

- [ ] Anonymous/public, owner/private and another-user reads match legacy/API
  visibility, counts and labels; empty collections are discoverable.
- [ ] More than one page: search across all documented fields, combine category,
  manufacturer and two tags, compare tag AND results, sort each allowed field
  both ways, change page size and reach final/first pages. No client-side global
  sorting or complete inventory download occurs.
- [ ] Type/filter quickly and navigate Back/Forward, bookmark/refresh direct
  collection and query URLs, use legacy `q`, clear filters and change sort/page
  with a pending search draft. The latest query wins, with no stale results.
- [ ] Invalid/nonexistent/private collection, invalid IDs/sort, out-of-range page,
  failed item/facet/session requests and retry provide usable recovery.
- [ ] Collection activation: only own context can activate; valid/missing CSRF,
  missing profile, double click and ambiguous network response behave as the
  shared contract specifies. New item uses the displayed active context.
- [ ] Configure columns, restore defaults, reload, block local storage; item and
  collection links retain native new-tab/keyboard behavior and legacy editing.
- [ ] Desktop 1440px, tablet 768px, mobile 360px, 200% zoom, reduced motion,
  keyboard traversal, selector pagination/search, column dialog containment,
  long names/many tags/missing photos and large counts remain usable.

Implementation uses the official [QTable server-pagination guidance](https://quasar.dev/vue-components/table/#server-side-pagination-filter-and-sorting)
and [QSelect async/filter guidance](https://quasar.dev/vue-components/select/).
Local rendered review is partial evidence, separate from this checklist.

## Phase 4 item detail

`/app/item/{item_id}/` displays all metadata, dates, notes and tags; photos,
links, authorized documents and parent/child/grandchild navigation. Native router
links from the browser carry a validated `return=/app/items/...` URL (including
filters/sort/page). Only same-origin item-browser paths are accepted; otherwise
Back to items falls back to the item's collection, or all items if unavailable.
Containment links preserve the same return context; normal new-tab behavior works.

Initial children/photos/documents/links are the API's ten-row envelopes. Each
resource's Load more follows its own `next` URL and preserves `page_size=10`.
Grandchildren load only when a child's Show contents is opened, from that child's
`children/?page_size=10`. There is no eager recursive tree fetch. Concurrent
resource reads have independent loading/error/retry and cancellation guards;
route/session refresh disposes old content and pending reads.

Primary-first photo order is unchanged. Select a thumbnail to display that photo
above; Open full image uses the authorized image route in a new tab. Missing
photos/files have explicit fallbacks. Documents use authorized `/document/{id}/`:
ordinary clicks fetch a Blob for download with inline HTTP/network errors, duplicate
click prevention, cancellation and object-URL cleanup. Modified/new-tab clicks
retain native delivery behavior. Saved external links allow HTTP/HTTPS with
`noopener noreferrer`; invalid/unsafe URLs remain visible as text. Labels/notes
are escaped text, never HTML.

Phase 6 supersedes the legacy Edit/New destinations: owners use SPA metadata editing and explicit owned collection context. Previously, New used the displayed active collection
context. No metadata/attachment write API, stored-photo editor, dependencies or
schema migrations were added. Authorized reads set the SPA document title; loading
or failed reads clear prior item titles. Legacy `/item/{id}/` title/Open Graph
metadata stays unchanged. Phase 14 must add permission-scoped Django shell metadata
for primary item/QR routes before cutover; the temporary SPA shell remains generic
before JavaScript bootstrap. No SSR infrastructure was introduced.

### Phase 4 user-validation checklist

Results remain pending; use disposable/test data and the phase completion record.

- [ ] Compare every legacy field, optional relation, month-only release date,
  notes/newlines, all other dates/timestamps, tags and missing values.
- [ ] Anonymous public, owner private and another-user reads, unavailable item,
  session expiry/logout/visibility change and direct refresh must not expose
  private metadata, attachments or containment links. Test rapid item navigation.
- [ ] Bookmark/refresh detail with return context, Back/Forward, new-tab links and
  parent/child/grandchild navigation preserve browser query/page. Forged/external
  return URLs must fall back locally.
- [ ] More than ten children/photos/documents/links: independent continuation,
  scoped absolute/relative URLs, retry/cancel and no eager whole-tree fetch.
- [ ] Select each photo, open full images, absent/missing file fallback; download
  documents normally/new-tab, missing file, proxy HTML errors, duplicate clicks,
  navigation cancellation and object-URL cleanup. Validate saved safe/unsafe links.
- [ ] Owner Edit/New now opens the SPA metadata editor; non-owners have no mutation controls. Legacy attachment management remains available.
- [ ] Desktop 1440px, 768px and 360px, keyboard/focus/thumbnail/disclosure links,
  200% zoom, reduced motion, long names/tags/notes/URLs and attachment errors.
- [ ] Operator build/static/start workflow, deep refresh and protected media through
  nginx; no production result is claimed by local source/build/browser review.

Component references: [Quasar image guidance](https://quasar.dev/vue-components/img/)
and [disclosure accessibility guidance](https://quasar.dev/vue-components/expansion-item/).
The implementation uses native image/button/link semantics within the Quasar shell.

## Phase 6 metadata editor

Routes: /app/items/new/ and /app/item/{item_id}/edit/. Both are recognized by Django
for direct refresh. Browser/detail New/Edit links use them; the legacy external
routes remain operational. The editor uses all ItemForm metadata fields and the
[Phase 5 write contract](../api-v1.md#phase-5-item-metadata-writes).

- New can receive collection=<owned ID>; otherwise it preselects an owned active
  collection, or asks for one. It never activates a collection. Profile is not
  required for metadata writes. Editor collections use collections/?scope=owned.
- Shared/personal lookup catalogs and same-collection parent items are searchable
  in paginated QSelect controls. Parent choices include asset tags and omit the
  current item. Cycles/descendant integrity remain server validation. A collection
  change retains the old parent with an explicit mismatch error until cleared or
  replaced; unrelated values remain. Lookup ownership stays the current account.
- Contextual category/manufacturer/status/tag dialogs POST personal values and
  select the result. Dialog closure returns focus to its selector. Status uses the
  existing stored-color allowlist. These lookup creations save immediately and
  survive metadata Cancel; uncertain results are explained before another request.
- Text, optional relations, tags and all four dates map to explicit metadata
  writes. Release month is a masked YYYY-MM text input: untouched months preserve
  the original stored day; changed months submit day 01; clearing submits null.
  Three other dates use native date inputs. Blank name retains backend auto-name.
- Save has a pending guard, field errors plus focused summary, and status feedback.
  Successful POST records the returned ID immediately and replaces the creation
  route with the edit route; later saves use PATCH. Uncertain POST results require
  review and an explicit duplicate-risk confirmation before retry; no automatic
  replay. DELETE uses a named confirmation dialog and returns to the browser.
- A changed/expired/unavailable session disables mutation controls without erasing
  draft input. Original identity is required to resume. Log in can open a new tab,
  then Refresh session reestablishes CSRF without submitting automatically.
- Dirty metadata guards SPA navigation, same-window legacy links, native logout
  forms and browser unload. Discard confirmation identifies retained lookup
  creations. Native approved departures bypass a second unload prompt; modified/
  new-tab links retain browser behavior. In-flight writes block app departures.
- Existing-item Attachments links to /items/{id}/edit/ with the same dirty guard.
  New items explain that metadata must save first. Link/document/photo editing
  remains legacy until Phases 7/8; no stored-image editor was added.

Checks: typecheck, lint, build, Django and scoped Ruff passed. Partial owner/
anonymous Chrome review covers 1440/768/360px, initial values, selectors, status
dialog name/focus return and an unsaved-name discard prompt. Mobile controls/
actions measured 44px with no horizontal overflow. Evidence is ignored
.artifacts/phase-6/. No write requests or automated tests were run.

### Phase 6 user-validation checklist

- [ ] Create, reload, edit and delete; blank-name/asset assignment; every ItemForm
  field, null/empty values, tag replacement and release-day preservation.
- [ ] Owned/active/absent collections, missing profile, parent changes/subtree moves,
  invalid cycles, foreign/private targets and combined selection errors.
- [ ] Lookup search/pagination, contextual creation/selection, all status colors,
  server errors, duplicates and keyboard focus after success/cancel.
- [ ] Dirty Save/Cancel/back/navigation/unload, native attachment/account/logout
  links, modified clicks and busy-state departures.
- [ ] Session expiry/account switch/CSRF refresh keep input and prevent stale-account
  writes. Network/proxy/validation failures retain values; uncertain writes do not
  replay automatically.
- [ ] Double submissions, successful creation route replacement, uncertain creation
  reconciliation/retry, deletion outcomes and sensible browser return filters.
- [ ] Desktop/tablet/mobile, full keyboard/dialog containment, long labels, many
  tags, touch/date/month input, 200% zoom, reduced motion and error-summary focus.
