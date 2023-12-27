# Spymaster

J. M. F. Tsang (j.m.f.tsang@cantab.net)

---

This is a remake of Richard Bartle's game 
[Spymaster](https://www.youhaventlived.com/spymaster/), rewritten with a
Python backend. 

Spymaster is based on [Goofspiel](https://en.wikipedia.org/wiki/Goofspiel),
a classic game of bluffing and double-bluffing.

It's my attempt at writing a multiplayer browser game. 


## Usage

At the moment only the backend (with a TUI) is ready.

```bash
# Play against the computer
python -m spymaster Russia

# Play two AIs against each other
python -m spymaster Russia America
```

The frontend is looking a little bare...
![img.png](FrontendScreenshot.png)
...but eventually a webserver can be started with
```bash
python -m spymaster.webserver
```
