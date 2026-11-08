# OKUTERM PLAYBOOK

### How to build okuterm-style terminal dashboards and monitors

**Audience:** Claude Code (or any coding agent) asked to build a live terminal dashboard, monitor or status display in the okuterm style.
**Outcome:** a single runnable Python program, standard library only, that draws an animated, okudagram-style panel and behaves well on its target device.

---

## 0. Read this first: the ten rules

1. **The target defaults to desktop.** Use the **edge** profile only when the user says so: Raspberry Pi, SBC, kiosk, small screen, "on the device", framebuffer, tty, headless display and so on. If you're unsure and nothing expensive depends on it, build for desktop and say so in one line.
2. **Build on `okukit.py`** (Appendix A). Copy it into the project unchanged, then write the dashboard as a separate file. Don't re-derive the primitives.
3. **`build()` is a pure function.** `build(painter, cols, rows, frame, state) -> list[str]` does no I/O. Data comes from `Source` objects and output goes through `Screen.draw`. That separation is what makes the work testable.
4. **Every line in a frame has exactly the same visible width, `W`.** Check this with `check_frame()` and a width assertion in every colour and glyph mode.
5. **Never crash the render loop on data.** A failed source shows `----` and a dim gauge, never a traceback.
6. **Use only single-width glyphs from the active glyph set.** No emoji, CJK, box-drawing art outside the kit, or Nerd Font icons.
7. **Colour carries meaning.** Pastels for structure, blue/lavender for normal, orange for warning, red for critical (blinking only at critical), dim for no data.
8. **Labels are short, UPPERCASE and original.** Never put franchise names, logos, ship names, character names or trademarked interface names in the UI.
9. **Verify before delivering:** run the multi-mode width test, run the program for a few seconds, and check Ctrl+C restores the terminal (section 11).
10. **Deliver something runnable:** the files, a one-line run command, and for edge targets the autostart unit and console setup.

---

## 1. Intake

Work out the following from the request. Fill any gaps with the defaults and state the assumptions you made in one line at the top of your reply. Ask before building only when a wrong guess would be expensive, for example a fleet of devices or an unknown, proprietary data source.

| Question | Default |
|---|---|
| Target profile | **desktop** |
| What it monitors | Local system: CPU, memory, disk (+ temperature on edge) |
| Data sources & how to reach them | stdlib / `/proc`; `psutil` if present |
| Refresh rate | desktop 0.5 s · edge 1.0 s |
| Screen size | desktop: adapt to the terminal, 50–100 cols · edge: ask, or assume 800×480 (≈100×30) |
| Interaction | `q` quits, `TAB`/number keys switch pages if there's more than one page; none on edge kiosks |
| Thresholds | warn 70–80 %, crit 90 %; temperature warn 65 °C, crit 80 °C |
| Title | Short, original, UPPERCASE (`OPS MONITOR`, `GREENHOUSE`, `BUILD STATUS`) |
| Dependencies | **none** beyond Python 3.7+; `psutil` optional on desktop |

---

## 2. Target profiles

| | **Desktop** (default) | **Edge** |
|---|---|---|
| Typical host | Windows Terminal, iTerm2, WezTerm, Kitty, GNOME Terminal, tmux pane | Raspberry Pi / SBC on the Linux framebuffer console (`/dev/tty1`), often with no keyboard |
| `TERM` | `xterm-256color`, `wezterm`, … | `linux` |
| Colour | truecolor (fallback 256) | **16 colours**; the kit maps RGB automatically |
| Glyphs | `unicode`: half blocks + `▁▂▃▄▅▆▇█` sparklines | `cp437`: `█ ▀ ▄ ▌ ▐ ░ ▒ ▓` only |
| Size | Resizable; redraw each frame at the current width | Fixed; set by panel resolution ÷ font cell size |
| Refresh | 0.5 s | 1.0 s or slower (lower CPU load on small boards) |
| Data | `psutil` if installed, else stdlib | stdlib `/proc` + `/sys` readers (no pip on device) |
| Launch | `python dashboard.py` | systemd service bound to `tty1`, auto-restart |
| Extras | Keyboard pages, alt-screen | Disable console blanking, pick a console font, set a UTF-8 locale |

A Pi running a graphical desktop with a full-screen terminal emulator counts as **desktop** for rendering. Use the edge autostart pattern only if the user wants it to boot straight into the dashboard.

---

## 3. Design language

### 3.1 Anatomy

```
 ▄████████████████████████████████████  ███████████  ██████   ← top frame bar (1.5 rows)
████▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀     elbow + 3 segments, 2-col gaps
████   OPS MONITOR                                 14:39:01   ← title row: name left, clock right
▀▀▀▀                                                          ← sidebar block ends on ▀▀▀▀
▄▄▄▄   CPU   ▐██████████████████████████████████████▌   34%   ← next block starts on ▄▄▄▄
████   MEM   ▐██████████████████████████████████████▌   61%     gauges: label(6) bar value
████   DISK  ▐██████████████████████████████████████▌   48%
████   TEMP  ▐██████████████████████████████████████▌   52C
▀▀▀▀
▄▄▄▄   49-6890 05-4242 65-7961 51-4969 61-5866 74-3578        ← decorative number clutter
▀▀▀▀   86-1311 72-9400 68-8037 61-2163 82-5212 82-1596
▄▄▄▄
████   ▐ SYSTEM ▌ ▐ TRENDS ▌                                  ← pills (page tabs / status tags)
████▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄   ← bottom frame bar
 ▀████████████████████████████████████  ███████████  ██████
```

### 3.2 Geometry

