# QueekSync PyQt6 GUI Rewrite — COMPLETE ✅

## What happened
The customtkinter GUI's scrolling could not be fixed after 15+ attempts
(the `CTkScrollableFrame` canvas refuses to scroll via external handlers).
Per your request, the GUI was **recoded in PyQt6**, where scrolling is a
native, built-in capability.

## How to run it

```bash
cd /home/cgmikeg/QueekSync
./run_qt.sh          # or: .venv/bin/python main_qt.py
```

The old customtkinter UI is untouched and still runnable via `main.py` /
`run.sh`, but the PyQt6 version is the one to use.

## Scrolling — verified working (tested programmatically)

Every panel uses a custom `ScrollArea` (subclass of Qt's `QScrollArea`)
that overrides `keyPressEvent` / `wheelEvent` to drive the vertical
scrollbar directly — no focus tricks, no canvas hacks:

| Action             | Dashboard | Profiles | Monitor | Settings |
|--------------------|:---------:|:--------:|:-------:|:--------:|
| Mouse wheel        | ✅        | ✅       | ✅      | ✅       |
| Page Up / Page Down| ✅        | ✅       | ✅      | ✅       |
| Home (jump top)    | ✅        | ✅       | ✅      | ✅       |
| End (jump bottom)  | ✅        | ✅       | ✅      | ✅       |
| Arrow keys         | ✅        | ✅       | ✅      | ✅       |

The Monitor panel's log viewer (`QPlainTextEdit`) scrolls natively too.

## What was built

New package `src/ui_qt/` (old `src/ui/` kept as reference):

| File | Purpose |
|------|---------|
| `theme.py` | Design tokens + full QSS stylesheet (dark glass, accent `#3b82f6`) |
| `widgets.py` | GlassCard, buttons, StatusBadge, StatTile, LogViewer, ProgressBar, ColourPicker, **ScrollArea** |
| `sidebar.py` | Sidebar navigation (4 pages, accent highlight) |
| `dashboard.py` | Stats row + responsive 1–4 col card grid (reflows on resize) |
| `profiles_panel.py` | Profile list CRUD, Sync All, Import/Export |
| `monitor_panel.py` | Active job cards + colour-tagged sync log |
| `settings_panel.py` | Theme, notifications, log level, storage, about |
| `profile_editor.py` | 6-tab editor (General, Source, Destination, Options, Schedule, Filters) with connection testing |
| `sftp_browser.py` | Remote SFTP folder browser dialog |
| `app.py` | `QMainWindow` wiring: nav, panels, event pump (QTimer), scheduler/watcher, logging, permission helpers |

Entry point: `main_qt.py` · Launcher: `run_qt.sh` · `PyQt6>=6.6.0` added to `requirements.txt`.

## Architecture notes
- **Core layer reused as-is**: `core/config.py`, `core/profile.py`,
  `core/syncer.py`, `core/scheduler.py`, `core/watcher.py` — no changes needed.
- **Thread safety**: scheduler/watcher callbacks push profile IDs into a
  `queue.Queue`; a 100 ms `QTimer` pumps both that queue and the sync-event
  queue on the UI thread (same pattern as before, now Qt-native).
- **Themes**: `Settings → Theme` applies dark/light/system instantly via QSS.

## Verification performed
1. All 10 `ui_qt` modules import cleanly.
2. `QueekSyncApp` instantiates; all 4 panels navigate.
3. Every panel contains a `ScrollArea` (native scrolling widget).
4. Programmatic wheel + key events moved the scrollbar in every panel.
5. Profile editor opens, all 6 tabs switch, save path exercises both endpoints.
6. Simulated sync events create monitor cards + log lines; success state shows ✔.
7. `timeout 8 .venv/bin/python main_qt.py` ran the full 8 s without crashing.
