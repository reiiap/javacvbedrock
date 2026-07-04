# 🚀 Java ➜ Bedrock Resource Pack Converter  
### Versi ReiiAp

Converter untuk mengubah Resource Pack Minecraft Java Edition menjadi format Bedrock Edition dengan dukungan Custom Model Data, model 3D, dan integrasi Geyser.

Repository ini merupakan versi yang dikelola dan diotomatisasi oleh ReiiAp, berbasis dari project asli milik Kas-tle.

---

## 📦 Tentang Project Ini

Script ini akan mengubah:

- Resource Pack Java Edition (.zip)
- Custom Model Data (predicate)
- Model 3D Item
- Model Block
- Texture Atlas
- Validasi JSON/YAML best-effort
- Java model parser untuk parent chain, texture variable, element, display, dan
  override metadata
- Baking model ke intermediate representation (`target/model_ir/*.json`)
- Rendering inventory icon otomatis untuk model yang bisa dipanggang
- File bahasa Java (`assets/*/lang/*.json` dan `.lang`)
- `sounds.json` + file OGG
- Metadata animasi `.png.mcmeta` sebagai `flipbook_textures.json`

Menjadi:

- Resource Pack Bedrock Edition
- Behavior Pack (untuk preview model)
- File mapping kompatibel Geyser
- config.json berisi hash model
- `conversion_report.json` berisi resource yang ditemukan, aset yang dikonversi,
  peringatan, error non-fatal, dan durasi proses

Project ini cocok untuk server yang menggunakan:
- GeyserMC
- Custom Item
- Server Hybrid Java-Bedrock

---

## 🖥 Cara Menjalankan (Local)

Pastikan file `.zip` resource pack Java dan script converter berada di folder yang sama.

Jalankan:

./converter.sh NamaResourcePack.zip

---

## ⚙ Opsi Tambahan (Flags)

| Flag | Fungsi |
|------|--------|
| `-w` | Nonaktifkan prompt warning |
| `-m` | Merge dengan Bedrock pack lain (.mcpack) |
| `-a` | Override material attachable |
| `-b` | Override material block |
| `-f` | URL fallback Java pack |
| `-v` | Versi default asset Java |

Contoh penggunaan:

./converter.sh MyPack.zip -w false -m "BasePack.mcpack" -v "1.18.2"

---

## 🧩 Dukungan Custom Icon (sprites.json)

Jika menggunakan sprite 2D untuk model 3D, tambahkan file `sprites.json` di root resource pack Java.

Contoh format:

{
  "diamond_sword": [
    {
      "custom_model_data": 1,
      "sprite": "textures/items/custom_sword"
    }
  ]
}

File ini akan otomatis terintegrasi ke:

- item_texture.json
- File mapping Geyser

---

## 🤖 Versi GitHub Actions (Otomatis)

Repository ini mendukung sistem otomatis melalui GitHub Actions.

Cara pakai:

1. Buat Issue baru  
2. Masukkan link public .zip resource pack Java  
3. Sistem akan memproses otomatis  
4. Bot akan membalas dengan link hasil convert  
5. Issue akan tertutup otomatis  

---

## 📂 Output Yang Dihasilkan

Converter akan menghasilkan:

- Resource Pack Bedrock  
- Behavior Pack (preview model)  
- File mapping Geyser  
- config.json  
- Conversion report (`target/conversion_report.json`)
- Bedrock text files (`target/rp/texts/*.lang`) jika pack Java memiliki bahasa
- Bedrock sound definitions (`target/rp/sounds/sound_definitions.json`) jika pack
  Java memiliki `sounds.json`
- Bedrock flipbook metadata (`target/rp/textures/flipbook_textures.json`) untuk
  tekstur animasi yang memiliki `.png.mcmeta`
- Baked model IR (`target/model_ir/*.json`) dan icon hasil render
  (`target/rp/textures/items/generated/*.png`) untuk model Java yang valid

Hash model dibuat berdasarkan kombinasi predicate dan MD5 (7 karakter pertama) dan akan tetap konsisten walaupun dilakukan convert ulang.

---

## 🧪 Pipeline Best-Effort

Selain alur utama `converter.sh`, repository ini menjalankan
`javacv_pipeline.py` sebelum packaging. Pipeline ini tidak mengganti proses
konversi yang sudah ada; ia menambahkan tahap produksi yang aman dan
non-fatal:

1. Discover namespace, model, tekstur, animasi, suara, font, bahasa, serta
   marker plugin ItemsAdder, Nexo, dan Oraxen.
2. Validasi JSON / `.mcmeta` dan YAML bila PyYAML tersedia.
3. Resolve parent model Java, texture variable, element, display transform,
   override, Custom Model Data metadata, dan baked mesh IR.
4. Render icon inventory otomatis dari model generated/layered dan model
   element-based. Jika Pillow tidak tersedia, pipeline tetap melanjutkan dengan
   fallback aman dan warning.
5. Konversi language Java ke format `.lang` Bedrock.
6. Konversi `sounds.json` ke `sound_definitions.json` dan menyalin OGG.
7. Konversi metadata animasi `.png.mcmeta` ke `flipbook_textures.json`.
8. Menulis laporan lengkap ke `target/conversion_report.json`.

Jika ada aset hilang, JSON invalid, YAML invalid, atau fitur yang tidak bisa
dikonversi tepat, pipeline akan mencatat warning dan melanjutkan proses.

---

## ⚠ Catatan Penting

- Block dengan ukuran lebih dari 1.9 block tidak akan ter-load (limit Bedrock).
- Output hanya bisa digunakan di Bedrock 1.16.210 ke atas.
- Aktifkan setting "Holiday Creator Features".
- Disarankan menggunakan Creative Mode untuk preview model.

Command untuk mendapatkan item hasil convert:

/give @p geysercmd:gmdl_xxxxxxx

---

## 📦 Dependencies

Dibutuhkan:

- jq (1.6+)
- moreutils
- imagemagick (6+)
- nodejs
- spritesheet-js
- unzip
- zip
- uuid-runtime

Contoh install Ubuntu:

> sudo apt install moreutils jq imagemagick unzip zip nodejs uuid-runtime
> npm i -g spritesheet-js  

---

## 🪟 Untuk Pengguna Windows

Disarankan menggunakan WSL (Ubuntu).

Jika jq yang terinstall versi 1.5, install manual versi 1.6:

wget https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64  
sudo chmod +x jq-linux64  
sudo mv jq-linux64 /usr/bin/jq  

---

## 👤 Kredit


Project By:  
https://github.com/reiiap

---

## 📜 Lisensi

GNU AFFERO GENERAL PUBLIC LICENSE.
