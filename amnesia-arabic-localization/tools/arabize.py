#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arabize.py — Amnesia: The Dark Descent Arabic localization tool.

HPL2 has no RTL/Arabic shaping support, so we pre-process the text:
  1. Shape Arabic letters into Presentation Forms-B (contextual forms + lam-alef ligatures).
  2. Reverse each line for RTL display (keeping Latin words, digits, $Variables and [br] tags intact).
  3. Encode all non-ASCII chars as [uNNNN] decimal escapes (same format as official chinese/russian .lang files).

Usage:
  python3 arabize.py --base english.lang --overlay ar_batch1.lang [--overlay ar_batch2.lang ...] \
                     --out arabic.lang [--fonts fonts/ara]

  --base     Original English .lang (fallback for untranslated entries).
  --overlay  A .lang file (UTF-8, normal readable Arabic) whose entries override the base.
  --out      Output .lang, ASCII with [uNNNN] escapes, CRLF line endings.
  --fonts    If given, the RESOURCES section is rewritten to point to this fonts dir.
"""
import argparse, re, sys, xml.etree.ElementTree as ET

# base char -> (isolated, final, initial, medial); initial/medial None => right-joining only
FORMS = {
 0x0621:(0xFE80,None,None,None),
 0x0622:(0xFE81,0xFE82,None,None), 0x0623:(0xFE83,0xFE84,None,None),
 0x0624:(0xFE85,0xFE86,None,None), 0x0625:(0xFE87,0xFE88,None,None),
 0x0626:(0xFE89,0xFE8A,0xFE8B,0xFE8C), 0x0627:(0xFE8D,0xFE8E,None,None),
 0x0628:(0xFE8F,0xFE90,0xFE91,0xFE92), 0x0629:(0xFE93,0xFE94,None,None),
 0x062A:(0xFE95,0xFE96,0xFE97,0xFE98), 0x062B:(0xFE99,0xFE9A,0xFE9B,0xFE9C),
 0x062C:(0xFE9D,0xFE9E,0xFE9F,0xFEA0), 0x062D:(0xFEA1,0xFEA2,0xFEA3,0xFEA4),
 0x062E:(0xFEA5,0xFEA6,0xFEA7,0xFEA8), 0x062F:(0xFEA9,0xFEAA,None,None),
 0x0630:(0xFEAB,0xFEAC,None,None), 0x0631:(0xFEAD,0xFEAE,None,None),
 0x0632:(0xFEAF,0xFEB0,None,None), 0x0633:(0xFEB1,0xFEB2,0xFEB3,0xFEB4),
 0x0634:(0xFEB5,0xFEB6,0xFEB7,0xFEB8), 0x0635:(0xFEB9,0xFEBA,0xFEBB,0xFEBC),
 0x0636:(0xFEBD,0xFEBE,0xFEBF,0xFEC0), 0x0637:(0xFEC1,0xFEC2,0xFEC3,0xFEC4),
 0x0638:(0xFEC5,0xFEC6,0xFEC7,0xFEC8), 0x0639:(0xFEC9,0xFECA,0xFECB,0xFECC),
 0x063A:(0xFECD,0xFECE,0xFECF,0xFED0), 0x0641:(0xFED1,0xFED2,0xFED3,0xFED4),
 0x0642:(0xFED5,0xFED6,0xFED7,0xFED8), 0x0643:(0xFED9,0xFEDA,0xFEDB,0xFEDC),
 0x0644:(0xFEDD,0xFEDE,0xFEDF,0xFEE0), 0x0645:(0xFEE1,0xFEE2,0xFEE3,0xFEE4),
 0x0646:(0xFEE5,0xFEE6,0xFEE7,0xFEE8), 0x0647:(0xFEE9,0xFEEA,0xFEEB,0xFEEC),
 0x0648:(0xFEED,0xFEEE,None,None), 0x0649:(0xFEEF,0xFEF0,None,None),
 0x064A:(0xFEF1,0xFEF2,0xFEF3,0xFEF4),
}
LAM = 0x0644
LAM_ALEF = {0x0622:(0xFEF5,0xFEF6), 0x0623:(0xFEF7,0xFEF8),
            0x0625:(0xFEF9,0xFEFA), 0x0627:(0xFEFB,0xFEFC)}
TATWEEL = 0x0640
HARAKAT = set(range(0x064B,0x0653)) | {0x0670}

def dual(cp):   # joins to the following letter?
    return cp == TATWEEL or (cp in FORMS and FORMS[cp][2] is not None)
def joinable(cp):  # can receive a join from the previous letter?
    return cp == TATWEEL or cp in FORMS

def shape(text):
    """Contextual shaping of Arabic letters -> Presentation Forms-B."""
    src = [c for c in text if ord(c) not in HARAKAT]
    out, i, n = [], 0, len(src)
    while i < n:
        cp = ord(src[i])
        if cp not in FORMS and cp != TATWEEL:
            out.append((src[i], False)); i += 1; continue
        prev_joins = bool(out) and out[-1][1]          # previous glyph joins forward
        # lam-alef ligature
        if cp == LAM and i+1 < n and ord(src[i+1]) in LAM_ALEF:
            iso, fin = LAM_ALEF[ord(src[i+1])]
            out.append((chr(fin if prev_joins else iso), False)); i += 2; continue
        if cp == TATWEEL:
            out.append((chr(TATWEEL), True)); i += 1; continue
        iso, fin, ini, med = FORMS[cp]
        nxt_joins = i+1 < n and joinable(ord(src[i+1]))
        if prev_joins and nxt_joins and med: g = med
        elif prev_joins and fin:             g = fin
        elif nxt_joins and ini:              g = ini
        else:                                g = iso
        out.append((chr(g), dual(cp)))
        i += 1
    return ''.join(g for g, _ in out)

# tokens that must stay LTR and intact
PROTECTED = re.compile(r'(\$[A-Za-z0-9_]+|\[br\]|\[u\d+\]|#|%)')
LTR_RUN   = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 .,\'&;:/-]*[A-Za-z0-9]$|^[A-Za-z0-9]$')
MIRROR = {'(' :')', ')':'(', '[':']', ']':'[', '{':'}', '}':'{', '<':'>', '>':'<'}

def bidi_reverse(text):
    """Reverse for RTL rendering, keeping LTR tokens (Latin words, digits, $Vars) readable."""
    parts = PROTECTED.split(text)
    tokens = []
    for part in parts:
        if not part: continue
        if PROTECTED.fullmatch(part):
            tokens.append(part)                       # atomic
        else:
            # split further into LTR word runs vs single chars
            for m in re.split(r'([A-Za-z0-9]+(?:[.,\'/-][A-Za-z0-9]+)*)', part):
                if not m: continue
                if re.fullmatch(r'[A-Za-z0-9]+(?:[.,\'/-][A-Za-z0-9]+)*', m):
                    tokens.append(m)                  # atomic LTR
                else:
                    tokens.extend(list(m))            # single chars
    tokens.reverse()
    return ''.join(MIRROR.get(t, t) if len(t) == 1 else t for t in tokens)

def has_arabic(s):
    return any(0x0600 <= ord(c) <= 0x06FF or 0xFB50 <= ord(c) <= 0xFEFC for c in s)

def process_text(s):
    if not s:
        return s
    if has_arabic(s):
        lines = s.split('[br]')
        s = '[br]'.join(bidi_reverse(shape(l)) for l in lines)
    return ''.join(f'[u{ord(c)}]' if ord(c) > 127 else c for c in s)

def load_entries(path):
    tree = ET.parse(path)
    root = tree.getroot()
    d = {}
    for cat in root.findall('CATEGORY'):
        for e in cat.findall('Entry'):
            d[(cat.get('Name'), e.get('Name'))] = e.text or ''
    return tree, root, d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--overlay', action='append', default=[])
    ap.add_argument('--out', required=True)
    ap.add_argument('--fonts', default=None)
    a = ap.parse_args()

    tree, root, _ = load_entries(a.base)
    overrides = {}
    for ov in a.overlay:
        _, _, d = load_entries(ov)
        overrides.update(d)

    if a.fonts is not None:
        res = root.find('RESOURCES')
        if res is None:
            res = ET.SubElement(root, 'RESOURCES'); root.remove(res); root.insert(0, res)
        for c in list(res): res.remove(c)
        # Order matters: first dir wins name collisions in HPL2's FileSearcher,
        # so ara fonts override the eng ones, while fonts/eng keeps every stock
        # font (font_default.fnt for the gui skin!) reachable — without it the
        # engine derefs a NULL font in LuxPreMenu and crashes on startup.
        ET.SubElement(res, 'Directory', {'Path': a.fonts})
        ET.SubElement(res, 'Directory', {'Path': 'fonts/eng'})

    n = 0
    for cat in root.findall('CATEGORY'):
        for e in cat.findall('Entry'):
            key = (cat.get('Name'), e.get('Name'))
            if key in overrides:
                e.text = overrides[key]; n += 1
            e.text = process_text(e.text or '')

    xml = ET.tostring(root, encoding='unicode')
    xml = xml.replace('\n', '\r\n')
    with open(a.out, 'w', encoding='ascii', newline='') as f:
        f.write(xml)
    print(f'{a.out}: applied {n} translated entries.')

if __name__ == '__main__':
    main()
