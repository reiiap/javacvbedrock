#!/usr/bin/env python3
"""Best-effort Java resource pack finishing pipeline for JavaCVBedrock.

This module intentionally augments the existing shell converter instead of
replacing it.  It performs safe, non-fatal passes that are awkward in bash:
validation, plugin discovery, language/sound conversion, animation metadata, and
an auditable conversion report.
"""

from __future__ import annotations

import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from java_model_engine import JavaModelEngine, iter_model_files, stable_icon_name

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


JAVA_PACK = Path(".")
ASSETS = JAVA_PACK / "assets"
TARGET_RP = Path("target/rp")
REPORT_PATH = Path("target/conversion_report.json")
NAMESPACE_RE = re.compile(r"^[a-z0-9_.-]+$")


@dataclass
class Report:
    started_at: float = field(default_factory=time.time)
    discovered: dict[str, Any] = field(default_factory=lambda: {
        "namespaces": [],
        "plugins": [],
        "models": 0,
        "textures": 0,
        "animated_textures": 0,
        "sounds_json": 0,
        "language_files": 0,
        "font_files": 0,
        "particles": 0,
        "animations": 0,
        "animation_controllers": 0,
        "atlas_files": 0,
        "folder_inputs": 0,
        "zip_inputs": 0,
        "duplicates": [],
    })
    converted: dict[str, int] = field(default_factory=lambda: {
        "languages": 0,
        "sounds": 0,
        "sound_definitions": 0,
        "flipbook_textures": 0,
        "copied_plugin_assets": 0,
        "baked_models": 0,
        "rendered_icons": 0,
        "cached_icons": 0,
    })
    skipped: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        print(f"[PIPELINE WARN] {message}")
        self.warnings.append(message)

    def error(self, message: str) -> None:
        print(f"[PIPELINE ERROR] {message}")
        self.errors.append(message)

    def write(self) -> None:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "status": "completed_with_warnings" if self.warnings or self.errors else "completed",
            "elapsed_seconds": round(time.time() - self.started_at, 3),
            "discovered": self.discovered,
            "converted": self.converted,
            "skipped": self.skipped,
            "unsupported": self.unsupported,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[PIPELINE] Conversion report written: {REPORT_PATH}")


def iter_files(root: Path, suffixes: Iterable[str]) -> Iterable[Path]:
    suffixes = tuple(suffixes)
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file() and p.name.endswith(suffixes))


def load_json(path: Path, report: Report) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.warn(f"Invalid JSON in {path}: {exc}")
        return None


def discover(report: Report) -> None:
    print("[PIPELINE] Discovering Java resources")
    namespaces = []
    if ASSETS.exists():
        for ns in sorted(p.name for p in ASSETS.iterdir() if p.is_dir()):
            if NAMESPACE_RE.match(ns):
                namespaces.append(ns)
            else:
                report.warn(f"Invalid namespace '{ns}' under assets/")
    report.discovered["namespaces"] = namespaces
    report.discovered["models"] = sum(1 for _ in iter_files(ASSETS, (".json",)) if "/models/" in _.as_posix())
    report.discovered["textures"] = sum(1 for _ in iter_files(ASSETS, (".png",)))
    report.discovered["animated_textures"] = sum(1 for _ in iter_files(ASSETS, (".png.mcmeta",)))
    report.discovered["sounds_json"] = len(list(ASSETS.glob("*/sounds.json")))
    report.discovered["language_files"] = len(list(ASSETS.glob("*/lang/*.json"))) + len(list(ASSETS.glob("*/lang/*.lang")))
    report.discovered["font_files"] = len(list(ASSETS.glob("*/font/*.json")))
    report.discovered["particles"] = len(list(ASSETS.glob("*/particles/**/*.json")))
    report.discovered["animations"] = len(list(ASSETS.glob("*/animations/**/*.json")))
    report.discovered["animation_controllers"] = len(list(ASSETS.glob("*/animation_controllers/**/*.json")))
    report.discovered["atlas_files"] = len(list(ASSETS.glob("*/atlases/**/*.json"))) + len(list(ASSETS.glob("*/textures/atlas*.json")))
    report.discovered["folder_inputs"] = 1 if (JAVA_PACK / "pack.mcmeta").exists() or ASSETS.exists() else 0
    report.discovered["zip_inputs"] = len([p for p in JAVA_PACK.glob("*.zip") if zipfile.is_zipfile(p)])
    duplicate_map: dict[str, list[str]] = {}
    for path in iter_files(ASSETS, (".png", ".json", ".ogg", ".mcmeta")):
        try:
            rel_parts = path.relative_to(ASSETS).parts
            if len(rel_parts) > 1:
                key = "/".join(rel_parts[1:])
                duplicate_map.setdefault(key, []).append(path.as_posix())
        except Exception:
            continue
    duplicates = {key: paths for key, paths in duplicate_map.items() if len(paths) > 1}
    report.discovered["duplicates"] = duplicates
    for key, paths in duplicates.items():
        report.warn(f"Duplicate resource path across namespaces: {key} -> {paths}")

    markers = {
        "ItemsAdder": ["contents", "configs", "resourcepack", "itemsadder", "ItemsAdder"],
        "Nexo": ["items.yml", "glyphs.yml", "fonts.yml", "nexo", "Nexo"],
        "Oraxen": ["oraxen", "Oraxen", "glyphs.yml", "items.yml"],
    }
    plugins = []
    all_paths = list(JAVA_PACK.rglob("*"))
    for name, needles in markers.items():
        if any(any(needle.lower() == part.lower() or needle.lower() in part.lower() for part in p.parts) for needle in needles for p in all_paths):
            plugins.append(name)
    report.discovered["plugins"] = sorted(set(plugins))


