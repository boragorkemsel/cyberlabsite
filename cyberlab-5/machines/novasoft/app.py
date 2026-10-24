"""
NovaSoft - Kurumsal Web Sitesi (Kasitli zafiyetli - KOLAY seviye)
CyberLab TR egitim amacli - GERCEK ORTAMDA KULLANMAYIN!

Senaryo:
  NovaSoft adli bir yazilim sirketinin yeni web sitesi yayinda. Ama aceleyle
  hazirlandigi icin bircok "baslangic seviyesi" guvenlik hatasi var.
  Gorevin: Temel web kesif (recon) teknikleriyle 5 flag'i bulmak.
  Bu makine yeni baslayanlar icindir; tarayici ve basit araclarla cozulur.

Zafiyetler (hepsi kolay / recon):
  1. HTML yorumunda gizli flag (sayfa kaynagini goruntule)
  2. robots.txt -> gizli/eski bir sayfayi aciga cikarir
  3. Base64 ile kodlanmis gizli kod (coz)
  4. Varsayilan parola (admin / admin123)
  5. Gizli debug parametresi (?debug=true)
"""
import os
import sys
import base64
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "novasoft_demo_key"

FLAGS = {
    "html":    "CLAB{html_yorumlari_her_zaman_oku_a1c3}",
    "robots":  "CLAB{robots_txt_gizli_yol_gosterdi_d4f6}",
    "base64":  "CLAB{base64_cozuldu_gizli_kod_g7h9}",
    "parola":  "CLAB{varsayilan_parola_asla_birakma_k2m4}",
    "debug":   "CLAB{debug_modu_acik_kaldi_n5p7}",
}

# Base64 gorevi: flag'i base64 olarak kodla (oyuncu geri cozecek)
BETA_KOD_B64 = base64.b64encode(FLAGS["base64"].encode()).decode()

VARSAYILAN_KULLANICI = "admin"
VARSAYILAN_PAROLA = "admin123"

CSS = """
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',Arial,sans-serif; background:#0f1117; color:#e8ecf3; }
.nav { background:#151924; padding:16px 32px; display:flex; align-items:center;
       justify-content:space-between; border-bottom:1px solid #232838; }
.logo { font-size:1.3rem; font-weight:800; color:#fff; letter-spacing:.5px; }
.logo span { color:#7c5cff; }
.nav-links a { color:#9aa3b5; text-decoration:none; margin-left:24px; font-size:.92rem; font-weight:500; }
.nav-links a:hover { color:#fff; }
.hero { text-align:center; padding:90px 24px 70px; background:linear-gradient(180deg,#151924,#0f1117); }
.hero h1 { font-size:2.8rem; color:#fff; margin-bottom:16px; }
.hero h1 span { color:#7c5cff; }
.hero p { color:#9aa3b5; font-size:1.15rem; max-width:560px; margin:0 auto 28px; line-height:1.6; }
.wrap { max-width:820px; margin:0 auto; padding:40px 24px; }
.card { background:#151924; border:1px solid #232838; border-radius:14px; padding:30px; margin-bottom:22px; }
h2 { color:#fff; font-size:1.4rem; margin-bottom:14px; }
h3 { color:#c7cedb; font-size:1.05rem; margin-bottom:8px; }
p { line-height:1.7; color:#b5bdcc; margin-bottom:10px; }
.btn { background:#7c5cff; color:#fff; border:none; padding:12px 26px; border-radius:9px;
       font-size:.95rem; font-weight:600; cursor:pointer; text-decoration:none; display:inline-block;
       font-family:inherit; margin-top:10px; transition:background .15s; }
.btn:hover { background:#6847e0; }
label { display:block; font-size:.86rem; font-weight:600; color:#9aa3b5; margin:12px 0 5px; }
input { width:100%; padding:11px 13px; border:1px solid #2b3245; border-radius:8px;
        background:#0f1117; color:#e8ecf3; font-size:.95rem; font-family:inherit; }
input:focus { outline:none; border-color:#7c5cff; }
.feature-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:18px; }
.feature { background:#0f1117; border:1px solid #232838; border-radius:10px; padding:20px; }
.feature .ic { font-size:1.6rem; }
.feature h3 { margin:10px 0 6px; color:#fff; }
.feature p { font-size:.88rem; }
.code-box { background:#0a0c12; border:1px solid #232838; border-radius:8px; padding:14px 16px;
            font-family:monospace; color:#7c5cff; word-break:break-all; margin:12px 0; font-size:.95rem; }
.flagbox { background:#0a0c12; border:1px solid #2e7d46; color:#3fb950; font-family:monospace;
           padding:14px 16px; border-radius:8px; margin:12px 0; word-break:break-all; }
.alert { padding:12px 16px; border-radius:8px; margin-bottom:14px; font-size:.92rem; }
.alert-err { background:#2a1416; color:#ff6b6b; border:1px solid #5c2626; }
.alert-ok { background:#13241a; color:#3fb950; border:1px solid #27512f; }
.debug { background:#1a1206; border:1px solid #6b4e14; color:#f0b847; padding:16px; border-radius:8px; margin:14px 0; }
.footer { text-align:center; color:#5a6478; font-size:.85rem; padding:30px; border-top:1px solid #232838; margin-top:30px; }
</style>
"""

