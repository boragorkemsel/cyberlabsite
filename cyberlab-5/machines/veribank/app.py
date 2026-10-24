"""
VeriBank - Internet Subesi (Kasitli zafiyetli bankacilik uygulamasi)
CyberLab TR egitim amacli - GERCEK ORTAMDA KULLANMAYIN!

Senaryo:
  VeriBank'in internet subesi aceleyle gelistirilmis. Guvenlik testi (sizma testi)
  senin gorevin. Sana normal bir musteri hesabi verildi:
      Kullanici: musteri01   Parola: parola123
  Bu hesapla giris yap ve bankadaki zafiyetleri bulup flag'leri topla.

Zafiyetler:
  1. IDOR (Insecure Direct Object Reference) - baskasinin hesap detayini goruntuleme
  2. Cerez ile yetki yukseltme (privilege escalation) - rol cerezini degistirme
  3. Acik API / bilgi ifsasi - kimlik dogrulama olmayan API endpoint
  4. PIN kaba kuvvet (brute force) - hiz siniri olmayan 4 haneli PIN
  5. Is mantigi hatasi (business logic) - negatif tutarli transfer
"""
import os
import sys
from flask import (Flask, request, render_template_string, redirect,
                   session, make_response, jsonify, url_for)

app = Flask(__name__)
app.secret_key = "veribank_zayif_anahtar_2024"  # kasitli zayif anahtar

# ----- FLAG'LER -----
FLAGS = {
    "idor":    "CLAB{idor_mudur_hesabi_ele_gecti_9b2x}",
    "cerez":   "CLAB{cerez_rolu_yonetici_yapildi_4k7p}",
    "api":     "CLAB{acik_api_veri_sizdirdi_6m3q}",
    "pin":     "CLAB{pin_kaba_kuvvet_kirildi_2w8n}",
    "mantik":  "CLAB{negatif_transfer_bakiye_patladi_5t1v}",
}

GECERLI_PIN = "7391"          # 4 haneli kart PIN'i (brute force hedefi)
MANTIK_ESIGI = 1_000_000      # bu bakiyeyi gecince is mantigi flag'i acilir

# ----- VERITABANI (bellekte) -----
# Kullanici giris bilgileri
KULLANICILAR = {
    "musteri01": {"parola": "parola123", "hesap_no": 100123, "ad": "Mehmet Demir"},
}

# Hesaplar - IDOR ve API icin. 100100 = Genel Mudur (IDOR flag burada)
HESAPLAR = {
    100100: {"ad": "Ahmet Yilmaz", "unvan": "Genel Mudur", "bakiye": 8_540_250.75,
             "iban": "TR12 0006 1005 1978 6457 8410 00",
             "not": f"OZEL HESAP - Yonetim kurulu erisimi. Guvenlik notu: {FLAGS['idor']}"},
    100123: {"ad": "Mehmet Demir", "unvan": "Bireysel Musteri", "bakiye": 2500.00,
             "iban": "TR33 0006 1005 1978 6457 8410 23",
             "not": "Standart vadesiz mevduat hesabi."},
    100150: {"ad": "Ayse Kaya", "unvan": "Bireysel Musteri", "bakiye": 14230.40,
             "iban": "TR44 0006 1005 1978 6457 8410 50",
             "not": "Standart vadesiz mevduat hesabi."},
    100177: {"ad": "Can Ozturk", "unvan": "Ticari Musteri", "bakiye": 302150.00,
             "iban": "TR55 0006 1005 1978 6457 8410 77",
             "not": "Ticari hesap - KOBI paketi."},
}

# API'de sizan gizli destek hesabi (sadece API'de gorunur - bilgi ifsasi)
API_GIZLI = {"id": 999001, "ad": "VeriBank Destek Botu", "unvan": "Sistem",
             "aktif": True,
             "not": f"Dahili sistem hesabi - prod'da gizlenmeliydi: {FLAGS['api']}"}


