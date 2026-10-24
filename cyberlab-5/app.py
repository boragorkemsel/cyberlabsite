"""
CyberLab TR — yerel ağda çalışan, TryHackMe/HackTheBox tarzı
siber güvenlik eğitim platformu (MVP).

Çalıştırma:
    python3 app.py
Yerel ağdaki diğer cihazlardan erişim:
    http://<bu-bilgisayarin-ip-adresi>:5000
"""
import os
import secrets
from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageOps

from db import get_db, init_db, now_iso, LABFILES_DIR
from gamification import rank_for, compute_badges, compute_streak, BADGES
import machine_manager

app = Flask(__name__)
# Geliştirme için otomatik anahtar; üretimde ortam değişkeninden sabit anahtar ver.
app.secret_key = os.environ.get("CYBERLAB_SECRET", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # profil resmi en fazla 10 MB

SITE_NAME = "CyberLab TR"

# Profil resimleri static/avatars altında tutulur (Flask otomatik servis eder)
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

# Yerel saat dilimi (İstanbul, UTC+3) — haftalık sıralama için
LOCAL_TZ = timezone(timedelta(hours=3))


def week_start_utc_iso():
    """Bu haftanın (Pazartesi 00:00 yerel saat) UTC ISO karşılığı."""
    now_local = datetime.now(LOCAL_TZ)
    monday = (now_local - timedelta(days=now_local.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    return monday.astimezone(timezone.utc).isoformat(timespec="seconds")


# ----------------------------- Yardımcılar -----------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Bu sayfayı görmek için giriş yapmalısın.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_globals():
    return {"site_name": SITE_NAME, "user": current_user()}


def norm(s):
    return (s or "").strip().lower()


def user_progress(conn, user_id):
    """lab_id -> çözülen görev sayısı, ve toplanan toplam puan."""
    rows = conn.execute(
        """SELECT t.lab_id AS lab_id, t.points AS points
           FROM completions c JOIN tasks t ON t.id = c.task_id
           WHERE c.user_id = ?""",
        (user_id,),
    ).fetchall()
    solved_by_lab = {}
    points = 0
    for r in rows:
        solved_by_lab[r["lab_id"]] = solved_by_lab.get(r["lab_id"], 0) + 1
        points += r["points"]
    return solved_by_lab, points


def lab_task_totals(conn):
    """lab_id -> (görev sayısı, toplam puan)."""
    rows = conn.execute(
        "SELECT lab_id, COUNT(*) AS c, COALESCE(SUM(points),0) AS p FROM tasks GROUP BY lab_id"
    ).fetchall()
    return {r["lab_id"]: (r["c"], r["p"]) for r in rows}


def _fmt_when(iso_ts):
    """UTC ISO -> 'x dk/saat/gün önce' (yerel)."""
    try:
        t = datetime.fromisoformat(iso_ts).astimezone(LOCAL_TZ)
    except Exception:
        return ""
    now = datetime.now(LOCAL_TZ)
    sec = (now - t).total_seconds()
    if sec < 60: return "az önce"
    if sec < 3600: return f"{int(sec // 60)} dk önce"
    if sec < 86400: return f"{int(sec // 3600)} saat önce"
    return f"{int(sec // 86400)} gün önce"


def _machine_points(conn, uid, week_iso=None):
    """Makine gorevlerinden kazanilan toplam ve haftalik puani dondur."""
    rows = conn.execute(
        "SELECT points, completed_at FROM machine_completions WHERE user_id=?",
        (uid,)).fetchall()
    total = 0
    weekly = 0
    timestamps = []
    for r in rows:
        total += r["points"]
        timestamps.append(r["completed_at"])
        if week_iso and r["completed_at"] >= week_iso:
            weekly += r["points"]
    return total, weekly, timestamps


def user_stats(conn, uid):
    """Kullanıcının tüm oyunlaştırma istatistikleri (rütbe, rozet, seri için)."""
    from collections import defaultdict
    rows = conn.execute(
        """SELECT t.points AS pts, l.id AS lab_id, l.difficulty AS diff,
                  l.category AS cat, l.name AS lab_name, c.completed_at AS ca
           FROM completions c
           JOIN tasks t ON t.id = c.task_id
           JOIN labs l ON l.id = t.lab_id
           WHERE c.user_id = ?
           ORDER BY c.completed_at DESC""", (uid,)).fetchall()
    totals = lab_task_totals(conn)
    week = week_start_utc_iso()

    solved_by_lab = defaultdict(int)
    lab_meta = {}
    points_all = 0
    points_week = 0
    timestamps = []
    recent = []
    for r in rows:
        solved_by_lab[r["lab_id"]] += 1
        lab_meta[r["lab_id"]] = (r["diff"], r["cat"], r["lab_name"])
        points_all += r["pts"]
        if r["ca"] >= week:
            points_week += r["pts"]
        timestamps.append(r["ca"])
        if len(recent) < 6:
            recent.append({"lab": r["lab_name"], "pts": r["pts"], "when": _fmt_when(r["ca"])})

    # Makine gorevlerinden gelen puanlari ekle
    m_total, m_weekly, m_ts = _machine_points(conn, uid, week)
    points_all += m_total
    points_week += m_weekly
    timestamps.extend(m_ts)

    fully_diff = defaultdict(int)
    fully_cats = set()
    fully_count = 0
    for lab_id, cnt in solved_by_lab.items():
        tot = totals.get(lab_id, (0, 0))[0]
        if tot and cnt == tot:
            fully_count += 1
            d, c, _ = lab_meta[lab_id]
            fully_diff[d] += 1
            fully_cats.add(c)

    total_labs = conn.execute("SELECT COUNT(*) AS c FROM labs").fetchone()["c"]

    # Makine istatistikleri: tum gorevleri cozulmus makine sayisi
    msolved = {r["task_id"] for r in conn.execute(
        "SELECT task_id FROM machine_completions WHERE user_id=?", (uid,)).fetchall()}
    total_machines = len(machine_manager.MACHINE_CATALOG)
    solved_machines = 0
    for mid, minfo in machine_manager.MACHINE_CATALOG.items():
        mn = len(minfo["tasks"])
        if mn and all(f"machine_{mid}_{i}" in msolved for i in range(mn)):
            solved_machines += 1

    return {
        "points_all": points_all,
        "points_week": points_week,
        "solved_tasks": len(rows),
        "solved_labs": fully_count,
        "total_labs": total_labs,
        "solved_machines": solved_machines,
        "total_machines": total_machines,
        "fully_diff": dict(fully_diff),
        "fully_cats": fully_cats,
        "streak": compute_streak(timestamps),
        "recent": recent,
    }


# ------------------------------- Rotalar -------------------------------
@app.route("/")
def index():
    u = current_user()
    if not u:
        return render_template("index.html")
    # Giriş yapmış kullanıcıya kişiselleştirilmiş anasayfa
    conn = get_db()
    stats = user_stats(conn, session["user_id"])
    wk = week_start_utc_iso()
    rank_rows = conn.execute(
        """SELECT uid, SUM(pts) AS pts FROM (
               SELECT u.id AS uid, t.points AS pts FROM completions c
               JOIN tasks t ON t.id=c.task_id JOIN users u ON u.id=c.user_id
               WHERE c.completed_at >= ?
               UNION ALL
               SELECT mc.user_id AS uid, mc.points AS pts FROM machine_completions mc
               WHERE mc.completed_at >= ?
           ) GROUP BY uid ORDER BY pts DESC""", (wk, wk)).fetchall()
    week_rank = next((i + 1 for i, r in enumerate(rank_rows) if r["uid"] == session["user_id"]), None)
    rec = recommended_lab(conn, session["user_id"])
    conn.close()
    rank = rank_for(stats["points_all"])
    earned, locked = compute_badges(stats)

    # Motivasyon mesajları
    motives = []
    if stats["streak"] >= 3:
        motives.append(f"{stats['streak']} günlük serin var, bırakma!")
    if stats["solved_labs"] == 0:
        motives.append("İlk lab'ını çözmeye ne dersin? Hadi başla!")
    elif stats["solved_labs"] < 5:
        motives.append("Güzel gidiyorsun, devam et!")
    elif stats["solved_labs"] >= 10:
        motives.append("Gerçek bir avcısın! Zor lab'lara göz at.")
    import random
    motivation = random.choice(motives) if motives else None

    return render_template("home.html", stats=stats, rank=rank, earned=earned,
                           locked=locked, week_rank=week_rank, rec=rec,
                           motivation=motivation)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("panel"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        errors = []
        if len(username) < 3:
            errors.append("Kullanıcı adı en az 3 karakter olmalı.")
        if "@" not in email or "." not in email:
            errors.append("Geçerli bir e-posta adresi gir.")
        if len(password) < 6:
            errors.append("Parola en az 6 karakter olmalı.")
        if password != password2:
            errors.append("Parolalar eşleşmiyor.")

        conn = get_db()
        if not errors:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if exists:
                errors.append("Bu kullanıcı adı veya e-posta zaten kayıtlı.")

        if errors:
            for e in errors:
                flash(e, "error")
            conn.close()
            return render_template("register.html", username=username, email=email)

        conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, email, generate_password_hash(password), now_iso()),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        session["user_id"] = user["id"]
        flash(f"Hoş geldin, {username}! Hesabın oluşturuldu.", "success")
        return redirect(url_for("panel"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("panel"))
    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identifier, identifier.lower()),
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Tekrar hoş geldin, {user['username']}!", "success")
            nxt = request.args.get("next") or url_for("panel")
            return redirect(nxt)
        flash("Kullanıcı adı/e-posta veya parola hatalı.", "error")
        return render_template("login.html", identifier=identifier)
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    labs = conn.execute("SELECT * FROM labs ORDER BY id ASC").fetchall()
    totals = lab_task_totals(conn)
    solved_by_lab, points = user_progress(conn, session["user_id"])
    conn.close()

    diff = request.args.get("difficulty")
    cat = request.args.get("category")
    q = (request.args.get("q") or "").strip().lower()
    status = request.args.get("status")   # 'solved' / 'unsolved'

    categories = sorted({lab["category"] for lab in labs})
    labs_view = []
    solved_labs = 0
    for lab in labs:
        tcount, tpts = totals.get(lab["id"], (0, 0))
        scount = solved_by_lab.get(lab["id"], 0)
        fully = tcount > 0 and scount == tcount
        if fully:
            solved_labs += 1
        if diff and lab["difficulty"] != diff:
            continue
        if cat and lab["category"] != cat:
            continue
        if status == "solved" and not fully:
            continue
        if status == "unsolved" and fully:
            continue
        if q and q not in (lab["name"] + " " + lab["short_desc"] + " " +
                           lab["tags"] + " " + lab["category"]).lower():
            continue
        labs_view.append({
            "row": lab, "solved": scount, "total": tcount,
            "points": tpts, "fully": fully,
        })

    stats = {"points": points, "solved": solved_labs, "total": len(labs),
             "showing": len(labs_view)}
    return render_template("dashboard.html", labs=labs_view, stats=stats,
                           active_diff=diff, active_cat=cat, q=q,
                           active_status=status, categories=categories)


@app.route("/lab/<slug>", methods=["GET", "POST"])
@login_required
def lab_detail(slug):
    conn = get_db()
    lab = conn.execute("SELECT * FROM labs WHERE slug = ?", (slug,)).fetchone()
    if not lab:
        conn.close()
        abort(404)
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE lab_id = ? ORDER BY ordinal", (lab["id"],)
    ).fetchall()

    if request.method == "POST":
        task_id = request.form.get("task_id")
        answer = request.form.get("answer") or ""
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND lab_id = ?", (task_id, lab["id"])
        ).fetchone()
        if task and norm(answer) == norm(task["answer"]):
            already = conn.execute(
                "SELECT 1 FROM completions WHERE user_id=? AND task_id=?",
                (session["user_id"], task["id"]),
            ).fetchone()
            if already:
                flash("Bu görevi zaten çözmüştün. ✓", "success")
            else:
                conn.execute(
                    "INSERT INTO completions (user_id, task_id, completed_at) VALUES (?,?,?)",
                    (session["user_id"], task["id"], now_iso()),
                )
                conn.commit()
                flash(f"Doğru cevap! +{task['points']} puan 🎉", "success")
                # Lab'ın tüm görevleri artık çözüldü mü? → kutlama sinyali
                task_ids = [t["id"] for t in tasks]
                done = {
                    r["task_id"] for r in conn.execute(
                        "SELECT task_id FROM completions WHERE user_id=?",
                        (session["user_id"],)
                    ).fetchall()
                }
                if task_ids and all(tid in done for tid in task_ids):
                    session["celebrate"] = slug
        else:
            flash("Yanlış cevap. Tekrar dene.", "error")
        conn.close()
        return redirect(url_for("lab_detail", slug=slug) + "#gorevler")

    solved = {
        r["task_id"] for r in conn.execute(
            "SELECT task_id FROM completions WHERE user_id=?", (session["user_id"],)
        ).fetchall()
    }
    conn.close()
    files = [f for f in lab["files"].split(",") if f]
    total_pts = sum(t["points"] for t in tasks)
    done_pts = sum(t["points"] for t in tasks if t["id"] in solved)
    fully = bool(tasks) and all(t["id"] in solved for t in tasks)
    just_completed = session.pop("celebrate", None) == slug
    return render_template("lab.html", lab=lab, tasks=tasks, solved=solved,
                           files=files, total_pts=total_pts, done_pts=done_pts,
                           fully=fully, just_completed=just_completed)


@app.route("/lab/<slug>/reset", methods=["POST"])
@login_required
def lab_reset(slug):
    conn = get_db()
    lab = conn.execute("SELECT id FROM labs WHERE slug = ?", (slug,)).fetchone()
    if not lab:
        conn.close()
        abort(404)
    conn.execute(
        """DELETE FROM completions
           WHERE user_id = ? AND task_id IN (SELECT id FROM tasks WHERE lab_id = ?)""",
        (session["user_id"], lab["id"]),
    )
    conn.commit()
    conn.close()
    flash("Lab sıfırlandı. Baştan çözebilirsin.", "success")
    return redirect(url_for("lab_detail", slug=slug))


@app.route("/download/<slug>/<path:filename>")
@login_required
def download(slug, filename):
    conn = get_db()
    lab = conn.execute("SELECT files FROM labs WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    if not lab:
        abort(404)
    allowed = [f for f in lab["files"].split(",") if f]
    if filename not in allowed:
        abort(404)
    return send_from_directory(LABFILES_DIR, filename, as_attachment=True)


def recommended_lab(conn, uid):
    """Henüz tam çözülmemiş en kolay lab'ı öner."""
    totals = lab_task_totals(conn)
    solved = {}
    for r in conn.execute(
        "SELECT t.lab_id AS lab_id FROM completions c JOIN tasks t ON t.id=c.task_id WHERE c.user_id=?",
        (uid,)):
        solved[r["lab_id"]] = solved.get(r["lab_id"], 0) + 1
    order = {"Kolay": 0, "Orta": 1, "Zor": 2}
    cand = []
    for l in conn.execute("SELECT * FROM labs").fetchall():
        tot = totals.get(l["id"], (0, 0))[0]
        if not (tot and solved.get(l["id"], 0) == tot):
            cand.append(l)
    cand.sort(key=lambda l: (order.get(l["difficulty"], 9), l["id"]))
    return cand[0] if cand else None


@app.route("/panel", methods=["GET", "POST"])
@login_required
def panel():
    if request.method == "POST":
        _handle_avatar_upload()
        return redirect(url_for("panel"))
    conn = get_db()
    stats = user_stats(conn, session["user_id"])
    diff_tot = {r["difficulty"]: r["c"] for r in conn.execute(
        "SELECT difficulty, COUNT(*) c FROM labs GROUP BY difficulty").fetchall()}
    wk = week_start_utc_iso()
    rank_rows = conn.execute(
        """SELECT uid, SUM(pts) AS pts FROM (
               SELECT u.id AS uid, t.points AS pts FROM completions c
               JOIN tasks t ON t.id=c.task_id JOIN users u ON u.id=c.user_id
               WHERE c.completed_at >= ?
               UNION ALL
               SELECT mc.user_id AS uid, mc.points AS pts FROM machine_completions mc
               WHERE mc.completed_at >= ?
           ) GROUP BY uid ORDER BY pts DESC""", (wk, wk)).fetchall()
    week_rank = next((i + 1 for i, r in enumerate(rank_rows) if r["uid"] == session["user_id"]), None)
    rec = recommended_lab(conn, session["user_id"])
    conn.close()

    rank = rank_for(stats["points_all"])
    earned, locked = compute_badges(stats)
    diff_prog = {d: {"done": stats["fully_diff"].get(d, 0), "total": diff_tot.get(d, 0)}
                 for d in ["Kolay", "Orta", "Zor"]}
    return render_template("panel.html", stats=stats, rank=rank, earned=earned,
                           locked=locked, diff_prog=diff_prog, week_rank=week_rank, rec=rec)


@app.route("/ogren")
def ogren():
    return render_template("ogren.html")


@app.route("/fiyatlandirma")
def fiyatlandirma():
    return render_template("fiyatlandirma.html")


def _handle_avatar_upload():
    """Orijinal resmi al, tarayıcıdan gelen kırpma koordinatlarına göre
    sunucu tarafında PIL ile kes → 256px kare PNG olarak kaydet."""
    file = request.files.get("avatar")
    if not file or not file.filename:
        flash("Lütfen bir resim dosyası seç.", "error")
        return
    try:
        img = Image.open(file.stream)
        img = ImageOps.exif_transpose(img)   # telefon fotoğraflarının yönünü düzelt
        img = img.convert("RGB")
    except Exception:
        flash("Geçerli bir resim dosyası değil (PNG/JPG yükle).", "error")
        return

    w, h = img.size
    # Tarayıcıdan gelen kırpma karesi (doğal piksel koordinatları)
    try:
        s = int(float(request.form["s"]))
        sx = int(float(request.form["sx"]))
        sy = int(float(request.form["sy"]))
        s = max(1, min(s, w, h))
        sx = max(0, min(sx, w - s))
        sy = max(0, min(sy, h - s))
    except (KeyError, ValueError, TypeError):
        # Koordinat yoksa: ortadan kare kırp (yedek)
        s = min(w, h)
        sx = (w - s) // 2
        sy = (h - s) // 2

    img = img.crop((sx, sy, sx + s, sy + s)).resize((256, 256))
    fname = f"user_{session['user_id']}.png"
    img.save(os.path.join(AVATAR_DIR, fname), "PNG")
    rel = f"avatars/{fname}"
    conn = get_db()
    conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (rel, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Profil resmin güncellendi.", "success")


@app.route("/siralama")
@login_required
def siralama():
    period = request.args.get("period", "week")   # week | all
    conn = get_db()
    if period == "all":
        rows = conn.execute(
            """SELECT uid, username, avatar, SUM(pts) AS pts, SUM(solved) AS solved FROM (
                   SELECT u.id AS uid, u.username AS username, u.avatar AS avatar,
                          t.points AS pts, 1 AS solved
                   FROM completions c
                   JOIN tasks t ON t.id = c.task_id
                   JOIN users u ON u.id = c.user_id
                   UNION ALL
                   SELECT u.id AS uid, u.username AS username, u.avatar AS avatar,
                          mc.points AS pts, 1 AS solved
                   FROM machine_completions mc
                   JOIN users u ON u.id = mc.user_id
               ) GROUP BY uid
               ORDER BY pts DESC, solved DESC, username ASC
               LIMIT 100""").fetchall()
    else:
        wk = week_start_utc_iso()
        rows = conn.execute(
            """SELECT uid, username, avatar, SUM(pts) AS pts, SUM(solved) AS solved FROM (
                   SELECT u.id AS uid, u.username AS username, u.avatar AS avatar,
                          t.points AS pts, 1 AS solved
                   FROM completions c
                   JOIN tasks t ON t.id = c.task_id
                   JOIN users u ON u.id = c.user_id
                   WHERE c.completed_at >= ?
                   UNION ALL
                   SELECT u.id AS uid, u.username AS username, u.avatar AS avatar,
                          mc.points AS pts, 1 AS solved
                   FROM machine_completions mc
                   JOIN users u ON u.id = mc.user_id
                   WHERE mc.completed_at >= ?
               ) GROUP BY uid
               ORDER BY pts DESC, solved DESC, username ASC
               LIMIT 100""", (wk, wk)).fetchall()
    conn.close()
    board = []
    for i, r in enumerate(rows):
        d = dict(r, rank=i + 1)
        d["rankinfo"] = rank_for(r["pts"])   # tüm-zamanlar rütbesi bilgisi
        board.append(d)
    return render_template("siralama.html", board=board,
                           me=session["user_id"], period=period)


@app.route("/hakkinda")
def hakkinda():
    return render_template("hakkinda.html")


@app.route("/iletisim")
def iletisim():
    return render_template("iletisim.html")


@app.route("/ayarlar", methods=["GET", "POST"])
@login_required
def ayarlar():
    conn = get_db()
    user_row = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new = request.form.get("new_password") or ""
        new2 = request.form.get("new_password2") or ""
        if not check_password_hash(user_row["password_hash"], current):
            flash("Mevcut parola hatalı.", "error")
        elif len(new) < 6:
            flash("Yeni parola en az 6 karakter olmalı.", "error")
        elif new != new2:
            flash("Yeni parolalar eşleşmiyor.", "error")
        else:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new), session["user_id"]),
            )
            conn.commit()
            flash("Parolan güncellendi.", "success")
        conn.close()
        return redirect(url_for("ayarlar"))
    conn.close()
    return render_template("ayarlar.html", account=user_row)


