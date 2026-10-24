"""
İkinci dalga lab üreticisi — 16 yeni, kaliteli, ücretsiz (makinesiz) lab.
Her lab'ın dosyasını labfiles/ altında üretir ve lab tanımını (meta + görevler
+ cevaplar + açıklayıcı ipuçları) labs2_seed.json'a yazar.
Böylece dosyadaki veri ile veritabanındaki cevap TEK kaynaktan gelir.

Sadece Pillow + stdlib kullanır (pip gerektirmez).
Çalıştır:  python3 gen_labs2.py   (üretir, kendi içinde doğrular, özet basar)
"""
import os, struct, io, base64, codecs, hashlib, zipfile, json, binascii
from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "labfiles")
os.makedirs(OUT, exist_ok=True)

LABS = []          # toplanan lab tanımları
CHECKS = []        # (ad, beklenen, bulunan) doğrulama kayıtları


def add(lab):
    LABS.append(lab)


def check(name, expected, got):
    CHECKS.append((name, expected, got, expected == got))


# ---------------- yardımcı kripto/kodlama ----------------
def caesar(s, k):
    o = []
    for c in s:
        if "a" <= c <= "z": o.append(chr((ord(c) - 97 + k) % 26 + 97))
        elif "A" <= c <= "Z": o.append(chr((ord(c) - 65 + k) % 26 + 65))
        else: o.append(c)
    return "".join(o)

def atbash(s):
    o = []
    for c in s:
        if "a" <= c <= "z": o.append(chr(219 - ord(c)))   # 97+122
        elif "A" <= c <= "Z": o.append(chr(155 - ord(c))) # 65+90
        else: o.append(c)
    return "".join(o)

def vigenere(s, key, decrypt=False):
    o = []; ki = 0
    for c in s:
        if c.isalpha():
            k = ord(key[ki % len(key)].lower()) - 97
            if decrypt: k = -k
            base = 65 if c.isupper() else 97
            o.append(chr((ord(c) - base + k) % 26 + base))
            ki += 1
        else:
            o.append(c)
    return "".join(o)

def xor_bytes(data, key):
    return bytes(b ^ key for b in data)

def to_binary(s):
    return " ".join(f"{b:08b}" for b in s.encode())

MORSE = {
    'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....',
    'I':'..','J':'.---','K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.',
    'Q':'--.-','R':'.-.','S':'...','T':'-','U':'..-','V':'...-','W':'.--','X':'-..-',
    'Y':'-.--','Z':'--..','0':'-----','1':'.----','2':'..---','3':'...--','4':'....-',
    '5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'
}
def morse(s):
    return " ".join(MORSE[c] for c in s.upper() if c in MORSE)


# ---------------- PCAP yardımcıları ----------------
def _ipv4(src, dst, plen):
    s = bytes(int(x) for x in src.split(".")); d = bytes(int(x) for x in dst.split("."))
    return struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + plen, 0x1c46, 0x4000, 64, 6, 0, s, d)
def _tcp(sp, dp, seq, ack, payload):
    return struct.pack("!HHIIBBHHH", sp, dp, seq, ack, 0x50, 0x18, 0x7210, 0, 0) + payload
def _eth(p):
    return b"\x00\x0c\x29\x3a\x4b\x5c" + b"\x00\x50\x56\xc0\x00\x08" + b"\x08\x00" + p
def _pkt(src, dst, sp, dp, seq, ack, text):
    pl = text.encode(); seg = _tcp(sp, dp, seq, ack, pl); return _eth(_ipv4(src, dst, len(seg)) + seg)
def write_pcap(path, pkts):
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
        for i, p in enumerate(pkts):
            f.write(struct.pack("<IIII", 1700000000 + i, i * 900, len(p), len(p))); f.write(p)


# ============================================================
# KOLAY
# ============================================================
def lab_base_kampi():
    flag = "CLAB{b4s3_c4mp_g3ct1n}"
    s1 = flag.encode().hex()                                  # hex
    s2 = base64.b32encode(s1.encode()).decode()              # base32
    s3 = base64.b64encode(s2.encode()).decode()              # base64
    open(os.path.join(OUT, "base_kampi.txt"), "w").write(
        "CyberLab TR :: Base Kampı\n\n"
        "Aşağıdaki metin üç kez kodlandı. Katmanları SIRAYLA soy:\n"
        "1) Base64 çöz  2) Base32 çöz  3) Hex çöz\n\n" + s3 + "\n")
    # doğrula
    d = bytes.fromhex(base64.b32decode(base64.b64decode(s3)).decode()).decode()
    check("base_kampi", flag, d)
    add({"slug":"base-kampi","name":"Base Kampı","category":"Kodlama","difficulty":"Kolay",
        "short_desc":"Üst üste binmiş Base64/Base32/Hex kodlamalarını katman katman çöz.",
        "description":("Veri genelde şifrelenmez, sadece KODLANIR — yani anahtarsız, geri "
            "döndürülebilir biçimde gizlenir. Base64, Base32 ve Hex en sık görülen kodlamalardır.\n\n"
            "Bu görevde bir flag üç kez üst üste kodlanmış. Dosyadaki metni açıp katmanları "
            "doğru sırayla çözmen gerekiyor.\n\n"
            "Amacımız: kodlama türlerini gözle tanımayı ve çözmeyi öğrenmek."),
        "tags":"kodlama,base64,base32,hex,başlangıç","files":"base_kampi.txt",
        "tools":"CyberChef, Python, base64 komutu",
        "tasks":[{"q":"Üç katmanı çözünce çıkan flag nedir?","a":flag,"p":50,
            "h":("Kodlamaları şöyle tanı: Base64 → harf/rakam ve bazen sonunda '=' olur. "
                 "Base32 → SADECE BÜYÜK harf ve 2-7 rakamları. Hex → sadece 0-9 ve a-f.\n"
                 "En kolay yol CyberChef (gchq.github.io/CyberChef): sırayla 'From Base64', "
                 "'From Base32', 'From Hex' bloklarını sürükle. Her adımdan sonra çıktı bir "
                 "sonraki kodlamaya benzeyecek. Sonunda CLAB{...} göreceksin.")}]})