def validate(report: Report) -> None:
    print("[PIPELINE] Validating JSON/YAML resources")
    for path in iter_files(JAVA_PACK, (".json", ".mcmeta")):
        if ".git" not in path.parts and "target" not in path.parts:
            load_json(path, report)
    for path in iter_files(JAVA_PACK, (".yml", ".yaml")):
        if yaml is None:
            report.warn(f"YAML validation skipped for {path}: PyYAML is not installed")
            continue
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            report.warn(f"Invalid YAML in {path}: {exc}")
    print("[PIPELINE] Validating model parent and texture references")
    engine = JavaModelEngine(ASSETS, report.warn)
    for path in iter_model_files(ASSETS):
        baked = engine.bake(path)
        if baked is None:
            report.skipped.append(f"model:{path.as_posix()}")
            continue
        for texture_ref in baked.textures.values():
            resolved = engine.resolve_texture_name(texture_ref, baked.textures)
            if resolved and engine.texture_path(resolved) is None:
                report.warn(f"Missing texture '{resolved}' referenced by {path}")
        for warning in baked.warnings:
            report.warn(warning)


def convert_languages(report: Report) -> None:
    print("[PIPELINE] Converting language files")
    out_dir = TARGET_RP / "texts"
    out_dir.mkdir(parents=True, exist_ok=True)
    languages: list[str] = []
    for path in list(ASSETS.glob("*/lang/*.json")) + list(ASSETS.glob("*/lang/*.lang")):
        locale = path.stem
        out_name = f"{locale}.lang"
        out_path = out_dir / out_name
        try:
            if path.suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                lines = [f"{k}={v}" for k, v in sorted(data.items())]
            else:
                lines = path.read_text(encoding="utf-8").splitlines()
            with out_path.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(line for line in lines if line and not line.lstrip().startswith("#")))
                handle.write("\n")
            languages.append(out_name)
            report.converted["languages"] += 1
        except Exception as exc:
            report.warn(f"Could not convert language file {path}: {exc}")
    if languages:
        (out_dir / "languages.json").write_text(json.dumps(sorted(set(languages)), indent=2), encoding="utf-8")


def convert_sounds(report: Report) -> None:
    print("[PIPELINE] Converting sounds")
    out_dir = TARGET_RP / "sounds"
    out_dir.mkdir(parents=True, exist_ok=True)
    definitions: dict[str, Any] = {"format_version": "1.14.0", "sound_definitions": {}}
    for sounds_json in ASSETS.glob("*/sounds.json"):
        namespace = sounds_json.parent.name
        data = load_json(sounds_json, report)
        if not isinstance(data, dict):
            continue
        for event, payload in data.items():
            entries = payload.get("sounds", []) if isinstance(payload, dict) else []
            sounds = []
            for entry in entries:
                name = entry if isinstance(entry, str) else entry.get("name") if isinstance(entry, dict) else None
                if not name:
                    continue
                snd_ns, snd_path = name.split(":", 1) if ":" in name else (namespace, name)
                src = ASSETS / snd_ns / "sounds" / f"{snd_path}.ogg"
                if not src.exists():
                    report.warn(f"Missing sound asset for {namespace}:{event}: {src}")
                    continue
                rel = Path("sounds") / (snd_path if snd_ns == "minecraft" else f"{snd_ns}/{snd_path}")
                dst = TARGET_RP / f"{rel}.ogg"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                sound_entry: Any = rel.as_posix()
                if isinstance(entry, dict):
                    sound_entry = {k: v for k, v in entry.items() if k != "name"}
                    sound_entry["name"] = rel.as_posix()
                sounds.append(sound_entry)
                report.converted["sounds"] += 1
            if sounds:
                definitions["sound_definitions"][f"{namespace}:{event}"] = {
                    "category": (payload.get("category", "neutral") if isinstance(payload, dict) else "neutral"),
                    "sounds": sounds,
                }
                report.converted["sound_definitions"] += 1
    if definitions["sound_definitions"]:
        (out_dir / "sound_definitions.json").write_text(json.dumps(definitions, indent=2), encoding="utf-8")