# ----------------------------- Makine Rotaları -----------------------------
@app.route("/machines")
@login_required
def machines_list():
    machines = machine_manager.list_machines()
    conn = get_db()
    solved = {r["task_id"] for r in conn.execute(
        "SELECT task_id FROM machine_completions WHERE user_id=?",
        (session["user_id"],)).fetchall()}
    conn.close()
    for m in machines:
        info = machine_manager.get_machine_info(m["id"])
        n = len(info["tasks"]) if info else 0
        done = sum(1 for i in range(n) if f"machine_{m['id']}_{i}" in solved)
        m["done"] = done
        m["total"] = n
        m["fully"] = n > 0 and done == n
    return render_template("machines.html", machines=machines)


@app.route("/machine/<machine_id>")
@login_required
def machine_detail(machine_id):
    info = machine_manager.get_machine_info(machine_id)
    if not info:
        abort(404)
    running = machine_manager.is_running(machine_id)
    port = machine_manager.get_port(machine_id)
    # Bu makinenin gorevlerini ve cozum durumunu al
    tasks = info["tasks"]
    conn = get_db()
    solved_set = set()
    for r in conn.execute(
        "SELECT task_id FROM machine_completions WHERE user_id=?", (session["user_id"],)
    ).fetchall():
        solved_set.add(r["task_id"])
    task_views = []
    done_pts = 0
    total_pts = 0
    for i, t in enumerate(tasks):
        tid = f"machine_{machine_id}_{i}"
        done = tid in solved_set
        if done:
            done_pts += t["points"]
        total_pts += t["points"]
        task_views.append({
            "id": tid, "question": t["question"],
            "hint": t["hint"], "points": t["points"], "done": done,
        })
    conn.close()
    fully = len(task_views) > 0 and all(t["done"] for t in task_views)
    just_completed = session.pop("machine_celebrate", None) == machine_id
    return render_template("machine.html", info=info, machine_id=machine_id,
                           running=running, port=port, tasks=task_views,
                           done_pts=done_pts, total_pts=total_pts, fully=fully,
                           just_completed=just_completed)


