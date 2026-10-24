"""
DevHub - Gelistirici Isbirligi Platformu (Kasitli zafiyetli - ZOR seviye)
CyberLab TR egitim amacli - GERCEK ORTAMDA KULLANMAYIN!

Senaryo:
  DevHub, yazilimcilarin proje ve snippet paylastigi dahili bir platform.
  Ileri seviye web zafiyetleri barindirir. Giris: gelistirici / dev123
  Bu makine ZOR seviyedir; araclar ve script gerektirebilir.

Zafiyetler (ileri seviye, hepsi FARKLI):
  1. JWT alg:none  -> imzasiz token ile yetki yukseltme (admin)
  2. SSTI (Jinja2) -> sunucu sablonuna enjeksiyon, config sizdirma
  3. SSRF          -> sunucu tarafli istekle sadece dahili endpoint'e erisim
  4. UNION SQLi    -> arama kutusundan gizli tabloyu dump etme
  5. Pickle Insecure Deserialization -> base64 pickle ile kod calistirma
"""
import os
import sys
import json
import hmac
import base64
import hashlib
import pickle
import sqlite3
import subprocess
import urllib.request
from flask import Flask, request, render_template_string, redirect, make_response

app = Flask(__name__)

FLAGS = {
    "jwt":    "CLAB{jwt_alg_none_imzasiz_token_j0n3}",
    "ssti":   "CLAB{ssti_jinja2_config_sizdi_t3mpl}",
    "ssrf":   "CLAB{ssrf_dahili_servise_ulasildi_1nt3rnal}",
    "sqli":   "CLAB{union_sqli_gizli_tablo_un10n}",
    "pickle": "CLAB{pickle_rce_deserializasyon_p1ckl3}",
}

# SSTI icin flag'i Flask config'e koy ({{config}} ile sizar)
app.config["DEVHUB_SECRET"] = FLAGS["ssti"]

JWT_SECRET = "dh_s3cret_imza_anahtari_2024"
GIZLI_DOSYA = "devhub_gizli.txt"   # pickle RCE hedefi (cwd'de olusturulur)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devhub.db")


# ---------- JWT (stdlib ile, harici kutuphane yok) ----------
def _b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def _b64url_dec(s):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())