- **Panel width `W`:** `max(50, min(cols - 1, 100))` on desktop (40 minimum in compact mode).
- **Sidebar:** 4 columns wide, followed by 3 spaces of padding, so the content (inner) width is **`W - 7`**.
- **Frame bars:** elbow + segment 1 (shares the elbow colour), then segment 2 (`max(8, W//5)`) and segment 3 (6 wide), with **2-column gaps**. The gaps are what make the style recognisable, so never close them.
- **Sidebar blocks:** each block is at least **2 rows**. A block ends on the upper half (`▀`) and the next starts on the lower half (`▄`), which leaves one thin gap between them. The block row counts **must equal** the number of content lines. Put the arithmetic in code, not in your head (section 6.4).
- **Gauges:** `label(6) + gauge(width + 2) + value(6)`, so the bar width is `inner - 14`.
- **Vertical rhythm:** title, blank, data group, blank, clutter, blank, tabs/status. Use one blank row between groups. In compact mode, drop the blanks and the clutter first.

### 3.3 Palette and colour roles

| Constant | RGB | Role |
|---|---|---|
| `PEACH` | 255,153,102 | Top elbow, primary structure, first sidebar block |
| `LAV` | 204,153,204 | Secondary structure, normal-state accents |
| `GOLD` | 255,204,153 | Text (`TEXT`), tertiary structure |
| `BLUE` | 153,153,255 | Normal values, primary clutter |
| `SALMON` | 204,102,102 | Bottom elbow, lower sidebar block |
| `ORANGE` | 255,170,0 | Title, active tab, **warning** level |
| `RED` | 255,68,68 | **Critical** level only (may blink) |
| `DIM` | 55,55,75 | Empty gauge track, inactive tabs, **no data** |
| `FAINT` | 110,110,170 | Secondary clutter, de-emphasised text |

The background is always the terminal's black. Never paint a background except inside pills.

### 3.4 Typography

- UPPERCASE labels of six characters or fewer (`CPU`, `MEM`, `TEMP`, `QUEUE`, `UPLINK`).
- Right-align numbers in fixed-width fields (`f"{v:4.0f}%"`). Values must never shift the layout when they change length.
- Missing value: `----`. Stale value: show the value in `DIM` and add a `STALE` pill.
- Units go straight after the number with no space (`52C`, `61%`, `3.2k`).

### 3.5 Motion

- Clocks and values update every frame.
- Clutter re-seeds every ~4 frames (`clutter(p, w, frame // 4, ...)`) so it **ticks** rather than flickers.
- **Blink** (`blink(frame, RED)`) is reserved for critical alerts. Nothing else flashes.
- Sparklines scroll naturally as history grows.

### 3.6 Originality guard

The style is generic: rounded frames, pastel blocks, number clutter. The **content** must be original. Don't use franchise names, starship or character names, real in-universe system names or acronyms, insignia, or numbers that are known in-jokes from a show. Invent your own titles and reference codes. If the user asks for a specific franchise's branding, build the generic style and explain in one line why you left the branding out.

---

## 4. Architecture

```
 Source(fn, interval)  ──►  state  ──►  build(p, cols, rows, frame, state) -> list[str]  ──►  Screen.draw(lines)
   polls, caches,              page,          pure: no I/O, no sleeps, no globals mutated        flicker-free redraw,
   never raises                 alerts         except reading Source.value                         alt screen, cleanup
```

The program skeleton is the same for every dashboard:

```python
import time
from okukit import *

REFRESH = 0.5
cpu = Source(cpu_percent, 1.0, history=120)
mem = Source(mem_percent, 2.0)

def build(p, cols, rows, frame, page):
    W = max(50, min(cols - 1, 100)); inner = W - 7
    content = [...]                                 # list of painted strings
    spec = [(2, PEACH), (len(content) - 2, LAV)]    # rows must sum to len(content)
    return panel(p, W, content, spec)

def main():
    p = Painter(Caps.detect())
    page = frame = 0
    with Screen() as scr:
        keys = Keys()
        try:
            while True:
                k = keys.read()
                if k in ("q", "Q"): break
                cols, rows = scr.size()
                scr.draw(build(p, cols, rows, frame, page))
                frame += 1
                time.sleep(REFRESH)
        finally:
            keys.close()

if __name__ == "__main__":
    main()
```

The full reference implementation is `example_dashboard.py` (Appendix B). Start from it.

---

## 5. Component reference (`okukit.py`)

All components take a `Painter` `p` first and return painted strings whose **visible width is known exactly**.

| Function | Visible width | Purpose |
|---|---|---|
| `frame_bar(p, W, top, (c1, c2, c3))` | `W` (2 rows) | Top/bottom frame with elbow and gapped segments |
| `sidebar(p, spec)` | 4 per row | Coloured sidebar blocks; `spec = [(rows, rgb), …]` with rows ≥ 2 |
| `panel(p, W, lines, spec, top=…, bottom=…)` | `W` | Full framed screen; pads every content line to `W - 7` |
| `gauge(p, pct, width, rgb)` | `width + 2` | Capped bar; `pct=None` draws an empty "no data" bar |
| `spark(p, values, width, rgb, lo, hi)` | `width` | Sparkline of the most recent values; `None` shows a gap |
| `pill(p, label, rgb)` | `len(label) + 4` | Rounded tag/button: half-block caps, label on a colour background |
| `clutter(p, width, seed, rgb)` | `width` | Decorative `NN-NNNN` groups |
| `level_colour(v, warn, crit, ok=BLUE)` | n/a | Threshold colour; `None` gives `DIM` |
| `blink(frame, on, off=DIM)` | n/a | Alternating colour for critical alerts |
| `fit(s, width)` | `width` | Pad, or truncate as plain text, to an exact width |
| `hjoin(blocks, gap=2)` | sum | Place panels side by side |
| `vis_len(s)` / `strip(s)` | n/a | Width / text without ANSI codes |
| `check_frame(lines, W)` | n/a | Lists problems: too wide, control characters or wide characters |