def convert_flipbooks(report: Report) -> None:
    print("[PIPELINE] Converting animated texture metadata")
    flipbook: list[dict[str, Any]] = []
    for meta_path in iter_files(ASSETS, (".png.mcmeta",)):
        png_path = Path(str(meta_path)[:-7])
        meta = load_json(meta_path, report)
        animation = meta.get("animation", {}) if isinstance(meta, dict) else {}
        if not png_path.exists():
            report.warn(f"Animation metadata has no PNG pair: {meta_path}")
            continue
        try:
            rel = png_path.relative_to(ASSETS / png_path.parts[1] / "textures").with_suffix("").as_posix()
        except Exception:
            rel = png_path.with_suffix("").name
        entry: dict[str, Any] = {"flipbook_texture": f"textures/{rel}", "atlas_tile": rel.split("/")[-1]}
        if "frametime" in animation:
            entry["ticks_per_frame"] = animation["frametime"]
        if "frames" in animation:
            entry["frames"] = animation["frames"]
        flipbook.append(entry)
    if flipbook:
        out = TARGET_RP / "textures" / "flipbook_textures.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(flipbook, indent=2), encoding="utf-8")
        report.converted["flipbook_textures"] = len(flipbook)


def bake_and_render_models(report: Report) -> None:
    print("[PIPELINE] Baking models and rendering missing inventory icons")
    engine = JavaModelEngine(ASSETS, report.warn)
    ir_dir = Path("target/model_ir")
    icon_dir = TARGET_RP / "textures" / "items" / "generated"
    item_texture_path = TARGET_RP / "textures" / "item_texture.json"
    ir_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    if item_texture_path.exists():
        try:
            item_texture = json.loads(item_texture_path.read_text(encoding="utf-8"))
        except Exception:
            item_texture = {"resource_pack_name": "geyser_custom", "texture_name": "atlas.items", "texture_data": {}}
    else:
        item_texture = {"resource_pack_name": "geyser_custom", "texture_name": "atlas.items", "texture_data": {}}
    item_texture.setdefault("texture_data", {})

    for path in iter_model_files(ASSETS):
        baked = engine.bake(path)
        if baked is None:
            report.skipped.append(f"model:{path.as_posix()}")
            continue
        safe_id = stable_icon_name(baked.model_id)
        (ir_dir / f"{safe_id}.json").write_text(json.dumps(baked.to_ir(), indent=2), encoding="utf-8")
        report.converted["baked_models"] += 1

        has_existing_icon = safe_id in item_texture["texture_data"]
        icon_path = icon_dir / f"{safe_id}.png"
        if has_existing_icon or icon_path.exists():
            report.converted["cached_icons"] += 1
            continue
        if engine.render_icon(baked, icon_path):
            item_texture["texture_data"][safe_id] = {"textures": f"textures/items/generated/{safe_id}"}
            report.converted["rendered_icons"] += 1
        else:
            report.unsupported.append(f"render_icon:{baked.model_id}")
            report.warn(f"Could not render inventory icon for {baked.model_id}; keeping existing converter output")
        for warning in baked.warnings:
            report.warn(warning)

    item_texture_path.parent.mkdir(parents=True, exist_ok=True)
    item_texture_path.write_text(json.dumps(item_texture, indent=2), encoding="utf-8")


def main() -> int:
    report = Report()
    try:
        discover(report)
        validate(report)
        convert_languages(report)
        convert_sounds(report)
        convert_flipbooks(report)
        bake_and_render_models(report)
    except Exception as exc:
        report.error(f"Unexpected non-fatal pipeline error: {exc}")
    finally:
        report.write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
