#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Entry program for make.fun bounty the-passport-page-of-a-countr-2-20261121-0318.
Writes one 1024x1024 PNG of an invented passport spread for the
Republic of Nareen (a fictional tidal-delta republic) to /output/entry.png.

Pure Python 3.13 stdlib only: no network, no third-party packages.
The PNG encoder, the stroke font and every drawing are in this file.
"""
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- PNG writer
def write_png(path, rgb, w, h):
    """Write an RGB bytearray (w*h*3) as a PNG with no filtering."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(ctype, data):
        c = struct.pack(">I", len(data)) + ctype + data
        c += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ------------------------------------------------------------------- Canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set_px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = c

    def blend_px(self, x, y, c, a):
        """Blend colour c over the pixel with alpha a (0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            b = self.buf
            b[i] = int(b[i] * (1 - a) + c[0] * a)
            b[i + 1] = int(b[i + 1] * (1 - a) + c[1] * a)
            b[i + 2] = int(b[i + 2] * (1 - a) + c[2] * a)

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.w, int(x + w)), min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._idx(x0, yy)
            self.buf[i:i + len(row)] = row

    def hline(self, x0, x1, y, c, thick=1):
        for t in range(thick):
            self.fill_rect(x0, y + t - thick // 2, x1 - x0, 1, c)

    def vline(self, x, y0, y1, c, thick=1):
        for t in range(thick):
            self.fill_rect(x + t - thick // 2, y0, 1, y1 - y0, c)

    def line(self, x0, y0, x1, y1, c, thick=1):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        r = thick // 2
        while True:
            if thick <= 1:
                self.set_px(x0, y0, c)
            else:
                self.fill_circle(x0, y0, r, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def polyline(self, pts, c, thick=1, closed=False):
        n = len(pts)
        if n < 2:
            return
        for i in range(n - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, thick)
        if closed:
            self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], c, thick)

    def fill_circle(self, cx, cy, r, c):
        cx, cy, r = int(round(cx)), int(round(cy)), int(round(r))
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (yy - cy) ** 2)))
            self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, c)

    def circle(self, cx, cy, r, c, thick=1):
        steps = max(24, int(2 * math.pi * r))
        pts = [(cx + r * math.cos(2 * math.pi * i / steps),
                cy + r * math.sin(2 * math.pi * i / steps)) for i in range(steps)]
        self.polyline(pts, c, thick, closed=True)

    def fill_ellipse(self, cx, cy, rx, ry, c):
        for yy in range(int(cy - ry), int(cy + ry) + 1):
            t = (yy - cy) / ry if ry else 0
            if abs(t) > 1:
                continue
            dx = int(rx * math.sqrt(1 - t * t))
            self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, c)

    def fill_poly(self, pts, c):
        """Scanline polygon fill (pts: list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(math.ceil(min(ys))), int(math.floor(max(ys)))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0) if yy1 != yy0 else 0
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[i]), y, int(xs[i + 1]) - int(xs[i]) + 1, 1, c)

    def wave(self, x0, x1, ybase, amp, period, c, thick=1, phase=0.0):
        pts = []
        x = x0
        while x <= x1:
            pts.append((x, ybase + amp * math.sin(2 * math.pi * (x - x0) / period + phase)))
            x += 4
        self.polyline(pts, c, thick)

    def arc(self, cx, cy, r, a0, a1, c, thick=1):
        steps = max(8, int(abs(a1 - a0) * r / 6))
        pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
                cy + r * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]
        self.polyline(pts, c, thick)

