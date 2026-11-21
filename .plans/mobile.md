# Plan: Mobile app (PWA + Capacitor)

## Context

- The game is a FastAPI app (`src/spymaster/webserver/__init__.py`) with a
  Preact frontend built by Parcel into `dist/frontend`. Gameplay, presence,
  session cookies, AI opponents and `/analysis` all run on the remote server
  (deployed at `https://spymaster.fastapicloud.dev/`). `npx cap`/PWA work must
  not move any of that logic into the client.
- The frontend is multi-page: `main.html` (game) is a Parcel entry;
  `help.html` and `privacy.html` are plain HTML served from source and rendered
  by `help_view()` / `privacy_view()`. `dist/frontend/main.html` has a footer
  with GitHub / Help / Tournaments / Privacy links, all `target="_blank"`.
  `Lobby.tsx` also has a `target="_blank"` "How to play" link. `weights.html`
  and `tournaments.html` are standalone entry points with no navigation.
- Bootstrap 5.3.2 CSS is loaded from jsDelivr in all five HTML pages with an
  SRI hash. No Bootstrap JS is used. `privacy.html` discloses the CDN request.
- Notifications are web-only today: `notifications.ts` uses
  `Notification.requestPermission()` and `new Notification(...)`, gated on
  `document.visibilityState === "hidden"`. Call sites are in `messages.ts`
  (challenge, declined, accepted, mission result). No service worker, manifest,
  push, or Capacitor code exists.
- There is no local/offline game engine; `/ws` carries all gameplay and
  `/analysis` is a server-side Nash/minimax computation using the shared
  `ADAPTIVE_ANALYSER`.

### Decisions from the user

1. Ship as a PWA **and** wrap it with Capacitor for native mobile apps.
2. Use **native OS notifications on mobile**; keep browser notifications on web.
3. Server, other services, AIs and analysis stay **remote**. **No offline play.**
4. **Vendor Bootstrap locally first**, and update the privacy policy accordingly.
5. Add proper **navigation/pages for Help and Privacy**; **remove the
   Tournaments link**. Tournaments and weights are to become separate apps
   later — leave their routes/files intact for now.
6. **Commit after each step, then stop and prompt** before starting the next.

### Non-goals

- No offline gameplay, no cached game state, no local AI/analysis, no local
  database, no push service / VAPID / FCM / APNs infrastructure, no store
  submission, no removal of `/tournaments` or `/weights` routes, no Bootstrap
  JS bundle.

## Architecture

- **Remote origin is the source of truth.** Capacitor `server.url` points at
  the deployed site. `webDir` remains `dist/frontend` so Parcel output is still
  available for the PWA build and native assets, but the app never serves game
  logic from the device.
