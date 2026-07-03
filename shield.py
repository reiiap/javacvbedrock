#!/usr/bin/env python3
"""
shield.py  -  Java shield custom model -> Bedrock attachable (fixed)
=====================================================================
Fixes:
  1. Support pack yang hanya define "default" (tanpa blocking variant)
  2. check == 1 sekarang generate attachable yang valid
  3. Tidak crash jika blocking attachable file tidak ada
  4. Proper animate/animation block untuk 1-variant dan 2-variant shield
"""

import os, json, glob

# ── Parse shield predicates dari models/item/shield.json ───────────────────

shield_path = "pack/assets/minecraft/models/item/shield.json"
if not os.path.exists(shield_path):
    print("[SHIELD] Tidak ada shield.json, skip.")
    raise SystemExit(0)

with open(shield_path) as f:
    data = json.load(f)

overrides  = data.get("overrides", [])
predicates = [d.get("predicate", {}) for d in overrides]
models     = [d.get("model", "")     for d in overrides]

for m, p in zip(models, predicates):
    if m in ("item/shield", "minecraft:item/shield") or "custom_model_data" not in p:
        continue

    cmd   = p["custom_model_data"]
    fpath = f"cache/shield/{cmd}.json"

    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    if not os.path.exists(fpath):
        with open(fpath, "w") as f:
            f.write("{}")

    with open(fpath, "r") as f:
        entry = json.load(f)

    is_blocking = "blocking" in p
    key = "blocking" if is_blocking else "default"
    entry[key] = m

    entry["check"] = entry.get("check", 0) + 1

    with open(fpath, "w") as f:
        json.dump(entry, f, indent=2)


# ── Build attachables dari cache ────────────────────────────────────────────

def find_attachable(model_path: str):
    """Cari file attachable berdasarkan model path."""
    namespace = model_path.split(":")[0] if ":" in model_path else "minecraft"
    path      = model_path.split(":")[1] if ":" in model_path else model_path
    files     = glob.glob(f"staging/target/rp/attachables/{namespace}/{path}*.json")
    for fa in files:
        if f"{path.split('/')[-1]}." in fa:
            return fa
    # Fallback: ambil file pertama yang ditemukan
    return files[0] if files else None


for cache_file in glob.glob("cache/shield/*.json"):
    with open(cache_file, "r") as f:
        entry = json.load(f)

    check = entry.get("check", 0)

    # ── Case 1: Ada default DAN blocking ─────────────────────────────────
    if check >= 2 and "default" in entry and "blocking" in entry:
        try:
            animation     = {}
            saf           = None
            adata         = None
            animate       = []
            gmdl          = None

            for variant in ["default", "blocking"]:
                fa = find_attachable(entry[variant])
                if fa is None:
                    print(f"[SHIELD] Attachable tidak ditemukan untuk {entry[variant]}, skip variant {variant}")
                    continue

                with open(fa, "r") as f:
                    dataA = json.load(f)

                anim_items = dataA["minecraft:attachable"]["description"]["animations"]
                identifier = dataA["minecraft:attachable"]["description"]["identifier"]

                if variant == "default":
                    saf   = fa
                    adata = dataA
                    gmdl  = identifier

                    animation["mainhand.first_person"]  = anim_items.get("firstperson_main_hand", "")
                    animation["mainhand.thierd_person"] = anim_items.get("thirdperson_main_hand", "")
                    animation["offhand.first_person"]   = anim_items.get("firstperson_off_hand", "")
                    animation["offhand.thierd_person"]  = anim_items.get("thirdperson_off_hand", "")

                    animate = [
                        {"mainhand.thierd_person.block": f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && query.is_sneaking"},
                        {"mainhand.first_person.block":  f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && query.is_sneaking"},
                        {"mainhand.first_person":        f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && !query.is_sneaking"},
                        {"mainhand.thierd_person":       f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && !query.is_sneaking"},
                        {"offhand.thierd_person.block":  f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && query.is_sneaking"},
                        {"offhand.first_person.block":   f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && query.is_sneaking"},
                        {"offhand.first_person":         f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && !query.is_sneaking"},
                        {"offhand.thierd_person":        f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && !query.is_sneaking"},
                    ]
                else:
                    animation["mainhand.first_person.block"]  = anim_items.get("firstperson_main_hand", "")
                    animation["mainhand.thierd_person.block"] = anim_items.get("thirdperson_main_hand", "")
                    animation["offhand.first_person.block"]   = anim_items.get("firstperson_off_hand", "")
                    animation["offhand.thierd_person.block"]  = anim_items.get("thirdperson_off_hand", "")

                    # Hapus attachable blocking yang terpisah, udah di-merge ke default
                    if fa != saf:
                        try:
                            os.remove(fa)
                        except Exception:
                            pass

            if saf and adata and gmdl:
                adata["minecraft:attachable"]["description"]["animations"] = animation
                adata["minecraft:attachable"]["description"]["scripts"]["animate"] = animate
                with open(saf, "w") as f:
                    json.dump(adata, f)
                print(f"[SHIELD] OK (default+blocking): {gmdl}")

        except Exception as e:
            print(f"[SHIELD] Error processing {cache_file}: {e}")

    # ── Case 2: Hanya default (tanpa blocking variant) ────────────────────
    elif check >= 1 and "default" in entry:
        try:
            fa = find_attachable(entry["default"])
            if fa is None:
                print(f"[SHIELD] Attachable tidak ditemukan untuk {entry['default']}, skip")
                continue

            with open(fa, "r") as f:
                dataA = json.load(f)

            gmdl      = dataA["minecraft:attachable"]["description"]["identifier"]
            anim_items = dataA["minecraft:attachable"]["description"]["animations"]

            animation = {
                "mainhand.first_person":  anim_items.get("firstperson_main_hand", ""),
                "mainhand.thierd_person": anim_items.get("thirdperson_main_hand", ""),
                "offhand.first_person":   anim_items.get("firstperson_off_hand", ""),
                "offhand.thierd_person":  anim_items.get("thirdperson_off_hand", ""),
            }

            animate = [
                {"mainhand.first_person":  f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}')"},
                {"mainhand.thierd_person": f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}')"},
                {"offhand.first_person":   f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}')"},
                {"offhand.thierd_person":  f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}')"},
            ]

            dataA["minecraft:attachable"]["description"]["animations"] = animation
            dataA["minecraft:attachable"]["description"]["scripts"]["animate"] = animate

            with open(fa, "w") as f:
                json.dump(dataA, f)

            print(f"[SHIELD] OK (default only): {gmdl}")

        except Exception as e:
            print(f"[SHIELD] Error processing {cache_file}: {e}")

    else:
        print(f"[SHIELD] Skip {cache_file} - data tidak lengkap: {entry}")
