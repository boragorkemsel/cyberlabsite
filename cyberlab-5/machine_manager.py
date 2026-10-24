"""
Makine Yoneticisi — zafiyetli uygulamalari baslatip durduran modul.
Her makine ayri bir portta calisan ayri bir Python prosesidir.
"""
import os
import sys
import subprocess
import signal
import time

MACHINES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "machines")

# Calisan makineler: {machine_id: {"process": Popen, "port": int, "started_by": user_id}}
_running = {}

# Makine tanimlari
MACHINE_CATALOG = {
    "hackme_web": {
        "name": "HackMe Web",
        "description": "SQL Injection, Command Injection ve Directory Traversal zafiyetleri iceren bir sirket portali. Web guvenliginin temellerini ogrenin.",
        "difficulty": "Kolay",
        "category": "Web Guvenligi",
        "base_port": 7000,
        "script": "machines/hackme_web/app.py",
        "tasks": [
            {
                "question": "Giris sayfasinda SQL Injection ile admin olarak giris yap. Admin flag'ini bul. (CLAB{...})",
                "answer": "CLAB{sql_injection_basarili_7x9k}",
                "hint": "Kullanici adi alanina ' OR '1'='1' -- gibi bir payload dene. Amac: WHERE kosulunu her zaman dogru yapmak.",
                "points": 30,
            },
            {
                "question": "Ping aracindaki Command Injection zafiyetini kullanarak sunucunun ortam degiskenlerinde (environment variables) saklanan gizli flag'i bul. (CLAB{...})",
                "answer": "CLAB{command_injection_ustasi_4m2p}",
                "hint": "Ping alanina `127.0.0.1; env` ya da `127.0.0.1; echo $APP_SECRET_FLAG` dene. Noktali virgul (;) ile ikinci bir komut calistirabilirsin. Flag ortam degiskenlerinde gizli.",
                "points": 30,
            },
            {
                "question": "Dosya goruntuleme sayfasindaki Directory Traversal zafiyetini kullan. secret/flag.txt dosyasini oku. (CLAB{...})",
                "answer": "CLAB{directory_traversal_pro_8w3n}",
                "hint": "Dosya adina ../secret/flag.txt gibi bir ust dizin gecisi dene. Uygulama dosya yolunu filtrelemiyor.",
                "points": 25,
            },
            {
                "question": "Web uygulamasinin gizli admin panelini bul. Flag'i yaz. (CLAB{...})",
                "answer": "CLAB{gizli_admin_paneli_bulundu_5q1r}",
                "hint": "Web sitesinin kaynak kodunu (HTML yorumlari) incele veya robots.txt dosyasini kontrol et. Gizli URL'ler orada olabilir.",
                "points": 25,
            },
            {
                "question": "robots.txt dosyasinda gizlenen flag'i bul. (CLAB{...})",
                "answer": "CLAB{robots_txt_ipucu_yakalandi_2j6v}",
                "hint": "Tarayicida /robots.txt adresine git. Arama motorlari icin gizlenen dizinlere ve yorumlara bak.",
                "points": 15,
            },
        ],
    },

    "veribank": {
        "name": "VeriBank",
        "description": "Bir internet bankaciligi portali. IDOR, cerez ile yetki yukseltme, acik API, PIN kaba kuvvet ve is mantigi hatasi zafiyetlerini barindirir. Giris icin test hesabi: musteri01 / parola123.",
        "difficulty": "Orta",
        "category": "Web Guvenligi",
        "base_port": 7001,
        "script": "machines/veribank/app.py",
        "tasks": [
            {
                "question": "IDOR zafiyetini kullanarak Genel Mudur'un (100100 numarali hesap) hesap detayini goruntule. 'Aciklama / Not' alanindaki flag'i bul. (CLAB{...})",
                "answer": "CLAB{idor_mudur_hesabi_ele_gecti_9b2x}",
                "hint": "Giris yaptiktan sonra kendi hesap detayina bak: URL `/hesap/detay?no=100123` gibi. Buradaki 'no' parametresini baska bir numarayla (100100) degistir. Uygulama hesabin sana ait olup olmadigini kontrol etmiyor.",
                "points": 30,
            },
            {
                "question": "Cerez (cookie) ile yetki yukseltme yaparak Yonetim Paneli'ne gir. Panodeki flag'i bul. (CLAB{...})",
                "answer": "CLAB{cerez_rolu_yonetici_yapildi_4k7p}",
                "hint": "Giris yapinca tarayicina `vb_rol=musteri` adli bir cerez yazilir. Tarayici gelistirici araclarindan (F12 > Application/Storage > Cookies) bu cerezi `yonetici` yap, sonra /yonetim sayfasini ac.",
                "points": 30,
            },
            {
                "question": "Kimlik dogrulamasi olmayan acik API endpoint'ini bul ve sizan gizli destek hesabinin notundaki flag'i yakala. (CLAB{...})",
                "answer": "CLAB{acik_api_veri_sizdirdi_6m3q}",
                "hint": "Panonun (pano sayfasi) kaynak kodunu (sag tik > Sayfa Kaynagini Goruntule) incele. HTML yorumunda ve script icinde bir API adresi (/api/v1/...) gizli. O adrese git, tum kullanicilar JSON olarak doner.",
                "points": 25,
            },
            {
                "question": "Kart Dogrulama sayfasindaki 4 haneli PIN'i kaba kuvvet (brute force) ile kir. Dogru PIN'de cikan flag'i yaz. (CLAB{...})",
                "answer": "CLAB{pin_kaba_kuvvet_kirildi_2w8n}",
                "hint": "/kart-dogrula sayfasinda PIN denemelerinde hiz siniri yok. 0000-9999 arasini deneyen kisa bir script yaz (orn. Python requests ile POST 'pin' alani). Dogru PIN flag'i aciyor.",
                "points": 25,
            },
            {
                "question": "Para Transferi sayfasindaki is mantigi (business logic) hatasini kullanarak bakiyeni 1.000.000 TL uzerine cikar. Cikan flag'i yaz. (CLAB{...})",
                "answer": "CLAB{negatif_transfer_bakiye_patladi_5t1v}",
                "hint": "Transfer tutari pozitif mi diye kontrol edilmiyor. Tutar alanina NEGATIF bir deger (orn. -2000000) gir; para dusmek yerine bakiyene eklenir. Bakiye 1.000.000'u gecince flag cikar.",
                "points": 30,
            },
        ],
    },

    "novasoft": {
        "name": "NovaSoft",
        "description": "Bir yazilim sirketinin aceleyle yayina alinmis kurumsal web sitesi. Temel web kesif (recon) tekniklerini ogreten baslangic seviyesi makine: HTML yorumlari, robots.txt, base64, varsayilan parola ve gizli parametreler.",
        "difficulty": "Kolay",
        "category": "Web Guvenligi",
        "base_port": 7002,
        "script": "machines/novasoft/app.py",
        "tasks": [
            {
                "question": "Ana sayfanin kaynak kodunda (HTML) gizlenmis gelistirici notundaki flag'i bul. (CLAB{...})",
                "answer": "CLAB{html_yorumlari_her_zaman_oku_a1c3}",
                "hint": "Ana sayfada sag tik > 'Sayfa Kaynagini Goruntule' (Ctrl+U). HTML yorumlari <!-- ... --> icine bak; gelistiriciler oraya not birakir.",
                "points": 15,
            },
            {
                "question": "robots.txt dosyasini incele ve arama motorlarindan gizlenen eski sayfayi bul. O sayfadaki flag'i yaz. (CLAB{...})",
                "answer": "CLAB{robots_txt_gizli_yol_gosterdi_d4f6}",
                "hint": "/robots.txt adresine git. 'Disallow' satirlari gizlenen dizinleri gosterir. Oradaki /eski-panel gibi bir yolu tarayicida ac.",
                "points": 15,
            },
            {
                "question": "Kariyer sayfasindaki base64 ile kodlanmis 'Basvuru Referans Kodu'nu coz ve icindeki flag'i bul. (CLAB{...})",
                "answer": "CLAB{base64_cozuldu_gizli_kod_g7h9}",
                "hint": "/kariyer sayfasindaki kod base64'tur. CyberChef 'From Base64', ya da terminalde: echo '<kod>' | base64 -d. (== ile biten metinler genelde base64'tur.)",
                "points": 20,
            },
            {
                "question": "Yonetici giris panelinde degistirilmemis varsayilan parola ile giris yap. Cikan flag'i yaz. (CLAB{...})",
                "answer": "CLAB{varsayilan_parola_asla_birakma_k2m4}",
                "hint": "/yonetici sayfasinda cok yaygin varsayilan bilgileri dene: kullanici 'admin', parola 'admin123' veya 'admin'. Gelistiriciler kurulum parolasini degistirmeyi unutur.",
                "points": 25,
            },
            {
                "question": "Sistem Durumu sayfasindaki gizli debug parametresini bul ve debug modunu ac. Cikan flag'i yaz. (CLAB{...})",
                "answer": "CLAB{debug_modu_acik_kaldi_n5p7}",
                "hint": "/sistem sayfasini ac, sonra URL'nin sonuna ?debug=true ekle: /sistem?debug=true. Gizli gelistirme parametreleri cogu zaman aktif unutulur.",
                "points": 25,
            },
        ],
    },

    "retroarcade": {
        "name": "RetroArcade",
        "description": "Retro oyun temali bir hobi sitesi. Istemci tarafi JavaScript, HTTP basliklari, dizin listeleme, gizli form alanlari ve hex kodlama gibi FARKLI kesif tekniklerini ogreten kolay seviye makine.",
        "difficulty": "Kolay",
        "category": "Web Guvenligi",
        "base_port": 7004,
        "script": "machines/retroarcade/app.py",
        "tasks": [
            {
                "question": "Uye girisi sayfasindaki sifre kontrolu istemci tarafinda (JavaScript) yapiliyor. Sayfanin JavaScript kodunu inceleyerek gizli VIP bayragini bul. (CLAB{...})",
                "answer": "CLAB{js_asla_guvenli_degil_r3tr0}",
                "hint": "/uye-girisi sayfasinda sag tik > Sayfa Kaynagi (Ctrl+U) veya F12 ile JavaScript'i oku. Sifre ve flag dogrudan kodun icinde yazili. Istemci tarafi dogrulamaya asla guvenilmez!",
                "points": 15,
            },
            {
                "question": "Ana sayfanin HTTP yanit basliklarinda (response headers) gizlenmis flag'i bul. (CLAB{...})",
                "answer": "CLAB{http_basligi_bayragi_h34d3r}",
                "hint": "Yanit basliklarina bak: terminalde `curl -I http://<ip>:7004/` ya da tarayicida F12 > Network sekmesi > ana istek > Response Headers. 'X-' ile baslayan ozel bir basliga dikkat et.",
                "points": 15,
            },
            {
                "question": "Sitede dizin listeleme (directory listing) acik birakilmis bir klasor var. O klasordeki gizli dosyayi bul ve icindeki flag'i yaz. (CLAB{...})",
                "answer": "CLAB{acik_dizin_listeleme_d1rl1st}",
                "hint": "/eski-oyunlar/ adresine git; klasor icerigi listeleniyor. Nokta (.) ile baslayan gizli bir dosya var; onu ac.",
                "points": 20,
            },
            {
                "question": "Skor tablosu formundaki gizli alani (hidden field) degistirerek admin olarak skor gonder. Cikan flag'i yaz. (CLAB{...})",
                "answer": "CLAB{gizli_form_alani_degisti_h1dd3n}",
                "hint": "/skor-tablosu formunda gizli bir alan var: rol=oyuncu. F12 ile HTML'i duzenleyip bu degeri 'admin' yap (veya istegi elle gonder), sonra formu gonder.",
                "points": 25,
            },
            {
                "question": "Profil sayfasindaki 'Oyuncu Kodu' hex (onaltilik) ile kodlanmistir. Coz ve icindeki flag'i bul. (CLAB{...})",
                "answer": "CLAB{hex_kodu_cozuldu_h3xx}",
                "hint": "/profil sayfasindaki uzun kod hex'tir. CyberChef 'From Hex', ya da terminalde: echo '<kod>' | xxd -r -p. Sadece 0-9 ve a-f karakterleri iceren diziler genelde hex'tir.",
                "points": 25,
            },
        ],
    },

    "devhub": {
        "name": "DevHub",
        "description": "Gelistiricilerin kod paylastigi dahili bir platform. JWT alg:none, SSTI (template injection), SSRF, UNION tabanli SQL Injection ve guvensiz pickle deserializasyonu gibi ILERI seviye zafiyetler icerir. Giris: gelistirici / dev123.",
        "difficulty": "Zor",
        "category": "Web Guvenligi",
        "base_port": 7003,
        "script": "machines/devhub/app.py",
        "tasks": [
            {
                "question": "JWT token'daki 'alg:none' zafiyetini kullanarak rolunu 'admin' yap ve Yonetim Paneli'ndeki flag'i al. (CLAB{...})",
                "answer": "CLAB{jwt_alg_none_imzasiz_token_j0n3}",
                "hint": "Giris yapinca 'dh_token' cerezinde bir JWT olur (3 parca, nokta ile ayrilir). Her parca base64url'dur. Header'i {\"alg\":\"none\",\"typ\":\"JWT\"}, payload'u {\"kullanici\":\"gelistirici\",\"rol\":\"admin\"} yap, imza kismini bos birak (sonu nokta ile bitsin). Sunucu alg:none oldugunda imzayi kontrol etmiyor. jwt.io ya da kisa bir script kullanabilirsin.",
                "points": 25,
            },
            {
                "question": "Profil sayfasindaki 'ad' parametresi Jinja2 sablonuna dogrudan konuyor (SSTI). Sablon enjeksiyonu ile sunucu yapilandirmasini (config) sizdir ve flag'i bul. (CLAB{...})",
                "answer": "CLAB{ssti_jinja2_config_sizdi_t3mpl}",
                "hint": "/profil?ad=... parametresine once {{7*7}} yaz; 49 donerse SSTI vardir. Sonra ?ad={{config}} ile Flask config'ini dok; icinde DEVHUB_SECRET anahtarinda flag var. (?ad={{config.items()}} de olur.)",
                "points": 25,
            },
            {
                "question": "Webhook/URL onizleme araci sunucu tarafli istek yapiyor (SSRF). Bunu kullanarak sadece dahili erisime acik olan /dahili/anahtar endpoint'ine ulas ve flag'i al. (CLAB{...})",
                "answer": "CLAB{ssrf_dahili_servise_ulasildi_1nt3rnal}",
                "hint": "/dahili/anahtar sadece 127.0.0.1'den erisilebilir; disaridan acarsan 403 alirsin. Webhook alanina makinenin KENDI adresini yaz: http://127.0.0.1:7003/dahili/anahtar. Sunucu kendi kendine istek atinca dahili kontrolu gecer.",
                "points": 30,
            },
            {
                "question": "Snippet arama kutusu UNION tabanli SQL Injection'a acik. 'gizli' tablosundaki admin_flag kaydini dump et. (CLAB{...})",
                "answer": "CLAB{union_sqli_gizli_tablo_un10n}",
                "hint": "Arama sorgusu iki sutun donuyor (baslik, dil). Su payload'u dene: ' UNION SELECT anahtar, deger FROM gizli --  (sonda bosluk birak). Gizli tabloda anahtar/deger sutunlari var.",
                "points": 30,
            },
            {
                "question": "Oturum geri yukleme ozelligi base64 pickle verisini guvensiz sekilde deserialize ediyor (RCE). Bir pickle payload'u ile sunucudaki devhub_gizli.txt dosyasini oku. (CLAB{...})",
                "answer": "CLAB{pickle_rce_deserializasyon_p1ckl3}",
                "hint": "__reduce__ metodu (subprocess.check_output, (['cat','devhub_gizli.txt'],)) donen bir sinif yaz, pickle.dumps ile serialize et, base64'le ve /oturum-geri-yukle formuna yapistir. Sunucu pickle.loads calistirinca komut kosar ve dosya icerigi ekrana gelir. (Guvenlik icin bu testi sadece kendi lab'inda yap!)",
                "points": 35,
            },
        ],
    },
}