def jwt_olustur(payload):
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(JWT_SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"

def jwt_dogrula(token):
    try:
        h_b64, p_b64, s_b64 = token.split(".")
        header = json.loads(_b64url_dec(h_b64))
        payload = json.loads(_b64url_dec(p_b64))
        # KASITLI ZAFIYET: alg "none" ise imza KONTROL EDILMEZ!
        if str(header.get("alg", "")).lower() == "none":
            return payload
        beklenen = hmac.new(JWT_SECRET.encode(), f"{h_b64}.{p_b64}".encode(),
                            hashlib.sha256).digest()
        if hmac.compare_digest(_b64url(beklenen), s_b64):
            return payload
        return None
    except Exception:
        return None


# ---------- Veritabani (UNION SQLi icin) ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS snippetler")
    conn.execute("DROP TABLE IF EXISTS gizli")
    conn.execute("CREATE TABLE snippetler (id INTEGER, baslik TEXT, dil TEXT)")
    conn.execute("CREATE TABLE gizli (anahtar TEXT, deger TEXT)")
    conn.executemany("INSERT INTO snippetler VALUES (?,?,?)", [
        (1, "Hizli siralama", "Python"),
        (2, "Binary arama", "C++"),
        (3, "JWT olusturucu", "JavaScript"),
        (4, "CSV okuyucu", "Python"),
    ])
    conn.execute("INSERT INTO gizli VALUES (?,?)", ("admin_flag", FLAGS["sqli"]))
    conn.commit()
    conn.close()


CSS = """
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'SF Mono','Consolas',monospace; background:#0d1117; color:#c9d1d9; }
.nav { background:#161b22; padding:14px 28px; display:flex; align-items:center;
       justify-content:space-between; border-bottom:1px solid #30363d; }
.logo { font-size:1.25rem; font-weight:700; color:#58a6ff; }
.logo b { color:#f0f6fc; }
.nav a { color:#8b949e; text-decoration:none; margin-left:20px; font-size:.9rem; }
.nav a:hover { color:#58a6ff; }
.wrap { max-width:820px; margin:0 auto; padding:34px 22px; }
.card { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:24px; margin-bottom:20px; }
h1 { color:#f0f6fc; font-size:1.6rem; margin-bottom:12px; }
h2 { color:#58a6ff; font-size:1.2rem; margin-bottom:12px; }
p { line-height:1.7; color:#8b949e; margin-bottom:10px; }
code,.mono { font-family:inherit; color:#79c0ff; }
label { display:block; font-size:.85rem; color:#8b949e; margin:12px 0 5px; font-weight:600; }
input,textarea { width:100%; padding:10px 12px; background:#0d1117; border:1px solid #30363d;
        color:#c9d1d9; border-radius:7px; font-family:inherit; font-size:.92rem; }
input:focus,textarea:focus { outline:none; border-color:#58a6ff; }
.btn { background:#238636; color:#fff; border:none; padding:10px 22px; border-radius:7px;
       font-family:inherit; font-weight:600; cursor:pointer; text-decoration:none; display:inline-block; margin-top:10px; }
.btn:hover { background:#2ea043; }
.flagbox { background:#0a0c10; border:1px solid #238636; color:#3fb950; padding:13px 15px;
           border-radius:7px; margin:12px 0; word-break:break-all; }
.alert { padding:11px 15px; border-radius:7px; margin-bottom:14px; font-size:.9rem; }
.alert-err { background:#2a1416; color:#f85149; border:1px solid #5c2626; }
.alert-ok { background:#0f2417; color:#3fb950; border:1px solid #1f6f3f; }
table { width:100%; border-collapse:collapse; margin-top:10px; }
th,td { text-align:left; padding:9px 12px; border-bottom:1px solid #30363d; font-size:.9rem; }
th { color:#8b949e; }
.out { background:#0a0c10; border:1px solid #30363d; border-radius:7px; padding:14px;
       font-family:inherit; color:#c9d1d9; white-space:pre-wrap; word-break:break-all; margin-top:12px; font-size:.88rem; }
.footer { text-align:center; color:#484f58; padding:26px; font-size:.82rem; }
.badge { background:#1f6feb33; color:#58a6ff; padding:2px 9px; border-radius:12px; font-size:.78rem; }
</style>
"""

def nav(payload=None):
    rol = payload.get("rol", "misafir") if payload else "misafir"
    return f"""
    <div class="nav">
        <div class="logo">Dev<b>Hub</b></div>
        <div>
            <a href="/">Panel</a>
            <a href="/snippet-ara">Snippet Ara</a>
            <a href="/profil">Profil</a>
            <a href="/webhook">Webhook</a>
            <a href="/oturum-geri-yukle">Oturum</a>
            <a href="/yonetim">Yonetim</a>
            <span class="badge">{rol}</span>
        </div>
    </div>
    """

def sayfa(govde, payload=None):
    return CSS + nav(payload) + f'<div class="wrap">{govde}</div>' + \
        '<div class="footer">DevHub &middot; Dahili Gelistirici Platformu v3.2</div>'


def mevcut_token():
    return request.cookies.get("dh_token", "")


@app.route("/")
def home():
    payload = jwt_dogrula(mevcut_token())
    if not payload:
        return redirect("/giris")
    govde = f"""
    <div class="card">
        <h1>Hos geldin, {payload.get('kullanici','gelistirici')}</h1>
        <p>DevHub paneline eristin. Rolun: <b>{payload.get('rol')}</b></p>
    </div>
    <div class="card">
        <h2>Hizli Erisim</h2>
        <p>&#128269; <a href="/snippet-ara" style="color:#58a6ff">Snippet Ara</a> - kod parcaciklarini ara</p>
        <p>&#128100; <a href="/profil" style="color:#58a6ff">Profil</a> - gorunen adini ayarla</p>
        <p>&#128279; <a href="/webhook" style="color:#58a6ff">Webhook</a> - URL onizleme araci</p>
        <p>&#128190; <a href="/oturum-geri-yukle" style="color:#58a6ff">Oturum</a> - kayitli oturumu yukle</p>
        <p>&#9881; <a href="/yonetim" style="color:#58a6ff">Yonetim</a> - sadece admin</p>
    </div>
    """
    return sayfa(govde, payload)


@app.route("/giris", methods=["GET", "POST"])
def giris():
    hata = ""
    if request.method == "POST":
        k = request.form.get("kullanici", "")
        p = request.form.get("parola", "")
        if k == "gelistirici" and p == "dev123":
            token = jwt_olustur({"kullanici": k, "rol": "uye"})
            resp = make_response(redirect("/"))
            resp.set_cookie("dh_token", token)
            return resp
        hata = '<div class="alert alert-err">Hatali giris bilgileri.</div>'
    govde = f"""
    <div class="card" style="max-width:420px;margin:0 auto;">
        <h1>DevHub Giris</h1>
        {hata}
        <form method="POST">
            <label>Kullanici</label><input name="kullanici" placeholder="gelistirici" autocomplete="off" required>
            <label>Parola</label><input type="password" name="parola" placeholder="dev123" required>
            <button class="btn" type="submit" style="width:100%">Giris Yap</button>
        </form>
        <p style="font-size:.82rem;margin-top:12px">Test: gelistirici / dev123</p>
    </div>
    """
    return sayfa(govde)


@app.route("/yonetim")
def yonetim():
    # ZAFIYET 1: yetki JWT'den okunur; alg:none ile rol=admin sahteleyebilirsin
    payload = jwt_dogrula(mevcut_token())
    if not payload:
        return redirect("/giris")
    if payload.get("rol") != "admin":
        govde = f"""
        <div class="card">
            <h1>Yonetim Paneli</h1>
            <div class="alert alert-err">Erisim yok. Bu alan sadece <b>admin</b> rolune aciktir.
            Mevcut rolun: <b>{payload.get('rol')}</b></div>
            <p>Not: Oturum bilgin JWT token'da (dh_token cerezi) tutulur.</p>
        </div>
        """
        return sayfa(govde, payload)
    govde = f"""
    <div class="card">
        <h1>Yonetim Paneli</h1>
        <div class="alert alert-ok">Admin erisimi onaylandi!</div>
        <div class="flagbox">{FLAGS['jwt']}</div>
    </div>
    """
    return sayfa(govde, payload)


@app.route("/profil", methods=["GET", "POST"])
def profil():
    # ZAFIYET 2: gorunen ad render_template_string ile islenir -> SSTI
    payload = jwt_dogrula(mevcut_token())
    if not payload:
        return redirect("/giris")
    ad = request.args.get("ad", "gelistirici")
    # KASITLI SSTI: kullanici girdisi dogrudan sablona konur
    try:
        karsilama = render_template_string("Merhaba " + ad + "! Profilin hazir.")
    except Exception as e:
        karsilama = f"Sablon hatasi: {e}"
    govde = f"""
    <div class="card">
        <h1>Profil</h1>
        <p>Gorunen adini degistirmek icin ?ad= parametresini kullan.</p>
        <div class="out">{karsilama}</div>
        <form method="get" style="margin-top:14px">
            <label>Gorunen Ad</label>
            <input name="ad" value="{ad}" autocomplete="off">
            <button class="btn" type="submit">Guncelle</button>
        </form>
    </div>
    """
    return sayfa(govde, payload)


@app.route("/snippet-ara")
def snippet_ara():
    # ZAFIYET 4: arama sorgusu dogrudan SQL'e konur -> UNION SQLi
    payload = jwt_dogrula(mevcut_token())
    if not payload:
        return redirect("/giris")
    q = request.args.get("q", "")
    sonuc_html = ""
    hata = ""
    if q:
        conn = sqlite3.connect(DB_PATH)
        sorgu = f"SELECT baslik, dil FROM snippetler WHERE baslik LIKE '%{q}%'"
        try:
            rows = conn.execute(sorgu).fetchall()
            satir = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>" for r in rows)
            sonuc_html = f"<table><tr><th>Baslik</th><th>Dil</th></tr>{satir}</table>"
        except Exception as e:
            hata = f'<div class="alert alert-err">SQL hatasi: {e}</div>'
        conn.close()
    govde = f"""
    <div class="card">
        <h1>Snippet Ara</h1>
        <p>Kod parcaciklarinda baslik ara.</p>
        <form method="get">
            <input name="q" value="{q}" placeholder="orn: Python" autocomplete="off">
            <button class="btn" type="submit">Ara</button>
        </form>
        {hata}
        {sonuc_html}
    </div>
    """
    return sayfa(govde, payload)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # ZAFIYET 3: sunucu, kullanici URL'sini kendisi ceker -> SSRF
    payload = jwt_dogrula(mevcut_token())
    if not payload:
        return redirect("/giris")
    cikti = ""
    if request.method == "POST":
        url = request.form.get("url", "")
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                icerik = r.read(2000).decode("utf-8", "replace")
            cikti = f'<div class="out">{icerik}</div>'
        except Exception as e:
            cikti = f'<div class="alert alert-err">Istek basarisiz: {e}</div>'
    govde = f"""
    <div class="card">
        <h1>Webhook / URL Onizleme</h1>
        <p>Bir URL gir, sunucu onizleme icin iceriini cekip gostersin.</p>
        <form method="POST">
            <label>URL</label>
            <input name="url" placeholder="https://..." autocomplete="off">
            <button class="btn" type="submit">Onizle</button>
        </form>
        {cikti}
    </div>
    """
    return sayfa(govde, payload)


@app.route("/dahili/anahtar")
def dahili_anahtar():
    # Sadece sunucunun KENDISI (127.0.0.1) erisebilir -> SSRF hedefi
    uzak = request.remote_addr
    if uzak not in ("127.0.0.1", "::1", "localhost"):
        return "Erisim reddedildi: bu endpoint sadece dahili aglardan erisilebilir.", 403
    return f"DAHILI SERVIS - Gizli anahtar: {FLAGS['ssrf']}", 200, {"Content-Type": "text/plain"}


@app.route("/oturum-geri-yukle", methods=["GET", "POST"])
def oturum_geri_yukle():
    # ZAFIYET 5: base64 pickle guvensiz sekilde deserialize edilir -> RCE
    payload = jwt_dogrula(mevcut_token())
    if not payload:
        return redirect("/giris")
    cikti = ""
    if request.method == "POST":
        veri = request.form.get("oturum", "")
        try:
            obj = pickle.loads(base64.b64decode(veri))   # GUVENSIZ!
            cikti = f'<div class="out">Oturum geri yuklendi: {obj}</div>'
        except Exception as e:
            cikti = f'<div class="alert alert-err">Cozme hatasi: {e}</div>'
    govde = f"""
    <div class="card">
        <h1>Oturum Geri Yukle</h1>
        <p>Daha once disa aktardigin oturumu (base64) yapistir, sistem geri yuklesin.</p>
        <p style="font-size:.84rem">Ipucu: oturum nesneleri Python <code>pickle</code> ile saklanir.
           Sunucuda <code>{GIZLI_DOSYA}</code> adli bir dosya var.</p>
        <form method="POST">
            <label>Oturum Verisi (base64)</label>
            <textarea name="oturum" rows="3" placeholder="gAS..."></textarea>
            <button class="btn" type="submit">Geri Yukle</button>
        </form>
        {cikti}
    </div>
    """
    return sayfa(govde, payload)


if __name__ == "__main__":
    # cwd'yi script dizinine sabitle (pickle RCE hedef dosyasi + db icin)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open(GIZLI_DOSYA, "w") as f:
        f.write(FLAGS["pickle"] + "\n")
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7003
    print(f"[DevHub] Zafiyetli gelistirici platformu port {port}'da calisiyor...")
    # threaded=True: SSRF ile kendine istek atinca kilitlenmesin
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