Infrastructure:

| Class | Purpose |
|---|---|
| `Caps.detect()` | Picks the colour mode (`truecolor`/`256`/`16`/`none`) and glyph set (`unicode`/`cp437`/`ascii`) from `TERM`, `COLORTERM`, `WT_SESSION`, `NO_COLOR` and the stdout encoding. Override with `OKU_COLOR` / `OKU_GLYPHS`. |
| `Painter(caps)` | `fg(text, rgb)`, `bg(text, rgb, ink)`; maps RGB to the best available colour. |
| `Source(fn, interval, threaded=False, history=0)` | Cached polling. `.get()` returns the value or `None`; `.ok`, `.error`, `.updated` and `.history` are also available. |
| `Keys()` | Non-blocking key reads on Windows and POSIX; turns itself off when stdin isn't a TTY. |
| `Screen()` | Context manager: turns on VT on Windows, alt screen, hidden cursor, flicker-free `draw()`, full restore on exit or Ctrl+C. |

Stdlib data readers: `cpu_percent()`, `mem_percent()` (both use `psutil` if present), `linux_cpu_percent()`, `linux_mem_percent()`, `linux_temp_c(zone)` and `disk_percent(path)`.

---

## 6. Layout recipes

### 6.1 Single panel (default)

Title, blank, gauges, blank, two clutter rows, blank, tabs or status. See `build()` in Appendix B.

### 6.2 Compact (small screens, `rows < 17` or `W < 56`)

Drop the blank rows and the clutter, and use two sidebar blocks:

```python
content = title + body + [tabs]
spec = [(2, PEACH), (len(content) - 2, LAV)]
```

### 6.3 Pages

Draw `pill()` tabs: `ORANGE` for the active page, `DIM` for the others. `TAB` cycles through the pages and `1`–`9` jump to one. Every page **must return the same number of body lines** so the sidebar spec stays valid. Pad short pages with `""`.

### 6.4 Sidebar spec arithmetic

Always derive the spec from `len(content)`:

```python
n = len(content)
spec = [(2, PEACH), (len(body) + 1, LAV), (2, GOLD), (n - len(body) - 5, SALMON)]
assert sum(r for r, _ in spec) == n and all(r >= 2 for r, _ in spec)
```

`panel()` raises a `ValueError` if the counts don't match. Treat that as a bug in your layout, and never catch it.

### 6.5 Multi-panel grid (wide desktop terminals)

Build each panel at its own width, then join them:

```python
left  = panel(p, 60, left_lines,  left_spec)
right = panel(p, 40, right_lines, right_spec, top=(LAV, BLUE, GOLD), bottom=(GOLD, LAV, PEACH))
lines = hjoin([left, right], gap=2)
```

Choose the panel widths from `cols`. Fall back to stacking the panels vertically, or to paging, when `cols < 104`.

### 6.6 Status grid (many services)

Use one row per item: `fit(name, 10) + pill(p, "ONLINE", BLUE)`, with `ORANGE` for `DEGRADED`, `RED` + `blink` for `DOWN` and `DIM` for `UNKNOWN`. Give the pills a fixed label width so the columns line up (`"DOWN".ljust(8)`).

---

## 7. Data sources

- **Wrap every reading in a `Source`.** Choose the interval to match the data, not the frame rate: CPU 1 s, memory 2 s, disk 30 s, network/API 10–60 s.
- **For slow or blocking calls** (HTTP, MQTT, SNMP, subprocesses), use `Source(fn, 30, threaded=True)`. The render loop must never wait on I/O.
- **Staleness:** `time.time() - src.updated > 3 * src.interval` means stale. Dim the value and show a `STALE` pill.
- **Errors:** `src.ok is False` means show `----` and optionally `fit(src.error, inner)` in `FAINT` on a status line. Never let the error text change the line width.
- **History:** pass `history=N` (N ≥ sparkline width) to collect values for `spark()`.
- **Desktop:** use `psutil` when it's available (`cpu_percent`/`mem_percent` already do), and mention `pip install psutil` in the delivery.
- **Edge:** use the stdlib `/proc` and `/sys` readers and don't depend on pip. Temperature comes from `/sys/class/thermal/thermal_zone0/temp`. Use `Source` so a missing sensor just shows `----`.
- **Normalise to a percentage for gauges** by passing `100 * value / max`, with `max` as a named constant. Show the raw value with its unit in the value column.
- **Simulated data:** only when the user asks for a demo, or a real source is unreachable while you're building. Label it on screen (`SIMULATED` pill) and say so in the delivery.

---

## 8. Desktop profile details

- `Caps.detect()` picks truecolor in Windows Terminal (`WT_SESSION`), in any terminal that sets `COLORTERM=truecolor`, and in Windows consoles from 1703 on. Inside tmux, truecolor needs `set -as terminal-features ",*:RGB"`; otherwise users can set `OKU_COLOR=256`.
- macOS Terminal.app has no truecolor support, so tell the user to run `OKU_COLOR=256 python dashboard.py` or use iTerm2/WezTerm.
- The width adapts every frame, so resizing works without any signal handling.
- `Screen` uses the alternate screen, so the user's scrollback comes back on exit.
- The run command is `python dashboard.py` (or `py dashboard.py` on Windows).

---

## 9. Edge profile details

### 9.1 Sizing

The number of columns and rows is the panel resolution divided by the console font cell size:

| Panel | 8×16 font | 10×20 Terminus | 16×32 Terminus |
|---|---|---|---|
| 480×320 (3.5″) | 60×20 | 48×16 (compact) | 30×10 (too small) |
| 800×480 (5″/7″) | 100×30 | 80×24 | 50×15 (compact) |
| 1024×600 | 128×37 | 102×30 | 64×18 |
| 1920×1080 HDMI | 240×67 | 192×54 | 120×33 |

