"""Build the README's Nord-font SVGs.

GitHub READMEs can't load custom fonts, so every piece of text is converted
into vector shapes. Edit the TEXT section and rerun:

    pip install fonttools
    python make_nord_svgs.py --fonts ./fonts --out ./assets
"""
import argparse
import os

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# ---------------------------------------------------------------- TEXT
NAME = "Doms"
SUBTITLE = "Software developer from the Philippines"
TAGLINES = [
    "Web apps with ASP.NET MVC and Laravel",
    "Interfaces with React",
    "Cross-platform mobile with Flutter",
]
TITLES = {
    "title-tech-stack": "Tech stack",
    "title-github-stats": "GitHub stats",
    "title-contributions": "Contributions",
}
LABELS = {
    "label-languages": "Languages",
    "label-frameworks": "Frameworks and libraries",
    "label-tools": "Tools",
}

# ---------------------------------------------------------------- COLORS
TEAL, BLUE, NAVY = "#2DD4BF", "#60A5FA", "#111A2E"
THEMES = {
    # GitHub's own text colors, so the images sit naturally on each theme
    "dark": {"text": "#E6EDF3", "muted": "#9198A1", "accent": "#2DD4BF"},
    "light": {"text": "#1F2328", "muted": "#59636E", "accent": "#0F766E"},
}


class Face:
    """One font file: glyph outlines, advances and GPOS pair kerning."""

    def __init__(self, path):
        self.font = TTFont(path)
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]
        self.kern_lookups = self._kern_subtables()

    def _kern_subtables(self):
        if "GPOS" not in self.font:
            return []
        gpos = self.font["GPOS"].table
        idx = set()
        for rec in gpos.FeatureList.FeatureRecord:
            if rec.FeatureTag == "kern":
                idx.update(rec.Feature.LookupListIndex)
        lookups = []
        for i in sorted(idx):
            lk = gpos.LookupList.Lookup[i]
            subs = []
            for st in lk.SubTable:
                if lk.LookupType == 9:
                    if st.ExtensionLookupType != 2:
                        continue
                    st = st.ExtSubTable
                elif lk.LookupType != 2:
                    continue
                subs.append(st)
            if subs:
                lookups.append(subs)
        return lookups

    def kern(self, left, right):
        total = 0
        for subs in self.kern_lookups:
            for st in subs:
                cov = st.Coverage.glyphs
                if left not in cov:
                    continue
                if st.Format == 1:
                    ps = st.PairSet[cov.index(left)]
                    hit = next((r for r in ps.PairValueRecord if r.SecondGlyph == right), None)
                    if hit is None:
                        continue
                    v = hit.Value1
                else:
                    c1 = st.ClassDef1.classDefs.get(left, 0)
                    c2 = st.ClassDef2.classDefs.get(right, 0)
                    v = st.Class1Record[c1].Class2Record[c2].Value1
                total += getattr(v, "XAdvance", 0) or 0 if v else 0
                break  # first matching subtable wins within a lookup
        return total

    def glyph_names(self, text):
        return [self.cmap.get(ord(ch), ".notdef") for ch in text]

    def layout(self, text, size, tracking_em=0.0):
        """Return [(glyph, x)] in pixels and total width."""
        s = size / self.upm
        names = self.glyph_names(text)
        out, x = [], 0.0
        for i, g in enumerate(names):
            out.append((g, x))
            x += self.hmtx[g][0] * s
            if i < len(names) - 1:
                x += self.kern(g, names[i + 1]) * s + tracking_em * size
        return out, x

    def path(self, text, size, x0, baseline, tracking_em=0.0, anchor="start"):
        placed, width = self.layout(text, size, tracking_em)
        if anchor == "middle":
            x0 -= width / 2
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        for g, x in placed:
            tp = TransformPen(pen, (s, 0, 0, -s, x0 + x, baseline))
            self.glyphs[g].draw(tp)
        return pen.getCommands(), width

    def vmetrics(self, size):
        """Visible top/bottom of the font's caps and descenders, in px."""
        s = size / self.upm
        top, bot = 0, 0
        for ch in "HÉbdfhklO0":
            g = self.cmap.get(ord(ch))
            if not g:
                continue
            bp = BoundsPen(self.glyphs)
            self.glyphs[g].draw(bp)
            if bp.bounds:
                top = max(top, bp.bounds[3])
        for ch in "gjpqy,Q":
            g = self.cmap.get(ord(ch))
            if not g:
                continue
            bp = BoundsPen(self.glyphs)
            self.glyphs[g].draw(bp)
            if bp.bounds:
                bot = min(bot, bp.bounds[1])
        return top * s, -bot * s