# ----- ORTAK SABLON PARCALARI -----
CSS = """
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; background:#eef2f7; color:#1a2435; }
.topbar { background:linear-gradient(90deg,#0a2a5e,#114393); color:#fff; padding:0 24px;
          display:flex; align-items:center; justify-content:space-between; height:62px;
          box-shadow:0 2px 10px rgba(0,0,0,.15); }
.brand { font-size:1.35rem; font-weight:700; letter-spacing:.5px; display:flex; align-items:center; gap:10px; }
.brand .logo { width:30px; height:30px; background:#2d9cdb; border-radius:7px;
               display:flex; align-items:center; justify-content:center; font-size:1rem; }
.topnav a { color:#cfe0f5; text-decoration:none; margin-left:20px; font-size:.92rem; font-weight:500; }
.topnav a:hover { color:#fff; }
.wrap { max-width:860px; margin:30px auto; padding:0 20px; }
.card { background:#fff; border-radius:12px; padding:26px; margin-bottom:20px;
        box-shadow:0 2px 12px rgba(16,40,80,.07); border:1px solid #e3e9f2; }
h1 { font-size:1.5rem; margin-bottom:6px; color:#0a2a5e; }
h2 { font-size:1.15rem; margin-bottom:14px; color:#114393; }
p { line-height:1.6; margin-bottom:8px; }
label { display:block; font-size:.86rem; font-weight:600; color:#44536b; margin:12px 0 5px; }
input, select { width:100%; padding:11px 13px; border:1px solid #cdd7e5; border-radius:8px;
                font-size:.95rem; font-family:inherit; background:#fafcff; }
input:focus { outline:none; border-color:#2d9cdb; box-shadow:0 0 0 3px rgba(45,156,219,.15); }
.btn { background:#114393; color:#fff; border:none; padding:11px 24px; border-radius:8px;
       font-size:.95rem; font-weight:600; cursor:pointer; font-family:inherit; text-decoration:none;
       display:inline-block; margin-top:14px; transition:background .15s; }
.btn:hover { background:#0a2a5e; }
.btn-light { background:#eaf1fb; color:#114393; }
.btn-light:hover { background:#d8e6f8; }
.muted { color:#7585a0; font-size:.88rem; }
.row { display:flex; gap:16px; flex-wrap:wrap; }
.row > div { flex:1; min-width:200px; }
.tag { display:inline-block; background:#eaf1fb; color:#114393; padding:3px 11px;
       border-radius:20px; font-size:.78rem; font-weight:600; }
.saldo { font-size:2rem; font-weight:700; color:#0a7d3c; margin:6px 0; }
.kv { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid #eef2f7; }
.kv:last-child { border-bottom:none; }
.kv span:first-child { color:#7585a0; font-size:.88rem; }
.kv span:last-child { font-weight:600; }
.alert { padding:13px 16px; border-radius:8px; margin-bottom:16px; font-size:.92rem; }
.alert-ok { background:#e6f7ec; color:#0a7d3c; border:1px solid #b6e6c8; }
.alert-err { background:#fdeaea; color:#c0392b; border:1px solid #f5c6c6; }
.alert-info{ background:#eaf4fd; color:#114393; border:1px solid #c3dcf5; }
.flagbox { background:#0d1117; color:#3fb950; font-family:monospace; padding:14px 16px;
           border-radius:8px; margin:12px 0; font-size:.95rem; word-break:break-all; }
.menu-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-top:8px; }
.menu-item { background:#f6f9fd; border:1px solid #e3e9f2; border-radius:10px; padding:18px;
             text-decoration:none; color:#1a2435; display:block; transition:border-color .15s, transform .1s; }
.menu-item:hover { border-color:#2d9cdb; transform:translateY(-2px); }
.menu-item .mi-ic { font-size:1.4rem; }
.menu-item .mi-t { font-weight:700; margin:6px 0 2px; color:#114393; }
.menu-item .mi-d { font-size:.82rem; color:#7585a0; }
.footer { text-align:center; color:#9aa7bd; font-size:.82rem; padding:20px; }
table { width:100%; border-collapse:collapse; margin-top:10px; }
th,td { text-align:left; padding:10px 12px; border-bottom:1px solid #eef2f7; font-size:.9rem; }
th { color:#7585a0; font-weight:600; font-size:.8rem; text-transform:uppercase; }
</style>
"""