On large HDMI screens, pick a big font so the 100-column panel fills the screen and can be read from across a room. You can also raise the `W` cap in `build()`.

### 9.2 Console setup (Raspberry Pi OS / Debian)

```bash
# Font: choose "Terminus" and a size in the menus (or set FONTFACE/FONTSIZE in /etc/default/console-setup)
sudo dpkg-reconfigure console-setup

# Stop the screen blanking: add to the single line in /boot/firmware/cmdline.txt
#   (older images: /boot/cmdline.txt)
consoleblank=0
```

If the block glyphs show as diamonds or question marks, the console font lacks them. Switch to a Terminus/Uni2 font, or set `OKU_GLYPHS=ascii`.

### 9.3 Autostart on tty1 (systemd)

Create `/etc/systemd/system/okuterm.service`:

```ini
[Unit]
Description=okuterm dashboard on tty1
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=simple
User=okuterm
SupplementaryGroups=tty video
WorkingDirectory=/opt/okuterm
ExecStart=/usr/bin/python3 /opt/okuterm/dashboard.py
StandardInput=tty
StandardOutput=tty
StandardError=journal
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Environment=TERM=linux
Environment=LANG=C.UTF-8
Environment=PYTHONIOENCODING=utf-8
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo useradd --system --no-create-home okuterm
sudo mkdir -p /opt/okuterm && sudo cp okukit.py dashboard.py /opt/okuterm/
sudo systemctl disable --now getty@tty1.service
sudo systemctl daemon-reload
sudo systemctl enable --now okuterm.service
journalctl -u okuterm -f          # tracebacks land here, not on the screen
```

Notes for the agent to pass on:
- **`LANG=C.UTF-8` / `PYTHONIOENCODING` matter.** Without them, systemd starts Python with an ASCII stdout, and `Caps.detect()` correctly but disappointingly falls back to ASCII glyphs.
- If the service fails with a permission error on `/dev/tty1`, check the `tty` group membership, or (for a single-purpose device) remove the `User=` line to run as root, and say so plainly.
- No keyboard is assumed, so the dashboard must not need input. `Keys` turns itself off when stdin isn't a TTY.
- To get a login prompt back: `sudo systemctl disable --now okuterm && sudo systemctl enable --now getty@tty1`.

### 9.4 Edge rendering checklist

- Test with `OKU_COLOR=16 OKU_GLYPHS=cp437` at the device's exact cols×rows.
- Check the palette under 16-colour mapping. Pastels collapse onto a few ANSI colours, so make sure warning and critical still look different (orange becomes yellow, red stays red).
- Refresh at 1 s or slower, and keep `history` lengths modest.
- Over SSH, the same program works in the user's desktop terminal. Detection picks the richer mode automatically.

---

## 10. Workflow for the agent

1. **Intake** (section 1). Settle the profile, data sources, size and thresholds. State your assumptions.
2. **Set up a task list** for anything beyond a trivial change: toolkit, data layer, layout, verify, deliver.
3. **Copy `okukit.py`** into the project from Appendix A, unchanged. If you change it, keep `check_frame` and the width guarantees.
4. **Write the data layer:** one `Source` per reading, with appropriate intervals, `threaded=True` for anything slow, and stdlib readers on edge.
5. **Write `build()`.** Start from Appendix B. Choose the recipe (section 6), derive the sidebar spec from `len(content)`, and add a compact branch if the screen can be small.
6. **Apply the design rules** (section 3): colour roles, labels, fixed-width values, blinking only at critical, original names.
7. **Verify** (section 11). Fix anything that fails and rerun until it passes.
8. **Deliver** (section 12).

---

## 11. Verification

### 11.1 Multi-mode width test (always run)

Save this as `test_frames.py` next to the dashboard and run it with `python test_frames.py`:

```python
import itertools, okukit as k, dashboard as d   # rename to your module

SIZES = [(120, 40), (80, 24), (60, 20), (48, 14)]   # add the device's exact size for edge
for color, glyphs in itertools.product(["truecolor", "256", "16", "none"],
                                       ["unicode", "cp437", "ascii"]):
    p = k.Painter(k.Caps(color, glyphs))
    for cols, rows in SIZES:
        for page in range(len(getattr(d, "PAGES", [0]))):
            for frame in range(4):
                lines = d.build(p, cols, rows, frame, page)
                W = max(40, min(cols - 1, 100))          # match your build()'s W rule
                widths = {k.vis_len(l) for l in lines}
                assert widths == {W}, (color, glyphs, cols, rows, page, widths)
                assert not k.check_frame(lines, W), k.check_frame(lines, W)
                assert len(lines) <= rows, (cols, rows, len(lines))
print("all frames OK")
```

### 11.2 Look at it

Print one plain frame and check it by eye for alignment, rhythm and labels:

```bash
python -c "import okukit as k, dashboard as d; print('\n'.join(d.build(k.Painter(k.Caps('none','unicode')), 80, 24, 3, 0)))"
```

### 11.3 Run it

```bash
timeout 3 python dashboard.py </dev/null >/dev/null; echo "exit $?"    # 124 = ran until timeout, no crash
```

### 11.4 Clean exit

Send SIGINT and confirm the program exits with code 0 and its output ends with the restore sequence:

```python
import subprocess, signal, sys, time
pr = subprocess.Popen([sys.executable, "dashboard.py"], stdin=subprocess.DEVNULL,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
time.sleep(1.5); pr.send_signal(signal.SIGINT)
out, err = pr.communicate(timeout=5)
assert pr.returncode == 0 and not err, err
assert out.endswith(b"\x1b[0m\x1b[?25h\x1b[?1049l")
print("clean exit OK")
```

