#!/usr/bin/env python3
"""
okuterm.py - a live, LCARS-inspired terminal panel drawn with Unicode block characters.

Run:       python okuterm.py          (Ctrl+C to quit)
Optional:  pip install psutil         (real CPU / memory / swap; otherwise simulated)
Needs a truecolor terminal: Windows Terminal, iTerm2, and most Linux terminals work.
"""
import os
import random
import shutil
import sys
import time

try:
    import psutil
except ImportError:
    psutil = None

# ---- palette ---------------------------------------------------------------
PEACH  = (255, 153, 102)
ORANGE = (255, 170, 0)
LAV    = (204, 153, 204)
GOLD   = (255, 204, 153)
BLUE   = (153, 153, 255)
SALMON = (204, 102, 102)
DIM    = (55, 55, 75)        # empty part of gauges
FAINT  = (110, 110, 170)     # background number clutter
TEXT   = (255, 204, 153)

RESET = "\x1b[0m"


def paint(text, rgb):
    r, g, b = rgb
    return f"\x1b[38;2;{r};{g};{b}m{text}{RESET}"


# ---- data sources ----------------------------------------------------------
class Walk:
    """Smoothly wandering value, used when real data isn't available."""

    def __init__(self, start):
        self.v = start

    def __call__(self):
        self.v = min(97, max(3, self.v + random.uniform(-7, 7)))
        return self.v


ROOT = os.path.abspath(os.sep)
_sim_cpu, _sim_mem, _sim_swap = Walk(35), Walk(55), Walk(15)


def read_metrics():
    disk = shutil.disk_usage(ROOT)
    disk_pct = disk.used / disk.total * 100
    if psutil:
        return [("CPU", psutil.cpu_percent(interval=None)),
                ("MEM", psutil.virtual_memory().percent),
                ("DISK", disk_pct),
                ("SWAP", psutil.swap_memory().percent)]
    return [("CPU", _sim_cpu()), ("MEM", _sim_mem()),
            ("DISK", disk_pct), ("SWAP", _sim_swap())]


# ---- drawing pieces --------------------------------------------------------
def bar(W, top):
    """Top or bottom frame bar, 1.5 rows thick, with a rounded elbow on the left."""
    s3 = 6
    s2 = max(8, W // 5)
    s1 = W - s2 - s3 - 4            # 4 = two 2-char gaps
    gap = "  "
    if top:
        c1, c2, c3 = PEACH, LAV, BLUE
        return [
            paint(" ▄" + "█" * (s1 - 2), c1) + gap + paint("█" * s2, c2) + gap + paint("█" * s3, c3),
            paint("████" + "▀" * (s1 - 4), c1) + gap + paint("▀" * s2, c2) + gap + paint("▀" * s3, c3),
        ]
    c1, c2, c3 = SALMON, GOLD, ORANGE
    return [
        paint("████" + "▄" * (s1 - 4), c1) + gap + paint("▄" * s2, c2) + gap + paint("▄" * s3, c3),
        paint(" ▀" + "█" * (s1 - 2), c1) + gap + paint("█" * s2, c2) + gap + paint("█" * s3, c3),
    ]


# Left sidebar: (rows, colour). Rows must add up to the number of content lines.
SIDEBAR = [(2, PEACH), (4, LAV), (3, GOLD), (2, SALMON)]


def sidebar_cells():
    cells = []
    for i, (n, rgb) in enumerate(SIDEBAR):
        for j in range(n):
            ch = "████"
            if j == 0 and i > 0:
                ch = "▄▄▄▄"                     # half-height start = gap above
            if j == n - 1 and i < len(SIDEBAR) - 1:
                ch = "▀▀▀▀"                     # half-height end = gap below
            cells.append(paint(ch, rgb))
    return cells


def gauge(pct, width, rgb):
    filled = round(width * pct / 100)
    return (paint("▐", rgb)
            + paint("█" * filled, rgb)
            + paint("█" * (width - filled), DIM)
            + paint("▌", rgb if filled == width else DIM))


def content(W, frame, metrics):
    inner = W - 7                                # right of sidebar (4) + padding (3)
    lines = []

    title = "SYSTEM MONITOR"
    right = f"{time.strftime('%H:%M:%S')}  REF {frame % 100:02d}-{(frame * 37) % 10000:04d}"
    lines.append(paint(title, ORANGE)
                 + " " * max(1, inner - len(title) - len(right))
                 + paint(right, TEXT))
    lines.append("")

    g = max(10, inner - 14)                      # label 6 + caps 2 + "  NNN%" 6
    for (label, pct), rgb in zip(metrics, [PEACH, LAV, GOLD, BLUE]):
        lines.append(paint(f"{label:<6}", TEXT) + gauge(pct, g, rgb)
                     + paint(f"  {pct:3.0f}%", TEXT))
    lines.append("")

    # Tiny "data" clutter, refreshed every few frames so it ticks rather than flickers.
    rng = random.Random(frame // 4)
    for colour in (BLUE, FAINT):
        s = ""
        while len(s) + 8 <= inner:
            s += f"{rng.randint(0, 99):02d}-{rng.randint(0, 9999):04d} "
        lines.append(paint(s.rstrip(), colour))
    lines.append("")

    if psutil:
        lines.append(paint("LIVE", GOLD))
    else:
        lines.append(paint("CPU / MEM / SWAP SIMULATED - pip install psutil", SALMON))
    return lines


def render(frame):
    cols = shutil.get_terminal_size((80, 24)).columns
    W = max(50, min(cols - 1, 100))
    out = bar(W, top=True)
    for side, line in zip(sidebar_cells(), content(W, frame, read_metrics())):
        out.append(side + "   " + line)
    out += bar(W, top=False)
    # cursor home, clear each line's tail, clear anything left below
    return "\x1b[H" + "\x1b[K\n".join(out) + "\x1b[K\x1b[J"


def main():
    if os.name == "nt":
        os.system("")                            # enable ANSI escapes in older Windows consoles
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write("\x1b[?1049h\x1b[?25l")     # alternate screen, hide cursor
    if psutil:
        psutil.cpu_percent(interval=None)        # prime the first CPU reading
    frame = 0
    try:
        while True:
            sys.stdout.write(render(frame))
            sys.stdout.flush()
            frame += 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + "\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
