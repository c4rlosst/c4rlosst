"""Converts a photo into the ASCII art used on the profile card.

Writes assets/ascii_data.json with a dark-theme version (light glyphs on dark)
and a light-theme version (dark ink on white), each with per-character colors.

Run:  python scripts/build_ascii.py path/to/photo.jpg
Then: python scripts/build_card.py
"""
import colorsys
import json
import pathlib
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

COLS, ROWS = 92, 57            # ~1.73:1 character cells, matches an ART_W x ART_H box of 333 x 358
RAMP = " .:-=+*#%@"           # light -> dense
LEVELS = 4                     # color quantization steps per channel
BACK_ROW, BACK_SLOPE = 29, 0.6  # line along the cat's back; the panel in the top-left corner is above it
LEFT_COLS, LEFT_SAT_MAX = 42, 0.45  # left part of the photo where the fur reads warmer
NECK_X, NECK_Y, NECK_SAT_MAX = (40, 66), 36, 0.5  # lower-right fur (chin and neck) above the hand
CHEEK_Y, CHEEK_SAT_MAX = (30, 50), 0.34             # right cheek, up to the edge of the hand
FILL_Y = 38                                          # from this row down, the body is filled edge to edge


def load(path):
    im = Image.open(path).convert("RGB")
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = im.filter(ImageFilter.UnsharpMask(radius=6, percent=120, threshold=2))
    return im.resize((COLS, ROWS), Image.LANCZOS)


def quant(v):
    step = 255 / (LEVELS - 1)
    return round(v / step) * step


def tint(rgb, theme, lum):
    """Mute the photo color so the art stays soft: desaturate, then set lightness for the theme."""
    r, g, b = (x / 255 for x in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s *= 0.55
    if theme == "dark":
        v = 0.55 + 0.45 * lum
    else:
        v = 0.12 + 0.38 * lum
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % tuple(int(quant(x * 255)) for x in (r, g, b))


def convert(im, theme, mask):
    px = im.load()
    lums = sorted((0.299 * px[x, y][0] + 0.587 * px[x, y][1] + 0.114 * px[x, y][2]) / 255
                  for y in range(ROWS) for x in range(COLS) if mask[y][x])
    lo, hi = lums[len(lums) // 50], lums[-len(lums) // 50]
    chars, colors = [], []
    for y in range(ROWS):
        row_c, row_k = "", []
        for x in range(COLS):
            rgb = px[x, y]
            lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
            if theme == "dark":
                tone = lum
            else:  # dark ink on white: stretch the cat's own tonal range so the fur keeps enough ink
                tone = 0.3 + 0.7 * (1 - min(1, max(0, (lum - lo) / (hi - lo))))
            idx = min(9, max(0, round((tone ** 1.15) * 9)))
            row_c += RAMP[idx]
            row_k.append(tint(rgb, theme, lum))
        chars.append(row_c)
        colors.append(row_k)
    return dict(chars=chars, colors=colors)


def cat_mask(path, sat_max=0.27):
    """True where the cell belongs to the cat: the gray fur is low-saturation, while the curtain, panel,
    table and hand are all strongly colored. Holes (eyes, tongue) are filled and only the biggest blob is kept."""
    im = Image.open(path).convert("RGB").resize((COLS * 4, ROWS * 4), Image.BOX)
    hsv = im.convert("HSV").resize((COLS, ROWS), Image.BOX)
    px = hsv.load()
    # the fur on the left is lit warmer than the face, so it needs a looser cutoff there (the gold table is far more saturated)
    def limit(x, y):
        if x < LEFT_COLS:
            return LEFT_SAT_MAX
        if NECK_X[0] <= x < NECK_X[1] and y >= NECK_Y:  # neck and chin: darker, warmer fur; the hand starts right of this
            return NECK_SAT_MAX
        if x >= NECK_X[1] and CHEEK_Y[0] <= y < CHEEK_Y[1]:  # right cheek, next to the hand (skin is more saturated)
            return CHEEK_SAT_MAX
        return sat_max

    on = [[px[x, y][1] / 255 < limit(x, y) and px[x, y][2] > 25 for x in range(COLS)] for y in range(ROWS)]
    # the gray-blue panel in the top-left corner is as unsaturated as the fur, so cut it out by position
    # (everything above a line that follows the cat's back: from row BACK_ROW at the left edge, rising by BACK_SLOPE per column)
    for y in range(ROWS):
        for x in range(COLS):
            if y < BACK_ROW - BACK_SLOPE * x:
                on[y][x] = False

    # drop thin, ragged bits along the edge: a cell stays only if enough of its 8 neighbors are also cat
    for _ in range(2):
        keep = [[on[y][x] and sum(on[ny][nx]
                                  for ny in range(max(0, y - 1), min(ROWS, y + 2))
                                  for nx in range(max(0, x - 1), min(COLS, x + 2))
                                  if (nx, ny) != (x, y)) >= 5
                 for x in range(COLS)] for y in range(ROWS)]
        on = keep

    def neighbors(x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS:
                yield nx, ny

    # biggest connected component of "cat" cells
    seen, best = set(), []
    for y in range(ROWS):
        for x in range(COLS):
            if on[y][x] and (x, y) not in seen:
                comp, stack = [], [(x, y)]
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    comp.append((cx, cy))
                    for n in neighbors(cx, cy):
                        if on[n[1]][n[0]] and n not in seen:
                            seen.add(n); stack.append(n)
                if len(comp) > len(best):
                    best = comp
    mask = [[False] * COLS for _ in range(ROWS)]
    for x, y in best:
        mask[y][x] = True
    # fill holes: anything not reachable from the border through non-mask cells is inside the cat
    outside, stack = set(), [(x, y) for y in range(ROWS) for x in range(COLS)
                              if (x in (0, COLS - 1) or y in (0, ROWS - 1)) and not mask[y][x]]
    outside.update(stack)
    while stack:
        cx, cy = stack.pop()
        for n in neighbors(cx, cy):
            if not mask[n[1]][n[0]] and n not in outside:
                outside.add(n); stack.append(n)
    for y in range(ROWS):
        for x in range(COLS):
            if (x, y) not in outside:
                mask[y][x] = True
    # the table edge cuts a diagonal through the cat's lower body; fill it so the body reaches the bottom edge
    for y in range(FILL_Y, ROWS):
        for x in range(COLS):
            mask[y][x] = True
    return mask


def main():
    im = load(sys.argv[1])
    mask = cat_mask(sys.argv[1])
    data = dict(cols=COLS, rows=ROWS, dark=convert(im, "dark", mask), light=convert(im, "light", mask))
    for theme in ("dark", "light"):
        d = data[theme]
        d["chars"] = ["".join(ch if mask[y][x] else " " for x, ch in enumerate(row)) for y, row in enumerate(d["chars"])]
    if "--mask" in sys.argv:
        print("\n".join("".join("#" if m else "." for m in row) for row in mask))
    (ASSETS / "ascii_data.json").write_text(json.dumps(data), encoding="utf8")
    print("wrote assets/ascii_data.json")


if __name__ == "__main__":
    main()