(Background jobs in a non-interactive shell ignore SIGINT, which is why the test resets the handler with `preexec_fn`.)

### 11.5 Data failure

Temporarily make one source's function `raise RuntimeError`. The frame must still render, with `----` and a dim gauge.

---

## 12. Delivery

Give the user:

1. **The files:** `okukit.py`, `dashboard.py` (named for its purpose, e.g. `greenhouse_monitor.py`) and `test_frames.py`.
2. **Run instructions:** one line, plus `pip install psutil` if it's useful on desktop.
3. **Edge only:** the systemd unit, the console setup commands (section 9) and the device size you designed for.
4. **What's real and what's simulated**, if anything is simulated.
5. **One customisation pointer:** where to change the palette, thresholds and refresh rate.

Keep the summary short. The user can run it and see it for themselves.

---

## 13. Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Ragged right edge | A line wasn't padded, or a value changed length | Use `panel()`/`fit()`; fixed-width number formats |
| `ValueError: content has N lines, sidebar has M` | Spec not derived from content | Section 6.4; pages must have equal body lengths |
| Gauges look full in a monochrome terminal | Empty track drawn with `█` in `DIM` | The kit uses `░`/`.` automatically in `16`/`none` modes; don't bypass `gauge()` |
| Diamonds/`?` instead of blocks | Font lacks the glyphs, or the stdout encoding isn't UTF-8 | Terminus/Uni2 font; `LANG=C.UTF-8`; `OKU_GLYPHS=ascii` |
| Washed-out or wrong colours | Truecolor sent to a 256/16-colour terminal | `OKU_COLOR=256` or `16`; check `COLORTERM`/tmux RGB |
| Whole-screen flicker | Clearing with `ESC[2J` every frame | Use `Screen.draw()` (home + overwrite + `ESC[K`) |
| Lines wrap and the panel scrolls | `W` ≥ terminal columns | `W ≤ cols - 1`; `Screen.draw` also truncates as a backstop |
| UI freezes for seconds | Blocking network call in the render path | `Source(..., threaded=True)` |
| Terminal left with no cursor after a crash | Exception outside `with Screen()` | Keep the whole loop inside the context manager; `reset` fixes a broken terminal |
| Dashboard on tty1 shows ASCII only | systemd locale is POSIX | `Environment=LANG=C.UTF-8` and `PYTHONIOENCODING=utf-8` |
| Screen goes black after 10 minutes (edge) | Console blanking | `consoleblank=0` on the kernel command line |

---

## Appendix A: `okukit.py`

Copy this into the project verbatim.

