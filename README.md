# okuterm

**A live, okudagram-style terminal panel drawn entirely with Unicode block characters.**

okuterm draws an animated sci-fi control-panel display, inspired by the LCARS look from classic science-fiction TV, right in your terminal. It has rounded "elbow" frames, a split sidebar in pastel colours, gauge bars and rows of small changing numbers. The panel redraws twice a second and shows live system stats.

It's a single Python file with no required dependencies.

```
 ▄████████████████████████████████████  ███████████  ██████
████▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀
████   SYSTEM MONITOR                 14:25:06  REF 05-0185
▀▀▀▀
▄▄▄▄   CPU   ▐██████████████████████████████████████▌   34%
████   MEM   ▐██████████████████████████████████████▌   61%
████   DISK  ▐██████████████████████████████████████▌   48%
▀▀▀▀   SWAP  ▐██████████████████████████████████████▌   12%
▄▄▄▄
████   17-9325 97-1033 32-1931 63-7364 60-6219 26-1537
▀▀▀▀   62-0464 49-7090 77-0034 89-7297 34-3748 75-1674
▄▄▄▄
████   LIVE
████▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄
 ▀████████████████████████████████████  ███████████  ██████
```

*This preview has the colours removed. In a real terminal every block has its own truecolor shade, and the empty part of each gauge shows as dark grey.*

---

## ✨ What is an okudagram?

"Okudagram" is the nickname for the fictional computer display graphics made for sci-fi screens. The name comes from Michael Okuda, the designer behind them. The style uses flat colour blocks on black, rounded frame corners, pill-shaped buttons, segmented bars and lots of tiny decorative numbers.

okuterm brings that look into the terminal. It uses Unicode block elements and ANSI truecolor, so it needs no graphics library, GUI or browser.

## 🎯 What it's for

- **A desk-side status display:** run it on a spare monitor, a Raspberry Pi screen or a tmux pane.
- **A starting point for your own dashboards:** swap the system stats for weather, build status, stock prices or home-automation sensors.
- **Learning terminal graphics:** the code is short and shows how to use half-block characters, truecolor escapes and flicker-free redraws.
- **Fun:** it's a small piece of sci-fi set dressing for your terminal.

## 📦 Requirements

- Python 3.7+
- A terminal with **truecolor (24-bit) support**, such as Windows Terminal, iTerm2, WezTerm, Kitty, Alacritty, GNOME Terminal or Konsole
- *Optional:* [`psutil`](https://pypi.org/project/psutil/) for real CPU, memory and swap readings

> The legacy Windows console (`cmd.exe` in conhost) and macOS Terminal.app don't fully support truecolor. The shapes still draw, but the colours will be wrong.

## 🚀 Quick start

```bash
git clone https://github.com/MushroomFleet/okuterm-dev.git
cd okuterm-dev

# optional, for real system stats
pip install psutil

python okuterm.py
```

Press **Ctrl+C** to quit. okuterm runs in the terminal's alternate screen, so when you quit, your previous terminal contents come back untouched.

### Live vs. simulated data

| Metric | With `psutil` | Without `psutil` |
|--------|---------------|------------------|
| CPU    | Real          | Simulated (smooth random walk) |
| MEM    | Real          | Simulated |
| DISK   | Real          | Real (uses Python's standard library) |
| SWAP   | Real          | Simulated |

The bottom line of the panel shows **LIVE** when everything is real. Otherwise it tells you which values are simulated.

## 🎨 Customising

Everything lives in `okuterm.py`, and the main things to change are near the top.

**Colours:** edit the palette constants:

```python
PEACH  = (255, 153, 102)
ORANGE = (255, 170, 0)
LAV    = (204, 153, 204)
GOLD   = (255, 204, 153)
BLUE   = (153, 153, 255)
SALMON = (204, 102, 102)
```

**Sidebar blocks:** each entry is `(rows, colour)`. The row counts must add up to the number of content lines, which is currently 11:

```python
SIDEBAR = [(2, PEACH), (4, LAV), (3, GOLD), (2, SALMON)]
```

**What the panel shows:** edit `read_metrics()` to change the data source, and `content()` to change the layout. Each metric is just a `(label, percent)` pair, so anything you can turn into a percentage can drive a gauge.

**Refresh rate:** change `time.sleep(0.5)` in `main()`.

**Width:** the panel fits your terminal width each frame, between 50 and 100 columns.

## 🔧 How it works

- **Block elements for curves:** a terminal cell is about twice as tall as it is wide. Half blocks (`▀ ▄ ▌ ▐`) double the vertical resolution, which is enough to fake rounded elbows and capped gauge bars.
- **Gaps make the style:** frame bars are split into separate segments with small black gaps. Sidebar blocks end on `▀▀▀▀` and the next one starts on `▄▄▄▄`, which leaves a thin gap between them.
- **Truecolor ANSI:** every element is wrapped in `ESC[38;2;R;G;Bm`, so any RGB colour works.
- **Flicker-free redraw:** each frame moves the cursor home (`ESC[H`), overwrites the old lines, clears each line's leftover tail (`ESC[K`) and clears anything below (`ESC[J`). The screen is never fully wiped, so nothing flashes.
- **Ticking clutter:** the decorative number rows use a seeded random generator that changes every few frames, so they tick over instead of flickering.

## 🗺️ Ideas for extending

- Multiple panels or pages, switched with a keypress
- Network throughput, temperature sensors or battery gauges
- Blinking alert segments when a value crosses a threshold
- A pure 7-bit ASCII fallback mode for limited terminals
- A config file for palettes and layouts

## ⚖️ Disclaimer

okuterm is an independent fan project inspired by a general visual style. It isn't affiliated with or endorsed by any studio or rights holder. All labels and graphics in this repository are original.

---

## 📚 Citation

### Academic Citation

If you use this codebase in your research or project, please cite:

```bibtex
@software{okuterm,
  title = {okuterm: A live okudagram-style terminal panel drawn with Unicode block characters},
  author = {Drift Johnson},
  year = {2026},
  url = {https://github.com/MushroomFleet/okuterm-dev},
  version = {1.0.0}
}
```

### Donate:

[![Ko-Fi](https://cdn.ko-fi.com/cdn/kofi3.png?v=3)](https://ko-fi.com/driftjohnson)
