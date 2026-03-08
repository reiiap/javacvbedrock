#!/usr/bin/env python3
"""
font.py  -  Java bitmap font -> Bedrock glyph conversion (fixed)
=================================================================
Fix utama:
  - Tile size ditentukan dari field 'height' di default.json provider,
    bukan dari pixel size image aslinya.
  - Di Java, 'height' adalah render height dalam px (di layar 1x).
  - Bedrock spritesheet tile size harus proporsional terhadap height itu.
  - Sebelumnya code pakai raw pixel size image -> glyph kegedean.

Logic size:
  - Ambil height dari provider JSON
  - Tile = height x height (square tile)
  - Jika height <= 0 atau ada special use (GUI fullscreen dll), skip
  - glyphsize = (tile_w * 16, tile_h * 16) karena 16x16 grid glyph

Untuk multi-char per provider (bitmap spritesheet dengan baris/kolom),
setiap char mendapat 1 cell dari grid image.
"""

from PIL import Image
from font_sprite import sprite
from io import BytesIO
import glob, os, json

lines = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, "a", "b", "c", "d", "e", "f"]

try:
    with open("pack/assets/minecraft/font/default.json", "r") as f:
        data = json.load(f)
except Exception as e:
    print("[FONT ERROR]", e)
    raise SystemExit(0)

# Build provider lookup: hex_code -> (height, ascent, path)
providers = []
for d in data.get('providers', []):
    try:
        if d.get('type', 'bitmap') != 'bitmap':
            continue
        chars   = d['chars']
        path    = d['file']
        height  = d.get('height', 8)
        ascent  = d.get('ascent', height)
        providers.append({
            'chars':  chars,
            'path':   path,
            'height': height,
            'ascent': ascent,
        })
    except Exception:
        continue

symbols = [p['chars'] for p in providers]
paths   = [p['path']  for p in providers]
heights = [p['height'] for p in providers]
ascents = [p['ascent'] for p in providers]


def createfolder(glyph):
    os.makedirs(f"images/{glyph}", exist_ok=True)
    os.makedirs(f"export/{glyph}",  exist_ok=True)
    os.makedirs("font/",            exist_ok=True)


def create_empty(glyph, blankimg):
    for line in lines:
        for linee in lines:
            name = f"{line}{linee}"
            dst  = f"images/{glyph}/0x{glyph}{name}.png"
            if not os.path.isfile(dst):
                img = Image.open(blankimg).copy()
                img.save(dst, "PNG")
    for line in lines:
        name = f"{line}{line}"
        dst  = f"images/{glyph}/0x{glyph}{name}.png"
        if not os.path.isfile(dst):
            img = Image.open(blankimg).copy()
            img.save(dst, "PNG")


