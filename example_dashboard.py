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
