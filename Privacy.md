# Privacy policy

Spymaster is a small, non-commercial hobby project. This policy explains what
information the web app handles and why.

## What we collect

- **A username.** The name you type to play. It is shown to other players and
  does not have to be your real name.
- **A session cookie.** When you connect, the server sets a single `session`
  cookie containing a random identifier. It keeps you logged in across reloads
  and reconnects. It is marked `HttpOnly` and `SameSite=Lax` and is not used for
  advertising or analytics.
- **Game state.** Your moves, scores and current game are held in the server's
  memory while you play.

## What we do not collect

- No passwords, email addresses or accounts.
- No advertising, tracking or analytics cookies.
- We do not sell or share your information.

## Online service

An internet connection is required to play. Game state, AI opponents and
analysis all run on the remote server; the app has no offline game engine.

## Notifications

If you enable notifications, Spymaster alerts you to challenges and game events
that need your attention. The server sends those events over the existing
connection, and the app or browser creates the notification on your device; no
push service is operated. On mobile you can revoke permission at any time in the
device settings. Notifications require the app or page to be running or
backgrounded with a live connection — after the app is fully terminated or the
page is closed, no notification can be produced.

## Third parties

Bootstrap and all other stylesheets, scripts and icons are served by the same
server as the game. The app loads no assets from third-party CDNs, so no third
party receives your IP address in order to serve them.

## Retention

Usernames and game state live in the server's memory and are discarded when the
server restarts or the session ends. The session cookie stays in your browser
until you clear it.

## Your choices

You can play under any name you like, clear the session cookie at any time, or
simply stop using the site.

## Contact

Questions? Contact J. M. F. Tsang at <j.m.f.tsang@cantab.net> or open an issue
on GitHub.

*Last updated: 21 November 2026.*
