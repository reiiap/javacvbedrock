"""Source- and target-neutral Minecraft resource IR.

The classes in this module intentionally do not model Java Edition, Bedrock
Edition, or any third-party plugin format. They are the stable contract shared by
parsers, validators, transformers, optimizers, and generators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Sequence


class ResourceKind(StrEnum):
    TEXTURE = "texture"
    MODEL = "model"
    FONT = "font"
    SOUND = "sound"
    ANIMATION = "animation"
    ITEM = "item"
    BLOCK = "block"
    ENTITY = "entity"
    ATTACHABLE = "attachable"
    PARTICLE = "particle"
    LANGUAGE = "language"
    ATLAS = "atlas"
    PACK_METADATA = "pack_metadata"
    MANIFEST = "manifest"


@dataclass(frozen=True, slots=True)
class ResourceId:
    namespace: str
    path: str

    def as_key(self) -> str:
        return f"{self.namespace}:{self.path}"


@dataclass(frozen=True, slots=True)
class Resource:
    id: ResourceId
    kind: ResourceKind
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class TextureResource(Resource):
    image_ref: str = ""
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class ModelResource(Resource):
    parent: ResourceId | None = None
    texture_refs: Sequence[ResourceId] = ()
    geometry: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FontResource(Resource):
    providers: Sequence[Mapping[str, Any]] = ()


@dataclass(frozen=True, slots=True)
class SoundResource(Resource):
    sound_refs: Sequence[str] = ()
    category: str | None = None


@dataclass(frozen=True, slots=True)
class AnimationResource(Resource):
    target: ResourceId | None = None
    timeline: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ItemResource(Resource):
    model: ResourceId | None = None
    textures: Sequence[ResourceId] = ()
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BlockResource(Resource):
    model: ResourceId | None = None
    textures: Sequence[ResourceId] = ()
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EntityResource(Resource):
    model: ResourceId | None = None
    animations: Sequence[ResourceId] = ()
    textures: Sequence[ResourceId] = ()


@dataclass(frozen=True, slots=True)
class AttachableResource(Resource):
    model: ResourceId | None = None
    textures: Sequence[ResourceId] = ()
    animations: Sequence[ResourceId] = ()


@dataclass(frozen=True, slots=True)
class ParticleResource(Resource):
    texture: ResourceId | None = None
    definition: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LanguageResource(Resource):
    locale: str = ""
    translations: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AtlasResource(Resource):
    texture_refs: Sequence[ResourceId] = ()
    layout: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PackMetadataResource(Resource):
    name: str = ""
    description: str = ""
    version: Sequence[int] = ()


@dataclass(frozen=True, slots=True)
class ManifestResource(Resource):
    modules: Sequence[Mapping[str, Any]] = ()
    dependencies: Sequence[Mapping[str, Any]] = ()