def get_machine_info(machine_id):
    """Makine katalogundan bilgi getir."""
    return MACHINE_CATALOG.get(machine_id)


def list_machines():
    """Tum makine tanimlarini dondur."""
    result = []
    for mid, info in MACHINE_CATALOG.items():
        status = "running" if mid in _running else "stopped"
        port = _running[mid]["port"] if mid in _running else None
        result.append({
            "id": mid,
            "name": info["name"],
            "description": info["description"],
            "difficulty": info["difficulty"],
            "category": info["category"],
            "status": status,
            "port": port,
        })
    return result


def start_machine(machine_id, user_id):
    """Makineyi baslat, port numarasini dondur."""
    if machine_id in _running:
        return {"status": "already_running", "port": _running[machine_id]["port"]}

    info = MACHINE_CATALOG.get(machine_id)
    if not info:
        return {"status": "error", "message": "Makine bulunamadi"}

    port = info["base_port"]
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), info["script"])

    if not os.path.exists(script):
        return {"status": "error", "message": f"Script bulunamadi: {script}"}

    # Makinenin ciktisini log dosyasina yaz (hem crash teshisi hem de
    # uzun suren prosesin pipe buffer'ini doldurmamasi icin)
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "machine_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{machine_id}.log")

    try:
        logf = open(log_path, "w")
        # Makineyi kendi script dizininde calistir ki goreli dosyalari bulsun
        process = subprocess.Popen(
            [sys.executable, script, str(port)],
            stdout=logf,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(script),
            preexec_fn=os.setsid,
        )
        # Biraz bekle, crash olup olmadigini kontrol et
        time.sleep(2.0)
        if process.poll() is not None:
            logf.close()
            err = ""
            try:
                with open(log_path) as f:
                    err = f.read().strip().replace("\n", " ")[-300:]
            except Exception:
                pass
            return {"status": "error",
                    "message": f"Makine baslatilamadi. Hata: {err or 'bilinmiyor'}"}

        _running[machine_id] = {
            "process": process,
            "port": port,
            "started_by": user_id,
            "pid": process.pid,
            "logf": logf,
        }
        return {"status": "started", "port": port, "pid": process.pid}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def stop_machine(machine_id):
    """Makineyi durdur."""
    if machine_id not in _running:
        return {"status": "not_running"}

    info = _running[machine_id]
    pid = info["process"].pid
    # Once process group ile dene
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        info["process"].wait(timeout=3)
    except Exception:
        # Fallback: dogrudan pid ile kill
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        # Portu dinleyen prosesi de oldurelim
        port = info.get("port")
        if port:
            try:
                subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=3)
            except Exception:
                pass

    del _running[machine_id]
    return {"status": "stopped"}


def is_running(machine_id):
    """Makine calisiyor mu?"""
    if machine_id not in _running:
        return False
    # Proses hala yasiyormu kontrol et
    if _running[machine_id]["process"].poll() is not None:
        del _running[machine_id]
        return False
    return True


def get_port(machine_id):
    """Calisan makinenin portunu dondur."""
    if machine_id in _running:
        return _running[machine_id]["port"]
    return None