- **Vendored Bootstrap:** add `bootstrap@5.3.2` as a dev dependency purely as
  the source of the minified CSS; copy the CSS plus its MIT licence into
  `src/frontend/static/vendor/`. All pages link to
  `/static/vendor/bootstrap.min.css` (absolute path, so Parcel leaves it
  untouched and FastAPI's `/static` mount serves it). Remove CDN URLs and SRI
  attributes.
- **Navigation:** a small Bootstrap navbar in each server-rendered page, with
  same-tab internal links (so the WebView stays inside the app). GitHub remains
  the only `target="_blank"` link. Footer is reduced to GitHub; Tournaments is
  no longer linked.
- **PWA:** manifest + icons for installability, plus a deliberately minimal
  service worker that only cache-first-caches same-origin static assets
  (Bootstrap, CSS/JS bundles, icons, manifest). All navigations, `/api/*`,
  `/analysis`, cookies and `/ws` go to the network. No offline fallback page —
  offline means the browser's normal error, because offline play is unsupported.
- **Native notifications:** `@capacitor/local-notifications`, triggered from the
  existing WebSocket message handler. No new backend service. Known limitation
  to document: if the app is fully terminated the socket is gone, so no
  notification can be produced; notifications work while the app is open or
  backgrounded with a live connection.

## Working-tree precondition

The tree already has **unrelated, staged and unstaged minimax changes**
(`.plans/minimax-2ply.md`, `computer_players.py`, `nash_players.py`,
`webserver/__init__.py`, two test files, `benchmark_nash.py`). Do not include or
alter them. For every step, stage and commit **only the named paths**:

```bash
git add <paths-for-this-step>
git commit -m "<short imperative subject>" -- <same paths>
```

Never use bare `git add -A` or `git commit` here. After each commit, stop and
ask before continuing. Commit subjects follow repo style: short, imperative,
capitalised, no Conventional Commits prefixes.

---

## Step 0 — Record the plan

- Copy the finalized plan into the repo at `.plans/mobile.md` (the harness only
  permits writing plan files under `~/.opencode/plan` while in Plan mode, so
  this is the first implementation action).
- Commit only `.plans/mobile.md`: `Add mobile app plan`.
- **Stop, report the commit, and prompt before Step 1.**

## Step 1 — Vendor Bootstrap locally and update the privacy policy

Files: `package.json`, `package-lock.json`,
`src/frontend/static/vendor/bootstrap.min.css` (new),
`src/frontend/static/vendor/bootstrap.LICENSE` (new), `main.html`,
`help.html`, `privacy.html`, `weights.html`, `tournaments.html`,
`tests/test_webserver.py`.

- `npm install --save-dev bootstrap@5.3.2`.
- Copy `node_modules/bootstrap/dist/css/bootstrap.min.css` and
  `node_modules/bootstrap/LICENSE` into `src/frontend/static/vendor/`. Keep the
  exact 5.3.2 minified file; no CDN, no SRI attributes, no Bootstrap JS.
- Replace the jsDelivr `<link>` in all five HTML pages with
  `<link rel="stylesheet" href="/static/vendor/bootstrap.min.css">`, keeping
  `spymaster.css` after it where present. Confirm the Parcel-built
  `dist/frontend/main.html` retains the absolute `/static/vendor/...` URL.
- In `src/frontend/privacy.html`:
  - replace the "Third parties" jsDelivr paragraph with a statement that
    Bootstrap and all other static assets are served from the app's own
    server, so no third-party CDN sees the user's IP;
  - add that an internet connection is required because game state, AI players
    and analysis run on the remote server;
  - update "Last updated" to 21 November 2026.
  Leave the notification wording for Step 5.
- Add tests in `tests/test_webserver.py` (new `TestStaticPages` class) asserting
  `/privacy` mentions locally served Bootstrap and no `cdn.jsdelivr`, and that
  the HTML templates contain no CDN stylesheet link.
- Verify: `npm run build`, `npm run typecheck`, `uv run -m unittest`,
  `ruff check --fix --output-format=concise`, `ty check --output-format=concise`.
- Commit as `Vendor Bootstrap locally`. **Stop and prompt.**

## Step 2 — Add Help/Privacy navigation, remove the Tournaments link

Files: `src/frontend/main.html`, `help.html`, `privacy.html`,
`src/frontend/static/components/Lobby.tsx`, `tests/test_webserver.py`.

- Add a JS-free Bootstrap navbar to `main.html`, `help.html` and `privacy.html`
  (identical markup, with a comment to keep the copies in sync): brand link to
  `/`, then `Game`, `Help`, `Privacy` links. Use `navbar navbar-dark bg-dark
  border-bottom border-secondary` plus a flex wrapper and `nav-link` classes;
  do not use `navbar-expand`/toggler because Bootstrap JS is not loaded.
- Keep "← Back to the game" on Help and Privacy. Reduce footers to the GitHub
  link only. Remove the `href="/tournaments"` link from `main.html`.
- Remove `target="_blank"` from internal links: the footer links in
  `main.html`, `help.html`, `privacy.html` and the "How to play" link in
  `Lobby.tsx:108-112`. Keep GitHub's `target="_blank" rel="noopener noreferrer"`.
- Leave `/tournaments`, `/weights`, their APIs, Parcel entries and files alone;
  they stay reachable by direct URL for the planned separate apps.
- Tests: navbar present in each page; no internal `target="_blank"`; no
  `/tournaments` link in `main.html` or its built output; Help and Privacy
  links point to `/help` and `/privacy`.
- Verify (same commands as Step 1), then commit as
  `Add help and privacy navigation`. **Stop and prompt.**

> Before Step 4 you can tell me if you would rather **not** commit the generated
> `android/` and `ios/` projects; the default in this plan is to commit them so
> a fresh checkout can build the native apps.

## Step 3 — PWA manifest, icons and a network-only service worker

Files: `src/frontend/static/manifest.json` (new),
`src/frontend/static/icons/icon-192.png` and `icon-512.png` and
`apple-touch-icon.png` (new), `src/frontend/static/sw.js` (new),
`src/frontend/static/index.tsx`, `main.html`, `help.html`, `privacy.html`,
`src/spymaster/webserver/__init__.py`, `tests/test_webserver.py`.

- Generate 192px, 512px and 180px icons from `src/frontend/static/icon.png`
  (e.g. `sips -Z 512 ... --out ...` on macOS) into
  `src/frontend/static/icons/`.
- Add `manifest.json` served at `/static/manifest.json` with `name`,
  `short_name: "Spymaster"`, `start_url: "/"`, `scope: "/"`,
  `display: "standalone"`, `theme_color`/`background_color` matching the dark
  Bootstrap theme, and 192/512 icon entries (`purpose: "any maskable"`).
- Add to the `<head>` of `main.html`, `help.html`, `privacy.html`: manifest
  link, `theme-color`, `apple-mobile-web-app-capable`, `apple-touch-icon`.
- Add `sw.js` served at `/static/sw.js`:
  - versioned cache name plus `install`/`activate` cleanup;
  - `fetch` handler that only handles same-origin GETs for static-looking
    assets (`/static/...`, or `.js`, `.css`, `.png`, `.ico`, `.json`) with
    `request.destination` of `style`, `script`, `image` or `manifest`;
  - cache-first for those assets, network for everything else; explicitly
    never touch `/ws`, `/analysis`, `/api/*`, HTML navigations or cookies;
  - no offline fallback, in line with "no offline play".
- Register the SW in `index.tsx` only on the web path, using a runtime guard
  that does not need Capacitor types yet:
  `const native = (window as any).Capacitor?.isNativePlatform?.() ?? false;`
  and skip registration when `native` is true.
- Add `GET /sw.js` in the webserver returning `FileResponse` from
  `static_dir / "sw.js"` with `Service-Worker-Allowed: /` and
  `Cache-Control: no-cache`; import `FileResponse` from `fastapi.responses`.
  Verify it is matched as an explicit route rather than by `app.frontend`.
- Tests: `/sw.js` returns 200, JavaScript content type and
  `Service-Worker-Allowed: /`; manifest parses and lists both icons; SW source
  contains no `/api`, `/analysis` or `/ws` interception.
- Verify (including a fresh `npm run build`), then commit as
  `Add PWA manifest and service worker`. **Stop and prompt.**

## Step 4 — Capacitor wrapper loading the remote app

Files: `package.json`, `package-lock.json`, `capacitor.config.ts` (new),
`capacitor.config.json` if generated (remove duplicate), `assets/` (new),
`android/` and `ios/` (new, generated), `.gitignore` only if native projects
are excluded, `README.md`, `tests/test_webserver.py` if needed.

- Install `@capacitor/core @capacitor/cli @capacitor/android @capacitor/ios`
  and dev dependency `@capacitor/assets`.
- `npx cap init "Spymaster" com.jmftsang.spymaster --web-dir dist/frontend`.
  App id can be changed before a store submission; nothing is submitted now.
- Configure `server.url` as `https://spymaster.fastapicloud.dev/` and
  `server.allowNavigation` to that host so `/help` and `/privacy` stay inside
  the WebView. Keep the origin as the single source of truth.
- Create `assets/icon.png` and `assets/splash.png` from the existing icon and
  run `npx capacitor-assets generate --android --ios` so native icons are
  consistent with the PWA icon.
- `npx cap add android` and `npx cap add ios`; then `npx cap sync`.
- Add npm scripts: `cap:sync` (`npm run build && cap sync`),
  `cap:android` (`cap open android`), `cap:ios` (`cap open ios`).
- README: prerequisites (Android Studio, Xcode + CocoaPods), build/sync/open
  commands, the remote-server requirement, and how to temporarily point the
  config at a locally running backend for development.
- Decide native-project tracking: **default is to commit `android/` and
  `ios/`**; if the user opts for a lean repo, add them to `.gitignore` and
  document `npx cap add` as a one-time setup instead.
- Verify: `npm run build`, `npm run typecheck`, `npx cap sync`,
  `uv run -m unittest`, `ruff check --fix --output-format=concise`,
  `ty check --output-format=concise`.
- Commit as `Add Capacitor mobile wrapper`. **Stop and prompt.**

## Step 5 — Native notifications on mobile

Files: `package.json`, `package-lock.json`,
`src/frontend/static/notifications.ts`,
`src/frontend/static/components/NotificationPrompt.tsx`,
`src/frontend/privacy.html`, native project files touched by `cap sync`,
`tests/test_webserver.py` if needed.

- Install `@capacitor/local-notifications`; run `npx cap sync`.
- In `notifications.ts`:
  - detect native with `Capacitor.isNativePlatform()` from `@capacitor/core`;
  - on native, `notificationsSupported` is true, and
    `enableNotifications()` calls `LocalNotifications.requestPermissions()`,
    mapping `display === "granted"` to the existing `notificationPermission`
    signal; on web keep `Notification.requestPermission()` unchanged;
  - on native, `notify(title, body)` calls
    `LocalNotifications.schedule({ notifications: [{ id, title, body, schedule: { at: new Date(Date.now() + 500) } }] })`
    with a monotonically increasing integer id; keep the `new Notification`
    path on web and its visibility gate;
  - drop the `document.visibilityState` gate on native — WebView visibility is
    unreliable and the OS controls presentation;
  - keep dismissal in `localStorage` for the prompt, and note in a comment
    that permission is otherwise managed by the OS settings.
- Update `NotificationPrompt.tsx` wording to "device notifications" when
  native (a single generic sentence is fine).
- Privacy policy: add a short Notifications section — what triggers them
  (challenges and game events), that they are generated on the device from
  messages sent by the game server, that permission can be revoked in device
  settings, that they require the app to be running/backgrounded with a live
  connection (no notifications after the app is terminated), and no push
  service is operated. Refresh the "Last updated" date.
- Verify: `npm run typecheck`, `npm run build`, `npx cap sync`, full Python
  test/lint/type checks. Commit as `Use native notifications on mobile`.
  **Stop and prompt.**

## Step 6 — Documentation and final verification

Files: `README.md`, any small fixes found during verification.

- Add a README "Mobile" section covering: PWA installation from the browser,
  Android/iOS build commands, remote-server-only operation (internet required;
  AI and analysis stay server-side), and notification behaviour/limitations.
- Run the full verification suite:
  `npm run build`, `npm run typecheck`, `uv run -m unittest`,
  `ruff check --fix --output-format=concise`, `ty check --output-format=concise`,
  `npx cap sync`.
- Manual checklist to report (not necessarily executable here): PWA installs
  and opens at `/`; Help/Privacy open inside the app; no Tournaments link;
  static assets load with the network offline for third-party hosts blocked;
  notifications fire on a challenge in a native dev build; an offline device
  cannot play (expected).
- Commit any remaining changes as `Document mobile builds`. **Stop and report
  completion.**

---

## Verification commands used throughout

```bash
npm run build
npm run typecheck
uv run -m unittest
ruff check --fix --output-format=concise
ty check --output-format=concise
```

`npm run build` must precede `uv run -m unittest`, because `/` reads
`dist/frontend/main.html` (CI already does this).

## Risks / notes

- Parcel rewrites relative asset URLs in `main.html` to hashed root paths, but
  leaves absolute `/static/...` URLs alone; verify the built HTML after Step 1.
- `StaticFiles` is mounted at `/static`; a service worker registered from
  `/static/sw.js` would be scoped to `/static/`. Registering the explicit
  `/sw.js` route with `Service-Worker-Allowed: /` avoids that.
- FastAPI 0.143's `app.frontend("/", ...)` is a low-priority fallback; explicit
  routes such as `/sw.js` must still be checked before it.
- Capacitor's remote `server.url` means native builds always fetch the current
  deployed HTML/JS/CSS; no stale local bundle can drift from the server.
- Committing native projects increases repo size but keeps builds reproducible;
  the user can choose the lean alternative at the Step 4 prompt.
- Existing minimax work in the tree is unrelated and must stay out of these
  commits.
