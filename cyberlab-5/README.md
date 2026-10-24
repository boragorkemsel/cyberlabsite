# CyberLab TR

Yerel ağda çalışan, TryHackMe / HackTheBox tarzı Türkçe siber güvenlik
eğitim platformu — MVP (ilk sürüm).

## Özellikler (bu sürüm)

- **Panelim** — kişisel kontrol paneli: rütbe + ilerleme, puan, günlük seri,
  zorluğa göre ilerleme, önerilen lab, son aktiviteler, rozetler
- **Rütbe sistemi** — toplam puana göre Çaylak → Acemi → Gözcü → … → Efsane
- **Rozetler/başarımlar** — 13 otomatik kazanılan rozet (gamification.py)
- **Günlük seri (streak)** — ardışık aktif günler
- **23 gerçek, çözülebilir lab** (makinesiz, hepsi statik dosya)
- Her lab'da birden çok görev, indirilebilir dosya, açıklayıcı ipuçları, puan
- Lab'da **arama + kategori + zorluk + durum (çözüldü/çözülmedi)** filtreleri
- **Sıralama** — Haftalık ve Tüm Zamanlar, rütbe rozetleriyle
- Lab tamamlama kutlaması (konfeti) + "Tekrar Çöz" ile sıfırlama
- Profil resmi (kırpma aracıyla), parola değiştirme
- Anasayfa, Öğren, Fiyatlandırma, Hakkında, İletişim/Destek sayfaları
- Mor / siyah tema

## Laboratuvarlar (makinesiz / ücretsiz içerik)

| Lab | Kategori | Zorluk | Dosya |
|-----|----------|--------|-------|
| Paket Avı | Ağ Adli Bilişimi | Kolay | capture.pcap |
| Log Dedektifi | Log Analizi / Blue Team | Kolay | access.log |
| Gizli Mesaj | Steganografi | Kolay | gizli.png |
| Katman Katman | Steganografi / Dosya Analizi | Orta | kapak.jpg |
| Şifre Çözücü | Kriptografi | Orta | mesaj.txt |
| Kırılan Parola | Hash Kırma | Orta | hashes.txt, wordlist.txt |
| Dijital İz | OSINT / Metadata | Kolay | fotograf.png |

Flag formatı: **`CLAB{...}`** (platformun kendi formatı).

Toplam **23 lab / 39 görev** (makinesiz, ücretsiz içerik). İlk 7'si `db.py`
içinde tanımlı; diğer 16'sı `gen_labs2.py` ile üretilip `labs2_seed.json`'a yazılır.

Lab dosyaları `labfiles/` klasöründedir. Dosyaları yeniden üretmek için:

    python3 gen_labs.py      # ilk 7 lab'ın dosyaları
    python3 gen_labs2.py     # diğer 16 lab + labs2_seed.json (kendi içinde doğrular)
    python3 db.py            # veritabanını baştan kur (tüm labları yükler)

`gen_labs2.py` her lab'ı ürettikten sonra çözüp cevabı doğrular; "Tüm
doğrulamalar BAŞARILI" yazması tüm flag'lerin dosyalarla tutarlı olduğunu gösterir.

Yeni lab eklerken: cevaplar dosya içeriğinden türetildiği için tek kaynak
`gen_labs2.py`'dır — orada ekle, çalıştır, `python3 db.py` ile yükle.

## Gereksinimler

Python 3.9+ ve şu paketler: **Flask, Jinja2, Werkzeug** (Flask ile birlikte gelir).

Kurulu değilse:

    pip install Flask

## Çalıştırma

    cd cyberlab
    python3 app.py

Açılınca kendi bilgisayarında:  http://127.0.0.1:5000

### Yerel ağdaki diğer cihazlardan erişim

Uygulama `0.0.0.0:5000` dinler. Aynı Wi-Fi/ağdaki başka bir cihazdan
bu bilgisayarın IP'si ile gir:

    http://<bilgisayarin-ip-adresi>:5000

IP'yi öğrenmek için:
- Linux/Mac:  `ip addr` veya `ifconfig`
- Windows:    `ipconfig`

> Not: Güvenlik duvarı 5000 portuna izin vermiyorsa açman gerekebilir.

## Veritabanı

SQLite (`cyberlab.db`) ilk çalıştırmada otomatik oluşur ve laboratuvarlar
yüklenir. Sıfırlamak için dosyayı sil, yeniden başlat. İçeriği yeniden
yüklemek için:

    python3 db.py

## Güvenlik notu (MVP)

- `debug=True` sadece geliştirme içindir; gerçek yayında kapat.
- Üretimde sabit bir gizli anahtar ver:  `CYBERLAB_SECRET` ortam değişkeni.
- Flag'ler şu an veritabanında düz metin ve herkese aynı. İleride kullanıcıya
  özel üretim + hash karşılaştırma eklenecek.

## Yol haritası (sonraki adımlar)

1. Kullanıcıya özel, dinamik flag üretimi
2. Writeup / çözüm ve ipucu sistemi (kademeli ipuçları)
3. Gerçek "makine başlat" altyapısı (Docker konteyner + izolasyon + VPN)
4. Liderlik tablosu (leaderboard) ve rozetler
5. PostgreSQL'e geçiş, admin paneli (lab ekleme/düzenleme)
6. KVKK uyumu (aydınlatma metni, açık rıza) ve kullanım şartları / AUP
