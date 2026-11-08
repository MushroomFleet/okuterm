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
