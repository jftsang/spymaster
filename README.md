# Spymaster

J. M. F. Tsang (j.m.f.tsang@cantab.net)

---

Play now: https://spymaster.fastapicloud.dev/

This is a remake of Richard Bartle's game [Spymaster][bartle], rewritten
with a Python backend, a modernized frontend, and the ability to define
custom AI players. 

Spymaster is based on [Goofspiel][goofspiel], a classic game of bluffing
and double-bluffing. Read [the rules](HowToPlay.md) for instructions.

[bartle]: https://www.youhaventlived.com/spymaster/
[goofspiel]: https://en.wikipedia.org/wiki/Goofspiel

## Usage

![Screenshot of the frontend](FrontendScreenshot.png)

```bash
# Start a webserver
python -m spymaster.webserver
# then go to http://localhost:8000
```
```bash
# Play against a computer player
python -m spymaster Russia
```
```bash
# Play two AIs against each other
python -m spymaster Russia America
```

## Mobile

### Progressive web app

Open https://spymaster.fastapicloud.dev/ in a modern mobile browser and use the
browser's "Install app" or "Add to Home Screen" action. The manifest and
service worker make the site installable; only static assets are cached, and
gameplay always requires a network connection.

### Native apps

The `android/` and `ios/` projects are Capacitor wrappers around the web app.
They load the deployed site in a WebView; game state, AI opponents and analysis
remain on the server, and there is no offline play.

Prerequisites:

- Android Studio with the Android SDK installed.
- Xcode and CocoaPods on macOS.

From the repository root:

```bash
npm install
npm run cap:sync     # rebuild the web assets and sync the native projects
npm run cap:android  # open the Android project in Android Studio
npm run cap:ios      # open the iOS project in Xcode
```

With the SDKs configured, `npx cap run android` and `npx cap run ios` can build
and launch on a connected device or simulator instead. `capacitor.config.ts`
points the WebView at `https://spymaster.fastapicloud.dev/`; the copied web
assets under `dist/frontend/` are kept for PWA builds, but neither the PWA nor
the native apps use them for gameplay.

For local development, temporarily change `remoteOrigin` in
`capacitor.config.ts` to the URL of your running backend (use an address
reachable from the device or emulator), run `npm run cap:sync`, and revert the
change before committing.

Notifications are optional. When enabled, the app creates them on the device
from events sent over the live game connection; no push service is operated.
They work while the app or page is running or backgrounded with that connection
open, but not after a native app is fully terminated or a browser tab is closed.
Permission can be revoked in the device or browser settings.