def svg(w, h, body, title, style=""):
    style_block = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {w:.2f} {h:.2f}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{style_block}{body}</svg>\n"
    )


def text_svg(face, text, size, tracking, color, pad_x=2, pad_y=3):
    top, bot = face.vmetrics(size)
    h = top + bot + pad_y * 2
    d, w = face.path(text, size, pad_x, pad_y + top, tracking)
    return svg(w + pad_x * 2, h, f'<path fill="{color}" d="{d}"/>', text)


def header_svg(black, book):
    W, H = 1200, 256
    wave = (
        f"M0 0H{W}V196"
        "C1080 236 960 250 820 222"
        "C680 194 560 160 410 190"
        "C270 218 120 246 0 206Z"
    )
    name_d, _ = black.path(NAME, 104, W / 2, 128, 0.06, anchor="middle")
    sub_d, _ = book.path(SUBTITLE, 19, W / 2, 172, 0.16, anchor="middle")
    body = (
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{TEAL}"/><stop offset="1" stop-color="{BLUE}"/>'
        "</linearGradient></defs>"
        f'<path fill="url(#g)" d="{wave}"/>'
        f'<path fill="{NAVY}" d="{name_d}"/>'
        f'<path fill="{NAVY}" fill-opacity=".82" d="{sub_d}"/>'
    )
    return svg(W, H, body, f"{NAME}, {SUBTITLE.lower()}")


def tagline_svg(face, color):
    size, tracking = 15, 0.12
    top, bot = face.vmetrics(size)
    widths = [face.layout(t, size, tracking)[1] for t in TAGLINES]
    W, H = max(widths) + 8, top + bot + 8
    n, step = len(TAGLINES), 3.2
    total = n * step
    on = step / total * 100
    fade = 0.35 / total * 100
    style = (
        f".l{{opacity:0;animation:cycle {total:.1f}s infinite}}"
        f"@keyframes cycle{{0%{{opacity:0}}{fade:.2f}%{{opacity:1}}"
        f"{on - fade:.2f}%{{opacity:1}}{on:.2f}%,100%{{opacity:0}}}}"
        + "".join(f".l{i}{{animation-delay:{i * step:.1f}s}}" for i in range(n))
        + "@media (prefers-reduced-motion:reduce){.l{animation:none}.l0{opacity:1}}"
    )
    paths = "".join(
        f'<path class="l l{i}" fill="{color}" d="{face.path(t, size, W / 2, 4 + top, tracking, "middle")[0]}"/>'
        for i, t in enumerate(TAGLINES)
    )
    return svg(W, H, paths, " / ".join(TAGLINES), style)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", default="./fonts")
    ap.add_argument("--out", default="./assets")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    f = lambda n: Face(os.path.join(a.fonts, f"Nord-{n}.ttf"))
    black, bold, book, regular = f("Black"), f("Bold"), f("Book"), f("Regular")

    files = {"header.svg": header_svg(black, book)}
    for theme, c in THEMES.items():
        files[f"tagline-{theme}.svg"] = tagline_svg(book, c["accent"])
        for key, text in TITLES.items():
            files[f"{key}-{theme}.svg"] = text_svg(bold, text, 17, 0.16, c["text"])
        for key, text in LABELS.items():
            files[f"{key}-{theme}.svg"] = text_svg(regular, text, 11, 0.2, c["muted"])

    for name, content in files.items():
        with open(os.path.join(a.out, name), "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"{name:34s} {len(content) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