def nav():
    return """
    <div class="nav">
        <div class="logo">Nova<span>Soft</span></div>
        <div class="nav-links">
            <a href="/">Ana Sayfa</a>
            <a href="/hakkimizda">Hakkimizda</a>
            <a href="/kariyer">Kariyer</a>
            <a href="/sistem">Sistem Durumu</a>
            <a href="/yonetici">Giris</a>
        </div>
    </div>
    """

def sayfa(govde):
    return CSS + nav() + govde + \
        '<div class="footer">NovaSoft Yazilim A.S. &copy; 2024 &middot; Tum haklari saklidir.</div>'


@app.route("/")
def home():
    # KASITLI ZAFIYET 1: HTML yorumunda gizli flag + robots ipucu
    govde = f"""
    <div class="hero">
        <h1>Gelecegi <span>NovaSoft</span> ile Kodlayin</h1>
        <p>Isletmeniz icin modern yazilim cozumleri. Bulut, mobil ve yapay zeka
           alaninda uctan uca hizmet.</p>
        <a class="btn" href="/kariyer">Bize Katilin</a>
    </div>
    <!--
      Gelistirici notu: Siteyi hizlica yayina aldik.
      TODO: Asagidaki test flag'ini kaldirmayi unutma!
      {FLAGS['html']}
      Ayrica /robots.txt dosyasini da guncelle.
    -->
    <div class="wrap">
        <div class="card">
            <h2>Hizmetlerimiz</h2>
            <div class="feature-grid">
                <div class="feature"><div class="ic">&#9729;</div><h3>Bulut</h3><p>Olceklenebilir altyapi.</p></div>
                <div class="feature"><div class="ic">&#128241;</div><h3>Mobil</h3><p>iOS ve Android uygulamalar.</p></div>
                <div class="feature"><div class="ic">&#129302;</div><h3>Yapay Zeka</h3><p>Akilli otomasyon.</p></div>
            </div>
        </div>
    </div>
    """
    return sayfa(govde)


@app.route("/hakkimizda")
def hakkimizda():
    govde = """
    <div class="wrap">
        <div class="card">
            <h2>Hakkimizda</h2>
            <p>NovaSoft, 2019 yilinda kurulmus bir yazilim sirketidir. 50'den fazla
               muhendisimizle Turkiye'nin onde gelen sirketlerine hizmet veriyoruz.</p>
            <p>Misyonumuz: Teknolojiyi herkes icin erisilebilir kilmak.</p>
        </div>
    </div>
    """
    return sayfa(govde)


@app.route("/robots.txt")
def robots():
    # KASITLI ZAFIYET 2: robots.txt gizli/eski bir sayfayi aciga cikarir
    return ("User-agent: *\n"
            "Disallow: /eski-panel\n"
            "Disallow: /kariyer\n"
            "# Not: /eski-panel eski surumden kaldi, arama motorlari gormesin.\n"), \
           200, {"Content-Type": "text/plain"}