def topbar(giris=True):
    if giris and session.get("kullanici"):
        links = """
        <a href="/pano">Panom</a>
        <a href="/hesap/detay?no={}">Hesabim</a>
        <a href="/transfer">Para Transferi</a>
        <a href="/cikis">Cikis</a>
        """.format(session.get("hesap_no", ""))
    else:
        links = '<a href="/">Ana Sayfa</a> <a href="/login">Giris</a>'
    return f"""
    <div class="topbar">
        <div class="brand"><span class="logo">&#127974;</span> VeriBank <span style="font-weight:400;font-size:.85rem;opacity:.8">Internet Subesi</span></div>
        <div class="topnav">{links}</div>
    </div>
    """


def sayfa(govde, giris=True):
    return CSS + topbar(giris) + f'<div class="wrap">{govde}</div>' + \
        '<div class="footer">VeriBank &copy; 2024 &middot; Guvenli internet bankaciligi &middot; Musteri Hizmetleri: 0850 000 00 00</div>'


# ----- ROTALAR -----
@app.route("/")
def home():
    if session.get("kullanici"):
        return redirect("/pano")
    govde = """
    <div class="card">
        <h1>VeriBank Internet Subesi'ne Hos Geldiniz</h1>
        <p class="muted">Hesabiniza guvenle erisin. Lutfen giris yapin.</p>
        <a class="btn" href="/login">Giris Yap</a>
    </div>
    <div class="card">
        <h2>Duyuru</h2>
        <p>Yeni internet subemiz yayinda! Daha hizli, daha modern.
           Sorun yasarsaniz BT ekibimize bildirin.</p>
        <p class="muted">Not: Sistem guvenlik denetiminden gecmektedir.</p>
    </div>
    """
    return sayfa(govde, giris=False)


@app.route("/login", methods=["GET", "POST"])
def login():
    hata = None
    if request.method == "POST":
        k = request.form.get("kullanici", "").strip()
        p = request.form.get("parola", "")
        u = KULLANICILAR.get(k)
        if u and u["parola"] == p:
            session["kullanici"] = k
            session["hesap_no"] = u["hesap_no"]
            session["ad"] = u["ad"]
            # Baslangic bakiyesi session'da tutulur (transfer icin)
            session["bakiye"] = HESAPLAR[u["hesap_no"]]["bakiye"]
            resp = make_response(redirect("/pano"))
            # KASITLI ZAFIYET: rol duz metin cerezde tutuluyor!
            resp.set_cookie("vb_rol", "musteri")
            return resp
        hata = "Kullanici adi veya parola hatali."
    alert = f'<div class="alert alert-err">{hata}</div>' if hata else ''
    govde = f"""
    <div class="card" style="max-width:420px;margin:0 auto;">
        <h1>Giris Yap</h1>
        {alert}
        <form method="POST">
            <label>Kullanici Adi</label>
            <input name="kullanici" placeholder="musteri01" autocomplete="off" required>
            <label>Parola</label>
            <input type="password" name="parola" placeholder="********" required>
            <button class="btn" type="submit" style="width:100%">Giris Yap</button>
        </form>
        <p class="muted" style="margin-top:16px">
            <strong>Test hesabi:</strong> musteri01 / parola123
        </p>
    </div>
    """
    return sayfa(govde, giris=False)


def _giris_gerekli():
    return bool(session.get("kullanici"))