def imagetoexport(glyph, blankimg, tile_size):
    """Paste glyph image into blank tile of tile_size, respecting provider height."""
    filelist = [f for f in os.listdir(f'images/{glyph}') if f.endswith('.png')]
    for img_name in filelist:
        base  = Image.open(blankimg)
        logo  = Image.open(f'images/{glyph}/{img_name}')
        bw, bh = base.size
        lw, lh = logo.size

        # Resize logo to fit within tile while keeping aspect ratio
        logo.thumbnail((bw, bh), Image.LANCZOS)
        lw, lh = logo.size

        base_copy = base.copy()
        position  = (0, (bh // 2) - (lh // 2))
        base_copy.paste(logo, position, logo if logo.mode == 'RGBA' else None)
        base_copy.save(f"export/{glyph}/{img_name}")


# Collect all unique glyph prefixes (2-hex-digit prefix, e.g. "E0", "E1")
glyphs = []
for char_list in symbols:
    try:
        symbolbe = ''.join(char_list)
        sbh = hex(ord(symbolbe))
        a   = sbh[2:]
        ab  = a[:2]
        glyphs.append(ab.upper())
    except Exception as e:
        print(f"Symbol Error: {e}")
        continue
glyphs = list(dict.fromkeys(glyphs))
print("[FONT FILE] Glyph prefixes:", glyphs)

listglyphdone = []


def converterpack(glyph):
    createfolder(glyph)
    maxsw, maxsh = 0, 0
    best_height  = 8  # default fallback tile height

    if len(symbols) != len(paths):
        return False

    for symboll, path, height, ascent in zip(symbols, paths, heights, ascents):
        symbolbe    = ''.join(symboll)
        symbolbehex = hex(ord(symbolbe))

        if glyph in listglyphdone:
            return False

        # Pad hex to 6 digits (e.g. 0xe123 -> 0x00e123)
        if len(symbolbehex) == 6:
            symbol      = symbolbehex[4:]
            symbolcheck = symbolbehex[2:4]
        elif len(symbolbehex) == 5:
            symbolbehex = symbolbehex[:2] + "0" + symbolbehex[2:]
            symbol      = symbolbehex[4:]
            symbolcheck = symbolbehex[2:4]
            glyphs.append(symbolcheck.upper())
        else:
            continue

        if symbolcheck.upper() != glyph.upper():
            continue

        # Skip glyphs with non-positive height (invisible spacers)
        if height <= 0:
            print(f"  [SKIP] height={height} for {glyph} (spacer/invisible)")
            continue

        # Record the provider's intended render height for tile sizing
        best_height = max(best_height, height)

        # Load and save the glyph image
        try:
            if ":" in path:
                ns       = path.split(":")[0]
                pathnew  = path.split(":")[1]
                img_path = f"pack/assets/{ns}/textures/{pathnew}"
            else:
                img_path = f"pack/assets/minecraft/textures/{path}"

            imagefont = Image.open(img_path)

            # For multi-char bitmap fonts, the image is a grid.
            # Rows in chars list = rows of the grid. Each char = one cell.
            # Extract the correct cell for this char.
            n_cols = max(len(row) for row in symboll) if isinstance(symboll[0], str) else 1
            n_rows = len(symboll)
            if n_cols > 1 or n_rows > 1:
                # Find position of this char in the grid
                char_idx_row, char_idx_col = 0, 0
                found = False
                for r, row in enumerate(symboll):
                    for c, ch in enumerate(row):
                        if ch == symbolbe:
                            char_idx_row, char_idx_col = r, c
                            found = True
                            break
                    if found:
                        break
                iw, ih = imagefont.size
                cell_w  = iw // n_cols
                cell_h  = ih // n_rows
                box     = (char_idx_col * cell_w, char_idx_row * cell_h,
                           (char_idx_col + 1) * cell_w, (char_idx_row + 1) * cell_h)
                image = imagefont.crop(box)
            else:
                image = imagefont.copy()

            image.save(f"images/{glyph}/0x{glyph}{symbol}.png", "PNG")

        except Exception as e:
            print(f"  [ERROR] {e}")
            continue

    # After processing all providers for this glyph prefix:
    files = glob.glob(f"images/{glyph}/*.png")
    if not files:
        return False

    for file in files:
        img = Image.open(file)
        sw, sh = img.size
        maxsw   = max(maxsw, sw)
        maxsh   = max(maxsh, sh)

    # FIX: Use provider 'height' as the canonical tile size, not raw pixel size.
    # This matches Java's behavior where 'height' controls on-screen render size.
    # Cap to 256 for sanity (some GUI items have height 170 etc — these are full
    # GUI overlays placed at specific positions, not inline text glyphs).
    tile_dim = max(1, min(best_height, 256))
    size     = (tile_dim, tile_dim)

    glyphsize = (size[0] * 16, size[1] * 16)

    print(f"  [FONT] Glyph {glyph}: tile={size}, sheet={glyphsize}, src_px=({maxsw},{maxsh}), provider_height={best_height}")

    img    = Image.open("blank256.png")
    imgre  = img.resize(size, Image.LANCZOS)
    imgre.save("blankimg.png")
    blankimg = "blankimg.png"

    create_empty(glyph, blankimg)
    imagetoexport(glyph, blankimg, size)
    sprite(glyph, glyphsize, size)
    listglyphdone.append(glyph)


for glyph in glyphs:
    converterpack(glyph)
