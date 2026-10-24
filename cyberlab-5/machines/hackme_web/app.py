"""
HackMe Web - Kasitli zafiyetli web uygulamasi
CyberLab TR egitim amacli - GERCEK ORTAMDA KULLANMAYIN!

Zafiyetler:
1. SQL Injection (login sayfasi)
2. Command Injection (ping araci)
3. Directory Traversal (dosya okuma)
4. Gizli admin paneli
5. Robots.txt'te ipucu
6. HTML yorumlarinda gizli bilgi
"""
import os
import sys
import sqlite3
import subprocess
from flask import Flask, request, render_template_string, redirect, session, send_file

app = Flask(__name__)
app.secret_key = "super_secret_key_12345"  # kasitli zayif anahtar

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hackme.db")

# ----- FLAGS -----
FLAGS = {
    "sqli":       "CLAB{sql_injection_basarili_7x9k}",
    "cmdi":       "CLAB{command_injection_ustasi_4m2p}",
    "traversal":  "CLAB{directory_traversal_pro_8w3n}",
    "admin":      "CLAB{gizli_admin_paneli_bulundu_5q1r}",
    "robots":     "CLAB{robots_txt_ipucu_yakalandi_2j6v}",
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS users")
    conn.execute("DROP TABLE IF EXISTS secrets")
    conn.execute("""CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        role TEXT DEFAULT 'user'
    )""")
    conn.execute("""CREATE TABLE secrets (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT
    )""")
    # Kasitli olarak duz metin parola (zafiyetli!)
    conn.execute("INSERT INTO users VALUES (1, 'admin', 'Sup3rS3cretP@ss!', 'admin')")
    conn.execute("INSERT INTO users VALUES (2, 'kullanici', '123456', 'user')")
    conn.execute("INSERT INTO users VALUES (3, 'test', 'test', 'user')")
    conn.execute(f"INSERT INTO secrets VALUES (1, 'Admin Flag', '{FLAGS['admin']}')")
    conn.execute(f"INSERT INTO secrets VALUES (2, 'SQL Flag', '{FLAGS['sqli']}')")
    conn.commit()
    conn.close()

    # Gizli flag dosyasi olustur
    flag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret")
    os.makedirs(flag_dir, exist_ok=True)
    with open(os.path.join(flag_dir, "flag.txt"), "w") as f:
        f.write(f"Tebrikler! Directory Traversal ile bu dosyayi buldun!\n\n{FLAGS['traversal']}\n")


# ----- TEMPLATE'LER -----
BASE_CSS = """
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff41; min-height: 100vh; }
.container { max-width: 800px; margin: 0 auto; padding: 20px; }
h1, h2 { color: #00ff41; margin-bottom: 15px; }
a { color: #00aaff; }
.nav { background: #111; padding: 12px 20px; display: flex; gap: 20px; align-items: center; border-bottom: 1px solid #333; }
.nav a { color: #888; text-decoration: none; }
.nav a:hover { color: #00ff41; }
.nav .brand { color: #ff4444; font-weight: bold; font-size: 1.2rem; }
input, textarea { background: #1a1a1a; border: 1px solid #333; color: #00ff41; padding: 10px; border-radius: 4px; width: 100%; margin: 8px 0; font-family: inherit; }
button, .btn { background: #00aa33; color: #000; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-weight: bold; font-family: inherit; text-decoration: none; display: inline-block; }
button:hover, .btn:hover { background: #00ff41; }
.card { background: #111; border: 1px solid #333; border-radius: 8px; padding: 20px; margin: 15px 0; }
.error { color: #ff4444; margin: 10px 0; }
.success { color: #00ff41; margin: 10px 0; }
pre { background: #0a0a0a; border: 1px solid #333; padding: 15px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; margin: 10px 0; }
.warning { background: #331a00; border: 1px solid #ff6600; padding: 15px; border-radius: 8px; margin: 15px 0; color: #ffaa44; }
</style>
"""

HOME_PAGE = BASE_CSS + """
<div class="nav">
    <span class="brand">HackMe Corp</span>
    <a href="/">Ana Sayfa</a>
    <a href="/login">Giris</a>
    <a href="/tools">Araclar</a>
    <a href="/files">Dosyalar</a>
    <!-- TODO: /4dm1n-p4n3l sayfasini kaldir - guvensiz! -->
</div>
<div class="container">
    <h1>HackMe Corp - Calisanlar Portali</h1>
    <div class="card">
        <h2>Hosgeldiniz!</h2>
        <p>Bu portal HackMe Corp calisanlari icindir.</p>
        <p>Lutfen giris yapiniz.</p>
        <br>
        <a class="btn" href="/login">Giris Yap</a>
    </div>
    <div class="warning">
        <strong>Sistem Bakimi:</strong> Sunucu guncellenmektedir.
        Sorun yasarsaniz IT ekibine bildirin.
    </div>
</div>
"""

LOGIN_PAGE = BASE_CSS + """
<div class="nav">
    <span class="brand">HackMe Corp</span>
    <a href="/">Ana Sayfa</a>
    <a href="/login">Giris</a>
    <a href="/tools">Araclar</a>
    <a href="/files">Dosyalar</a>
</div>
<div class="container">
    <h1>Giris Yap</h1>
    <div class="card">
        <form method="POST">
            <label>Kullanici Adi:</label>
            <input type="text" name="username" placeholder="kullanici adi..." required>
            <label>Parola:</label>
            <input type="password" name="password" placeholder="parola..." required>
            <br><br>
            <button type="submit">Giris Yap</button>
        </form>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        {% if result %}
        <div class="success">
            <p>Hosgeldin, {{ result.username }}! (Rol: {{ result.role }})</p>
            {% if result.role == 'admin' %}
            <p>Admin olarak giris yaptin!</p>
            <p><strong>SQL Injection Flag:</strong> {{ sqli_flag }}</p>
            {% endif %}
        </div>
        {% endif %}
    </div>
    <!-- Debug: Varsayilan test hesabi: test / test -->
</div>
"""

TOOLS_PAGE = BASE_CSS + """
<div class="nav">
    <span class="brand">HackMe Corp</span>
    <a href="/">Ana Sayfa</a>
    <a href="/login">Giris</a>
    <a href="/tools">Araclar</a>
    <a href="/files">Dosyalar</a>
</div>
<div class="container">
    <h1>Ag Araclari</h1>
    <div class="card">
        <h2>Ping Testi</h2>
        <p>Bir IP adresine ping gonderin:</p>
        <form method="POST">
            <input type="text" name="target" placeholder="ornek: 127.0.0.1" required>
            <br>
            <button type="submit">Ping Gonder</button>
        </form>
        {% if output %}
        <h3>Sonuc:</h3>
        <pre>{{ output }}</pre>
        {% endif %}
    </div>
</div>
"""

FILES_PAGE = BASE_CSS + """
<div class="nav">
    <span class="brand">HackMe Corp</span>
    <a href="/">Ana Sayfa</a>
    <a href="/login">Giris</a>
    <a href="/tools">Araclar</a>
    <a href="/files">Dosyalar</a>
</div>
<div class="container">
    <h1>Dosya Goruntuleme</h1>
    <div class="card">
        <h2>Sirket Dokumanlari</h2>
        <p>Goruntulemek istediginiz dosya adini girin:</p>
        <form method="GET">
            <input type="text" name="file" placeholder="dosya adi (ornek: duyuru.txt)" value="{{ filename or '' }}">
            <br>
            <button type="submit">Goruntule</button>
        </form>
        <p style="color:#666; font-size:0.85rem; margin-top:8px;">Mevcut dosyalar: duyuru.txt, kurallar.txt</p>
        {% if content %}
        <h3>{{ filename }}:</h3>
        <pre>{{ content }}</pre>
        {% endif %}
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
    </div>
</div>
"""

ADMIN_PAGE = BASE_CSS + """
<div class="nav">
    <span class="brand">HackMe Corp</span>
    <a href="/">Ana Sayfa</a>
    <a href="/login">Giris</a>
    <a href="/tools">Araclar</a>
    <a href="/files">Dosyalar</a>
</div>
<div class="container">
    <h1>Admin Paneli</h1>
    <div class="card">
        <h2>Gizli Sirket Verileri</h2>
        <p>Bu sayfayi bulmaliydik...</p>
        <pre>
Kullanici Tablosu:
---
admin : Sup3rS3cretP@ss! (admin)
kullanici : 123456 (user)
test : test (user)
        </pre>
        <br>
        <p class="success"><strong>Admin Panel Flag:</strong> {{ admin_flag }}</p>
    </div>
</div>
"""


# ----- ROTALAR -----
@app.route("/")
def home():
    return render_template_string(HOME_PAGE)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    result = None
    sqli_flag = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # KASITLI SQL INJECTION ZAFIYETI!
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        try:
            row = conn.execute(query).fetchone()
            if row:
                result = dict(row)
                if result.get("role") == "admin":
                    sqli_flag = FLAGS["sqli"]
            else:
                error = "Hatali kullanici adi veya parola!"
        except Exception as e:
            error = f"Veritabani hatasi: {e}"
        conn.close()
    return render_template_string(LOGIN_PAGE, error=error, result=result, sqli_flag=sqli_flag)


@app.route("/tools", methods=["GET", "POST"])
def tools():
    output = None
    if request.method == "POST":
        target = request.form.get("target", "")
        # KASITLI COMMAND INJECTION ZAFIYETI!
        try:
            cmd = f"ping -c 2 {target}"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            output = result.stdout + result.stderr
            if not output.strip():
                output = "(Cikti yok)"
        except subprocess.TimeoutExpired:
            output = "Zaman asimi! (10 saniye)"
        except Exception as e:
            output = f"Hata: {e}"
    return render_template_string(TOOLS_PAGE, output=output)


@app.route("/files")
def files():
    filename = request.args.get("file", "")
    content = None
    error = None
    if filename:
        # KASITLI DIRECTORY TRAVERSAL ZAFIYETI!
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
        filepath = os.path.join(docs_dir, filename)
        try:
            with open(filepath, "r") as f:
                content = f.read()
        except FileNotFoundError:
            error = f"Dosya bulunamadi: {filename}"
        except Exception as e:
            error = f"Hata: {e}"
    return render_template_string(FILES_PAGE, filename=filename, content=content, error=error)


@app.route("/4dm1n-p4n3l")
def admin_panel():
    return render_template_string(ADMIN_PAGE, admin_flag=FLAGS["admin"])


@app.route("/robots.txt")
def robots():
    return f"""User-agent: *
Disallow: /4dm1n-p4n3l
Disallow: /secret/
# {FLAGS['robots']}
""", 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    # Dokumanlar klasoru
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "duyuru.txt"), "w") as f:
        f.write("HackMe Corp Duyuru\n==================\nSistem bakimdadir. Lutfen sabirl olun.\nIT Ekibi\n")
    with open(os.path.join(docs_dir, "kurallar.txt"), "w") as f:
        f.write("Sirket Kurallari\n================\n1. Parolalarinizi guclu tutun\n2. Supheli baglantilara tiklamayin\n3. IT ekibine danismadan yazilim kurmak yasaktir\n")

    init_db()

    # Command Injection flag'ini ortam degiskenine koy.
    # Oyuncu ping aracindaki komut enjeksiyonu ile `; env` veya
    # `; echo $APP_SECRET_FLAG` calistirarak bu flag'i bulabilir.
    # (Gercek hayatta sirlarin env'de tutulmasi yaygin bir hatadir.)
    os.environ["APP_SECRET_FLAG"] = FLAGS["cmdi"]

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7000
    print(f"[HackMe Web] Zafiyetli uygulama port {port}'da calisiyor...")
    app.run(host="0.0.0.0", port=port, debug=False)
