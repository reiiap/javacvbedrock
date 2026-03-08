#!/usr/bin/env python3

import json, glob, os, shutil

OUT_SOUNDS_DIR = "staging/target/rp/sounds"
OUT_DEFS_FILE  = os.path.join(OUT_SOUNDS_DIR, "sound_definitions.json")

os.makedirs(OUT_SOUNDS_DIR, exist_ok=True)

defs = {"format_version": "1.14.0", "sound_definitions": {}}


def copy_sound_file(sound_ref: str, json_namespace: str):

    # Pisahkan namespace dan path dari ref
    if ":" in sound_ref:
        snd_namespace, snd_path = sound_ref.split(":", 1)
    else:
        # Tidak ada explicit namespace -> gunakan minecraft sebagai default
        snd_namespace = "minecraft"
        snd_path = sound_ref

    # Lokasi file OGG di Java pack
    src = f"pack/assets/{snd_namespace}/sounds/{snd_path}.ogg"

    if not os.path.exists(src):
        print(f"  [WARN] Sound tidak ditemukan: {src}")
        return None

    # Tentukan path Bedrock (relative dari rp root, tanpa .ogg)
    if snd_namespace == "minecraft":
        # Minecraft namespace -> langsung di sounds/ tanpa prefix namespace
        bedrock_rel = f"sounds/{snd_path}"
    else:
        # Non-minecraft -> prefix dengan namespace untuk avoid collision
        bedrock_rel = f"sounds/{snd_namespace}/{snd_path}"

    # Copy OGG ke target
    dst = f"staging/target/rp/{bedrock_rel}.ogg"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)

    return bedrock_rel


def convert_entry(entry, json_namespace: str):

    if isinstance(entry, str):
        return copy_sound_file(entry, json_namespace)
    elif isinstance(entry, dict):
        name = entry.get("name", "")
        if not name:
            return None
        path = copy_sound_file(name, json_namespace)
        if path is None:
            return None
        # Passthrough semua field dict (volume, pitch, stream, weight, attenuation_distance, etc.)
        result = {k: v for k, v in entry.items() if k != "name"}
        result["name"] = path
        return result
    return None


# Valid Bedrock sound categories
VALID_CATEGORIES = {
    "ambient", "block", "bottle", "bucket", "hostile",
    "master", "music", "neutral", "player", "record", "ui", "weather"
}


def normalize_category(category: str) -> str:
    """Pastikan category valid untuk Bedrock. Fallback ke 'neutral'."""
    cat = str(category).lower() if category else "neutral"
    return cat if cat in VALID_CATEGORIES else "neutral"


sound_files = glob.glob("pack/assets/*/sounds.json")
print(f"[SOUND] Ditemukan {len(sound_files)} sounds.json")

for sounds_file in sound_files:
    sounds_file = sounds_file.replace("\\", "/")
    # Ambil namespace dari path: pack/assets/<namespace>/sounds.json
    json_namespace = sounds_file.split("/")[2]
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
            # Tetap daftarkan entry meskipun kosong (bisa karena file hilang di pack)
            if raw_sounds:
                print(f"  [SKIP] Tidak ada sound valid untuk: {bedrock_key} (raw: {len(raw_sounds)} entries)")
            continue

        defs["sound_definitions"][bedrock_key] = {
            "category": category,
            "sounds":   bedrock_sounds
        }
        print(f"  [OK] {bedrock_key} -> {len(bedrock_sounds)} sound(s)")

with open(OUT_DEFS_FILE, "w", encoding="utf-8") as f:
    json.dump(defs, f, indent=2)

total = len(defs["sound_definitions"])
print(f"[SOUND] Selesai - {total} sound definition(s) ditulis ke {OUT_DEFS_FILE}")
