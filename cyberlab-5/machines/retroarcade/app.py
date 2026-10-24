"""
RetroArcade - Retro Oyun Sitesi (Kasitli zafiyetli - KOLAY seviye)
CyberLab TR egitim amacli - GERCEK ORTAMDA KULLANMAYIN!

Senaryo:
  RetroArcade, eski tarz oyunlar oynatan bir hobi sitesi. Gelistiricisi
  guvenlige pek dikkat etmemis. Gorevin: 5 farkli yontemle flag'leri bulmak.
  Bu makine HackMe/NovaSoft'tan FARKLI teknikler ogretir.

Zafiyetler (hepsi kolay, farkli yontemler):
  1. Istemci tarafi (client-side) JS ile sifre kontrolu  -> JS'i oku
  2. HTTP yanit basliginda (response header) gizli flag   -> basliklara bak
  3. Dizin listeleme (directory listing) acik             -> dosyalari gez
  4. Gizli form alani (hidden field) manipulasyonu         -> alani degistir
  5. Hex (onaltilik) ile kodlanmis oyuncu kodu             -> hex coz
"""
import os
import sys
from flask import Flask, request, render_template_string, Response, make_response

app = Flask(__name__)

FLAGS = {
    "clientjs": "CLAB{js_asla_guvenli_degil_r3tr0}",
    "header":   "CLAB{http_basligi_bayragi_h34d3r}",
    "dirlist":  "CLAB{acik_dizin_listeleme_d1rl1st}",
    "hidden":   "CLAB{gizli_form_alani_degisti_h1dd3n}",
    "hex":      "CLAB{hex_kodu_cozuldu_h3xx}",
}

# Hex gorevi: oyuncu kodu hex olarak gosterilir
OYUNCU_KODU_HEX = FLAGS["hex"].encode().hex()

# Dizin listeleme icin bellekteki "dosyalar"
ESKI_OYUNLAR = {
    "pacman.txt": "Pac-Man - 1980 - Namco klasigi.",
    "tetris.txt": "Tetris - 1984 - Alexey Pajitnov.",
    "oku_beni.txt": "RetroArcade arsiv klasoru. Dikkat: bazi dosyalar gizli olmali!",
    ".gizli_not.txt": f"Yonetici notu: Bu klasoru kapatmayi unuttuk.\nFlag: {FLAGS['dirlist']}",
}

CSS = """
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Courier New',monospace; background:#1a0033; color:#f0e6ff; }
.scanlines { background:
  repeating-linear-gradient(0deg, rgba(0,0,0,.15) 0 1px, transparent 1px 3px); min-height:100vh; }
.nav { background:#2d0052; padding:16px 28px; display:flex; align-items:center;
       justify-content:space-between; border-bottom:3px solid #ff2e9a; }
.logo { font-size:1.5rem; font-weight:bold; color:#ffea00; text-shadow:2px 2px #ff2e9a; letter-spacing:2px; }
.nav a { color:#8be9fd; text-decoration:none; margin-left:20px; font-size:.9rem; }
.nav a:hover { color:#ffea00; }
.wrap { max-width:760px; margin:0 auto; padding:34px 22px; }
.card { background:#2d0052; border:2px solid #6a2c9c; border-radius:10px; padding:24px; margin-bottom:20px; }
h1 { color:#ffea00; text-shadow:2px 2px #ff2e9a; margin-bottom:12px; font-size:1.9rem; }
h2 { color:#ff2e9a; margin-bottom:12px; }
p { line-height:1.7; margin-bottom:10px; color:#d8c6f0; }
a.link { color:#8be9fd; }
.btn { background:#ff2e9a; color:#fff; border:none; padding:11px 22px; border-radius:7px;
       font-family:inherit; font-weight:bold; cursor:pointer; text-decoration:none; display:inline-block; margin-top:8px; }
.btn:hover { background:#ff5bb0; }
input,select { width:100%; padding:10px 12px; margin:8px 0; background:#1a0033; border:1px solid #6a2c9c;
               color:#f0e6ff; border-radius:6px; font-family:inherit; }
.flagbox { background:#0a0012; border:1px solid #3fb950; color:#3fb950; padding:13px 15px;
           border-radius:7px; margin:12px 0; word-break:break-all; }
.filelist a { display:block; padding:9px 12px; color:#8be9fd; text-decoration:none;
              border-bottom:1px solid #3d1766; font-family:monospace; }
.filelist a:hover { background:#3d1766; color:#ffea00; }
.ok { color:#3fb950; } .err { color:#ff6b6b; }
.code { background:#0a0012; border:1px solid #6a2c9c; padding:12px; border-radius:6px;
        font-family:monospace; color:#ffea00; word-break:break-all; margin:10px 0; }
.footer { text-align:center; color:#6a4c8c; padding:24px; font-size:.82rem; }
</style>
"""

def nav():
    return """
    <div class="nav">
        <div class="logo">&#128377; RETRO<span style="color:#8be9fd">ARCADE</span></div>
        <div>
            <a href="/">Ana Sayfa</a>
            <a href="/uye-girisi">Uye Girisi</a>
            <a href="/skor-tablosu">Skor Tablosu</a>
            <a href="/eski-oyunlar/">Arsiv</a>
            <a href="/profil">Profil</a>
        </div>
    </div>
    """

def sayfa(govde):
    return '<div class="scanlines">' + CSS + nav() + \
challenge_wrap(govde) + '<div class="footer">RetroArcade &copy; 1985-2024 &middot; Insert Coin to Continue</div></div>'