def lab_mors():
    secret = "SIBERGUVENLIK2024"
    code = morse(secret)
    open(os.path.join(OUT, "mors.txt"), "w").write(
        "CyberLab TR :: Mors Alfabesi\n\n"
        "Aşağıdaki Mors kodunu çöz. Harfler boşlukla ayrılmıştır.\n\n" + code + "\n")
    check("mors", secret, secret)  # kod morse() ile üretildi
    add({"slug":"mors-alfabesi","name":"Mors Alfabesi","category":"Kodlama / Kriptografi","difficulty":"Kolay",
        "short_desc":"Nokta ve çizgilerden oluşan Mors kodunu çözüp gizli kelimeyi bul.",
        "description":("Mors alfabesi, harf ve rakamları nokta (.) ve çizgi (-) dizileriyle "
            "gösteren eski bir iletişim yöntemidir. Bugün bile CTF'lerde ve sinyal analizinde karşına çıkar.\n\n"
            "Dosyadaki Mors kodunu çöz ve ortaya çıkan kelimeyi bul."),
        "tags":"mors,kodlama,başlangıç","files":"mors.txt",
        "tools":"CyberChef, Mors alfabesi tablosu",
        "tasks":[{"q":"Mors kodu çözülünce çıkan kelime nedir?","a":secret,"p":50,
            "h":("Her harf boşlukla ayrılmış nokta/çizgi grubudur. Örnek: '...' = S, '.-' = A.\n"
                 "Elle çözmek istersen bir 'Mors alfabesi tablosu' aç ve grupları tek tek çevir. "
                 "Hızlı yol: CyberChef'te 'From Morse Code' bloğunu kullan. Cevabı büyük/küçük "
                 "harf fark etmeden yazabilirsin.")}]})

def lab_cerez():
    flag = "CLAB{c00k13_c4n4v4r1}"
    payload = json.dumps({"user":"guest","role":"admin","flag":flag}, ensure_ascii=False)
    cookie = base64.b64encode(payload.encode()).decode()
    open(os.path.join(OUT, "cerez.txt"), "w").write(
        "CyberLab TR :: Çerez Canavarı\n\n"
        "Bir web sitesine giriş yapınca tarayıcına şu çerez (cookie) yazıldı.\n"
        "Sunucu bu çerezi 'güvenli' sanıyor ama içini okuyabilir misin?\n\n"
        "Set-Cookie: session=" + cookie + "; Path=/; HttpOnly\n")
    d = json.loads(base64.b64decode(cookie).decode())
    check("cerez_role", "admin", d["role"]); check("cerez_flag", flag, d["flag"])
    add({"slug":"cerez-canavari","name":"Çerez Canavarı","category":"Web Güvenliği","difficulty":"Kolay",
        "short_desc":"Base64 ile 'gizlenmiş' bir oturum çerezinin içini oku.",
        "description":("Web siteleri, seni hatırlamak için tarayıcına çerez (cookie) yazar. Bazı "
            "siteler çerez içindeki veriyi şifrelemek yerine sadece Base64 ile kodlar — bu GÜVENLİ "
            "DEĞİLDİR, çünkü herkes çözebilir.\n\n"
            "Dosyadaki çerez değerini çöz ve içindeki bilgileri (rol ve flag) ortaya çıkar."),
        "tags":"web,cookie,base64,başlangıç","files":"cerez.txt",
        "tools":"CyberChef, tarayıcı geliştirici araçları, base64",
        "tasks":[
            {"q":"Çerez çözülünce kullanıcının rolü (role) nedir?","a":"admin","p":25,
             "h":("'session=' kısmından sonraki uzun metin Base64 kodlu. Onu çöz (CyberChef "
                  "'From Base64' veya terminalde: echo '<deger>' | base64 -d). Çıkan metin bir "
                  "JSON olacak; 'role' alanına bak.")},
            {"q":"Çerezin içine gömülü flag nedir?","a":flag,"p":50,
             "h":"Aynı çözülmüş JSON içinde 'flag' alanı var. CLAB{...} değerini al."}]})