@app.route("/pano")
def pano():
    if not _giris_gerekli():
        return redirect("/login")
    no = session["hesap_no"]
    h = HESAPLAR[no]
    bakiye = session.get("bakiye", h["bakiye"])
    # NOT: Asagidaki HTML yorumunda dahili API endpoint ipucu birakilmis (bilgi ifsasi)
    govde = f"""
    <div class="card">
        <h1>Merhaba, {session['ad']}</h1>
        <p class="muted">Hesap No: {no} &middot; {h['unvan']}</p>
        <div class="saldo">{bakiye:,.2f} TL</div>
        <span class="tag">Vadesiz Mevduat</span>
    </div>
    <div class="card">
        <h2>Islemler</h2>
        <div class="menu-grid">
            <a class="menu-item" href="/hesap/detay?no={no}">
                <div class="mi-ic">&#128179;</div><div class="mi-t">Hesap Detayi</div>
                <div class="mi-d">Hesap bilgilerini goruntule</div>
            </a>
            <a class="menu-item" href="/transfer">
                <div class="mi-ic">&#128184;</div><div class="mi-t">Para Transferi</div>
                <div class="mi-d">EFT / Havale gonder</div>
            </a>
            <a class="menu-item" href="/kart-dogrula">
                <div class="mi-ic">&#128273;</div><div class="mi-t">Kart Dogrulama</div>
                <div class="mi-d">Kart PIN dogrulama</div>
            </a>
            <a class="menu-item" href="/yonetim">
                <div class="mi-ic">&#9881;</div><div class="mi-t">Yonetim</div>
                <div class="mi-d">Sadece yetkili personel</div>
            </a>
        </div>
    </div>
    <!-- TODO (BT ekibi): /api/v1/kullanicilar endpoint'i hala acik, prod'da kapatilacak -->
    <script>
      // Dahili hesap ozeti servisi (gelistirme asamasi)
      // fetch('/api/v1/kullanicilar').then(r => r.json())
    </script>
    """
    return sayfa(govde)


@app.route("/hesap/detay")
def hesap_detay():
    if not _giris_gerekli():
        return redirect("/login")
    # KASITLI IDOR: 'no' parametresi kullanicinin kendi hesabi mi diye KONTROL EDILMIYOR!
    try:
        no = int(request.args.get("no", session["hesap_no"]))
    except ValueError:
        no = session["hesap_no"]
    h = HESAPLAR.get(no)
    if not h:
        govde = '<div class="card"><h1>Hesap bulunamadi</h1><p class="muted">Bu numarada bir hesap yok.</p><a class="btn btn-light" href="/pano">Panoya don</a></div>'
        return sayfa(govde)
    # Kendi hesabinda session bakiyesini goster, digerlerinde kayitli bakiye
    bakiye = session.get("bakiye", h["bakiye"]) if no == session["hesap_no"] else h["bakiye"]
    govde = f"""
    <div class="card">
        <h1>Hesap Detayi</h1>
        <p class="muted">Hesap No: {no}</p>
        <div class="saldo">{bakiye:,.2f} TL</div>
    </div>
    <div class="card">
        <h2>Hesap Bilgileri</h2>
        <div class="kv"><span>Hesap Sahibi</span><span>{h['ad']}</span></div>
        <div class="kv"><span>Unvan</span><span>{h['unvan']}</span></div>
        <div class="kv"><span>IBAN</span><span>{h['iban']}</span></div>
        <div class="kv"><span>Aciklama / Not</span><span>{h['not']}</span></div>
    </div>
    <a class="btn btn-light" href="/pano">Panoya don</a>
    """
    return sayfa(govde)


@app.route("/yonetim")
def yonetim():
    if not _giris_gerekli():
        return redirect("/login")
    # KASITLI ZAFIYET: yetki, degistirilebilir 'vb_rol' cerezinden okunuyor
    rol = request.cookies.get("vb_rol", "musteri")
    if rol != "yonetici":
        govde = f"""
        <div class="card">
            <h1>Yonetim Paneli</h1>
            <div class="alert alert-err">Erisim reddedildi. Bu alan sadece <strong>yonetici</strong> rolundeki personele aciktir.</div>
            <p class="muted">Mevcut rolunuz: <strong>{rol}</strong></p>
            <a class="btn btn-light" href="/pano">Panoya don</a>
        </div>
        """
        return sayfa(govde)
    govde = f"""
    <div class="card">
        <h1>Yonetim Paneli</h1>
        <div class="alert alert-ok">Yonetici olarak giris yaptin! Hos geldin.</div>
        <h2>Gizli Yonetim Verileri</h2>
        <div class="kv"><span>Toplam musteri</span><span>4</span></div>
        <div class="kv"><span>Toplam mevduat</span><span>8.859.131,15 TL</span></div>
        <div class="flagbox">{FLAGS['cerez']}</div>
    </div>
    <a class="btn btn-light" href="/pano">Panoya don</a>
    """
    return sayfa(govde)


