#!/usr/bin/env python3
"""Java Edition model parsing, baking, and inventory icon rendering.

The engine is intentionally self-contained and dependency-light.  It resolves
vanilla-style model parent chains and texture variables, bakes Java model
`elements` into a mesh IR, and renders transparent PNG inventory icons with a
software orthographic/isometric renderer.  Generated/item-layer models are
rendered by compositing their texture layers, matching Java's 2D inventory icon
semantics more closely than forcing them through cube geometry.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

try:  # Pillow is preferred, but converter.sh environments do not always have it.
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover - exercised in minimal converter images
    Image = None
    ImageDraw = None

WarnFn = Callable[[str], None]

FACE_NORMALS = {
    "down": (0, -1, 0),
    "up": (0, 1, 0),
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
}

FACE_VERTICES = {
    "down": ((0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)),
    "up": ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),
    "north": ((1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0)),
    "south": ((0, 1, 1), (1, 1, 1), (1, 0, 1), (0, 0, 1)),
    "west": ((0, 1, 0), (0, 1, 1), (0, 0, 1), (0, 0, 0)),
    "east": ((1, 1, 1), (1, 1, 0), (1, 0, 0), (1, 0, 1)),
}


def _deep_merge(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    merged = dict(parent)
    for key, value in child.items():
        if key == "parent":
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def _clean_model_ref(ref: str) -> tuple[str, str]:
    if ":" in ref:
        namespace, model = ref.split(":", 1)
    else:
        namespace, model = "minecraft", ref
    return namespace, model


def _rotate_point(point: tuple[float, float, float], origin: tuple[float, float, float], axis: str, angle: float) -> tuple[float, float, float]:
    if not angle:
        return point
    x, y, z = point
    ox, oy, oz = origin
    x -= ox
    y -= oy
    z -= oz
    rad = math.radians(angle)
    c = math.cos(rad)
    s = math.sin(rad)
    if axis == "x":
        y, z = y * c - z * s, y * s + z * c
    elif axis == "y":
        x, z = x * c + z * s, -x * s + z * c
    elif axis == "z":
        x, y = x * c - y * s, x * s + y * c
    return (x + ox, y + oy, z + oz)


@dataclass(frozen=True)
class BakedFace:
    direction: str
    vertices: tuple[tuple[float, float, float], ...]
    uv: tuple[float, float, float, float]
    texture: str | None
    tintindex: int | None = None


@dataclass
class BakedModel:
    source: Path
    model_id: str
    parent_chain: list[str]
    textures: dict[str, str]
    display: dict[str, Any]
    overrides: list[dict[str, Any]]
    faces: list[BakedFace] = field(default_factory=list)
    generated_layers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def bounding_box(self) -> dict[str, list[float]]:
        points = [vertex for face in self.faces for vertex in face.vertices]
        if not points:
            return {"min": [0, 0, 0], "max": [0, 0, 0]}
        return {
            "min": [min(p[i] for p in points) for i in range(3)],
            "max": [max(p[i] for p in points) for i in range(3)],
        }

    def to_ir(self) -> dict[str, Any]:
        return {
            "source": self.source.as_posix(),
            "model_id": self.model_id,
            "parent_chain": self.parent_chain,
            "textures": self.textures,
            "display": self.display,
            "overrides": self.overrides,
            "bounding_box": self.bounding_box,
            "generated_layers": self.generated_layers,
            "faces": [
                {
                    "direction": face.direction,
                    "vertices": [list(vertex) for vertex in face.vertices],
                    "uv": list(face.uv),
                    "texture": face.texture,
                    "tintindex": face.tintindex,
                }
                for face in self.faces
            ],
            "warnings": self.warnings,
        }


class JavaModelEngine:
    def __init__(self, assets_root: Path = Path("assets"), warn: WarnFn | None = None):
        self.assets_root = assets_root
        self.warn = warn or (lambda message: None)
        self._json_cache: dict[Path, dict[str, Any] | None] = {}
        self._resolved_cache: dict[Path, dict[str, Any]] = {}
        self._texture_cache: dict[Path, Any | None] = {}

    def model_id_for_path(self, path: Path) -> str:
        parts = path.parts
        try:
            assets_idx = parts.index(self.assets_root.name)
            namespace = parts[assets_idx + 1]
            models_idx = parts.index("models")
            rel = Path(*parts[models_idx + 1:]).with_suffix("").as_posix()
            return f"{namespace}:{rel}"
        except Exception:
            return path.with_suffix("").as_posix()

    def path_for_model_id(self, model_id: str) -> Path | None:
        namespace, model = _clean_model_ref(model_id)
        candidates = [self.assets_root / namespace / "models" / f"{model}.json"]
        if namespace == "minecraft":
            candidates.append(self.assets_root / "minecraft" / "models" / f"{model}.json")
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def load_json(self, path: Path) -> dict[str, Any] | None:
        path = path.resolve()
        if path in self._json_cache:
            return self._json_cache[path]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                self.warn(f"Model JSON is not an object: {path}")
                data = None
        except Exception as exc:
            self.warn(f"Could not parse model JSON {path}: {exc}")
            data = None
        self._json_cache[path] = data
        return data

    def resolve_model(self, path: Path, stack: tuple[Path, ...] = ()) -> dict[str, Any] | None:
        path = path.resolve()
        if path in self._resolved_cache:
            return self._resolved_cache[path]
        if path in stack:
            self.warn(f"Circular model parent chain detected: {' -> '.join(p.as_posix() for p in stack + (path,))}")
            return None
        data = self.load_json(path)
        if data is None:
            return None
        parent_ref = data.get("parent")
        chain: list[str] = []
        builtin_parents = {
            "builtin/generated",
            "builtin/entity",
            "item/generated",
            "item/handheld",
            "item/handheld_rod",
        }
        if parent_ref and parent_ref not in builtin_parents:
            parent_path = self.path_for_model_id(str(parent_ref))
            if parent_path is None:
                self.warn(f"Missing parent '{parent_ref}' for model {path}")
            else:
                parent = self.resolve_model(parent_path, stack + (path,))
                if parent:
                    chain = list(parent.get("__parent_chain", [])) + [str(parent_ref)]
                    data = _deep_merge(parent, data)
        elif parent_ref:
            chain = [str(parent_ref)]
        data = dict(data)
        data["__parent_chain"] = chain
        self._resolved_cache[path] = data
        return data

    def resolve_texture_name(self, texture_ref: str | None, textures: dict[str, str], depth: int = 0) -> str | None:
        if not texture_ref:
            return None
        if depth > 16:
            self.warn(f"Texture variable recursion exceeded for {texture_ref}")
            return None
        if texture_ref.startswith("#"):
            key = texture_ref[1:]
            value = textures.get(key)
            if value is None:
                self.warn(f"Missing texture variable #{key}")
                return None
            return self.resolve_texture_name(value, textures, depth + 1)
        return texture_ref

    def texture_path(self, texture_ref: str | None) -> Path | None:
        if not texture_ref:
            return None
        namespace, texture = _clean_model_ref(texture_ref)
        candidate = self.assets_root / namespace / "textures" / f"{texture}.png"
        return candidate if candidate.exists() else None

    def load_texture(self, texture_ref: str | None) -> Any | None:
        if Image is None:
            return None
        path = self.texture_path(texture_ref)
        if path is None:
            if texture_ref:
                self.warn(f"Missing texture asset {texture_ref}")
            return None
        path = path.resolve()
        if path not in self._texture_cache:
            try:
                self._texture_cache[path] = Image.open(path).convert("RGBA")
            except Exception as exc:
                self.warn(f"Could not decode texture {path}: {exc}")
                self._texture_cache[path] = None
        cached = self._texture_cache[path]
        return cached.copy() if cached else None

    def bake(self, model_path: Path) -> BakedModel | None:
        resolved = self.resolve_model(model_path)
        if resolved is None:
            return None
        textures = {str(k): str(v) for k, v in resolved.get("textures", {}).items() if isinstance(v, str)}
        model = BakedModel(
            source=model_path,
            model_id=self.model_id_for_path(model_path),
            parent_chain=list(resolved.get("__parent_chain", [])),
            textures=textures,
            display=resolved.get("display", {}) if isinstance(resolved.get("display"), dict) else {},
            overrides=resolved.get("overrides", []) if isinstance(resolved.get("overrides"), list) else [],
        )
        for key in sorted(textures):
            if key.startswith("layer"):
                tex = self.resolve_texture_name(f"#{key}", textures)
                if tex:
                    model.generated_layers.append(tex)
        elements = resolved.get("elements")
        if not elements:
            if not model.generated_layers:
                model.warnings.append("Model has no elements and no generated texture layers")
            return model
        if not isinstance(elements, list):
            model.warnings.append("Model elements field is not a list")
            return model
        for element in elements:
            if not isinstance(element, dict):
                continue
            self._bake_element(element, textures, model)
        return model

    def _bake_element(self, element: dict[str, Any], textures: dict[str, str], model: BakedModel) -> None:
        try:
            frm = tuple(float(v) for v in element.get("from", [0, 0, 0]))
            to = tuple(float(v) for v in element.get("to", [16, 16, 16]))
        except Exception:
            model.warnings.append(f"Invalid element bounds in {model.source}")
            return
        rotation = element.get("rotation", {}) if isinstance(element.get("rotation"), dict) else {}
        origin = tuple(float(v) for v in rotation.get("origin", [8, 8, 8]))
        axis = str(rotation.get("axis", "")).lower()
        angle = float(rotation.get("angle", 0) or 0)
        faces = element.get("faces", {}) if isinstance(element.get("faces"), dict) else {}
        for direction, face_def in faces.items():
            if direction not in FACE_VERTICES or not isinstance(face_def, dict):
                continue
            texture = self.resolve_texture_name(face_def.get("texture"), textures)
            uv = face_def.get("uv")
            if isinstance(uv, list) and len(uv) == 4:
                face_uv = tuple(float(v) for v in uv)
            else:
                face_uv = self._default_uv(direction, frm, to)
            verts = []
            for selector in FACE_VERTICES[direction]:
                point = tuple(frm[i] if selector[i] == 0 else to[i] for i in range(3))
                point = _rotate_point(point, origin, axis, angle) if axis in {"x", "y", "z"} else point
                verts.append(point)
            model.faces.append(BakedFace(direction, tuple(verts), face_uv, texture, face_def.get("tintindex")))

    @staticmethod
    def _default_uv(direction: str, frm: tuple[float, float, float], to: tuple[float, float, float]) -> tuple[float, float, float, float]:
        if direction in {"up", "down"}:
            return (frm[0], frm[2], to[0], to[2])
        if direction in {"north", "south"}:
            return (frm[0], 16 - to[1], to[0], 16 - frm[1])
        return (frm[2], 16 - to[1], to[2], 16 - frm[1])

    def render_icon(self, baked: BakedModel, output: Path, size: int = 64) -> bool:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            return True
        if baked.generated_layers:
            return self._render_generated_layers(baked, output, size)
        if baked.faces:
            return self._render_mesh(baked, output, size)
        baked.warnings.append(f"No renderable geometry or layers for {baked.model_id}")
        return False

    def _render_generated_layers(self, baked: BakedModel, output: Path, size: int) -> bool:
        if Image is None:
            first_layer = next((layer for layer in baked.generated_layers if self.texture_path(layer)), None)
            if first_layer:
                shutil.copy2(self.texture_path(first_layer), output)  # type: ignore[arg-type]
                self.warn(f"Pillow is not installed; copied generated layer for {baked.model_id} instead of compositing layers")
                return True
            return False
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rendered = False
        for layer in baked.generated_layers:
            texture = self.load_texture(layer)
            if texture is None:
                continue
            texture.thumbnail((size, size), Image.Resampling.NEAREST)
            x = (size - texture.width) // 2
            y = (size - texture.height) // 2
            canvas.alpha_composite(texture, (x, y))
            rendered = True
        if rendered:
            canvas.save(output)
        return rendered

    def _render_mesh(self, baked: BakedModel, output: Path, size: int) -> bool:
        if Image is None or ImageDraw is None:
            _write_solid_png(output, size, size, (255, 0, 255, 160))
            self.warn(f"Pillow is not installed; wrote fallback software PNG for mesh icon {baked.model_id}")
            return True
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        projected_faces = []
        for face in baked.faces:
            pts = [self._project(vertex, size) for vertex in face.vertices]
            depth = sum(vertex[0] + vertex[1] + vertex[2] for vertex in face.vertices) / len(face.vertices)
            projected_faces.append((depth, face, pts))
        for _, face, pts in sorted(projected_faces, key=lambda item: item[0]):
            patch = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).polygon(pts, fill=255)
            color = self._sample_face_color(face)
            ImageDraw.Draw(patch).polygon(pts, fill=color)
            patch.putalpha(mask)
            canvas.alpha_composite(patch)
        bbox = canvas.getbbox()
        if not bbox:
            return False
        canvas.save(output)
        return True

    @staticmethod
    def _project(vertex: tuple[float, float, float], size: int) -> tuple[float, float]:
        x, y, z = (coord - 8 for coord in vertex)
        px = (x - z) * 0.72
        py = (x + z) * 0.36 - y * 0.82
        scale = size / 24
        return (size / 2 + px * scale, size / 2 + py * scale + size * 0.08)

    def _sample_face_color(self, face: BakedFace) -> tuple[int, int, int, int]:
        texture = self.load_texture(face.texture)
        if texture is None:
            return (255, 0, 255, 220)
        u1, v1, u2, v2 = face.uv
        width, height = texture.size
        box = (
            max(0, min(width, round(u1 / 16 * width))),
            max(0, min(height, round(v1 / 16 * height))),
            max(0, min(width, round(u2 / 16 * width))),
            max(0, min(height, round(v2 / 16 * height))),
        )
        if box[0] >= box[2] or box[1] >= box[3]:
            sample = texture
        else:
            sample = texture.crop(box)
        pixels = [p for p in sample.getdata() if p[3] > 0]
        if not pixels:
            return (255, 255, 255, 0)
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)
        a = sum(p[3] for p in pixels) // len(pixels)
        shade = {"up": 1.08, "down": 0.55, "north": 0.78, "south": 0.9, "west": 0.68, "east": 0.82}.get(face.direction, 1.0)
        return (min(255, int(r * shade)), min(255, int(g * shade)), min(255, int(b * shade)), a)


def stable_icon_name(model_id: str) -> str:
    return "rendered_" + hashlib.sha1(model_id.encode("utf-8")).hexdigest()[:12]


def iter_model_files(assets_root: Path = Path("assets")) -> Iterable[Path]:
    return assets_root.glob("*/models/**/*.json")


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)


def _write_solid_png(path: Path, width: int, height: int, rgba: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scanline = bytes(rgba) * width
    raw = b"".join(b"\x00" + scanline for _ in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(raw))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)