# ------------------------------------------------------------- Stroke font
# Single-stroke lettering on a 6-wide x 10-tall grid, y down, cap top = 0.
# Each glyph is a list of polylines; a 1-point polyline draws a dot.
FONT = {
    "A": [[(0, 9), (2.5, 0), (5, 9)], [(1.3, 6), (3.7, 6)]],
    "B": [[(0, 0), (0, 9)], [(0, 0), (3.2, 0), (4.8, 1.8), (3.2, 4.5), (0, 4.5)],
          [(0, 4.5), (3.2, 4.5), (4.8, 7.2), (3.2, 9), (0, 9)]],
    "C": [[(5, 2), (3.5, 0), (1.2, 0), (0, 2), (0, 7), (1.2, 9), (3.5, 9), (5, 7)]],
    "D": [[(0, 0), (0, 9)], [(0, 0), (3.2, 0), (5, 2.5), (5, 6.5), (3.2, 9), (0, 9)]],
    "E": [[(0, 0), (0, 9)], [(0, 0), (5, 0)], [(0, 4.5), (3.5, 4.5)], [(0, 9), (5, 9)]],
    "F": [[(0, 0), (0, 9)], [(0, 0), (5, 0)], [(0, 4.5), (3.5, 4.5)]],
    "G": [[(5, 2), (3.5, 0), (1.2, 0), (0, 2), (0, 7), (1.2, 9), (3.5, 9), (5, 7), (5, 4.5), (3, 4.5)]],
    "H": [[(0, 0), (0, 9)], [(5, 0), (5, 9)], [(0, 4.5), (5, 4.5)]],
    "I": [[(0.5, 0), (4.5, 0)], [(2.5, 0), (2.5, 9)], [(0.5, 9), (4.5, 9)]],
    "J": [[(5, 0), (5, 7), (3.5, 9), (1, 9), (0, 7)]],
    "K": [[(0, 0), (0, 9)], [(5, 0), (0, 4.5), (5, 9)]],
    "L": [[(0, 0), (0, 9)], [(0, 9), (5, 9)]],
    "M": [[(0, 9), (0, 0), (2.5, 5), (5, 0), (5, 9)]],
    "N": [[(0, 9), (0, 0), (5, 9), (5, 0)]],
    "O": [[(1.2, 0), (3.8, 0), (5, 2), (5, 7), (3.8, 9), (1.2, 9), (0, 7), (0, 2), (1.2, 0)]],
    "P": [[(0, 0), (0, 9)], [(0, 0), (3.2, 0), (5, 2), (3.2, 4.5), (0, 4.5)]],
    "Q": [[(1.2, 0), (3.8, 0), (5, 2), (5, 7), (3.8, 9), (1.2, 9), (0, 7), (0, 2), (1.2, 0)],
          [(3, 6), (5, 9)]],
    "R": [[(0, 0), (0, 9)], [(0, 0), (3.2, 0), (5, 2), (3.2, 4.5), (0, 4.5)], [(3.2, 4.5), (5, 9)]],
    "S": [[(5, 2), (4, 0), (1, 0), (0, 2), (0, 4), (1.5, 5), (3.5, 5), (5, 6), (5, 8), (4, 9), (1, 9), (0, 7)]],
    "T": [[(0, 0), (5, 0)], [(2.5, 0), (2.5, 9)]],
    "U": [[(0, 0), (0, 7), (1.2, 9), (3.8, 9), (5, 7), (5, 0)]],
    "V": [[(0, 0), (2.5, 9), (5, 0)]],
    "W": [[(0, 0), (1.2, 9), (2.5, 5), (3.8, 9), (5, 0)]],
    "X": [[(0, 0), (5, 9)], [(5, 0), (0, 9)]],
    "Y": [[(0, 0), (2.5, 4.5), (5, 0)], [(2.5, 4.5), (2.5, 9)]],
    "Z": [[(0, 0), (5, 0), (0, 9), (5, 9)]],
    "0": [[(1.2, 0), (3.8, 0), (5, 2), (5, 7), (3.8, 9), (1.2, 9), (0, 7), (0, 2), (1.2, 0)],
          [(4, 1), (1, 8)]],
    "1": [[(1, 2), (2.5, 0), (2.5, 9)], [(0.5, 9), (4.5, 9)]],
    "2": [[(0, 2), (1, 0), (4, 0), (5, 2), (5, 4), (0, 9), (5, 9)]],
    "3": [[(0, 1), (1, 0), (4, 0), (5, 2), (4, 4.5), (5, 5), (5, 8), (4, 9), (1, 9), (0, 8)]],
    "4": [[(0, 6), (3.5, 0), (3.5, 9)], [(0, 6), (5, 6)]],
    "5": [[(5, 0), (0, 0), (0, 4.5), (3.5, 4.5), (5, 6), (5, 8), (4, 9), (1, 9), (0, 7)]],
    "6": [[(5, 1), (4, 0), (1, 0), (0, 2), (0, 7), (1, 9), (4, 9), (5, 7), (5, 5), (4, 4), (1, 4), (0, 5)]],
    "7": [[(0, 0), (5, 0), (2, 9)]],
    "8": [[(1, 0), (4, 0), (5, 2), (4, 4.5), (1, 4.5), (0, 2), (1, 0)],
          [(1, 4.5), (4, 4.5), (5, 6.5), (4, 9), (1, 9), (0, 6.5), (1, 4.5)]],
    "9": [[(5, 9), (5, 2), (4, 0), (1, 0), (0, 2), (0, 4), (1, 5), (4, 5)]],
    " ": [],
    ".": [[(2.3, 8.3)]],
    ",": [[(2.3, 8.0)], [(2.3, 8.6), (1.6, 10)]],
    "-": [[(0.5, 4.5), (4.5, 4.5)]],
    "/": [[(4.5, 0), (0.5, 9)]],
    "(": [[(4, 0), (2, 2.5), (2, 6.5), (4, 9)]],
    ")": [[(1, 0), (3, 2.5), (3, 6.5), (1, 9)]],
    "<": [[(4.5, 1), (1, 4.5), (4.5, 8)]],
    ":": [[(2.5, 2.3)], [(2.5, 6.8)]],
    "'": [[(2.2, 0), (2.8, 2)]],
    "+": [[(2.5, 2), (2.5, 7)], [(0.5, 4.5), (4.5, 4.5)]],
    "=": [[(0.5, 3), (4.5, 3)], [(0.5, 6), (4.5, 6)]],
    "!": [[(2.5, 0), (2.5, 6.5)], [(2.5, 8.3)]],
    "?": [[(1, 0), (4, 0), (5, 2), (4, 4.5), (2.5, 4.5), (2.5, 6)], [(2.5, 8.3)]],
    "*": [[(2.5, 1), (2.5, 8)], [(0.5, 3), (4.5, 6)], [(4.5, 3), (0.5, 6)]],
}


