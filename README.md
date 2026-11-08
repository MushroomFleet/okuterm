# okuterm

**Live, okudagram-style terminal dashboards drawn entirely with Unicode block characters, for desktop terminals and edge devices.**

okuterm draws animated sci-fi control-panel displays, inspired by the LCARS look from classic science-fiction TV, right in your terminal. It has rounded "elbow" frames, a split sidebar in pastel colours, gauge bars, sparklines, pill-shaped tags and rows of small changing numbers.

The project has three parts:

- **`okuterm.py`:** a ready-to-run system monitor in one file.
- **`okukit.py`:** a toolkit for building your own okuterm-style dashboards. It runs on anything from a truecolor desktop terminal to a Raspberry Pi's text console.
- **`OKUTERM-PLAYBOOK.md`:** a complete playbook that teaches Claude Code (or any coding agent) to build okuterm dashboards to order.

Everything is standard-library Python with no required dependencies.

```
 ▄████████████████████████████████████  ███████████  ██████
████▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀
████   OPS MONITOR                                 14:39:01
▀▀▀▀
▄▄▄▄   CPU   ▐██████████████████████████████████████▌   34%
████   MEM   ▐██████████████████████████████████████▌   61%
████   DISK  ▐██████████████████████████████████████▌   48%
████   TEMP  ▐██████████████████████████████████████▌   52C
▀▀▀▀
▄▄▄▄   49-6890 05-4242 65-7961 51-4969 61-5866 74-3578
▀▀▀▀   86-1311 72-9400 68-8037 61-2163 82-5212 82-1596
▄▄▄▄
████   ▐ SYSTEM ▌ ▐ TRENDS ▌
████▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄
 ▀████████████████████████████████████  ███████████  ██████
```

*This preview has the colours removed. In a real terminal every block has its own colour, gauges change colour at warning and critical levels, and the empty part of each gauge shows as dark grey.*

---

## ✨ What is an okudagram?

"Okudagram" is the nickname for the fictional computer display graphics made for sci-fi screens. The name comes from Michael Okuda, the designer behind them. The style uses flat colour blocks on black, rounded frame corners, pill-shaped buttons, segmented bars and lots of tiny decorative numbers.

okuterm brings that look into the terminal. It uses Unicode block elements and ANSI colour, so it needs no graphics library, GUI or browser.

## 🎯 What it's for

- **A desk-side status display:** run it on a spare monitor or in a tmux pane.
- **Edge and kiosk displays:** boot a Raspberry Pi or other single-board computer straight into a full-screen dashboard on its attached screen.
- **Custom dashboards:** show server health, build status, sensors, home automation, weather, queues, or anything else you can turn into a number.
- **Agent-built tools:** hand the playbook to Claude Code and ask for the dashboard you want.
- **Learning terminal graphics:** the code is short and shows how to use half-block characters, colour fallbacks and flicker-free redraws.

## 📁 Repository contents

| File | What it is |
|---|---|
| `okuterm.py` | The original single-file system monitor (CPU, memory, disk, swap) |
| `okukit.py` | The dashboard toolkit: components, colour/glyph detection, data sources, keyboard, screen handling |
| `example_dashboard.py` | Reference dashboard built on okukit: two pages, alerts, sparklines, compact mode |
| `OKUTERM-PLAYBOOK.md` | The agent playbook for building okuterm dashboards (desktop by default, edge on request) |

## 📦 Requirements

