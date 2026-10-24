"""
Veritabanı yardımcıları ve ilk kurulum (seed).
Görev tabanlı model: her lab'ın birden çok görevi (task) vardır.
Cevaplar gen_labs.py ile üretilen gerçek dosyalardan doğrulanmıştır.
"""
import sqlite3
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cyberlab.db")
LABFILES_DIR = os.path.join(BASE_DIR, "labfiles")


def get_db():
    # timeout: kilit varsa hata vermek yerine 5 sn bekle (eşzamanlı kullanım)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    # WAL: okuma ve yazma birbirini daha az kilitler (çok kullanıcı için)
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    avatar        TEXT
);

CREATE TABLE IF NOT EXISTS labs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT    UNIQUE NOT NULL,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    difficulty  TEXT    NOT NULL,       -- Kolay / Orta / Zor
    short_desc  TEXT    NOT NULL,
    description TEXT    NOT NULL,
    tags        TEXT    NOT NULL,
    files       TEXT    NOT NULL,       -- virgülle ayrık indirilebilir dosyalar
    tools       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id   INTEGER NOT NULL,
    ordinal  INTEGER NOT NULL,
    question TEXT    NOT NULL,
    answer   TEXT    NOT NULL,
    hint     TEXT    NOT NULL,
    points   INTEGER NOT NULL,
    FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS completions (
    user_id      INTEGER NOT NULL,
    task_id      INTEGER NOT NULL,
    completed_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, task_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS machine_completions (
    user_id      INTEGER NOT NULL,
    task_id      TEXT    NOT NULL,
    points       INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, task_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

# Her lab: meta + görev listesi (soru, cevap, ipucu, puan)
SEED = [
    {
        "slug": "paket-avi",
        "name": "Paket Avı",
        "category": "Ağ Adli Bilişimi",
        "difficulty": "Kolay",
        "short_desc": "Yakalanmış ağ trafiğini (PCAP) analiz et, sızan kimlik bilgilerini ve flag'i bul.",
        "description": (
            "Bir ağ cihazından yakalanmış trafik kaydı (PCAP) elindeki tek kanıt. "
            "İçinde şifrelenmemiş (HTTP) bir oturum var.\n\n"
            "Dosyayı Wireshark ile aç ya da komut satırında 'strings' / 'tshark' kullan. "
            "Amacın: gönderilen kimlik bilgilerini ve dışarı sızdırılan flag'i tespit etmek.\n\n"
            "Bu, bir CTI/SOC analistinin günlük işinin temelidir: trafikte neyin açığa çıktığını görmek."
        ),
        "tags": "pcap,wireshark,network,http,başlangıç",
        "files": "capture.pcap",
        "tools": "Wireshark, tshark, strings",
        "tasks": [
            ("Giriş (login) isteğinde açık metin olarak yakalanan parola nedir?",
             "S3cr3tP@ss2024",
             "HTTP POST /login paketinin gövdesine bak. Wireshark'ta sağ tık → 'Follow TCP Stream', ya da 'strings capture.pcap'.",
             25),
            ("Sunucudan dışarı sızdırılan flag nedir? (CLAB{...})",
             "CLAB{p4ck3t_tr4ff1c_r3v34l3d}",
             "GET /api/export isteğindeki 'token' parametresine bak.",
             50),
        ],
    },
    {
        "slug": "log-dedektifi",
        "name": "Log Dedektifi",
        "category": "Log Analizi / Blue Team",
        "difficulty": "Kolay",
        "short_desc": "Web sunucusu erişim loglarında saldırıyı tespit et: saldırgan, yöntem ve sızıntı.",
        "description": (
            "Bir web sunucusunun erişim logu (access.log) sana verildi. Normal trafiğin arasına "
            "bir saldırı gizlenmiş.\n\n"
            "grep, awk ve cut gibi klasik araçlarla saldırganı, kullandığı tekniği ve "
            "dışarı sızan veriyi ortaya çıkar.\n\n"
            "Savunma (Blue Team) tarafının en temel becerisi: gürültünün içinden kötü niyetli aktiviteyi ayıklamak."
        ),
        "tags": "log,blue-team,grep,siem,başlangıç",
        "files": "access.log",
        "tools": "grep, awk, cut, metin editörü",
        "tasks": [
            ("Saldırganın IP adresi nedir?",
             "185.220.101.47",
             "En çok şüpheli istek yapan IP'yi bul: awk '{print $1}' access.log | sort | uniq -c | sort -rn. Ayrıca 'sqlmap' user-agent'ına bak.",
             25),
            ("LFI (dizin geçişi) ile hangi sistem dosyası okunmaya çalışıldı?",
             "/etc/passwd",
             "page= parametresinde ../../../ gibi dizin geçişi (path traversal) ara.",
             25),
            ("Admin panelinden dışarı sızan flag nedir?",
             "CLAB{l0g_4n4lys1s_m4st3r}",
             "Başarılı (HTTP 200) /admin/export isteğindeki 'note' parametresine bak.",
             50),
        ],
    },
    {
        "slug": "gizli-mesaj",
        "name": "Gizli Mesaj",
        "category": "Steganografi",
        "difficulty": "Kolay",
        "short_desc": "Masum görünen bir resim dosyasının içine gizlenmiş veriyi çıkar.",
        "description": (
            "Sıradan bir PNG resmi... gibi görünüyor. Ama içinde gizli bir mesaj var.\n\n"
            "Bir dosyada gözle görünen her şey, dosyadaki her şey değildir. Resmin ham "
            "baytlarına bakmayı dene.\n\n"
            "İlk steganografi refleksin her zaman 'strings' olmalı."
        ),
        "tags": "stego,strings,forensics,başlangıç",
        "files": "gizli.png",
        "tools": "strings, xxd, hexdump",
        "tasks": [
            ("Resim dosyasının içine gizlenmiş flag nedir?",
             "CLAB{str1ngs_f0und_m3}",
             "'strings gizli.png' çalıştır ve çıktının sonuna bak. Veya 'xxd gizli.png | tail'.",
             50),
        ],
    },
    {
        "slug": "katman-katman",
        "name": "Katman Katman",
        "category": "Steganografi / Dosya Analizi",
        "difficulty": "Orta",
        "short_desc": "Bir resmin sonuna gömülmüş gizli arşivi çıkar (polyglot dosya).",
        "description": (
            "Bu sadece bir kapak resmi değil. JPEG verisinin bittiği yerde başka bir dosya "
            "daha saklı.\n\n"
            "Dosyanın yapısını incele: bir arşiv (ZIP) resmin peşine eklenmiş. Çıkar ve içindekini oku.\n\n"
            "Gömülü dosyaları bulmak adli bilişimin klasik adımlarından biridir."
        ),
        "tags": "stego,binwalk,zip,forensics,orta",
        "files": "kapak.jpg",
        "tools": "binwalk, unzip, foremost",
        "tasks": [
            ("Resmin içine gömülü arşivdeki secret.txt dosyasında yazan flag nedir?",
             "CLAB{h1dd3n_1n_pl41n_s1ght}",
             "'binwalk kapak.jpg' ile gömülü ZIP'i gör, sonra doğrudan 'unzip kapak.jpg' ile çıkar. (Baştaki 'extra bytes' uyarısı normaldir.)",
             75),
        ],
    },
    {
        "slug": "sifre-cozucu",
        "name": "Şifre Çözücü",
        "category": "Kriptografi",
        "difficulty": "Orta",
        "short_desc": "Katmanlı kodlama ve klasik şifreleri çözerek gizli mesajları aç.",
        "description": (
            "İki ayrı kriptografi bulmacası tek dosyada (mesaj.txt). Teori değil, pratik çözme.\n\n"
            "Görev 1: İki katmanlı kodlama — önce Base64, sonra ROT13.\n"
            "Görev 2: Klasik Sezar şifresi (kayma = 7).\n\n"
            "CyberChef bu iş için biçilmiş kaftandır; ya da birkaç satır Python."
        ),
        "tags": "kripto,base64,rot13,sezar,cyberchef,orta",
        "files": "mesaj.txt",
        "tools": "CyberChef, Python, base64",
        "tasks": [
            ("Görev 1'i (Base64 → ROT13) çözünce çıkan flag nedir?",
             "CLAB{cl4ss1c_crypt0}",
             "Önce satırı Base64 çöz, çıkan metni ROT13 ile çöz. CyberChef: 'From Base64' + 'ROT13'.",
             50),
            ("Görev 2'yi (Sezar, kayma 7) çözünce çıkan flag nedir?",
             "CLAB{sh1ft_th3_l3tt3rs}",
             "Her harfi alfabede 7 geri kaydır. CyberChef'te 'ROT13 Brute Force' veya 'Caesar' işe yarar.",
             50),
        ],
    },
    {
        "slug": "kirilan-parola",
        "name": "Kırılan Parola",
        "category": "Hash Kırma",
        "difficulty": "Orta",
        "short_desc": "Ele geçirilmiş hash'leri verilen kelime listesiyle kır.",
        "description": (
            "Bir sızıntıdan iki parola hash'i (hashes.txt) ve bir kelime listesi (wordlist.txt) elinde.\n\n"
            "Hash'lerin karşılığı olan düz metin parolaları bul. Biri MD5 (32 karakter), "
            "diğeri SHA1 (40 karakter).\n\n"
            "john veya hashcat kullanabilir ya da kısa bir betikle wordlist'i deneyebilirsin."
        ),
        "tags": "hash,md5,sha1,john,hashcat,orta",
        "files": "hashes.txt,wordlist.txt",
        "tools": "john, hashcat, md5sum/sha1sum",
        "tasks": [
            ("MD5 hash'inin karşılığı olan parola nedir?",
             "Kaplan2024!",
             "32 karakterli hash MD5'tir. john --wordlist=wordlist.txt --format=raw-md5 hashes.txt — veya wordlist'teki her kelimenin md5'ini karşılaştır.",
             50),
            ("SHA1 hash'inin karşılığı olan parola nedir?",
             "g0khan_55",
             "40 karakterli hash SHA1'dir. Aynı wordlist ile --format=raw-sha1.",
             50),
        ],
    },
    {
        "slug": "dijital-iz",
        "name": "Dijital İz",
        "category": "OSINT / Metadata",
        "difficulty": "Kolay",
        "short_desc": "Bir fotoğrafın metadata'sından saklı bilgileri ve flag'i ortaya çıkar.",
        "description": (
            "Paylaşılan bir fotoğraf, göründüğünden fazlasını anlatır. Dosyanın metadata "
            "(üstveri) alanları, onu oluşturan kişi ve ortam hakkında ipucu barındırır.\n\n"
            "Fotoğrafın metadata'sını incele: düzenleyen kişi, kullanılan yazılım, konum "
            "ve gizlenmiş bir flag.\n\n"
            "OSINT'in temel refleksi: her dosyanın metadata'sına bak."
        ),
        "tags": "osint,metadata,exif,forensics,başlangıç",
        "files": "fotograf.png",
        "tools": "exiftool, strings, Python (PIL)",
        "tasks": [
            ("Fotoğrafı düzenleyen kişinin kullanıcı adı (Author alanı) nedir?",
             "mehmet.kaya",
             "exiftool fotograf.png — ya da 'strings fotograf.png | grep -i author'. 'Author' alanına bak.",
             25),
            ("Metadata içine saklanmış flag nedir?",
             "CLAB{m3t4d4t4_n3v3r_l13s}",
             "Metadata'daki 'Copyright' alanını kontrol et.",
             50),
        ],
    },
]


def init_db(force_seed=False):
    conn = get_db()
    conn.executescript(SCHEMA)
    # Mevcut veritabanları için migrasyon (avatar kolonu sonradan eklendi)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "avatar" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
    count = conn.execute("SELECT COUNT(*) AS c FROM labs").fetchone()["c"]
    if count == 0 or force_seed:
        if force_seed:
            conn.execute("DELETE FROM completions")
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM labs")
        # 1) İlk 7 lab (bu dosyada tanımlı, tuple görevli)
        for lab in SEED:
            cur = conn.execute(
                """INSERT INTO labs (slug, name, category, difficulty, short_desc,
                                     description, tags, files, tools)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (lab["slug"], lab["name"], lab["category"], lab["difficulty"],
                 lab["short_desc"], lab["description"], lab["tags"],
                 lab["files"], lab["tools"]),
            )
            lab_id = cur.lastrowid
            for i, (q, a, h, pts) in enumerate(lab["tasks"], start=1):
                conn.execute(
                    "INSERT INTO tasks (lab_id, ordinal, question, answer, hint, points) VALUES (?,?,?,?,?,?)",
                    (lab_id, i, q, a, h, pts),
                )

        # 2) İkinci dalga lab (gen_labs2.py üretir → labs2_seed.json), dict görevli
        seed2_path = os.path.join(BASE_DIR, "labs2_seed.json")
        if os.path.exists(seed2_path):
            import json
            with open(seed2_path, encoding="utf-8") as f:
                labs2 = json.load(f)
            for lab in labs2:
                cur = conn.execute(
                    """INSERT INTO labs (slug, name, category, difficulty, short_desc,
                                         description, tags, files, tools)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (lab["slug"], lab["name"], lab["category"], lab["difficulty"],
                     lab["short_desc"], lab["description"], lab["tags"],
                     lab["files"], lab["tools"]),
                )
                lab_id = cur.lastrowid
                for i, t in enumerate(lab["tasks"], start=1):
                    conn.execute(
                        "INSERT INTO tasks (lab_id, ordinal, question, answer, hint, points) VALUES (?,?,?,?,?,?)",
                        (lab_id, i, t["q"], t["a"], t["h"], t["p"]),
                    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db(force_seed=True)
    conn = get_db()
    labs = conn.execute("SELECT COUNT(*) c FROM labs").fetchone()["c"]
    tasks = conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"]
    pts = conn.execute("SELECT COALESCE(SUM(points),0) s FROM tasks").fetchone()["s"]
    conn.close()
    print(f"Hazır: {labs} lab, {tasks} görev, toplam {pts} puan. DB: {DB_PATH}")