```python
"""
okukit.py - building blocks for okuterm-style terminal dashboards.

Single file, standard library only. Works on desktop terminals (truecolor,
full Unicode) and on edge devices (Linux framebuffer console: 16 colours,
CP437-safe glyphs), and falls back to plain ASCII if it has to.

    from okukit import *
    caps = Caps.detect()
    p = Painter(caps)
    with Screen() as scr:
        while True:
            scr.draw(build_frame(p))      # your function -> list[str]
            time.sleep(0.5)

Environment overrides:
    OKU_COLOR  = truecolor | 256 | 16 | none
    OKU_GLYPHS = unicode | cp437 | ascii
    NO_COLOR   = (any value) -> no colour
"""
import os
import re
import sys
import threading
import time

# =============================================================================
# Palette (RGB). Painter maps these down to 256 / 16 colours automatically.
# =============================================================================
PEACH  = (255, 153, 102)
ORANGE = (255, 170, 0)
LAV    = (204, 153, 204)
GOLD   = (255, 204, 153)
BLUE   = (153, 153, 255)
SALMON = (204, 102, 102)
RED    = (255, 68, 68)
GREEN  = (136, 204, 136)
DIM    = (55, 55, 75)
FAINT  = (110, 110, 170)
TEXT   = GOLD
BLACK  = (0, 0, 0)

# =============================================================================
# Capability detection
# =============================================================================
GLYPHS = {
    # full block, upper half, lower half, left half, right half,
    # empty-gauge fill (used when colour can't show the empty part), sparkline ramp.
    # Note: "right" (▐) is the LEFT cap of a bar and "left" (▌) the RIGHT cap.
    "unicode": dict(full="█", top="▀", bot="▄", left="▌", right="▐",
                    empty="░", ramp=" ▁▂▃▄▅▆▇█"),
    # CP437 subset: safe on the Linux console's default fonts
    "cp437":   dict(full="█", top="▀", bot="▄", left="▌", right="▐",
                    empty="░", ramp=" ░▒▓█"),
    "ascii":   dict(full="#", top="=", bot="=", left="]", right="[",
                    empty=".", ramp=" .:-=+*#"),
}


class Caps:
    def __init__(self, color, glyphs):
        self.color = color          # "truecolor" | "256" | "16" | "none"
        self.glyphs = glyphs        # "unicode" | "cp437" | "ascii"
        self.g = GLYPHS[glyphs]

    @staticmethod
    def detect():
        term = os.environ.get("TERM", "").lower()
        colorterm = os.environ.get("COLORTERM", "").lower()

        color = os.environ.get("OKU_COLOR")
        if not color:
            if os.environ.get("NO_COLOR"):
                color = "none"
            elif term == "linux":                       # framebuffer / VT console
                color = "16"
            elif colorterm in ("truecolor", "24bit") or os.environ.get("WT_SESSION"):
                color = "truecolor"
            elif os.name == "nt":
                color = "truecolor"                     # Win10 1703+ consoles
            elif "256color" in term:
                color = "256"
            elif term in ("dumb", ""):
                color = "none"
            else:
                color = "16"

        glyphs = os.environ.get("OKU_GLYPHS")
        if not glyphs:
            enc = (getattr(sys.stdout, "encoding", "") or "").lower()
            if "utf" not in enc:
                glyphs = "ascii"
            elif term == "linux":
                glyphs = "cp437"
            else:
                glyphs = "unicode"
        return Caps(color, glyphs)


# =============================================================================
# Colour painting
# =============================================================================
_ANSI16 = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
           (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
           (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
           (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]


def _to256(r, g, b):
    if max(r, g, b) - min(r, g, b) < 12:                # greyscale ramp
        if r < 8:
            return 16
        if r > 238:
            return 231
        return min(255, 232 + (r - 8) // 10)
    q = lambda v: 0 if v < 48 else 1 if v < 115 else (v - 35) // 40
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


def _to16(rgb):
    return min(range(16), key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, _ANSI16[i])))


RESET = "\x1b[0m"
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def vis_len(s):
    """Visible width of a painted string (all okukit glyphs are single-width)."""
    return len(_ANSI_RE.sub("", s))


def strip(s):
    return _ANSI_RE.sub("", s)


class Painter:
    def __init__(self, caps):
        self.caps = caps
        self.g = caps.g

    def _code(self, rgb, bg=False):
        m = self.caps.color
        if m == "truecolor":
            return f"{48 if bg else 38};2;{rgb[0]};{rgb[1]};{rgb[2]}"
        if m == "256":
            return f"{48 if bg else 38};5;{_to256(*rgb)}"
        if m == "16":
            i = _to16(rgb)
            if bg:
                return str(40 + (i % 8))                # no bright backgrounds on the VT
            return f"1;{30 + i - 8}" if i >= 8 else str(30 + i)
        return ""

    def fg(self, text, rgb):
        if not text or self.caps.color == "none":
            return text
        return f"\x1b[{self._code(rgb)}m{text}{RESET}"

    def bg(self, text, rgb, ink=BLACK):
        if self.caps.color == "none":
            return text
        return f"\x1b[{self._code(rgb, bg=True)};{self._code(ink)}m{text}{RESET}"


# =============================================================================
# Components. Each returns painted strings of an exact, known visible width.
# =============================================================================
def frame_bar(p, W, top, colours):
    """Top/bottom frame: rounded elbow on the left, 3 segments, 2-col gaps.
    Returns 2 rows. Elbow + first segment share colours[0]."""
    g = p.g
    s3 = 6
    s2 = max(8, W // 5)
    s1 = W - s2 - s3 - 4
    c1, c2, c3 = colours
    gap = "  "
    if top:
        return [
            p.fg(" " + g["bot"] + g["full"] * (s1 - 2), c1) + gap
            + p.fg(g["full"] * s2, c2) + gap + p.fg(g["full"] * s3, c3),
            p.fg(g["full"] * 4 + g["top"] * (s1 - 4), c1) + gap
            + p.fg(g["top"] * s2, c2) + gap + p.fg(g["top"] * s3, c3),
        ]
    return [
        p.fg(g["full"] * 4 + g["bot"] * (s1 - 4), c1) + gap
        + p.fg(g["bot"] * s2, c2) + gap + p.fg(g["bot"] * s3, c3),
        p.fg(" " + g["top"] + g["full"] * (s1 - 2), c1) + gap
        + p.fg(g["full"] * s2, c2) + gap + p.fg(g["full"] * s3, c3),
    ]


def sidebar(p, spec, width=4):
    """spec = [(rows, colour), ...], each rows >= 2. Returns one cell per row.
    Blocks are separated by half-height ends so a thin gap shows between them."""
    g = p.g
    cells = []
    for i, (n, rgb) in enumerate(spec):
        if n < 2:
            raise ValueError("sidebar blocks need at least 2 rows")
        for j in range(n):
            ch = g["full"]
            if j == 0 and i > 0:
                ch = g["bot"]
            if j == n - 1 and i < len(spec) - 1:
                ch = g["top"]
            cells.append(p.fg(ch * width, rgb))
    return cells


def gauge(p, pct, width, rgb, empty=DIM):
    """Capped horizontal bar. Visible width = width + 2. pct None = no data."""
    g = p.g
    low = p.caps.color in ("16", "none")      # DIM is invisible/indistinct here
    ech = g["empty"] if low else g["full"]
    if p.caps.color == "16" and empty == DIM:
        empty = FAINT
    if pct is None:
        return p.fg(g["right"] + ech * width + g["left"], empty)
    pct = max(0.0, min(100.0, pct))
    filled = round(width * pct / 100)
    return (p.fg(g["right"], rgb) + p.fg(g["full"] * filled, rgb)
            + p.fg(ech * (width - filled), empty)
            + p.fg(g["left"], rgb if filled == width else empty))


def spark(p, values, width, rgb, lo=0.0, hi=100.0):
    """Sparkline of the last `width` values. Visible width = width."""
    ramp = p.g["ramp"]
    vals = list(values)[-width:]
    out = ""
    for v in vals:
        if v is None:
            out += " "
            continue
        t = (min(hi, max(lo, v)) - lo) / ((hi - lo) or 1)
        out += ramp[round(t * (len(ramp) - 1))]
    return p.fg(out.rjust(width), rgb)


def pill(p, label, rgb):
    """Rounded button/tag: half-block caps + label on a coloured background.
    Visible width = len(label) + 4."""
    g = p.g
    if p.caps.color == "none":
        return f"{g['right']} {label} {g['left']}"
    return p.fg(g["right"], rgb) + p.bg(f" {label} ", rgb) + p.fg(g["left"], rgb)


def clutter(p, width, seed, rgb):
    """Decorative number groups ('NN-NNNN'). Change the seed every few frames."""
    import random
    rng = random.Random(seed)
    s = ""
    while len(s) + 8 <= width:
        s += f"{rng.randint(0, 99):02d}-{rng.randint(0, 9999):04d} "
    return p.fg(s.rstrip().ljust(width), rgb)


def level_colour(value, warn, crit, ok=None):
    """Pick a colour for a value against thresholds (higher = worse)."""
    if value is None:
        return DIM
    if value >= crit:
        return RED
    if value >= warn:
        return ORANGE
    return ok or BLUE


def blink(frame, on_rgb, off_rgb=DIM, period=2):
    """Alternate colours on a frame counter (use for alerts only)."""
    return on_rgb if (frame // period) % 2 == 0 else off_rgb


def fit(s, width):
    """Pad (or hard-truncate plain text) to an exact visible width."""
    n = vis_len(s)
    if n <= width:
        return s + " " * (width - n)
    return strip(s)[:width]


def row(*parts):
    return "".join(parts)


# =============================================================================
# Panel: a full framed screen = top bar + (sidebar | content) + bottom bar
# =============================================================================
def panel(p, W, content_lines, spec,
          top=(PEACH, LAV, BLUE), bottom=(SALMON, GOLD, ORANGE)):
    """Assemble a framed panel. len(content_lines) must equal sum of spec rows.
    Content lines are padded to the inner width (W - 7)."""
    rows = sum(n for n, _ in spec)
    if len(content_lines) != rows:
        raise ValueError(f"content has {len(content_lines)} lines, sidebar has {rows}")
    inner = W - 7
    out = frame_bar(p, W, True, top)
    for side, line in zip(sidebar(p, spec), content_lines):
        out.append(side + "   " + fit(line, inner))
    out += frame_bar(p, W, False, bottom)
    return out


def hjoin(blocks, gap=2):
    """Place several panels (lists of lines) side by side."""
    h = max(len(b) for b in blocks)
    widths = [max((vis_len(l) for l in b), default=0) for b in blocks]
    out = []
    for i in range(h):
        parts = [fit(b[i] if i < len(b) else "", w) for b, w in zip(blocks, widths)]
        out.append((" " * gap).join(parts))
    return out


# =============================================================================
# Data sources
# =============================================================================
class Source:
    """Polls fn() every `interval` seconds; never raises into the render loop.
    threaded=True runs fn in a background thread (for slow / network calls).
    .value is None until the first success or after an error."""

    def __init__(self, fn, interval=1.0, threaded=False, history=0):
        self.fn, self.interval, self.threaded = fn, interval, threaded
        self.value, self.ok, self.error, self.updated = None, False, None, 0.0
        self.history = [] if history else None
        self._hist_len = history
        self._next = 0.0
        if threaded:
            threading.Thread(target=self._loop, daemon=True).start()

    def _poll(self):
        try:
            self.value, self.ok, self.error = self.fn(), True, None
        except Exception as e:                          # show, don't crash
            self.value, self.ok, self.error = None, False, str(e)[:60]
        self.updated = time.time()
        if self.history is not None:
            self.history.append(self.value)
            del self.history[:-self._hist_len]

    def _loop(self):
        while True:
            self._poll()
            time.sleep(self.interval)

    def get(self):
        if not self.threaded and time.time() >= self._next:
            self._next = time.time() + self.interval
            self._poll()
        return self.value


# ---- standard-library readers (Linux /proc and /sys; no psutil needed) ------
_cpu_prev = None


def linux_cpu_percent():
    global _cpu_prev
    with open("/proc/stat") as f:
        parts = [int(x) for x in f.readline().split()[1:]]
    idle, total = parts[3] + parts[4], sum(parts)
    prev, _cpu_prev = _cpu_prev, (idle, total)
    if prev is None or total == prev[1]:
        return 0.0
    return 100.0 * (1 - (idle - prev[0]) / (total - prev[1]))


def linux_mem_percent():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            info[k] = int(v.split()[0])
    return 100.0 * (1 - info["MemAvailable"] / info["MemTotal"])


def linux_temp_c(zone=0):
    with open(f"/sys/class/thermal/thermal_zone{zone}/temp") as f:
        return int(f.read()) / 1000.0


def disk_percent(path=None):
    import shutil
    u = shutil.disk_usage(path or os.path.abspath(os.sep))
    return 100.0 * u.used / u.total


def cpu_percent():
    try:
        import psutil
        return psutil.cpu_percent(interval=None)
    except ImportError:
        return linux_cpu_percent()


def mem_percent():
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        return linux_mem_percent()


# =============================================================================
# Keyboard (optional, non-blocking)
# =============================================================================
class Keys:
    """Non-blocking single-key reader. Use inside `with Screen():`.
    k.read() -> str or None. Silently disabled when stdin isn't a terminal."""

    def __init__(self):
        self._old = None
        self.enabled = sys.stdin.isatty()
        if self.enabled and os.name != "nt":
            import termios
            import tty
            self._old = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

    def read(self):
        if not self.enabled:
            return None
        if os.name == "nt":
            import msvcrt
            return msvcrt.getwch() if msvcrt.kbhit() else None
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def close(self):
        if self._old is not None:
            import termios
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old)
            self._old = None


# =============================================================================
# Screen: terminal setup / teardown and flicker-free drawing
# =============================================================================
class Screen:
    def __init__(self, alt=True):
        self.alt = alt

    def __enter__(self):
        if os.name == "nt":
            os.system("")                               # enable VT processing
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        seq = "\x1b[?25l\x1b[2J"
        if self.alt:
            seq = "\x1b[?1049h" + seq
        sys.stdout.write(seq)
        sys.stdout.flush()
        return self

    def size(self, default=(80, 24)):
        import shutil
        s = shutil.get_terminal_size(default)
        return s.columns, s.lines

    def draw(self, lines):
        cols, rows = self.size()
        lines = [fit(l, cols - 1) if vis_len(l) >= cols else l for l in lines[:rows]]
        sys.stdout.write("\x1b[H" + "\x1b[K\n".join(lines) + "\x1b[K\x1b[J")
        sys.stdout.flush()

    def __exit__(self, *exc):
        seq = RESET + "\x1b[?25h"
        if self.alt:
            seq += "\x1b[?1049l"
        sys.stdout.write(seq)
        sys.stdout.flush()
        return isinstance(exc[1], KeyboardInterrupt)    # Ctrl+C exits quietly


# =============================================================================
# Verification helper (for agents and tests)
# =============================================================================
def check_frame(lines, W=None):
    """Return a list of problems: ragged widths, stray characters, etc."""
    problems = []
    widths = [vis_len(l) for l in lines]
    if W is not None:
        for i, w in enumerate(widths):
            if w > W:
                problems.append(f"line {i}: width {w} > {W}")
    for i, l in enumerate(lines):
        bad = [c for c in strip(l) if ord(c) < 32 or 0x1F000 <= ord(c)]
        if bad:
            problems.append(f"line {i}: control/wide characters {bad!r}")
    return problems
```