@app.route("/eski-panel")
def eski_panel():
    govde = f"""
    <div class="wrap">
        <div class="card">
            <h2>Eski Yonetim Paneli (Kullanim Disi)</h2>
            <p>Bu sayfa eski surumden kalmistir ve artik kullanilmamaktadir.
               Yeni panele <a href="/yonetici" style="color:#7c5cff">buradan</a> ulasin.</p>
            <p>Ama birileri burada bir seyi unutmus gibi gorunuyor...</p>
            <div class="flagbox">{FLAGS['robots']}</div>
        </div>
    </div>
    """
    return sayfa(govde)


@app.route("/kariyer")
def kariyer():
    # KASITLI ZAFIYET 3: base64 ile kodlanmis gizli kod sayfada gorunur
    govde = f"""
    <div class="wrap">
        <div class="card">
            <h2>Kariyer</h2>
            <p>NovaSoft ailesine katilmak ister misin? Acik pozisyonlarimiz:</p>
            <p>&bull; Backend Gelistirici &bull; Guvenlik Uzmani &bull; DevOps Muhendisi</p>
            <h3 style="margin-top:20px">Basvuru Referans Kodu</h3>
            <p>Basvurunda asagidaki beta referans kodunu kullanman gerekiyor
               (kodlanmis halde saklanir):</p>
            <div class="code-box">{BETA_KOD_B64}</div>
            <p style="font-size:.85rem;color:#7585a0">Not: Bu kod standart bir kodlama ile saklanmaktadir.</p>
        </div>
    </div>
    """
    return sayfa(govde)


@app.route("/sistem")
def sistem():
    # KASITLI ZAFIYET 5: gizli debug parametresi
    debug = request.args.get("debug", "").lower() == "true"
    debug_blok = ""
    if debug:
        debug_blok = f"""
        <div class="debug">
            <strong>&#128295; DEBUG MODU AKTIF</strong><br>
            Ortam: production<br>
            Veritabani: nova_db @ 10.0.0.12<br>
            Surum: 2.4.1-beta<br>
            Debug anahtari (gizli): {FLAGS['debug']}
        </div>
        """
    govde = f"""
    <div class="wrap">
        <div class="card">
            <h2>Sistem Durumu</h2>
            <p>Tum servisler calisiyor. &#9989;</p>
            <p>Web Sunucusu: Aktif &middot; API: Aktif &middot; Veritabani: Aktif</p>
            {debug_blok}
            <p style="font-size:.85rem;color:#7585a0;margin-top:16px">
               Gelistiriciler icin: ek bilgi gormek icin debug parametresi kullanilabilir.</p>
        </div>
    </div>
    """
    return sayfa(govde)


@app.route("/yonetici", methods=["GET", "POST"])
def yonetici():
    # KASITLI ZAFIYET 4: varsayilan parola degistirilmemis (admin/admin123)
    alert = ""
    if request.method == "POST":
        k = request.form.get("kullanici", "")
        p = request.form.get("parola", "")
        if k == VARSAYILAN_KULLANICI and p == VARSAYILAN_PAROLA:
            alert = f"""<div class="alert alert-ok">Giris basarili! Hos geldin, yonetici.</div>
                        <div class="flagbox">{FLAGS['parola']}</div>"""
        else:
            alert = '<div class="alert alert-err">Kullanici adi veya parola hatali.</div>'
    govde = f"""
    <div class="wrap">
        <div class="card" style="max-width:420px;margin:0 auto;">
            <h2>Yonetici Girisi</h2>
            {alert}
            <form method="POST">
                <label>Kullanici Adi</label>
                <input name="kullanici" placeholder="kullanici adi" autocomplete="off" required>
                <label>Parola</label>
                <input type="password" name="parola" placeholder="parola" required>
                <button class="btn" type="submit" style="width:100%">Giris Yap</button>
            </form>
            <p style="font-size:.82rem;color:#7585a0;margin-top:14px">
               Ipucu: Kurulumdan sonra varsayilan parolayi degistirmeyi unutmayin!</p>
        </div>
    </div>
    """
    return sayfa(govde)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7002
    print(f"[NovaSoft] Zafiyetli kurumsal site port {port}'da calisiyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