- Python 3.7+
- **Desktop:** a terminal with truecolor support, such as Windows Terminal, iTerm2, WezTerm, Kitty, Alacritty, GNOME Terminal or Konsole. okukit drops back to 256 colours automatically elsewhere.
- **Edge:** a Linux framebuffer console (e.g. Raspberry Pi OS Lite) with a Terminus or Uni2 console font
- *Optional:* [`psutil`](https://pypi.org/project/psutil/) for real CPU, memory and swap readings on desktop. On Linux, okukit reads `/proc` and `/sys` directly when `psutil` isn't installed.

## 🚀 Quick start

```bash
git clone https://github.com/MushroomFleet/okuterm-dev.git
cd okuterm-dev

pip install psutil            # optional

python okuterm.py             # the original monitor
python example_dashboard.py   # the okukit reference dashboard
```

Controls: **q** or **Ctrl+C** quits. In `example_dashboard.py`, **TAB** or **1**/**2** switch pages. Both run in the terminal's alternate screen, so your previous terminal contents come back when you quit.

## 🧰 okukit: build your own

okukit is one file you drop into a project. A dashboard is a **pure `build()` function** that returns a list of lines. okukit takes care of colour, glyphs, terminal setup and redrawing.

```python
import time
from okukit import *

cpu = Source(cpu_percent, 1.0, history=120)

def build(p, cols, rows, frame):
    W = max(50, min(cols - 1, 100)); inner = W - 7
    v = cpu.get()
    content = [
        p.fg("MY MONITOR", ORANGE),
        "",
        p.fg("CPU   ", TEXT) + gauge(p, v, inner - 14, level_colour(v, 70, 90)),
        p.fg("TREND ", TEXT) + spark(p, cpu.history, inner - 6, PEACH),
    ]
    return panel(p, W, content, [(2, PEACH), (2, LAV)])

p = Painter(Caps.detect())
with Screen() as scr:
    frame = 0
    while True:
        cols, rows = scr.size()
        scr.draw(build(p, cols, rows, frame))
        frame += 1
        time.sleep(0.5)
```

**Components:** `frame_bar`, `sidebar`, `panel`, `gauge`, `spark`, `pill`, `clutter`, `hjoin` (side-by-side panels), `level_colour`, `blink`, `fit`.

**Infrastructure:**
- `Caps.detect()` picks the colour mode and glyph set.
- `Painter` maps RGB colours to whatever the terminal supports.
- `Source` polls data, caches it and handles errors, with optional background threads for slow calls.
- `Keys` reads keypresses without blocking.
- `Screen` handles setup, flicker-free drawing and clean exit.
- `check_frame()` is a layout checker for tests.

### Runs anywhere: automatic fallbacks

| | Colour | Glyphs |
|---|---|---|
| Modern desktop terminal | truecolor | full Unicode, `▁▂▃▄▅▆▇█` sparklines |
| Older / tmux without RGB | 256-colour | full Unicode |
| Linux console (`TERM=linux`) | 16-colour | CP437-safe set: `█ ▀ ▄ ▌ ▐ ░ ▒ ▓` |
| Non-UTF-8 or `NO_COLOR` | none | plain ASCII |

To override detection, set `OKU_COLOR=truecolor|256|16|none` and `OKU_GLYPHS=unicode|cp437|ascii`.

## 📟 Edge devices

okuterm dashboards run well as boot-to-dashboard kiosks on small screens attached to a Raspberry Pi or other SBC, with no desktop environment needed. The playbook covers the full setup:

- Sizing the panel to the screen and console font (e.g. 800×480 with Terminus 10×20 gives 80×24)
- Choosing a console font that has the block glyphs, and stopping the screen blanking
- A **systemd service** that runs the dashboard on `tty1` at boot and restarts it if it fails
- A compact layout for 3.5″ screens, and stdlib `/proc`/`/sys` readers so nothing needs pip on the device

## 🤖 The Claude Code playbook

`OKUTERM-PLAYBOOK.md` is written for coding agents. Put it in your project, or point Claude Code at it, and ask for a dashboard, for example *"build an okuterm monitor for my three web servers"* or *"make a greenhouse sensor display for my Pi's 5-inch screen"*. It covers:

- **Intake and defaults:** desktop unless you specify an edge device
- **Design language:** anatomy, geometry, palette roles, typography, motion, and a rule to keep all names original
- **Architecture and component reference**
- **Layout recipes:** single panel, compact, pages, multi-panel grid, status grid
- **Data source patterns:** intervals, threading, staleness, error display
- **Desktop and edge profiles**, including the autostart unit
- **Verification:** a multi-mode width test, a smoke run and a clean-exit test
- **Delivery checklist and a pitfalls table**

The toolkit and reference dashboard are included as appendices, so the playbook works on its own.

## 🎨 Customising `okuterm.py`

The original monitor keeps everything in one file:

- **Colours:** palette constants at the top (`PEACH`, `LAV`, `GOLD`, …)
- **Sidebar:** `SIDEBAR = [(rows, colour), ...]`; the row counts must add up to the number of content lines (11)
- **Content:** `read_metrics()` for data, `content()` for layout
- **Refresh rate:** `time.sleep(0.5)` in `main()`

For anything bigger, build on okukit instead.

## 🔧 How it works

- **Block elements for curves:** a terminal cell is about twice as tall as it is wide. Half blocks (`▀ ▄ ▌ ▐`) double the vertical resolution, which is enough to fake rounded elbows and capped gauges.
- **Gaps make the style:** frame bars are split into separate segments with 2-column gaps. Sidebar blocks end on `▀▀▀▀` and the next starts on `▄▄▄▄`, which leaves a thin gap between them.
- **Colour mapping:** colours are defined once as RGB and sent as truecolor, the nearest of 256 colours, or the nearest of 16, depending on the terminal.
- **Flicker-free redraw:** each frame moves the cursor home, overwrites the old lines and clears what's left over. The screen is never fully wiped, so nothing flashes.
- **Ticking clutter:** the decorative numbers re-seed every few frames, so they tick over instead of flickering.
- **Never crashes on data:** failed or missing readings show `----` and an empty gauge.

## 🗺️ Roadmap ideas

- Large seven-segment-style numeric readouts
- A config file for palettes and layouts
- More stdlib readers (network throughput, battery)
- Ready-made panels for common services (HTTP health checks, MQTT topics, Docker containers)
- Packaging okukit on PyPI

## ⚖️ Disclaimer

okuterm is an independent fan project inspired by a general visual style. It isn't affiliated with or endorsed by any studio or rights holder. All labels and graphics in this repository are original.

---

## 📚 Citation

### Academic Citation

If you use this codebase in your research or project, please cite:

```bibtex
@software{okuterm,
  title = {okuterm: Live okudagram-style terminal dashboards drawn with Unicode block characters},
  author = {Drift Johnson},
  year = {2026},
  url = {https://github.com/MushroomFleet/okuterm-dev},
  version = {1.0.0}
}
```

### Donate:

[![Ko-Fi](https://cdn.ko-fi.com/cdn/kofi3.png?v=3)](https://ko-fi.com/driftjohnson)
