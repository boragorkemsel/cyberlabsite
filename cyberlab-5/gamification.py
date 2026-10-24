"""
Oyunlaştırma: rütbe (rank), rozet (badge) ve seri (streak) hesaplamaları.
Saf Python — veritabanına dokunmaz; app.py istatistik sözlüğünü hazırlayıp verir.
"""
from datetime import date, timedelta, datetime, timezone

LOCAL_TZ = timezone(timedelta(hours=3))   # İstanbul

# ---------------- RÜTBELER (toplam puana göre) ----------------
# (eşik, ad, renk)
RANKS = [
    (0,    "Çaylak",  "#8b8398"),
    (100,  "Acemi",   "#34d399"),
    (300,  "Gözcü",   "#38bdf8"),
    (600,  "Analist", "#3b82f6"),
    (1000, "Avcı",    "#fb923c"),
    (1500, "Uzman",   "#f87171"),
    (2200, "Usta",    "#fbbf24"),
    (3000, "Efsane",  "#93bbfd"),
]


def rank_for(points):
    cur = RANKS[0]
    nxt = None
    for i, r in enumerate(RANKS):
        if points >= r[0]:
            cur = r
            nxt = RANKS[i + 1] if i + 1 < len(RANKS) else None
    if nxt:
        span = nxt[0] - cur[0]
        prog = int((points - cur[0]) / span * 100) if span else 100
        remaining = nxt[0] - points
    else:
        prog = 100
        remaining = 0
    return {
        "name": cur[1], "color": cur[2], "min": cur[0],
        "next_name": nxt[1] if nxt else None,
        "next_at": nxt[0] if nxt else None,
        "progress": max(0, min(100, prog)),
        "remaining": remaining,
    }


# ---------------- ROZETLER ----------------
# test: stats sözlüğünden True/False döndüren fonksiyon
def _cat_has(stats, keyword):
    return any(keyword.lower() in c.lower() for c in stats["fully_cats"])


BADGES = [
    {"id": "ilk_kan",    "name": "İlk Kan",      "icon": "🩸",
     "desc": "İlk görevini çöz",                  "test": lambda s: s["solved_tasks"] >= 1},
    {"id": "ilk_lab",    "name": "Lab Avcısı",   "icon": "🎯",
     "desc": "İlk laboratuvarı tamamla",          "test": lambda s: s["solved_labs"] >= 1},
    {"id": "bes_lab",    "name": "Beşlik",       "icon": "🖐️",
     "desc": "5 laboratuvar tamamla",             "test": lambda s: s["solved_labs"] >= 5},
    {"id": "on_lab",     "name": "Onluk Çete",   "icon": "🔟",
     "desc": "10 laboratuvar tamamla",            "test": lambda s: s["solved_labs"] >= 10},
    {"id": "koleksiyon", "name": "Koleksiyoncu", "icon": "🏆",
     "desc": "Tüm laboratuvarları tamamla",       "test": lambda s: s["total_labs"] > 0 and s["solved_labs"] >= s["total_labs"]},
    {"id": "kripto",     "name": "Kriptograf",   "icon": "🔐",
     "desc": "Bir kriptografi lab'ı bitir",       "test": lambda s: _cat_has(s, "Kripto")},
    {"id": "dedektif",   "name": "Dedektif",     "icon": "🕵️",
     "desc": "Bir log/Blue Team lab'ı bitir",     "test": lambda s: _cat_has(s, "Log") or _cat_has(s, "Blue")},
    {"id": "stego",      "name": "Gölge",        "icon": "🖼️",
     "desc": "Bir steganografi lab'ı bitir",      "test": lambda s: _cat_has(s, "Stegano")},
    {"id": "casus",      "name": "Casus",        "icon": "🔎",
     "desc": "Bir OSINT/Metadata lab'ı bitir",    "test": lambda s: _cat_has(s, "OSINT")},
    {"id": "cesur",      "name": "Cesur Yürek",  "icon": "💀",
     "desc": "Bir Zor lab'ı bitir",               "test": lambda s: s["fully_diff"].get("Zor", 0) >= 1},
    {"id": "puan500",    "name": "Puan Canavarı","icon": "⚡",
     "desc": "500 puana ulaş",                    "test": lambda s: s["points_all"] >= 500},
    {"id": "puan1000",   "name": "Zirve",        "icon": "👑",
     "desc": "1000 puana ulaş",                   "test": lambda s: s["points_all"] >= 1000},
    {"id": "seri3",      "name": "Seri Avcı",    "icon": "🔥",
     "desc": "3 gün üst üste aktif ol",           "test": lambda s: s["streak"] >= 3},
]


def compute_badges(stats):
    earned, locked = [], []
    for b in BADGES:
        (earned if b["test"](stats) else locked).append(b)
    return earned, locked


# ---------------- SERİ (STREAK) ----------------
def compute_streak(iso_timestamps):
    """iso_timestamps: completed_at değerleri (UTC ISO). Ardışık aktif gün sayısı."""
    days = set()
    for ts in iso_timestamps:
        try:
            d = datetime.fromisoformat(ts).astimezone(LOCAL_TZ).date()
            days.add(d)
        except Exception:
            pass
    if not days:
        return 0
    today = datetime.now(LOCAL_TZ).date()
    # Seri bugün ya da dün bitmeli (bugün henüz çözmemiş olabilir)
    if today in days:
        anchor = today
    elif (today - timedelta(days=1)) in days:
        anchor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    d = anchor
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    return streak
