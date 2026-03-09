#!/usr/bin/env python3
"""
sound.py - Java Resource Pack -> Bedrock sound_definitions.json converter
=========================================================================
Dipanggil via manager.py yang sudah extract pack ke direktori pack/.
Working directory saat dijalankan: staging/ (tempat converter.sh berjalan).

Mendukung 4 pola namespace di Java sounds.json:
  1. Cross-ns  : ref punya explicit namespace beda dari json_namespace
                 e.g. sounds.json di archmage_sounds/, ref "archmage:samus/bolt"
                 -> OGG: pack/assets/archmage/sounds/samus/bolt.ogg
                 -> Bedrock: sounds/archmage/samus/bolt

  2. Same-ns   : ref punya explicit namespace sama dengan json_namespace
                 e.g. sounds.json di foo/, ref "foo:step"
                 -> OGG: pack/assets/foo/sounds/step.ogg
                 -> Bedrock: sounds/foo/step

  3. No-ns     : ref tanpa namespace, json_namespace bukan minecraft
                 -> fallback ke minecraft namespace (Java default behavior)
                 e.g. sounds.json di golemking/, ref "littleroom/constructdeath"
                 -> OGG: pack/assets/minecraft/sounds/littleroom/constructdeath.ogg
                 -> Bedrock: sounds/littleroom/constructdeath

  4. Minecraft : sounds.json di namespace minecraft, ref tanpa namespace
                 -> OGG: pack/assets/minecraft/sounds/ref.ogg
                 -> Bedrock: sounds/ref
"""

import json, glob, os, shutil

# Auto-detect pack directory:
# - manager.py extract ke pack/assets/  -> PACK_DIR = "pack"
# - converter.sh unzip langsung         -> PACK_DIR = "."
if os.path.isdir("pack/assets"):
    PACK_DIR = "pack"
elif os.path.isdir("assets"):
    PACK_DIR = "."
else:
    print("[SOUND] ERROR: Tidak bisa menemukan assets/ directory. Pastikan pack sudah diekstrak.")
    raise SystemExit(1)

OUT_SOUNDS_DIR = "target/rp/sounds"
OUT_DEFS_FILE  = os.path.join(OUT_SOUNDS_DIR, "sound_definitions.json")

os.makedirs(OUT_SOUNDS_DIR, exist_ok=True)

defs = {"format_version": "1.14.0", "sound_definitions": {}}

# Valid Bedrock sound categories
VALID_CATEGORIES = {
    "ambient", "block", "bottle", "bucket", "hostile",
    "master", "music", "neutral", "player", "record", "ui", "weather"
}


def normalize_category(category) -> str:
    """Pastikan category valid untuk Bedrock. Fallback ke 'neutral'."""
    cat = str(category).lower() if category else "neutral"
    return cat if cat in VALID_CATEGORIES else "neutral"


def copy_sound_file(sound_ref: str, json_namespace: str):
    """
    Resolve sound ref ke file OGG, copy ke target Bedrock, return bedrock path.
    Returns None jika file tidak ditemukan.
    """
    if ":" in sound_ref:
        snd_namespace, snd_path = sound_ref.split(":", 1)
    else:
        # Tidak ada explicit namespace -> Java default: cari di minecraft namespace
        snd_namespace = "minecraft"
        snd_path = sound_ref

    # Lokasi file OGG di Java pack
    src = f"{PACK_DIR}/assets/{snd_namespace}/sounds/{snd_path}.ogg"

    if not os.path.exists(src):
        print(f"  [WARN] Sound tidak ditemukan: {src}")
        return None

    # Tentukan bedrock path (relative dari rp root, tanpa .ogg)
    if snd_namespace == "minecraft":
        # Minecraft namespace -> langsung di sounds/ tanpa prefix namespace
        bedrock_rel = f"sounds/{snd_path}"
    else:
        # Non-minecraft -> prefix dengan namespace untuk avoid collision
        bedrock_rel = f"sounds/{snd_namespace}/{snd_path}"

    # Copy OGG ke target
    dst = f"target/rp/{bedrock_rel}.ogg"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)

    return bedrock_rel


def convert_entry(entry, json_namespace: str):
    """
    Convert satu entry sound (string atau dict) ke format Bedrock.
    String  -> return bedrock path string
    Dict    -> return dict dengan semua field dipertahankan + name diganti bedrock path
    """
    if isinstance(entry, str):
        return copy_sound_file(entry, json_namespace)
    elif isinstance(entry, dict):
        name = entry.get("name", "")
        if not name:
            return None
        path = copy_sound_file(name, json_namespace)
        if path is None:
            return None
        # Passthrough semua field extra (volume, pitch, stream, weight, attenuation_distance, type, etc.)
        result = {k: v for k, v in entry.items() if k != "name"}
        result["name"] = path
        return result
    return None


# Scan semua sounds.json di semua namespace
sound_files = glob.glob(f"{PACK_DIR}/assets/*/sounds.json")
print(f"[SOUND] Ditemukan {len(sound_files)} sounds.json")

for sounds_file in sorted(sound_files):
    sounds_file = sounds_file.replace("\\", "/")
    # Ambil namespace dari path: pack/assets/<namespace>/sounds.json
    parts = sounds_file.split("/")
    json_namespace = parts[2]  # index 2 = namespace
    print(f"[SOUND] Proses namespace: {json_namespace}")

    try:
        with open(sounds_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [ERROR] Gagal parse {sounds_file}: {e}")
        continue

    for sound_name, sound_data in data.items():
        # Key Bedrock: "json_namespace:sound_event_name"
        bedrock_key = f"{json_namespace}:{sound_name}"

        category = normalize_category(sound_data.get("category", "neutral"))
        raw_sounds = sound_data.get("sounds", [])

        bedrock_sounds = []
        for entry in raw_sounds:
            converted = convert_entry(entry, json_namespace)
            if converted is not None:
                bedrock_sounds.append(converted)

        if not bedrock_sounds:
            if raw_sounds:
                print(f"  [SKIP] Tidak ada sound valid untuk: {bedrock_key} ({len(raw_sounds)} entries, semua file hilang)")
            continue

        defs["sound_definitions"][bedrock_key] = {
            "category": category,
            "sounds":   bedrock_sounds
        }
        print(f"  [OK] {bedrock_key} -> {len(bedrock_sounds)} sound(s)")

with open(OUT_DEFS_FILE, "w", encoding="utf-8") as f:
    json.dump(defs, f, indent=2)

total = len(defs["sound_definitions"])
print(f"[SOUND] Selesai - {total} sound definition(s) -> {OUT_DEFS_FILE}")