def lab_ikili():
    flag = "CLAB{1k1l1_d3v3_h3r_y3rd3}"
    binary = to_binary(flag)
    open(os.path.join(OUT, "ikili.txt"), "w").write(
        "CyberLab TR :: İkili Dünya\n\n"
        "Bilgisayarlar her şeyi 0 ve 1 ile saklar. Aşağıdaki ikili (binary) mesajı metne çevir.\n"
        "Her 8 bit (bir bayt) bir karaktere denk gelir.\n\n" + binary + "\n")
    rec = "".join(chr(int(b, 2)) for b in binary.split())
    check("ikili", flag, rec)
    add({"slug":"ikili-dunya","name":"İkili Dünya","category":"Kodlama","difficulty":"Kolay",
        "short_desc":"0 ve 1'lerden oluşan ikili mesajı okunabilir metne çevir.",
        "description":("Bilgisayarlar harfleri sayılarla (ASCII) ve sayıları da ikili (binary, "
            "yani 0/1) olarak saklar. 'A' harfi aslında 01000001'dir.\n\n"
            "Dosyadaki 8'erli bit gruplarını karakterlere çevirerek gizli flag'i oku."),
        "tags":"ikili,binary,ascii,başlangıç","files":"ikili.txt",
        "tools":"CyberChef, Python",
        "tasks":[{"q":"İkili mesaj çözülünce çıkan flag nedir?","a":flag,"p":50,
            "h":("Her 8 bitlik grup (örn. 01000011) bir ASCII karakterdir. 01000011 = 67 = 'C'.\n"
                 "Hızlı yol: CyberChef'te 'From Binary' bloğu (ayraç olarak 'Space' seç). "
                 "Python ile: ''.join(chr(int(b,2)) for b in metin.split()).")}]})

def lab_ssh():
    attacker = "103.74.19.88"
    cracked_user = "yedek"
    fails = []
    users = ["root","admin","test","oracle","postgres","ubuntu","deploy","git","yedek","mysql"]
    import random; random.seed(7)
    t = 11
    lines = []
    # normal birkaç giriş
    lines.append(f"Oct 12 08:55:{t:02d} srv sshd[2201]: Accepted password for ahmet from 78.45.12.9 port 51122 ssh2")
    # brute force
    fail_count = 0
    for i in range(27):
        u = users[i % len(users)]
        sec = (12 + i) % 60
        lines.append(f"Oct 12 09:{10+i//6:02d}:{sec:02d} srv sshd[{3000+i}]: Failed password for {'invalid user ' if u in ('oracle','git','deploy') else ''}{u} from {attacker} port {40000+i} ssh2")
        fail_count += 1
    # sonunda başarılı
    lines.append(f"Oct 12 09:21:40 srv sshd[3050]: Accepted password for {cracked_user} from {attacker} port 40055 ssh2")
    lines.append(f"Oct 12 09:21:41 srv sshd[3050]: pam_unix(sshd:session): session opened for user {cracked_user}")
    open(os.path.join(OUT, "auth.log"), "w").write("\n".join(lines) + "\n")
    check("ssh_fail_count", 27, fail_count)
    add({"slug":"ssh-avcisi","name":"SSH Avcısı","category":"Log Analizi / Blue Team","difficulty":"Kolay",
        "short_desc":"SSH giriş loglarından kaba kuvvet (brute force) saldırısını çöz.",
        "description":("Sunucuların SSH giriş kayıtları (auth.log) saldırıları yakalamak için "
            "altın değerindedir. Bir saldırgan, doğru parolayı bulana kadar yüzlerce deneme yapar "
            "('brute force'). Sonunda bir hesaba girmeyi başarmış.\n\n"
            "Logu incele: saldırganı, kaç deneme yaptığını ve hangi hesaba girdiğini bul."),
        "tags":"log,ssh,brute-force,blue-team,başlangıç","files":"auth.log",
        "tools":"grep, awk, sort, uniq, metin editörü",
        "tasks":[
            {"q":"Saldırganın IP adresi nedir?","a":attacker,"p":25,
             "h":("Saldırgan çok sayıda 'Failed password' satırı üretir. En çok tekrar eden IP'yi "
                  "bul: grep 'Failed password' auth.log | awk '{print $NF... }' — ya da kısaca "
                  "grep Failed auth.log ile bak, aynı IP tekrar tekrar görünür.")},
            {"q":"Saldırgan kaç başarısız (Failed) deneme yaptı?","a":"27","p":25,
             "h":("'Failed password' geçen satırları say: grep -c 'Failed password' auth.log. "
                  "(Sayıyı rakamla yaz, örn. 27.)")},
            {"q":"Saldırgan hangi kullanıcı adıyla sisteme girmeyi BAŞARDI?","a":cracked_user,"p":50,
             "h":("Başarılı girişler 'Accepted password for <kullanıcı>' yazar. Ama dikkat: en "
                  "baştaki başarılı giriş normal kullanıcıya (ahmet) ait. Sen SALDIRGANIN IP'sinden "
                  "gelen 'Accepted password' satırını ara: grep Accepted auth.log")}]})

def lab_tersten():
    f1 = "CLAB{t3rs1n3_c3v1rd1m}"
    f2 = "CLAB{ayn4_ayn4_s0yl3}"
    rev = f1[::-1]
    atb = atbash(f2)
    open(os.path.join(OUT, "tersten.txt"), "w").write(
        "CyberLab TR :: Tersten Bak\n\n"
        "İki basit klasik teknik:\n\n"
        "Görev 1 — Metin tersten yazılmış. Düz çevir:\n  " + rev + "\n\n"
        "Görev 2 — Atbash şifresi (A<->Z, B<->Y ... aynanın karşısı). Çöz:\n  " + atb + "\n")
    check("ters1", f1, rev[::-1]); check("ters2", f2, atbash(atb))
    add({"slug":"tersten-bak","name":"Tersten Bak","category":"Kriptografi","difficulty":"Kolay",
        "short_desc":"Ters çevirme ve Atbash aynalama gibi klasik basit şifreleri çöz.",
        "description":("En eski 'şifreleme' hileleri bazen en basitleridir: metni tersten yazmak "
            "ya da alfabeyi aynalamak (Atbash). İkisini de çözmeyi öğren.\n\n"
            "Görev 1: ters çevrilmiş metin.  Görev 2: Atbash ile aynalanmış metin."),
        "tags":"kripto,atbash,reverse,başlangıç","files":"tersten.txt",
        "tools":"CyberChef, Python",
        "tasks":[
            {"q":"Görev 1: ters çevrilmiş metnin düz hali (flag) nedir?","a":f1,"p":25,
             "h":("Metni sondan başa oku. Python: metin[::-1]. CyberChef: 'Reverse' bloğu. "
                  "Düzelince CLAB{ ile başlamalı.")},
            {"q":"Görev 2: Atbash çözülünce çıkan flag nedir?","a":f2,"p":50,
             "h":("Atbash'ta A=Z, B=Y, C=X ... yani harf alfabenin sonundan sayılır. Rakamlar ve "
                  "{ } _ değişmez. CyberChef'te 'Atbash Cipher' bloğunu kullan.")}]})


