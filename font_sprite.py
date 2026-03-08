def sprite(glyph: str, glyphsize: tuple, tile_size: tuple):

    from PIL import Image
    import os

    GRID = 16  # Bedrock selalu 16x16 grid

    export_dir = f"export/{glyph}"
    if not os.path.isdir(export_dir):
        print(f"[FONT_SPRITE] Export dir tidak ada: {export_dir}, skip")
        return

    tile_w = max(1, int(tile_size[0]))
    tile_h = max(1, int(tile_size[1]))
    sheet_w = tile_w * GRID
    sheet_h = tile_h * GRID

    # Buat blank spritesheet RGBA
    spritesheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    files = sorted(os.listdir(export_dir))
    placed = 0

    for fname in files:
        if not fname.lower().endswith(".png"):
            continue

        # Nama file: 0xGGcc.png dimana GG=glyph prefix, cc=posisi dalam grid
        # Contoh: 0xE3A2.png -> kolom = 0xA = 10, baris = 0x2 = 2
        stem = os.path.splitext(fname)[0]  # "0xE3A2"
        try:
            full_hex = stem[2:]   # "E3A2"
            low_byte = full_hex[2:4]  # "A2"
            col = int(low_byte[0], 16)  # high nibble = kolom
            row = int(low_byte[1], 16)  # low nibble  = baris
        except Exception as e:
            print(f"[FONT_SPRITE] Skip {fname}: tidak bisa parse posisi ({e})")
            continue

        try:
            img = Image.open(f"{export_dir}/{fname}").convert("RGBA")
        except Exception as e:
            print(f"[FONT_SPRITE] Skip {fname}: gagal buka ({e})")
            continue

        # Resize tile ke tile_w x tile_h dengan padding transparan (preserve aspect ratio)
        img_copy = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        img.thumbnail((tile_w, tile_h), Image.LANCZOS)
        paste_x = (tile_w - img.width) // 2
        paste_y = (tile_h - img.height) // 2
        img_copy.paste(img, (paste_x, paste_y), img)

        x = col * tile_w
        y = row * tile_h
        spritesheet.paste(img_copy, (x, y))
        placed += 1

    os.makedirs("staging/target/rp/font", exist_ok=True)
    out_path = f"staging/target/rp/font/glyph_{glyph}.png"
    spritesheet.save(out_path, "PNG")
    print(f"[FONT_SPRITE] glyph_{glyph}.png -> {sheet_w}x{sheet_h} ({placed} tiles, tile={tile_w}x{tile_h}px)")