@app.route("/machine/<machine_id>/start", methods=["POST"])
@login_required
def machine_start(machine_id):
    result = machine_manager.start_machine(machine_id, session["user_id"])
    if result["status"] in ("started", "already_running"):
        flash(f"Makine calisiyor! Port: {result['port']}", "success")
    else:
        flash(f"Makine baslatilamadi: {result.get('message', 'Bilinmeyen hata')}", "error")
    return redirect(url_for("machine_detail", machine_id=machine_id))


@app.route("/machine/<machine_id>/stop", methods=["POST"])
@login_required
def machine_stop(machine_id):
    machine_manager.stop_machine(machine_id)
    flash("Makine durduruldu.", "success")
    return redirect(url_for("machine_detail", machine_id=machine_id))


@app.route("/machine/<machine_id>/submit", methods=["POST"])
@login_required
def machine_submit(machine_id):
    info = machine_manager.get_machine_info(machine_id)
    if not info:
        abort(404)
    task_idx = request.form.get("task_idx")
    answer = (request.form.get("answer") or "").strip()
    try:
        idx = int(task_idx)
        task = info["tasks"][idx]
    except (ValueError, IndexError):
        flash("Gecersiz gorev.", "error")
        return redirect(url_for("machine_detail", machine_id=machine_id))

    tid = f"machine_{machine_id}_{idx}"
    if norm(answer) == norm(task["answer"]):
        conn = get_db()
        already = conn.execute(
            "SELECT 1 FROM machine_completions WHERE user_id=? AND task_id=?",
            (session["user_id"], tid)).fetchone()
        if not already:
            conn.execute(
                "INSERT INTO machine_completions (user_id, task_id, points, completed_at) VALUES (?,?,?,?)",
                (session["user_id"], tid, task["points"], now_iso()))
            conn.commit()
            flash(f"Dogru cevap! +{task['points']} puan 🎉", "success")
            # Makinenin tüm görevleri çözüldü mü? → kutlama + otomatik kapatma
            all_tids = {f"machine_{machine_id}_{i}" for i in range(len(info["tasks"]))}
            done = {
                r["task_id"] for r in conn.execute(
                    "SELECT task_id FROM machine_completions WHERE user_id=?",
                    (session["user_id"],)).fetchall()
            }
            if all_tids and all(t in done for t in all_tids):
                session["machine_celebrate"] = machine_id
                # Makineyi otomatik durdur (görevler bitti, artık gerek yok)
                machine_manager.stop_machine(machine_id)
        else:
            flash("Bu gorevi zaten cozmustun.", "success")
        conn.close()
    else:
        flash("Yanlis cevap. Tekrar dene.", "error")
    return redirect(url_for("machine_detail", machine_id=machine_id) + "#gorevler")


@app.route("/machine/<machine_id>/reset", methods=["POST"])
@login_required
def machine_reset(machine_id):
    info = machine_manager.get_machine_info(machine_id)
    if not info:
        abort(404)
    all_tids = [f"machine_{machine_id}_{i}" for i in range(len(info["tasks"]))]
    conn = get_db()
    conn.executemany(
        "DELETE FROM machine_completions WHERE user_id=? AND task_id=?",
        [(session["user_id"], tid) for tid in all_tids])
    conn.commit()
    conn.close()
    flash("Makine sıfırlandı. Baştan çözebilirsin.", "success")
    return redirect(url_for("machine_detail", machine_id=machine_id))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    # host=0.0.0.0 → yerel ağdaki diğer cihazlardan erişilebilir
    # use_reloader=False: makine başlatınca oluşan dosyalar (hackme.db, docs,
    # secret) reloader'ı tetikleyip ana uygulamayı yeniden başlatıyordu; bu da
    # başlatılan zafiyetli makine prosesini öldürüyordu. Reloader kapalı.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