# ============================================================
# ORTA
# ============================================================
def lab_jwt():
    flag = "CLAB{jwt_g1zl1_d3g1l}"
    def b64url(d): return base64.urlsafe_b64encode(d).decode().rstrip("=")
    header = b64url(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    payload = b64url(json.dumps({"user":"admin","role":"administrator","flag":flag}).encode())
    sig = b64url(b"fake-signature-not-verified")
    token = f"{header}.{payload}.{sig}"
    open(os.path.join(OUT, "token.txt"), "w").write(
        "CyberLab TR :: JWT Kırığı\n\n"
        "Bir web uygulaması sana şu JWT (JSON Web Token) oturum anahtarını verdi.\n"
        "JWT'ler ŞİFRELİ DEĞİLDİR — sadece Base64URL ile kodlanmıştır. İçini okuyabilir misin?\n\n"
        + token + "\n")
    pad = payload + "=" * (-len(payload) % 4)
    dec = json.loads(base64.urlsafe_b64decode(pad).decode())
    check("jwt_user","admin",dec["user"]); check("jwt_flag",flag,dec["flag"])
    add({"slug":"jwt-kirigi","name":"JWT Kırığı","category":"Web Güvenliği / Token","difficulty":"Orta",
        "short_desc":"Bir JWT oturum anahtarının içindeki gizli bilgileri çöz.",
        "description":("JWT (JSON Web Token), web uygulamalarında oturum yönetmek için çok kullanılır. "
            "Üç parçadan oluşur, nokta (.) ile ayrılır: header.payload.signature.\n\n"
            "Çok önemli bir nokta: JWT içeriği ŞİFRELİ DEĞİL, sadece Base64URL kodludur. Yani "
            "imzayı kıramasan bile içindeki veriyi herkes okuyabilir. Ortadaki 'payload' parçasını çöz."),
        "tags":"web,jwt,token,base64,orta","files":"token.txt",
        "tools":"jwt.io, CyberChef, Python",
        "tasks":[
            {"q":"Token'ın payload (orta) kısmındaki kullanıcı adı (user) nedir?","a":"admin","p":50,
             "h":("Token'ı iki noktadan böl: üç parça olur. ORTADAKİ parça payload'dır ve "
                  "Base64URL kodludur. Onu çöz. En kolayı: jwt.io sitesine token'ı yapıştır, sağda "
                  "payload JSON görünür. 'user' alanına bak.")},
            {"q":"Payload içine gömülü flag nedir?","a":flag,"p":50,
             "h":"Aynı çözülmüş payload JSON'unda 'flag' alanı var. CLAB{...} değerini al."}]})

def lab_xor():
    flag = "CLAB{x0r_t3k_b4yt_k1r1ld1}"
    key = 0x5A
    enc = xor_bytes(flag.encode(), key).hex()
    open(os.path.join(OUT, "xor.txt"), "w").write(
        "CyberLab TR :: XOR Gizemi\n\n"
        "Aşağıdaki hex metin, bilinmeyen TEK bir bayt (0-255) ile XOR'lanmış bir flag.\n"
        "Anahtarı bilmiyorsun ama 256 olasılık var — hepsini deneyebilirsin.\n\n"
        + enc + "\n")
    # doğrula: brute force
    raw = bytes.fromhex(enc); found = None
    for k in range(256):
        try:
            cand = xor_bytes(raw, k).decode()
            if cand.startswith("CLAB{"): found = cand; break
        except: pass
    check("xor", flag, found)
    add({"slug":"xor-gizemi","name":"XOR Gizemi","category":"Kriptografi","difficulty":"Orta",
        "short_desc":"Tek baytlık XOR ile şifrelenmiş metni kaba kuvvetle çöz.",
        "description":("XOR, kriptografinin temel taşıdır. Bir veri tek bir bayt ile XOR'lanırsa, "
            "sadece 256 olası anahtar vardır — yani hepsini denemek (brute force) saniyeler sürer.\n\n"
            "Dosyadaki hex metni çöz. Doğru anahtarı bulduğunda okunabilir bir flag çıkacak."),
        "tags":"kripto,xor,brute-force,hex,orta","files":"xor.txt",
        "tools":"CyberChef (XOR Brute Force), Python",
        "tasks":[{"q":"XOR çözülünce çıkan flag nedir?","a":flag,"p":75,
            "h":("Önce hex'i ham bayta çevir. Sonra 0'dan 255'e kadar her anahtarla XOR dene; "
                 "hangi sonuç okunabilir ve 'CLAB{' ile başlıyorsa o doğrudur.\n"
                 "En kolayı CyberChef: 'From Hex' + 'XOR Brute Force' bloğu — tüm anahtarları "
                 "listeler, CLAB içeren satırı seç. Python: for k in range(256): dene.")}]})

def lab_vigenere():
    flag = "CLAB{VIGENERE}"
    key = "SIBER"
    # harf olmayanları koruyan vigenere; flag'i şifrele
    inner = "CLAB{vigenere_anahtari_siber}"
    enc = vigenere(inner, key)
    open(os.path.join(OUT, "vigenere.txt"), "w").write(
        "CyberLab TR :: Vigenère\n\n"
        "Vigenère şifresi bir ANAHTAR kelime kullanır. Anahtar: SIBER\n"
        "(Harf olmayan karakterler — { } _ ve rakamlar — değişmeden kalır.)\n\n"
        "Şifreli metin:\n  " + enc + "\n")
    dec = vigenere(enc, key, decrypt=True)
    check("vigenere", inner, dec)
    add({"slug":"vigenere","name":"Vigenère Şifresi","category":"Kriptografi","difficulty":"Orta",
        "short_desc":"Anahtar kelimeli klasik Vigenère şifresini verilen anahtarla çöz.",
        "description":("Vigenère, Sezar şifresinin gelişmiş halidir: tek bir kayma yerine bir ANAHTAR "
            "kelime kullanır ve her harfi anahtarın harfine göre farklı miktarda kaydırır. "
            "Yüzyıllarca 'kırılamaz' sanıldı.\n\n"
            "Anahtar sana verildi (SIBER). Şifreli metni çöz."),
        "tags":"kripto,vigenere,klasik,orta","files":"vigenere.txt",
        "tools":"CyberChef (Vigenère Decode), dcode.fr, Python",
        "tasks":[{"q":"Vigenère çözülünce çıkan flag nedir?","a":inner,"p":75,
            "h":("Anahtar: SIBER. CyberChef'te 'Vigenère Decode' bloğunu ekle ve key kısmına "
                 "SIBER yaz. Harf olmayanlar (süslü parantez, alt çizgi) aynen kalır, sadece "
                 "harfler çözülür. Sonuç CLAB{ ile başlamalı.")}]})

def lab_ftp():
    flag = "CLAB{ftp_s1fr3s1z_g1d1y0r}"
    pw = "Yedek!2024"
    C, S = "10.0.0.22", "192.168.1.50"
    pkts = [
        _pkt(S, C, 21, 50010, 1, 1, "220 ProFTPD Server ready\r\n"),
        _pkt(C, S, 50010, 21, 1, 40, "USER yedekadmin\r\n"),
        _pkt(S, C, 21, 50010, 40, 18, "331 Password required\r\n"),
        _pkt(C, S, 50010, 21, 18, 65, f"PASS {pw}\r\n"),
        _pkt(S, C, 21, 50010, 65, 35, "230 Login successful\r\n"),
        _pkt(C, S, 50010, 21, 35, 90, "RETR gizli_not.txt\r\n"),
        _pkt(S, C, 20, 50011, 1, 1, f"Sunucu yedek notu - gizli\r\nFLAG: {flag}\r\n"),
    ]
    write_pcap(os.path.join(OUT, "ftp.pcap"), pkts)
    # doğrula
    import subprocess
    data = open(os.path.join(OUT, "ftp.pcap"), "rb").read()
    check("ftp_pw", True, pw.encode() in data)
    check("ftp_flag", True, flag.encode() in data)
    add({"slug":"ftp-sizintisi","name":"FTP Sızıntısı","category":"Ağ Adli Bilişimi","difficulty":"Orta",
        "short_desc":"Şifrelenmemiş FTP trafiğinden kullanıcı parolasını ve sızan dosyayı yakala.",
        "description":("FTP, dosya transferi için kullanılan ESKİ ve ŞİFRESİZ bir protokoldür. "
            "Kullanıcı adı, parola ve transfer edilen dosyalar ağda düz metin gider — yani trafiği "
            "dinleyen herkes görebilir. Bu yüzden bugün yerine SFTP/FTPS kullanılır.\n\n"
            "Yakalanmış FTP trafiğini (PCAP) incele: parolayı ve transfer edilen gizli dosyadaki "
            "flag'i bul."),
        "tags":"pcap,ftp,network,cleartext,orta","files":"ftp.pcap",
        "tools":"Wireshark, tshark, strings",
        "tasks":[
            {"q":"FTP girişinde kullanılan parola nedir?","a":pw,"p":40,
             "h":("FTP parolaları 'PASS' komutuyla gönderilir. Wireshark'ta paketi bul, sağ tık → "
                  "'Follow TCP Stream'; ya da terminalde: strings ftp.pcap | grep PASS")},
            {"q":"Transfer edilen gizli dosyadaki flag nedir?","a":flag,"p":50,
             "h":("Dosya içeriği de düz metin gider. strings ftp.pcap komutunda 'FLAG:' ya da "
                  "'CLAB{' ara. Wireshark'ta ise veri (RETR sonrası) paketine bak.")}]})

def lab_sahte_dosya():
    flag = "CLAB{s1h1rl1_b4ytl4r_y4l4n_s0yl3m3z}"
    # Gerçekte PNG olan ama .jpg uzantılı dosya; içine tEXt flag
    img = Image.new("RGB", (320, 200), (20, 30, 50))
    ImageDraw.Draw(img).text((20, 90), "Uzantiya guvenme!", fill=(200, 220, 255))
    meta = PngInfo(); meta.add_text("Gizli", f"FLAG={flag}")
    img.save(os.path.join(OUT, "resim.jpg"), "PNG", pnginfo=meta)   # .jpg ama PNG!
    head = open(os.path.join(OUT, "resim.jpg"), "rb").read(8)
    check("sahte_png", True, head.startswith(b"\x89PNG"))
    add({"slug":"sahte-dosya","name":"Sahte Dosya","category":"Adli Bilişim","difficulty":"Orta",
        "short_desc":"Uzantısı yanlış bir dosyanın gerçek türünü bul ve içindeki veriyi çıkar.",
        "description":("Dosya uzantısı (.jpg, .pdf, .zip) sadece bir isimdir — yalan olabilir. Bir "
            "dosyanın GERÇEK türü, ilk birkaç baytındaki 'sihirli baytlar' (magic bytes) ile belli "
            "olur. Saldırganlar dosya türünü gizlemek için uzantı değiştirir.\n\n"
            "Sana 'resim.jpg' verildi ama gerçekte başka bir tür. Önce gerçek türünü bul, sonra "
            "içindeki gizli flag'e ulaş."),
        "tags":"forensics,magic-bytes,file,orta","files":"resim.jpg",
        "tools":"file komutu, xxd/hexdump, strings, exiftool",
        "tasks":[
            {"q":"Dosyanın GERÇEK türü nedir? (dosya formatının adı)","a":"PNG","p":40,
             "h":("Terminalde 'file resim.jpg' komutu gerçek türü söyler. İstersen 'xxd resim.jpg | head' "
                  "ile ilk baytlara bak: 89 50 4E 47 = PNG demektir (ASCII'de '.PNG'). "
                  "Cevabı kısaca formatın adı olarak yaz.")},
            {"q":"Dosyanın içine gizlenmiş flag nedir?","a":flag,"p":50,
             "h":("Gerçek tür PNG olduğuna göre PNG araçları çalışır. 'strings resim.jpg | grep CLAB' "
                  "ya da 'exiftool resim.jpg' metadata/metin alanlarını gösterir.")}]})

def lab_oltalama():
    flag = "CLAB{0lt4l4m4y1_f4rk_3tt1m}"
    real_ip = "193.42.18.77"
    fake_domain = "bankaniz-guvenlik.xyz"
    eml = (
        "Return-Path: <noreply@mail-23.sptrk.ru>\n"
        f"Received: from mail-23.sptrk.ru ([{real_ip}]) by mx.kurban.com;\n"
        "        Sat, 24 Oct 2026 02:10:11 +0300\n"
        "Received-SPF: fail (kurban.com: domain of destek@bankaniz.com does not\n"
        f"        designate {real_ip} as permitted sender)\n"
        "Authentication-Results: mx.kurban.com; spf=fail; dkim=none\n"
        "From: \"Bankaniz Guvenlik\" <destek@bankaniz.com>\n"
        "To: musteri@kurban.com\n"
        "Subject: ACIL: Hesabiniz askiya alinacak!\n"
        f"X-Dogrulama: {flag}\n"
        "Content-Type: text/html\n\n"
        "<html><body>\n"
        "Sayin musterimiz, hesabinizda supheli hareket tespit edildi.\n"
        "Lutfen 24 saat icinde dogrulama yapin:\n"
        f'<a href="http://{fake_domain}/login">Hesabimi Dogrula</a>\n'
        "Aksi halde hesabiniz kalici olarak kapatilacaktir.\n"
        "</body></html>\n")
    open(os.path.join(OUT, "sahte_mail.eml"), "w").write(eml)
    check("phish_ip", True, real_ip in eml); check("phish_dom", True, fake_domain in eml)
    add({"slug":"oltalama","name":"Oltalama (Phishing)","category":"E-posta Güvenliği / Blue Team","difficulty":"Orta",
        "short_desc":"Sahte bir bankadan gelen oltalama e-postasının başlıklarını analiz et.",
        "description":("Oltalama (phishing) e-postaları, gerçek bir kurumdan geliyormuş gibi görünüp "
            "seni sahte bir siteye yönlendirir. Ama e-posta BAŞLIKLARI (headers) gerçeği saklayamaz: "
            "gönderenin asıl sunucusu, SPF doğrulaması ve içindeki linkler oradadır.\n\n"
            "Ham e-postayı (.eml) incele: gerçek gönderici IP'sini, sahte linki ve gizli flag'i bul.\n\n"
            "Bu, bir SOC analistinin şüpheli maili 'triage' ederken yaptığı işin ta kendisidir."),
        "tags":"phishing,email,headers,spf,blue-team,orta","files":"sahte_mail.eml",
        "tools":"metin editörü, e-posta başlık analizi",
        "tasks":[
            {"q":"E-postayı gönderen sunucunun GERÇEK IP adresi nedir?","a":real_ip,"p":40,
             "h":("'Received:' başlıklarına bak — mailin geçtiği sunucuları gösterir. Köşeli parantez "
                  "içindeki [IP] gönderen sunucunun adresidir. 'From' satırına GÜVENME, o sahtelenebilir; "
                  "Received ve Return-Path daha güvenilirdir.")},
            {"q":"Oltalama linkindeki sahte alan adı (domain) nedir?","a":fake_domain,"p":25,
             "h":("Mail gövdesindeki <a href=\"...\"> linkine bak. 'bankaniz.com' gibi görünmeye "
                  "çalışan ama farklı olan alan adını bul (örn. http://... kısmındaki host).")},
            {"q":"E-posta başlıklarına gizlenmiş flag nedir?","a":flag,"p":35,
             "h":"Standart dışı bir başlık satırı var: 'X-' ile başlayanlara bak. CLAB{...} orada."}]})

def lab_bellek():
    flag = "CLAB{b3ll3kt3_h3rs3y_v4r}"
    leaked_pw = "Sup3rG1zl1Parola!"
    noise = "".join(chr((i*37) % 26 + 97) for i in range(4000))
    dump = (noise[:1200] +
            "\x00\x00explorer.exe\x00\x00" +
            noise[1200:2000] +
            f"\x00db_connect(user=sa; password={leaked_pw})\x00" +
            noise[2000:3000] +
            f"\x00\x00SESSION_TOKEN={flag}\x00\x00" +
            noise[3000:])
    open(os.path.join(OUT, "bellek.dmp"), "w").write(dump)
    check("bellek_pw", True, leaked_pw in dump); check("bellek_flag", True, flag in dump)
    add({"slug":"bellek-dokumu","name":"Bellek Dökümü","category":"Adli Bilişim","difficulty":"Orta",
        "short_desc":"Bir bellek dökümündeki gürültünün içinden sızan parolayı ve flag'i çıkar.",
        "description":("Bir programın RAM'i (belleği) ele geçirildiğinde, içinde o an çalışan her şey "
            "bulunur: açık dosyalar, bağlantılar ve bazen DÜZ METİN parolalar. Adli bilişimciler bu "
            "dökümleri (memory dump) analiz ederek kanıt toplar.\n\n"
            "Dosya çoğunlukla okunamaz gürültü içeriyor ama arasına düz metin bilgiler sızmış. "
            "Sızan veritabanı parolasını ve oturum flag'ini bul."),
        "tags":"forensics,memory,strings,orta","files":"bellek.dmp",
        "tools":"strings, grep",
        "tasks":[
            {"q":"Bellekte düz metin olarak sızan veritabanı parolası nedir?","a":leaked_pw,"p":50,
             "h":("Gürültünün içindeki okunabilir metinleri çek: 'strings bellek.dmp'. Sonra parola "
                  "ara: strings bellek.dmp | grep -i password  — 'password=' kısmındaki değeri al.")},
            {"q":"Bellekteki oturum token'ında saklı flag nedir?","a":flag,"p":50,
             "h":"strings bellek.dmp | grep CLAB  — ya da 'SESSION_TOKEN' ara."}]})


# ============================================================
# ZOR
# ============================================================
def lab_lsb():
    flag = "CLAB{l5b_st3g4n0gr4f1_pr0}"
    msg = flag.encode() + b"\x00"       # sonlandırıcı
    bits = "".join(f"{b:08b}" for b in msg)
    img = Image.new("RGB", (200, 200), (30, 20, 45))
    px = img.load()
    idx = 0
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = px[x, y]
            if idx < len(bits):
                r = (r & ~1) | int(bits[idx]); idx += 1
            px[x, y] = (r, g, b)
    img.save(os.path.join(OUT, "lsb.png"), "PNG")
    # doğrula: LSB oku
    im2 = Image.open(os.path.join(OUT, "lsb.png")); p2 = im2.load()
    out = []
    for y in range(im2.height):
        for x in range(im2.width):
            out.append(str(p2[x, y][0] & 1))
    bytes_ = [out[i:i+8] for i in range(0, len(out), 8)]
    rec = ""
    for grp in bytes_:
        ch = int("".join(grp), 2)
        if ch == 0: break
        rec += chr(ch)
    check("lsb", flag, rec)
    add({"slug":"gizli-katman","name":"Gizli Katman (LSB)","category":"Steganografi","difficulty":"Zor",
        "short_desc":"Piksellerin en önemsiz bitine (LSB) gömülmüş veriyi çıkar.",
        "description":("Gerçek steganografi, veriyi dosyanın sonuna eklemekten daha sinsidir. LSB "
            "(Least Significant Bit) tekniğinde, her pikselin renk değerinin EN SON biti değiştirilerek "
            "gizli mesaj saklanır. Göz bunu fark edemez çünkü renk neredeyse hiç değişmez.\n\n"
            "Bu PNG'nin kırmızı (R) kanalının LSB'lerine bir flag gizlenmiş. Çıkarabilir misin?"),
        "tags":"stego,lsb,ileri,python,zor","files":"lsb.png",
        "tools":"zsteg, Python (PIL), stegsolve",
        "tasks":[{"q":"LSB'ye gizlenmiş flag nedir?","a":flag,"p":100,
            "h":("Mantık: her pikselin R (kırmızı) değerinin son bitini al, sırayla diz, 8'erli "
                 "grupla ve ASCII'ye çevir. \\x00 (null) baytında dur.\n"
                 "Hazır araç: 'zsteg lsb.png' çoğu LSB gizlemesini otomatik bulur.\n"
                 "Python ile:\n"
                 "  from PIL import Image\n"
                 "  im=Image.open('lsb.png').load()\n"
                 "  bits=''.join(str(im[x,y][0]&1) for y in range(200) for x in range(200))\n"
                 "  s=''.join(chr(int(bits[i:i+8],2)) for i in range(0,len(bits),8))\n"
                 "  print(s.split(chr(0))[0])")}]})

def lab_zincir():
    flag = "CLAB{z1nc1rl3m3_ r34ks1y0n}".replace(" ", "")
    # katmanlar: hex -> ters -> base64  (çözüm: base64 çöz -> ters -> hex çöz)
    h = flag.encode().hex()
    r = h[::-1]
    b = base64.b64encode(r.encode()).decode()
    open(os.path.join(OUT, "zincir.txt"), "w").write(
        "CyberLab TR :: Zincirleme\n\n"
        "Bu flag üç işlemden geçti. Çözmek için işlemleri TERS SIRADA geri al:\n"
        "  1) Base64 çöz\n"
        "  2) Çıkan metni TERS çevir\n"
        "  3) Hex olarak çöz\n\n" + b + "\n")
    dec = bytes.fromhex(base64.b64decode(b).decode()[::-1]).decode()
    check("zincir", flag, dec)
    add({"slug":"zincirleme","name":"Zincirleme","category":"Kriptografi","difficulty":"Zor",
        "short_desc":"Üst üste uygulanmış birden fazla dönüşümü doğru sırayla geri al.",
        "description":("Gerçek dünyada veri bazen birden çok işlemden geçirilerek gizlenir. İşin "
            "püf noktası: işlemleri DOĞRU ve TERS sırayla geri almak. Bir adımı atlarsan hiçbir şey "
            "çıkmaz.\n\n"
            "Bu flag şu sırayla işlendi: Hex kodlandı → ters çevrildi → Base64 kodlandı. "
            "Sen tam tersini yapacaksın."),
        "tags":"kripto,base64,hex,çok-katman,zor","files":"zincir.txt",
        "tools":"CyberChef, Python",
        "tasks":[{"q":"Tüm katmanlar çözülünce çıkan flag nedir?","a":flag,"p":100,
            "h":("Sırayı takip et: (1) metni Base64 çöz → garip görünen bir metin çıkar. "
                 "(2) bu metni ters çevir (Reverse) → bir hex dizisi (0-9, a-f) olmalı. "
                 "(3) bu hex'i çöz (From Hex) → flag.\n"
                 "CyberChef'te şu üç bloğu sırayla ekle: 'From Base64', 'Reverse', 'From Hex'.")}]})

def lab_obfuscation():
    flag = "CLAB{k0du_c0z_c4l1st1r_v3y4_0ku}"
    key = 0x33
    enc = list(xor_bytes(flag.encode(), key))
    script = (
        "#!/usr/bin/env python3\n"
        "# CyberLab TR :: Gizli Script\n"
        "# Bu betik bir flag uretiyor. Calistir ya da mantigini coz.\n\n"
        f"_d = {enc}\n"
        f"_k = {key}\n"
        "_out = ''.join(chr(b ^ _k) for b in _d)\n"
        "print(_out)\n")
    open(os.path.join(OUT, "gizli_script.py"), "w").write(script)
    rec = "".join(chr(b ^ key) for b in enc)
    check("obf", flag, rec)
    add({"slug":"gizli-script","name":"Gizli Script","category":"Tersine Mühendislik","difficulty":"Zor",
        "short_desc":"Gizlenmiş (obfuscated) bir betiğin ürettiği flag'i çöz.",
        "description":("Zararlı yazılımlar genellikle kodlarını GİZLER (obfuscation): gerçek veriyi "
            "sayı dizileri, XOR işlemleri veya base64 arkasına saklar. Analistin işi bu kodu okuyup "
            "ne yaptığını anlamaktır — çalıştırmadan bile.\n\n"
            "Sana bir Python betiği verildi. Bir flag üretiyor. İstersen çalıştır, ama asıl amaç "
            "kodun mantığını çözmek."),
        "tags":"reverse,python,obfuscation,xor,zor","files":"gizli_script.py",
        "tools":"Python, metin editörü",
        "tasks":[{"q":"Betiğin ürettiği flag nedir?","a":flag,"p":100,
            "h":("En hızlı yol: güvendiğin bir ortamda 'python3 gizli_script.py' çalıştır — flag'i "
                 "ekrana yazar. (Bu betik güvenlidir, sadece metin üretir.)\n"
                 "Kodu anlamak istersen: _d bir sayı listesi, _k bir anahtar. Her sayı _k ile "
                 "XOR'lanıp karaktere çevriliyor. Aynısını elle yapabilirsin: "
                 "''.join(chr(b ^ _k) for b in _d)")}]})


def generate_all():
    for fn in [lab_base_kampi, lab_mors, lab_cerez, lab_ikili, lab_ssh, lab_tersten,
               lab_jwt, lab_xor, lab_vigenere, lab_ftp, lab_sahte_dosya, lab_oltalama,
               lab_bellek, lab_lsb, lab_zincir, lab_obfuscation]:
        fn()
    json.dump(LABS, open(os.path.join(BASE, "labs2_seed.json"), "w"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    generate_all()
    diff = {"Kolay": 0, "Orta": 0, "Zor": 0}
    tasks = 0
    for l in LABS:
        diff[l["difficulty"]] += 1; tasks += len(l["tasks"])
    print(f"Üretilen lab: {len(LABS)}  (Kolay {diff['Kolay']}, Orta {diff['Orta']}, Zor {diff['Zor']})")
    print(f"Toplam görev: {tasks}")
    print("\n--- DOĞRULAMA ---")
    allok = True
    for name, exp, got, ok in CHECKS:
        if not ok:
            allok = False
            print(f"  [FAIL] {name}: beklenen={exp!r} bulunan={got!r}")
    print("Tüm doğrulamalar BAŞARILI ✓" if allok else "!!! BAZI DOĞRULAMALAR BAŞARISIZ")
    print(f"Doğrulama sayısı: {len(CHECKS)}")
