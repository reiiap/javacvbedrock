from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from javacvbedrock.diagnostics import Severity
from javacvbedrock.loading import PackKind, PackSourceError, ResourcePackLoader, ResourceType


class ResourcePackLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_pack(self, root: Path) -> None:
        (root / "assets" / "minecraft" / "textures" / "item").mkdir(parents=True)
        (root / "assets" / "minecraft" / "models" / "item").mkdir(parents=True)
        (root / "pack.mcmeta").write_text('{"pack":{"pack_format":15,"description":"test"}}', encoding="utf-8")
        (root / "assets" / "minecraft" / "textures" / "item" / "stick.png").write_bytes(b"png-data")
        (root / "assets" / "minecraft" / "models" / "item" / "stick.json").write_text("{}", encoding="utf-8")

    def test_folder_input_indexes_resources_and_namespaces(self) -> None:
        pack = self.root / "folder-pack"
        self._write_pack(pack)

        index = ResourcePackLoader().load(pack)

        self.assertEqual(index.origin_pack.kind, PackKind.VANILLA)
        self.assertEqual(index.namespaces, frozenset({"minecraft"}))
        self.assertEqual(len(index.entries), 3)
        self.assertEqual(len(index.by_type(ResourceType.PNG)), 1)
        texture = next(entry for entry in index.entries if entry.file_extension == "png")
        self.assertEqual(texture.namespace, "minecraft")
        self.assertEqual(texture.file_size, len(b"png-data"))
        self.assertEqual(len(texture.sha256), 64)
        self.assertEqual(index.read(texture), b"png-data")

    def test_zip_input_indexes_resources(self) -> None:
        pack = self.root / "zip-pack"
        self._write_pack(pack)
        archive = self.root / "zip-pack.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for path in pack.rglob("*"):
                output.write(path, path.relative_to(pack).as_posix())

        index = ResourcePackLoader().load(archive)

        self.assertEqual(index.origin_pack.kind, PackKind.VANILLA)
        self.assertEqual(len(index.by_namespace("minecraft")), 2)
        self.assertTrue(any(entry.relative_path.as_posix() == "pack.mcmeta" for entry in index.entries))

    def test_broken_zip_raises_pack_source_error(self) -> None:
        archive = self.root / "broken.zip"
        archive.write_bytes(b"not a zip")

        with self.assertRaises(PackSourceError):
            ResourcePackLoader().load(archive)

    def test_missing_assets_generates_warning(self) -> None:
        pack = self.root / "metadata-only"
        pack.mkdir()
        (pack / "pack.mcmeta").write_text("{}", encoding="utf-8")

        index = ResourcePackLoader().load(pack)

        warnings = [diagnostic.code for diagnostic in index.log.diagnostics if diagnostic.severity == Severity.WARNING]
        self.assertIn("assets.missing", warnings)

    def test_duplicate_files_generate_recoverable_error(self) -> None:
        pack = self.root / "duplicate-pack"
        self._write_pack(pack)
        duplicate = pack / "assets" / "minecraft" / "textures" / "item" / "Stick.PNG"
        duplicate.write_bytes(b"other")

        index = ResourcePackLoader().load(pack)

        errors = [diagnostic.code for diagnostic in index.log.diagnostics if diagnostic.severity == Severity.RECOVERABLE_ERROR]
        self.assertIn("path.duplicate", errors)

    def test_large_pack_indexes_all_files(self) -> None:
        pack = self.root / "large-pack"
        (pack / "assets" / "example" / "textures" / "item").mkdir(parents=True)
        (pack / "pack.mcmeta").write_text("{}", encoding="utf-8")
        for number in range(1200):
            (pack / "assets" / "example" / "textures" / "item" / f"item_{number}.png").write_bytes(
                f"data-{number}".encode()
            )

        index = ResourcePackLoader().load(pack)

        self.assertEqual(len(index.entries), 1201)
        self.assertEqual(len(index.by_type(ResourceType.PNG)), 1200)
        self.assertEqual(index.namespaces, frozenset({"example"}))


if __name__ == "__main__":
    unittest.main()
