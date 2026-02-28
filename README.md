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

Menjadi:

- Resource Pack Bedrock Edition
- Behavior Pack (untuk preview model)
- File mapping kompatibel Geyser
- config.json berisi hash model

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

Hash model dibuat berdasarkan kombinasi predicate dan MD5 (7 karakter pertama) dan akan tetap konsisten walaupun dilakukan convert ulang.

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

Distributed under the MIT License.