def challenge_wrap(govde):
    return f'<div class="wrap">{govde}</div>'


@app.route("/")
def home():
    # ZAFIYET 2: gizli flag HTTP yanit basliginda
    html = sayfa("""
    <div class="card">
        <h1>RETROARCADE'E HOS GELDIN</h1>
        <p>En iyi retro oyunlar burada! Pac-Man, Tetris, Space Invaders ve daha fazlasi.</p>
        <p>Uye ol, skorlarini kaydet, lider tablosuna gir!</p>
        <a class="btn" href="/uye-girisi">OYUNA BASLA</a>
    </div>
    <div class="card">
        <h2>Haftanin Oyunu</h2>
        <p>&#127918; Space Invaders - Dunya rekoru kirmaya var misin?</p>
    </div>
    """)
    resp = make_response(html)
    # Gelistirici buraya debug amacli bir baslik koymus ve kaldirmayi unutmus
    resp.headers["X-Oyun-Bayrak"] = FLAGS["header"]
    resp.headers["X-Powered-By"] = "RetroEngine/2.1"
    return resp


@app.route("/uye-girisi")
def uye_girisi():
    # ZAFIYET 1: sifre kontrolu TAMAMEN istemci tarafinda (JavaScript)
    govde = """
    <div class="card">
        <h1>Uye Girisi</h1>
        <p>VIP uye alanina girmek icin gizli sifreyi gir:</p>
        <input type="password" id="sifre" placeholder="VIP sifresi...">
        <button class="btn" onclick="kontrolEt()">Giris Yap</button>
        <p id="sonuc" style="margin-top:14px"></p>
    </div>
    <script>
      // VIP uye dogrulama sistemi (v1.0)
      function kontrolEt() {
        var girilen = document.getElementById('sifre').value;
        var dogruSifre = "retroVIP2024!";
        var gizliBayrak = "CLAB{js_asla_guvenli_degil_r3tr0}";
        if (girilen === dogruSifre) {
          document.getElementById('sonuc').innerHTML =
            '<span class="ok">Dogru! VIP bayragin: ' + gizliBayrak + '</span>';
        } else {
          document.getElementById('sonuc').innerHTML =
            '<span class="err">Yanlis sifre. Tekrar dene.</span>';
        }
      }
    </script>
    """
    return sayfa(govde)


@app.route("/skor-tablosu", methods=["GET", "POST"])
def skor_tablosu():
    # ZAFIYET 4: gizli form alani (hidden field) - rol=oyuncu, admin yapilabilir
    mesaj = ""
    if request.method == "POST":
        rol = request.form.get("rol", "oyuncu")
        isim = request.form.get("isim", "anonim")
        if rol == "admin":
            mesaj = f"""<div class="flagbox">Admin olarak skor eklendi! {FLAGS['hidden']}</div>"""
        else:
            mesaj = f'<p class="ok">Skorun eklendi, {isim}! (rol: {rol})</p>'
    govde = f"""
    <div class="card">
        <h1>Skor Tablosu</h1>
        <p>&#129351; 1. NEO ....... 99999</p>
        <p>&#129352; 2. RETRO ..... 85400</p>
        <p>&#129353; 3. PIXEL ..... 72100</p>
    </div>
    <div class="card">
        <h2>Skorunu Ekle</h2>
        {mesaj}
        <form method="POST">
            <input name="isim" placeholder="Oyuncu adin" autocomplete="off">
            <!-- rol alani normal oyuncular icin 'oyuncu' olmali -->
            <input type="hidden" name="rol" value="oyuncu">
            <button class="btn" type="submit">Skoru Gonder</button>
        </form>
    </div>
    """
    return sayfa(govde)


@app.route("/eski-oyunlar/")
def dizin_listesi():
    # ZAFIYET 3: dizin listeleme acik - tum dosyalar (gizli olanlar dahil) gorunur
    satirlar = ""
    for ad in sorted(ESKI_OYUNLAR.keys()):
        satirlar += f'<a href="/eski-oyunlar/{ad}">&#128196; {ad}</a>'
    govde = f"""
    <div class="card">
        <h1>Index of /eski-oyunlar/</h1>
        <p style="color:#6a4c8c">Apache/2.4.41 Dizin Listeleme</p>
        <div class="filelist">
            <a href="/">&#128193; ../ (ust dizin)</a>
            {satirlar}
        </div>
    </div>
    """
    return sayfa(govde)


@app.route("/eski-oyunlar/<path:dosya>")
def dizin_dosya(dosya):
    icerik = ESKI_OYUNLAR.get(dosya)
    if icerik is None:
        return sayfa('<div class="card"><h1>404</h1><p>Dosya bulunamadi.</p></div>'), 404
    return Response(icerik, mimetype="text/plain")


@app.route("/profil")
def profil():
    # ZAFIYET 5: oyuncu kodu hex olarak gosterilir
    govde = f"""
    <div class="card">
        <h1>Oyuncu Profili</h1>
        <p>Kullanici: Misafir</p>
        <p>Seviye: 7 &middot; Puan: 12.450</p>
        <h2 style="margin-top:18px">Oyuncu Kodun</h2>
        <p>Benzersiz oyuncu kodun asagida (makine tarafindan okunabilir formatta saklanir):</p>
        <div class="code">{OYUNCU_KODU_HEX}</div>
        <p style="font-size:.84rem;color:#6a4c8c">Format: onaltilik (hexadecimal) kodlama.</p>
    </div>
    """
    return sayfa(govde)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7004
    print(f"[RetroArcade] Zafiyetli retro oyun sitesi port {port}'da calisiyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