@app.route("/api/v1/kullanicilar")
def api_kullanicilar():
    # KASITLI ZAFIYET: kimlik dogrulama YOK, tum hesaplar + gizli destek hesabi sizar.
    # (Hesaplarin ozel 'not' alani burada paylasilmaz; asil sizinti gizli destek hesabidir.)
    data = []
    for hid, h in HESAPLAR.items():
        data.append({"id": hid, "ad": h["ad"], "unvan": h["unvan"],
                     "iban": h["iban"]})
    data.append(API_GIZLI)
    return jsonify({"durum": "ok", "kayit_sayisi": len(data), "kullanicilar": data})


@app.route("/kart-dogrula", methods=["GET", "POST"])
def kart_dogrula():
    if not _giris_gerekli():
        return redirect("/login")
    alert = ""
    # KASITLI ZAFIYET: PIN denemelerinde hiz siniri / kilitleme YOK (brute force)
    if request.method == "POST":
        pin = request.form.get("pin", "").strip()
        if pin == GECERLI_PIN:
            alert = f"""<div class="alert alert-ok">Kart dogrulandi! Islem onaylandi.</div>
                        <div class="flagbox">{FLAGS['pin']}</div>"""
        else:
            alert = '<div class="alert alert-err">Hatali PIN. Tekrar deneyin.</div>'
    govde = f"""
    <div class="card" style="max-width:420px;margin:0 auto;">
        <h1>Kart Dogrulama</h1>
        <p class="muted">Kartinizin 4 haneli PIN kodunu girin.</p>
        {alert}
        <form method="POST">
            <label>PIN (4 hane)</label>
            <input name="pin" maxlength="4" placeholder="****" autocomplete="off" required>
            <button class="btn" type="submit" style="width:100%">Dogrula</button>
        </form>
    </div>
    """
    return sayfa(govde)


@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if not _giris_gerekli():
        return redirect("/login")
    bakiye = session.get("bakiye", HESAPLAR[session["hesap_no"]]["bakiye"])
    alert = ""
    if request.method == "POST":
        hedef = request.form.get("hedef", "").strip()
        try:
            tutar = float(request.form.get("tutar", "0"))
        except ValueError:
            tutar = 0
        # KASITLI IS MANTIGI HATASI: tutarin pozitif olmasi KONTROL EDILMIYOR.
        # Negatif tutar gonderince para hesaptan dusmek yerine EKLENIR.
        if not hedef:
            alert = '<div class="alert alert-err">Hedef hesap/IBAN bos olamaz.</div>'
        else:
            bakiye = bakiye - tutar   # negatif tutar => bakiye artar
            session["bakiye"] = bakiye
            if bakiye >= MANTIK_ESIGI:
                alert = f"""<div class="alert alert-ok">Transfer tamamlandi. Yeni bakiye: {bakiye:,.2f} TL</div>
                <div class="alert alert-info">Olaganustu bakiye tespit edildi! Denetim kodu:</div>
                <div class="flagbox">{FLAGS['mantik']}</div>"""
            else:
                alert = f'<div class="alert alert-ok">Transfer tamamlandi. Yeni bakiye: {bakiye:,.2f} TL</div>'
    govde = f"""
    <div class="card">
        <h1>Para Transferi</h1>
        <p class="muted">Guncel bakiye: <strong>{bakiye:,.2f} TL</strong></p>
        {alert}
        <form method="POST">
            <label>Hedef Hesap / IBAN</label>
            <input name="hedef" placeholder="TR.. veya hesap no" autocomplete="off" required>
            <label>Tutar (TL)</label>
            <input name="tutar" placeholder="0.00" autocomplete="off" required>
            <button class="btn" type="submit" style="width:100%">Transferi Gonder</button>
        </form>
    </div>
    <a class="btn btn-light" href="/pano">Panoya don</a>
    """
    return sayfa(govde)


@app.route("/cikis")
def cikis():
    session.clear()
    resp = make_response(redirect("/"))
    resp.delete_cookie("vb_rol")
    return resp


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7001
    print(f"[VeriBank] Zafiyetli bankacilik uygulamasi port {port}'da calisiyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