def text_width(text, scale, spacing=1.0):
    return len(text) * 6.6 * scale * spacing


def draw_text(cv, x, y, text, scale, color, weight=1, align="left", spacing=1.0,
              rotate=0.0, cx=0.0, cy=0.0):
    """Draw stroke text. (x, y) is the top-left of the cap height.
    rotate is in degrees around (cx, cy); used for stamp text."""
    if align == "center":
        x -= text_width(text, scale, spacing) / 2
    elif align == "right":
        x -= text_width(text, scale, spacing)
    th = max(1, int(round(scale * 0.42))) if weight == 1 else max(1, int(round(scale * 0.62)))
    rad = math.radians(rotate)
    cosr, sinr = math.cos(rad), math.sin(rad)

    def map_pt(px, py):
        px = x + px
        py = y + py
        if rotate:
            px -= cx
            py -= cy
            px, py = px * cosr - py * sinr, px * sinr + py * cosr
            px += cx
            py += cy
        return px, py

    for ch in text:
        glyph = FONT.get(ch.upper(), FONT.get(ch, []))
        for stroke in glyph:
            if len(stroke) == 1:
                px, py = map_pt(stroke[0][0] * scale, stroke[0][1] * scale)
                cv.fill_circle(px, py, max(1, th // 2 + 0.5), color)
                continue
            pts = [map_pt(px * scale, py * scale) for px, py in stroke]
            cv.polyline(pts, color, th)
        x += 6.6 * scale * spacing


# ------------------------------------------------------------ MRZ check digit
def mrz_check(s):
    """ICAO 9303 check digit: values 0-9 as digits, A=10..Z=35, '<'=0,
    weights 7,3,1 repeating."""
    total = 0
    for i, ch in enumerate(s):
        if ch == "<":
            v = 0
        elif ch.isdigit():
            v = int(ch)
        else:
            v = ord(ch) - 55
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def build_mrz():
    """Two 44-char MRZ lines for the Nareen passport (ICAO 9303)."""
    line1 = "P<NARSOLENNE<<MIRA<ANOUK"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "NR482917<"                      # 9 chars: number + filler
    doc_cd = mrz_check(doc)
    nat = "NAR"
    dob = "880314"                          # 14 MAR 1988
    dob_cd = mrz_check(dob)
    sex = "F"
    exp = "340501"                          # 01 MAY 2034
    exp_cd = mrz_check(exp)
    opt = "<" * 15                          # optional data, 15 chars
    # Composite check digit (ICAO 9303): over document number + its check,
    # date of birth + its check, date of expiry + its check, optional data.
    composite = doc + doc_cd + dob + dob_cd + exp + exp_cd + opt
    line2 = doc + doc_cd + nat + dob + dob_cd + sex + exp + exp_cd + opt
    line2 = line2 + mrz_check(composite)
    assert len(line1) == 44 and len(line2) == 44, (len(line1), len(line2))
    return line1, line2

# ------------------------------------------------------------ Drawing helpers
def draw_heron_emblem(cv, cx, cy, r, ink):
    """Coat of arms of Nareen: a heron standing in tidal waves, in a ring."""
    cv.circle(cx, cy, r, ink, 3)
    cv.circle(cx, cy, r - 5, ink, 1)
    # waves at the bottom
    for dy, rr in ((r * 0.42, r * 0.62), (r * 0.60, r * 0.42), (r * 0.76, r * 0.20)):
        cv.wave(cx - rr, cx + rr, cy + dy, 3, 16, ink, 2)
    # heron body (flat, side view facing left)
    bx, by = cx + r * 0.05, cy - r * 0.08
    cv.fill_ellipse(bx, by, r * 0.30, r * 0.20, ink)
    # neck: S-curve up to the head
    cv.polyline([(bx - r * 0.18, by - r * 0.08), (bx - r * 0.30, by - r * 0.38),
                 (bx - r * 0.22, by - r * 0.62), (bx - r * 0.34, by - r * 0.72)],
                ink, 3)
    # head + beak
    cv.fill_circle(bx - r * 0.34, by - r * 0.72, r * 0.07, ink)
    cv.fill_poly([(bx - r * 0.40, by - r * 0.75), (bx - r * 0.72, by - r * 0.66),
                  (bx - r * 0.40, by - r * 0.68)], ink)
    # wing line
    cv.arc(bx, by, r * 0.20, math.pi * 0.15, math.pi * 0.85, ink, 2)
    # legs
    cv.line(bx - r * 0.06, by + r * 0.18, bx - r * 0.06, by + r * 0.42, ink, 2)
    cv.line(bx + r * 0.10, by + r * 0.18, bx + r * 0.14, by + r * 0.42, ink, 2)
    # three stars above
    for sx in (-r * 0.45, 0, r * 0.45):
        draw_text(cv, cx + sx, cy - r * 0.98, "*", 1.1, ink, weight=1, align="center")


def draw_portrait(cv, x, y, w, h):
    """Flat-illustration portrait of Mira Anouk Solenne, Ferry Master.
    Box (x, y, w, h); the figure is drawn in a pale blue-grey frame."""
    # frame background with faint guilloche arcs
    cv.fill_rect(x, y, w, h, (178, 190, 188))
    for rr in range(18, int(max(w, h) * 0.9), 16):
        cv.arc(x + w * 0.5, y + h * 1.05, rr, math.pi * 1.15, math.pi * 1.85, (150, 164, 162), 1)
    # shoulders / navy jacket
    cv.fill_poly([(x + w * 0.08, y + h), (x + w * 0.20, y + h * 0.78),
                  (x + w * 0.38, y + h * 0.72), (x + w * 0.62, y + h * 0.72),
                  (x + w * 0.80, y + h * 0.78), (x + w * 0.92, y + h)], (31, 58, 95))
    # white shirt V
    cv.fill_poly([(x + w * 0.44, y + h * 0.72), (x + w * 0.56, y + h * 0.72),
                  (x + w * 0.50, y + h * 0.90)], (240, 236, 224))
    # teal scarf band
    cv.fill_poly([(x + w * 0.36, y + h * 0.70), (x + w * 0.64, y + h * 0.70),
                  (x + w * 0.60, y + h * 0.80), (x + w * 0.40, y + h * 0.80)], (46, 125, 123))
    # brass buttons
    for by in (0.84, 0.93):
        cv.fill_circle(x + w * 0.50, y + h * by, 3, (198, 158, 74))
    # neck
    cv.fill_rect(x + w * 0.45, y + h * 0.60, w * 0.10, h * 0.13, (196, 150, 112))
    # face
    fx, fy = x + w * 0.50, y + h * 0.36
    cv.fill_ellipse(fx, fy, w * 0.155, h * 0.185, (217, 169, 134))
    # jaw shading
    cv.fill_ellipse(fx, fy + h * 0.10, w * 0.115, h * 0.085, (206, 158, 122))
    # hair: dark bun + side sweep
    cv.fill_ellipse(fx, fy - h * 0.13, w * 0.15, h * 0.09, (58, 42, 34))
    cv.fill_poly([(fx - w * 0.155, fy - h * 0.10), (fx - w * 0.15, fy + h * 0.06),
                  (fx - w * 0.10, fy - h * 0.02), (fx - w * 0.13, fy - h * 0.14)], (58, 42, 34))
    cv.fill_poly([(fx + w * 0.155, fy - h * 0.10), (fx + w * 0.15, fy + h * 0.06),
                  (fx + w * 0.10, fy - h * 0.02), (fx + w * 0.13, fy - h * 0.14)], (58, 42, 34))
    # ferry-master cap: navy band + brim + brass emblem
    cv.fill_poly([(fx - w * 0.17, fy - h * 0.135), (fx - w * 0.16, fy - h * 0.20),
                  (fx + w * 0.16, fy - h * 0.20), (fx + w * 0.17, fy - h * 0.135)], (31, 58, 95))
    cv.fill_ellipse(fx, fy - h * 0.20, w * 0.16, h * 0.035, (24, 46, 76))
    cv.fill_circle(fx, fy - h * 0.155, 4, (198, 158, 74))
    cv.fill_rect(fx - w * 0.17, fy - h * 0.135, w * 0.34, 3, (198, 158, 74))
    # eyes, brows, nose, mouth
    for ex in (-w * 0.062, w * 0.062):
        cv.fill_circle(fx + ex, fy - h * 0.005, 2.5, (40, 30, 26))
        cv.line(fx + ex - 7, fy - h * 0.05, fx + ex + 7, fy - h * 0.05, (58, 42, 34), 1)
    cv.line(fx + 1, fy + h * 0.01, fx - 2, fy + h * 0.07, (170, 120, 88), 2)
    cv.line(fx - 9, fy + h * 0.115, fx + 9, fy + h * 0.115, (150, 88, 70), 2)
    # cheek blush
    cv.fill_ellipse(fx - w * 0.10, fy + h * 0.06, 6, 4, (214, 140, 108))
    cv.fill_ellipse(fx + w * 0.10, fy + h * 0.06, 6, 4, (214, 140, 108))
    # thin inner border
    cv.fill_rect(x, y, w, 2, (31, 58, 95))
    cv.fill_rect(x, y + h - 2, w, 2, (31, 58, 95))
    cv.fill_rect(x, y, 2, h, (31, 58, 95))
    cv.fill_rect(x + w - 2, y, 2, h, (31, 58, 95))


def draw_stamp(cv, cx, cy, w, h, lines, ink, angle, scale=1.35, alpha=0.82):
    """A rotated rectangular ink stamp. lines: list of text lines (top first).
    The stamp is drawn with alpha blending so the paper shows through."""
    rad = math.radians(angle)
    cosr, sinr = math.cos(rad), math.sin(rad)

    def rot(px, py):
        return (cx + px * cosr - py * sinr, cy + px * sinr + py * cosr)

    hw, hh = w / 2.0, h / 2.0
    # border: draw as many short segments so alpha blends evenly
    corners = [rot(-hw, -hh), rot(hw, -hh), rot(hw, hh), rot(-hw, hh)]
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        steps = int(max(abs(x1 - x0), abs(y1 - y0)))
        for s in range(steps + 1):
            t = s / max(1, steps)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            for dy in (-1, 0, 1):
                cv.blend_px(int(px), int(py) + dy, ink, alpha)
    # inner border
    hw2, hh2 = hw - 7, hh - 7
    corners = [rot(-hw2, -hh2), rot(hw2, -hh2), rot(hw2, hh2), rot(-hw2, hh2)]
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        steps = int(max(abs(x1 - x0), abs(y1 - y0)))
        for s in range(steps + 1):
            t = s / max(1, steps)
            cv.blend_px(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), ink, alpha * 0.7)
    # text lines, centred on the stamp, rotated with it
    total_h = len(lines) * 13 * scale
    ty = cy - total_h / 2 + 2
    for ln in lines:
        tw = text_width(ln, scale)
        # draw each glyph via rotated placement: use draw_text with rotate
        draw_text(cv, cx - tw / 2, ty, ln, scale, ink, weight=1, spacing=1.0,
                  rotate=angle, cx=cx, cy=cy)
        ty += 13 * scale
    return


def draw_delta_map(cv, x, y, w, h):
    """Small map of the Lower Delta: tidal channels, stilt towns, Port Liora."""
    cv.fill_rect(x, y, w, h, (232, 226, 205))
    cv.fill_rect(x, y, w, 2, (31, 58, 95))
    cv.fill_rect(x, y + h - 2, w, 2, (31, 58, 95))
    cv.fill_rect(x, y, 2, h, (31, 58, 95))
    cv.fill_rect(x + w - 2, y, 2, h, (31, 58, 95))
    # sea (left) and land (right) wash
    cv.fill_poly([(x, y), (x + w * 0.30, y), (x + w * 0.22, y + h), (x, y + h)], (196, 210, 205))
    # main river channel: wavy vertical band
    river = []
    for yy in range(0, h + 1, 6):
        river.append((x + w * 0.42 + 14 * math.sin(yy / 34.0), y + yy))
    cv.polyline(river, (120, 158, 168), 7)
    # side channels
    for ph, amp in ((0.0, 10), (2.1, 8)):
        pts = []
        for xx in range(0, int(w * 0.55) + 1, 6):
            pts.append((x + xx, y + h * 0.62 + amp * math.sin(xx / 26.0 + ph)))
        cv.polyline(pts, (120, 158, 168), 4)
    # towns: dots + labels
    towns = [("PORT LIORA", 0.42, 0.30, True), ("STILT ROW", 0.60, 0.52, False),
             ("HERON FLATS", 0.72, 0.22, False), ("LOW TIDE", 0.55, 0.80, False)]
    for name, fx, fy, star in towns:
        tx, ty = x + w * fx, y + h * fy
        if star:
            draw_text(cv, tx, ty - 8, "*", 2.2, (150, 40, 30), align="center")
            cv.fill_circle(tx, ty, 4, (150, 40, 30))
        else:
            cv.fill_circle(tx, ty, 3, (31, 58, 95))
        draw_text(cv, tx + 9, ty - 5, name, 1.15, (31, 58, 95))
    # north arrow + scale bar
    draw_text(cv, x + w - 34, y + 10, "N", 1.6, (31, 58, 95))
    cv.line(x + w - 28, y + 26, x + w - 28, y + 44, (31, 58, 95), 2)
    cv.polyline([(x + w - 33, y + 32), (x + w - 28, y + 24), (x + w - 23, y + 32)], (31, 58, 95), 2)
    cv.fill_rect(x + 14, y + h - 16, 60, 3, (31, 58, 95))
    draw_text(cv, x + 14, y + h - 30, "0  5 KM", 1.0, (31, 58, 95))

# ------------------------------------------------------------------ Layout
NAVY = (31, 58, 95)
TEAL = (34, 96, 110)
INK = (38, 52, 66)
PAPER = (244, 236, 217)
GOLD = (198, 158, 74)
FAINT = (226, 216, 190)


def field(cv, x, y, label, value, lscale=1.15, vscale=1.85, lcolor=(96, 108, 104)):
    draw_text(cv, x, y, label, lscale, lcolor)
    draw_text(cv, x, y + 14, value, vscale, INK)


def build_page():
    cv = Canvas(W, H, NAVY)
    cv.fill_rect(10, 10, W - 20, H - 20, PAPER)
    # faint guilloche waves across the spread
    for yy in range(60, H - 40, 46):
        cv.wave(24, W - 24, yy, 5, 90, FAINT, 1, phase=yy * 0.13)
    # centre gutter shadow
    cv.fill_rect(508, 10, 8, H - 20, (198, 186, 158))
    cv.vline(506, 10, H - 10, (150, 138, 112), 2)
    cv.vline(518, 10, H - 10, (150, 138, 112), 2)
    # page borders (double rule)
    for (bx0, bx1) in ((24, 500), (524, 1000)):
        cv.fill_rect(bx0, 24, bx1 - bx0, 2, NAVY)
        cv.fill_rect(bx0, H - 26, bx1 - bx0, 2, NAVY)
        cv.fill_rect(bx0, 24, 2, H - 48, NAVY)
        cv.fill_rect(bx1 - 2, 24, 2, H - 48, NAVY)
        cv.fill_rect(bx0 + 6, 30, bx1 - bx0 - 12, 1, NAVY)
        cv.fill_rect(bx0 + 6, H - 32, bx1 - bx0 - 12, 1, NAVY)
        cv.fill_rect(bx0 + 6, 30, 1, H - 60, NAVY)
        cv.fill_rect(bx1 - 7, 30, 1, H - 60, NAVY)

    # ---------------------------------------------------------- left page
    cx = 262
    draw_text(cv, cx, 44, "REPUBLIC OF NAREEN", 3.2, NAVY, weight=2, align="center")
    draw_text(cv, cx, 86, "PASSPORT - PASSEPORT", 1.5, TEAL, align="center")
    draw_heron_emblem(cv, cx, 158, 34, TEAL)
    cv.hline(48, 476, 212, NAVY, 2)
    # type / code / number row
    field(cv, 48, 228, "TYPE", "P")
    field(cv, 150, 228, "CODE", "NAR")
    field(cv, 300, 228, "PASSPORT NO.", "NR 482 917")
    # portrait
    draw_portrait(cv, 48, 292, 160, 220)
    # data fields
    rows = [("SURNAME", "SOLENNE"), ("GIVEN NAMES", "MIRA ANOUK"),
            ("NATIONALITY", "NAREENI"), ("DATE OF BIRTH", "14 MAR 1988"),
            ("PLACE OF BIRTH", "PORT LIORA"), ("SEX", "F")]
    for i, (lab, val) in enumerate(rows):
        field(cv, 228, 296 + i * 36, lab, val)
    # registry stamp overlapping the portrait's lower corner only
    draw_stamp(cv, 128, 480, 132, 58,
               ["DELTA REGISTRY", "PORT LIORA", "02 MAY 2024"],
               TEAL, -12, scale=1.15)
    # issue block
    field(cv, 48, 540, "DATE OF ISSUE", "02 MAY 2024")
    field(cv, 280, 540, "DATE OF EXPIRY", "01 MAY 2034")
    field(cv, 48, 600, "AUTHORITY", "DELTA REGISTRY - PORT LIORA")
    # ferryman's endorsement box
    cv.fill_rect(48, 648, 428, 94, (250, 244, 228))
    cv.fill_rect(48, 648, 428, 2, NAVY)
    cv.fill_rect(48, 740, 428, 2, NAVY)
    cv.fill_rect(48, 648, 2, 94, NAVY)
    cv.fill_rect(474, 648, 2, 94, NAVY)
    draw_text(cv, cx, 660, "FERRYMAN'S ENDORSEMENT", 1.5, NAVY, align="center")
    draw_text(cv, cx, 688, "HOLDER MAY PILOT REGISTERED", 1.4, INK, align="center")
    draw_text(cv, cx, 710, "FERRIES IN THE LOWER DELTA", 1.4, INK, align="center")
    # machine-readable zone
    cv.fill_rect(48, 766, 428, 70, (255, 255, 255))
    line1, line2 = build_mrz()
    draw_text(cv, 56, 778, line1, 1.45, (20, 20, 20))
    draw_text(cv, 56, 802, line2, 1.45, (20, 20, 20))
    draw_text(cv, cx, 872, "THIS PASSPORT REMAINS THE PROPERTY OF THE REPUBLIC OF NAREEN",
              1.0, (96, 108, 104), align="center")

    # --------------------------------------------------------- right page
    cx2 = 762
    # faint watermark emblem behind the stamps
    draw_heron_emblem(cv, cx2, 480, 170, (232, 224, 204))
    draw_text(cv, cx2, 44, "VISAS", 3.0, NAVY, weight=2, align="center")
    draw_text(cv, cx2, 82, "ARRIVALS AND DEPARTURES", 1.5, TEAL, align="center")
    cv.hline(548, 976, 112, NAVY, 2)
    draw_stamp(cv, 648, 205, 200, 92,
               ["KAVARRA", "ENTRY 18 JUN 2024", "EXIT 24 JUN 2024"],
               (38, 84, 160), -8, scale=1.3)
    draw_stamp(cv, 876, 205, 200, 92,
               ["OSTRELL", "ENTRY 09 SEP 2024", "EXIT 16 SEP 2024"],
               (96, 58, 140), 6, scale=1.3)
    draw_stamp(cv, 648, 345, 200, 92,
               ["THALVOR", "ARRIVAL 22 JAN 2025", "DEPARTURE 30 JAN 2025"],
               (34, 110, 70), -5, scale=1.3)
    draw_stamp(cv, 876, 345, 200, 92,
               ["MERIDIA", "FREE PORT", "ENTRY 11 MAY 2025"],
               (150, 60, 40), 7, scale=1.3)
    draw_stamp(cv, cx2, 478, 320, 80,
               ["TIDAL TRANSIT", "FEE PAID 40 LIR", "11 MAY 2025"],
               (30, 90, 60), 0, scale=1.35)
    draw_text(cv, cx2, 548, "THE LOWER DELTA", 1.6, NAVY, align="center")
    draw_delta_map(cv, 548, 576, 428, 300)
    draw_text(cv, cx2, 920, "HOLDER'S OCCUPATION: FERRY MASTER - LOWER DELTA",
              1.3, INK, align="center")
    draw_text(cv, cx2, 952, "NAREENI - ENGLISH", 1.1, (96, 108, 104), align="center")
    return cv


def main():
    cv = build_page()
    out = "/output/entry.png"
    try:
        os.makedirs("/output", exist_ok=True)
        with open("/output/.write-test", "wb") as f:
            f.write(b"")
        os.remove("/output/.write-test")
    except OSError:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    size = write_png(out, cv.buf, W, H)
    print("wrote", out)
    print("dimensions: %dx%d" % (W, H))
    print("bytes:", size, "(limit 1048576)")
    line1, line2 = build_mrz()
    print("MRZ line 1:", line1)
    print("MRZ line 2:", line2)
    if size > 1048576:
        print("ERROR: over the 1 MiB gate")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
