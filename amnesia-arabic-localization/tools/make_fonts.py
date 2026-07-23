#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_fonts.py — Generate HPL2-compatible AngelCode bitmap fonts (fonts/ara)
containing Latin + Arabic Presentation Forms-B glyphs.

Creates: menu.fnt, game_header.fnt, game_default.fnt, game_hints.fnt, game_journal.fnt
Each .fnt keeps the filename the engine expects; page textures get unique
'ara_*.tga' names to avoid clashing with fonts/eng textures.

Usage: python3 make_fonts.py --ttf /path/to/ArabicFont.ttf --out fonts/ara
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont

# glyph set: printable ASCII + Arabic punctuation + Presentation Forms-B + lam-alef
CODEPOINTS = (list(range(32, 127))
              + [0x060C, 0x061B, 0x061F, 0x0640]
              + [c for c in range(0xFE70, 0xFEFD) if c != 0xFE75])

FONTS = {  # name -> pixel size
    'menu.fnt': 44,
    'game_header.fnt': 44,
    'game_default.fnt': 30,
    'game_hints.fnt': 30,
    'game_journal.fnt': 30,
}
# The gui skin and LuxBase load 'font_default.fnt' by hardcoded name; if it can't
# be resolved the game crashes with a NULL font at the first pre-menu screen.
# Written as a copy of game_default.fnt sharing its page texture.
FONT_ALIASES = {'font_default.fnt': 'game_default.fnt'}
PAGE_W = PAGE_H = 1024
PAD = 2

def build_font(ttf_path, name, size, outdir):
    font = ImageFont.truetype(ttf_path, size)
    ascent, descent = font.getmetrics()
    page = Image.new('RGBA', (PAGE_W, PAGE_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(page)

    chars, x, y, row_h = [], PAD, PAD, 0
    for cp in CODEPOINTS:
        ch = chr(cp)
        try:
            bbox = font.getbbox(ch)
        except Exception:
            continue
        if bbox is None:
            bbox = (0, 0, 0, 0)
        x0, y0, x1, y1 = bbox
        w, h = max(x1 - x0, 1), max(y1 - y0, 1)
        adv = max(int(round(font.getlength(ch))), 1) if cp != 32 else int(round(font.getlength(' ')))
        if x + w + PAD > PAGE_W:
            x, y = PAD, y + row_h + PAD
            row_h = 0
        if y + h + PAD > PAGE_H:
            raise RuntimeError('page overflow — increase PAGE size')
        if cp != 32:
            draw.text((x - x0, y - y0), ch, font=font, fill=(255, 255, 255, 255))
        chars.append(dict(id=cp, x=x, y=y, width=w, height=h,
                          xoffset=x0, yoffset=y0, xadvance=adv))
        x += w + PAD
        row_h = max(row_h, h)

    base = os.path.splitext(name)[0]
    tga_name = f'ara_{base}_0.tga'
    page.save(os.path.join(outdir, tga_name))

    lines = ['<?xml version="1.0"?>', '<font>',
             f'  <info face="ArabicAmnesia" size="{size}" bold="0" italic="0" charset="" unicode="1" '
             f'stretchH="100" smooth="1" aa="1" padding="0,0,0,0" spacing="{PAD},{PAD}" outline="0" />',
             f'  <common lineHeight="{ascent + descent}" base="{ascent}" scaleW="{PAGE_W}" scaleH="{PAGE_H}" '
             f'pages="1" packed="0" alphaChnl="0" redChnl="4" greenChnl="4" blueChnl="4" />',
             '  <pages>', f'    <page id="0" file="{tga_name}" />', '  </pages>',
             f'  <chars count="{len(chars)}">']
    for c in chars:
        lines.append('    <char id="{id}" x="{x}" y="{y}" width="{width}" height="{height}" '
                     'xoffset="{xoffset}" yoffset="{yoffset}" xadvance="{xadvance}" '
                     'page="0" chnl="15" />'.format(**c))
    lines += ['  </chars>', '  <kernings count="0" />', '</font>', '']
    with open(os.path.join(outdir, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    print(f'{name}: {len(chars)} glyphs, page {tga_name}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ttf', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, size in FONTS.items():
        build_font(a.ttf, name, size, a.out)
    for alias, src in FONT_ALIASES.items():
        with open(os.path.join(a.out, src), encoding='utf-8') as f:
            data = f.read()
        with open(os.path.join(a.out, alias), 'w', encoding='utf-8', newline='\n') as f:
            f.write(data)
        print(f'{alias}: alias of {src}')

if __name__ == '__main__':
    main()
