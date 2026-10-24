"""
Lab artifact (dosya) üreticisi.
Tüm gerçek lab dosyalarını cyberlab/labfiles/ altında üretir.
Flag'ler burada sabit; db.py seed'i aynı değerleri kullanır.
Sadece Pillow + stdlib kullanır (pip gerektirmez).
"""
import os
import struct
import io
import base64
import codecs
import hashlib
import zipfile
from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "labfiles")
os.makedirs(OUT, exist_ok=True)


# ============================================================
# 1) PCAP  —  Ağ adli bilişimi
# ============================================================
def make_pcap():
    def ipv4(src, dst, payload_len, proto=6):
        ver_ihl = 0x45
        tos = 0
        total_len = 20 + payload_len
        ident = 0x1c46
        flags_frag = 0x4000
        ttl = 64
        checksum = 0
        s = bytes(int(x) for x in src.split("."))
        d = bytes(int(x) for x in dst.split("."))
        return struct.pack("!BBHHHBBH4s4s", ver_ihl, tos, total_len, ident,
                           flags_frag, ttl, proto, checksum, s, d)

    def tcp(sport, dport, seq, ack, payload):
        data_off = 0x50          # 20 byte, opsiyon yok
        flags = 0x18             # PSH + ACK
        window = 0x7210
        checksum = 0
        urg = 0
        hdr = struct.pack("!HHIIBBHHH", sport, dport, seq, ack,
                          data_off, flags, window, checksum, urg)
        return hdr + payload

    def eth(payload):
        dst = b"\x00\x0c\x29\x3a\x4b\x5c"
        src = b"\x00\x50\x56\xc0\x00\x08"
        return dst + src + b"\x08\x00" + payload

    def packet(src_ip, dst_ip, sport, dport, seq, ack, http):
        payload = http.encode()
        seg = tcp(sport, dport, seq, ack, payload)
        ip = ipv4(src_ip, dst_ip, len(seg))
        return eth(ip + seg)

    CLIENT = "10.0.0.15"
    SERVER = "93.184.216.34"

    pkts = []
    # 1) POST /login  (kullanıcı adı + parola düz metin)
    http1 = ("POST /login HTTP/1.1\r\nHost: portal.sirket.local\r\n"
             "Content-Type: application/x-www-form-urlencoded\r\n"
             "Content-Length: 44\r\n\r\n"
             "username=admin&password=S3cr3tP@ss2024")
    pkts.append(packet(CLIENT, SERVER, 49512, 80, 1000, 2000, http1))
    # 2) 200 OK
    http2 = ("HTTP/1.1 200 OK\r\nServer: nginx\r\nSet-Cookie: session=ok\r\n"
             "Content-Length: 2\r\n\r\nOK")
    pkts.append(packet(SERVER, CLIENT, 2000, 1044, 80, 49512, http2))
    # 3) GET /api/export?token=FLAG  (sızan flag)
    http3 = ("GET /api/export?token=CLAB{p4ck3t_tr4ff1c_r3v34l3d} HTTP/1.1\r\n"
             "Host: portal.sirket.local\r\nCookie: session=ok\r\n"
             "User-Agent: curl/8.0\r\n\r\n")
    pkts.append(packet(CLIENT, SERVER, 49512, 80, 1044, 2004, http3))

    path = os.path.join(OUT, "capture.pcap")
    with open(path, "wb") as f:
        # global header: magic, v2.4, zone0, sig0, snaplen, linktype=1(Eth)
        f.write(struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
        ts = 1700000000
        for i, p in enumerate(pkts):
            f.write(struct.pack("<IIII", ts + i, i * 1000, len(p), len(p)))
            f.write(p)
    return {
        "file": "capture.pcap",
        "parola": "S3cr3tP@ss2024",
        "flag": "CLAB{p4ck3t_tr4ff1c_r3v34l3d}",
    }


# ============================================================
# 2) LOG  —  Web sunucu erişim logu analizi
# ============================================================
def make_log():
    attacker = "185.220.101.47"
    flag = "CLAB{l0g_4n4lys1s_m4st3r}"
    lines = []
    normal_ips = ["78.45.12.9", "92.168.5.21", "34.90.11.6", "88.247.33.102"]
    ua = '"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
    bot = '"sqlmap/1.7"'

    # Normal trafik
    base = [
        'GET / HTTP/1.1" 200 1534',
        'GET /style.css HTTP/1.1" 200 882',
        'GET /hakkimizda HTTP/1.1" 200 2201',
        'POST /iletisim HTTP/1.1" 200 341',
        'GET /urunler?id=12 HTTP/1.1" 200 1890',
    ]
    t = 10
    for i in range(22):
        ip = normal_ips[i % len(normal_ips)]
        req = base[i % len(base)]
        lines.append(f'{ip} - - [12/Oct/2026:09:{t:02d}:11 +0300] "{req} {ua}')
        t = (t + 1) % 60

    # Saldırgan: dizin keşfi -> SQLi -> LFI -> admin erişimi -> exfil
    atk = [
        ('GET /admin HTTP/1.1" 403 120', bot),
        ('GET /admin.php HTTP/1.1" 404 120', bot),
        ('GET /backup.zip HTTP/1.1" 404 120', bot),
        ("GET /urunler?id=12' OR '1'='1 HTTP/1.1\" 500 90", bot),
        ('GET /urunler?id=12 UNION SELECT username,password FROM users-- HTTP/1.1" 200 4120', bot),
        ('GET /index.php?page=../../../../etc/passwd HTTP/1.1" 200 2048', bot),
        ('POST /admin/login HTTP/1.1" 401 120', bot),
        ('POST /admin/login HTTP/1.1" 401 120', bot),
        ('POST /admin/login HTTP/1.1" 200 980', bot),
        (f'GET /admin/export?note={flag} HTTP/1.1" 200 512', bot),
    ]
    tt = 32
    for req, agent in atk:
        lines.append(f'{attacker} - - [12/Oct/2026:09:{tt:02d}:44 +0300] "{req} {agent}')
        tt += 1

    # Biraz daha normal trafik (gürültü)
    for i in range(10):
        ip = normal_ips[i % len(normal_ips)]
        lines.append(f'{ip} - - [12/Oct/2026:09:{tt:02d}:05 +0300] "{base[i % len(base)]} {ua}')
        tt += 1

    path = os.path.join(OUT, "access.log")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return {
        "file": "access.log",
        "ip": attacker,
        "lfi": "/etc/passwd",
        "flag": flag,
    }


# ============================================================
# 3) STEGO (strings) — dosya sonuna eklenmiş flag
# ============================================================
def make_stego_strings():
    flag = "CLAB{str1ngs_f0und_m3}"
    img = Image.new("RGB", (480, 300), (24, 16, 40))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 460, 280], outline=(168, 85, 247), width=3)
    d.text((60, 140), "CyberLab TR - Gizli Mesaj", fill=(236, 231, 245))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    # PNG'nin sonuna düz metin flag ekle (IEND'den sonra)
    data += b"\n<!-- gizli veri -->\nFLAG=" + flag.encode() + b"\n"
    path = os.path.join(OUT, "gizli.png")
    with open(path, "wb") as f:
        f.write(data)
    return {"file": "gizli.png", "flag": flag}