---

## Appendix B: `example_dashboard.py` (reference dashboard)

This is a working dashboard built on the kit. It has two pages, threshold colours, sparklines, a blinking temperature alert, clutter, compact mode and graceful no-data handling. Use it as the starting point for new dashboards.

```python
#!/usr/bin/env python3
"""
example_dashboard.py - reference okuterm dashboard built on okukit.

Shows: frame + sidebar panel, threshold-coloured gauges, sparkline history,
pills as page tabs, blinking alert, decorative clutter, two pages (TAB / 1 / 2),
compact layout for small screens, graceful 'no data' states.

    python example_dashboard.py            # q or Ctrl+C to quit
"""
import time

from okukit import (BLUE, DIM, FAINT, GOLD, LAV, ORANGE, PEACH, RED, SALMON, TEXT,
                    Caps, Keys, Painter, Screen, Source, blink, clutter, cpu_percent,
                    disk_percent, gauge, level_colour, linux_temp_c, mem_percent,
                    panel, pill, spark)

REFRESH = 0.5            # render interval, seconds

cpu  = Source(cpu_percent, 1.0, history=120)
mem  = Source(mem_percent, 2.0, history=120)
disk = Source(disk_percent, 30.0)
temp = Source(linux_temp_c, 5.0)        # None on machines without a thermal zone

PAGES = ["SYSTEM", "TRENDS"]


def fmt(v, unit="%", width=4):
    return "----".rjust(width) + unit if v is None else f"{v:{width}.0f}{unit}"


def page_system(p, inner, frame):
    g = max(10, inner - 14)
    lines = []
    for label, src, warn, crit in (("CPU", cpu, 70, 90), ("MEM", mem, 75, 90),
                                    ("DISK", disk, 80, 95)):
        v = src.get()
        lines.append(p.fg(f"{label:<6}", TEXT) + gauge(p, v, g, level_colour(v, warn, crit))
                     + p.fg(f" {fmt(v)}", TEXT))
    t = temp.get()
    tcol = level_colour(t, 65, 80, ok=LAV)
    if t is not None and t >= 80:
        tcol = blink(frame, RED)
    lines.append(p.fg(f"{'TEMP':<6}", TEXT) + gauge(p, t, g, tcol, ) + p.fg(f" {fmt(t, 'C')}", TEXT))
    return lines


def page_trends(p, inner, frame):
    w = inner - 13
    cpu.get(); mem.get()
    return [
        p.fg(f"{'CPU':<6}", TEXT) + spark(p, cpu.history, w, PEACH) + p.fg(f" {fmt(cpu.value)}", TEXT),
        "",
        p.fg(f"{'MEM':<6}", TEXT) + spark(p, mem.history, w, LAV) + p.fg(f" {fmt(mem.value)}", TEXT),
        "",
    ]


def build(p, cols, rows, frame, page):
    W = max(40, min(cols - 1, 100))
    inner = W - 7
    compact = rows < 17 or W < 56          # e.g. 3.5" edge screens

    tabs = " ".join(pill(p, name, ORANGE if i == page else DIM) for i, name in enumerate(PAGES))
    clock = time.strftime("%H:%M:%S")
    title = [p.fg("OPS MONITOR", ORANGE) + " " * max(1, inner - 11 - len(clock)) + p.fg(clock, TEXT)]

    body = (page_system if page == 0 else page_trends)(p, inner, frame)

    if compact:
        content = title + body + [tabs]
        n = len(content)
        spec = [(2, PEACH), (n - 2, LAV)]
    else:
        content = (title + [""] + body + [""]
                   + [clutter(p, inner, frame // 4, BLUE), clutter(p, inner, frame // 4 + 999, FAINT)]
                   + ["", tabs])
        n = len(content)
        spec = [(2, PEACH), (len(body) + 1, LAV), (2, GOLD), (n - len(body) - 5, SALMON)]
    return panel(p, W, content, spec)


def main():
    p = Painter(Caps.detect())
    page, frame = 0, 0
    with Screen() as scr:
        keys = Keys()
        try:
            while True:
                k = keys.read()
                if k in ("q", "Q"):
                    break
                if k == "\t":
                    page = (page + 1) % len(PAGES)
                elif k in ("1", "2"):
                    page = int(k) - 1
                cols, rows = scr.size()
                scr.draw(build(p, cols, rows, frame, page))
                frame += 1
                time.sleep(REFRESH)
        finally:
            keys.close()


if __name__ == "__main__":
    main()
```