# ============================================================
# 4) POLYGLOT — resme eklenmiş zip (binwalk/unzip)
# ============================================================
def make_polyglot():
    flag = "CLAB{h1dd3n_1n_pl41n_s1ght}"
    img = Image.new("RGB", (400, 250), (40, 20, 10))
    d = ImageDraw.Draw(img)
    d.text((40, 110), "Sadece bir kapak resmi... ya da degil?", fill=(255, 220, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    jpg = buf.getvalue()

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("secret.txt", f"Tebrikler! Arsivi buldun.\nFLAG: {flag}\n")
    path = os.path.join(OUT, "kapak.jpg")
    with open(path, "wb") as f:
        f.write(jpg + zbuf.getvalue())
    return {"file": "kapak.jpg", "flag": flag}


# ============================================================
# 5) CRYPTO — katmanlı kodlama (base64+rot13) ve Sezar
# ============================================================
def make_crypto():
    flag1 = "CLAB{cl4ss1c_crypt0}"
    flag2 = "CLAB{sh1ft_th3_l3tt3rs}"

    rot = codecs.encode(flag1, "rot_13")
    b64 = base64.b64encode(rot.encode()).decode()

    def caesar(s, k):
        out = []
        for c in s:
            if "a" <= c <= "z":
                out.append(chr((ord(c) - 97 + k) % 26 + 97))
            elif "A" <= c <= "Z":
                out.append(chr((ord(c) - 65 + k) % 26 + 65))
            else:
                out.append(c)
        return "".join(out)

    cae = caesar(flag2, 7)

    content = (
        "=== CyberLab TR :: Sifre Cozucu ===\n\n"
        "Gorev 1 - Iki katman: once Base64, sonra ROT13.\n"
        f"  {b64}\n\n"
        "Gorev 2 - Klasik Sezar sifresi (kayma = 7).\n"
        f"  {cae}\n"
    )
    path = os.path.join(OUT, "mesaj.txt")
    with open(path, "w") as f:
        f.write(content)
    return {"file": "mesaj.txt", "flag1": flag1, "flag2": flag2}


# ============================================================
# 6) HASH — md5 ve sha1, wordlist içinde çözüm var
# ============================================================
def make_hash():
    pw1 = "Kaplan2024!"
    pw2 = "g0khan_55"
    md5 = hashlib.md5(pw1.encode()).hexdigest()
    sha1 = hashlib.sha1(pw2.encode()).hexdigest()

    with open(os.path.join(OUT, "hashes.txt"), "w") as f:
        f.write(f"# md5\n{md5}\n\n# sha1\n{sha1}\n")

    decoys = ["123456", "password", "admin123", "qwerty", "istanbul",
              "superadmin", "deneme123", "P@rola1", "cyberlab", "flag2024",
              "gokhan55", "kaplan123", "G0khan_55", "Kaplan_2024"]
    words = decoys[:7] + [pw1] + decoys[7:] + [pw2]
    with open(os.path.join(OUT, "wordlist.txt"), "w") as f:
        f.write("\n".join(words) + "\n")
    return {"files": ["hashes.txt", "wordlist.txt"], "md5_pw": pw1, "sha1_pw": pw2}


# ============================================================
# 7) METADATA / OSINT — PNG tEXt alanları
# ============================================================
def make_metadata():
    flag = "CLAB{m3t4d4t4_n3v3r_l13s}"
    author = "mehmet.kaya"
    img = Image.new("RGB", (420, 280), (16, 24, 40))
    d = ImageDraw.Draw(img)
    d.text((40, 120), "Tatil fotografi :)", fill=(200, 220, 255))

    meta = PngInfo()
    meta.add_text("Author", author)
    meta.add_text("Software", "Adobe Photoshop 25.0 (Windows)")
    meta.add_text("Comment", "GPS: 41.0082, 28.9784 - cekim: 2026-08-14")
    meta.add_text("Copyright", f"internal-use FLAG:{flag}")

    path = os.path.join(OUT, "fotograf.png")
    img.save(path, "PNG", pnginfo=meta)
    return {"file": "fotograf.png", "author": author, "flag": flag}


if __name__ == "__main__":
    results = {
        "pcap": make_pcap(),
        "log": make_log(),
        "stego": make_stego_strings(),
        "polyglot": make_polyglot(),
        "crypto": make_crypto(),
        "hash": make_hash(),
        "metadata": make_metadata(),
    }
    import json
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("\nDosyalar:", os.listdir(OUT))
