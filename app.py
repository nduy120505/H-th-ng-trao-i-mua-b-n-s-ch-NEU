"""
app.py
======
Flask application – chỉ chứa routes, helpers và context processors.
Database: database.py  |  Templates: templates/  |  CSS/JS: static/
─────────────────────────────────────────────────────────────────────
Chạy : python3 app.py
URL  : http://localhost:5000
─────────────────────────────────────────────────────────────────────
Tài khoản mặc định:
  admin  / admin123
  sv001  / 123456
  sv002  / 123456
  sv003  / 123456
"""

import os
import secrets
import sqlite3
import smtplib
import ssl
import string
from functools import wraps
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, init_db, ensure_db_schema, DATABASE

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME or "no-reply@neu-bookstore.local").strip()
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() not in ("0", "false", "no")

PRIMARY_FACULTIES = [
    "Khoa Bảo hiểm",
    "Khoa Bất động sản và Kinh tế tài nguyên",
    "Khoa Công nghệ thông tin",
    "Khoa Đầu tư",
    "Khoa Du lịch và Khách sạn",
    "Khoa Hệ thống thông tin quản lý",
    "Khoa Kế hoạch và Phát triển",
    "Khoa Khoa học Cơ sở",
    "Khoa Khoa học dữ liệu và Trí tuệ nhân tạo",
    "Khoa Khoa học quản lý",
    "Khoa Kinh tế học",
    "Khoa Kinh tế và Quản lý nguồn nhân lực",
    "Khoa Luật",
    "Khoa Lý luận chính trị",
    "Khoa Marketing",
    "Khoa Môi trường, Biến đổi khí hậu và Đô thị",
    "Khoa Ngoại ngữ Kinh tế",
    "Khoa Quản trị kinh doanh",
    "Khoa Thống kê",
    "Khoa Toán kinh tế",
    "Viện Đào tạo Quốc tế",
    "Viện Đào tạo Tiên tiến, Chất lượng cao và POHE",
    "Viện Kế toán - Kiểm toán",
    "Viện Ngân hàng - Tài chính",
    "Viện Quản trị Kinh doanh",
    "Viện Thương mại và Kinh tế quốc tế",
]

LEGACY_FACULTIES = [
    "Khoa Kinh Tế",
    "Khoa Quản Trị Kinh Doanh",
    "Khoa Tài Chính – Ngân Hàng",
    "Khoa Kế Toán – Kiểm Toán",
    "Khoa Hệ Thống Thông Tin",
    "Khoa Luật Kinh Tế",
    "Khoa Bất Động Sản",
]

FACULTIES = PRIMARY_FACULTIES + [
    faculty for faculty in LEGACY_FACULTIES if faculty not in PRIMARY_FACULTIES
]

CONDITION_LABELS = {
    "new":      ("Mới 100%",    "badge-new"),
    "like_new": ("Như mới",     "badge-like-new"),
    "good":     ("Còn tốt",     "badge-good"),
    "fair":     ("Bình thường", "badge-fair"),
    "poor":     ("Cũ nhiều",    "badge-poor"),
}

TYPE_LABELS = {
    "sell":     ("Bán",      ""),
    "exchange": ("Trao đổi", ""),
    "free":     ("Miễn phí", ""),
}

REPORT_REASONS = [
    "Nghi ngờ lừa đảo",
    "Không giao sách sau khi nhận tiền",
    "Thông tin sách sai sự thật",
    "Spam / quấy rối",
    "Khác",
]

LISTING_STATUS_META = {
    "pending": ("Chờ duyệt", "badge-warning"),
    "active": ("Đang hiển thị", "badge-green"),
    "rejected": ("Bị từ chối", "badge-red-soft"),
    "sold": ("Đã bán", "badge-gray"),
    "reserved": ("Đặt cọc", "badge-blue"),
    "closed": ("Đã đóng", "badge-gray"),
}


VALID_BOOK_YEARS = ("1", "2", "3", "4")

MOJIBAKE_TOKENS = ("Ã", "Â", "Ä", "Å", "Æ", "áº", "á»", "â€", "đŸ")
VIETNAMESE_CHARS = set(
    "aăâbcdđeêghiklmnoôơpqrstuưvxy"
    "áàảãạắằẳẵặấầẩẫậ"
    "éèẻẽẹếềểễệ"
    "íìỉĩị"
    "óòỏõọốồổỗộớờởỡợ"
    "úùủũụứừửữự"
    "ýỳỷỹỵ"
)


def _text_quality_score(value: str) -> int:
    bad_score = sum(value.count(token) for token in MOJIBAKE_TOKENS) * 10
    good_score = sum(ch.lower() in VIETNAMESE_CHARS for ch in value)
    return good_score - bad_score


def repair_text(value):
    if not isinstance(value, str) or not value:
        return value

    candidates = [value]
    if any(token in value for token in MOJIBAKE_TOKENS):
        for encoding in ("cp1252", "latin1"):
            try:
                repaired = value.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            candidates.append(repaired)

    return max(candidates, key=_text_quality_score)


app.jinja_env.finalize = repair_text


def can_view_listing(listing, user_id, role):
    if not listing:
        return False
    return listing["status"] == "active" or listing["seller_id"] == user_id or role == "admin"


def can_manage_listing(listing, user_id, role):
    return bool(listing) and (listing["seller_id"] == user_id or role == "admin")


def format_local_timestamp(value, fmt="%H:%M"):
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S") + timedelta(hours=7)
        return dt.strftime(fmt)
    except ValueError:
        return value


def generate_temporary_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_new_password_email(user, new_password):
    subject = "Mat khau moi cho tai khoan NEU Bookstore"
    body = (
        f"Xin chao {user['full_name'] or user['username']},\n\n"
        "He thong da tao mat khau moi cho tai khoan NEU Bookstore cua ban.\n\n"
        f"Ten dang nhap: {user['username']}\n"
        f"Mat khau moi: {new_password}\n\n"
        "Vui long dang nhap va doi lai mat khau trong trang Ho so cua toi.\n"
        "Neu ban khong yeu cau thao tac nay, hay dang nhap va doi mat khau ngay."
    )

    if not SMTP_HOST:
        app.logger.warning(
            "SMTP_HOST is not configured. New password for %s: %s",
            user["email"],
            new_password,
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = user["email"]
    message.set_content(body)

    if SMTP_USE_TLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if SMTP_USERNAME:
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context()) as smtp:
            if SMTP_USERNAME:
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
    return True


def normalize_book_years(values):
    normalized = []
    seen = set()
    for value in values or []:
        year = str(value).strip()
        if year in VALID_BOOK_YEARS and year not in seen:
            normalized.append(year)
            seen.add(year)
    return normalized


def parse_book_years(value):
    if value is None:
        return []
    if isinstance(value, int):
        return normalize_book_years([value])
    return normalize_book_years(str(value).replace(";", ",").split(","))


def serialize_book_years(values):
    normalized = normalize_book_years(values)
    return ",".join(normalized) if normalized else None


def format_book_years(value):
    years = parse_book_years(value)
    if not years:
        return ""
    return ", ".join(f"Năm {year}" for year in years)


def serialize_message(row, current_user_id):
    return {
        "id": row["id"],
        "content": row["content"],
        "created_at": row["created_at"],
        "time": format_local_timestamp(row["created_at"]),
        "sender_id": row["sender_id"],
        "sender_name": row["sender_name"] or row["sender_username"],
        "is_me": row["sender_id"] == current_user_id,
    }


def recalculate_user_rating(conn, user_id):
    summary = conn.execute(
        """
        SELECT COALESCE(AVG(rating), 0) avg_rating, COUNT(*) total_reviews
        FROM reviews
        WHERE reviewed_id=?
        """,
        (user_id,),
    ).fetchone()
    conn.execute(
        "UPDATE users SET rating_avg=?, rating_count=? WHERE id=?",
        (summary["avg_rating"], summary["total_reviews"], user_id),
    )


def get_reputation_summary(conn, user_id):
    summary = conn.execute(
        """
        SELECT
            COALESCE(AVG(r.rating), 0) AS rating_avg,
            COUNT(r.id) AS rating_count,
            COUNT(DISTINCT CASE WHEN l.status='active' THEN l.id END) AS active_listings,
            COUNT(DISTINCT CASE WHEN l.status IN ('sold', 'reserved', 'closed') THEN l.id END) AS completed_listings,
            COUNT(DISTINCT CASE WHEN ur.status='pending' THEN ur.id END) AS pending_reports,
            COUNT(DISTINCT CASE WHEN ur.status='reviewed' THEN ur.id END) AS reviewed_reports
        FROM users u
        LEFT JOIN reviews r ON r.reviewed_id=u.id
        LEFT JOIN listings l ON l.seller_id=u.id
        LEFT JOIN user_reports ur ON ur.reported_user_id=u.id
        WHERE u.id=?
        GROUP BY u.id
        """,
        (user_id,),
    ).fetchone()
    return summary


def create_alerts_for_listing(conn, listing_id):
    listing = conn.execute(
        """
        SELECT l.id, b.title, b.author, b.subject_code, l.notes
        FROM listings l
        JOIN books b ON b.id=l.book_id
        WHERE l.id=? AND l.status='active'
        """,
        (listing_id,),
    ).fetchone()
    if not listing:
        return 0

    searchable_text = " ".join(
        str(listing[key] or "").lower()
        for key in ("title", "author", "subject_code", "notes")
    )
    if not searchable_text.strip():
        return 0

    watches = conn.execute(
        "SELECT id, user_id, query FROM wanted_books ORDER BY created_at DESC"
    ).fetchall()
    created = 0
    for watch in watches:
        query = (watch["query"] or "").strip().lower()
        if not query or query not in searchable_text:
            continue
        inserted = conn.execute(
            """
            INSERT OR IGNORE INTO alert_notifications(user_id, wanted_book_id, listing_id)
            VALUES (?, ?, ?)
            """,
            (watch["user_id"], watch["id"], listing_id),
        ).rowcount
        created += inserted
    return created


def bootstrap_database():
    if not os.path.exists(DATABASE):
        init_db()
    else:
        ensure_db_schema()


bootstrap_database()

# ─────────────────────────────────────────────────────────────────────────────
# Decorators & helpers
# ─────────────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập để tiếp tục.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Không có quyền truy cập.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_globals():
    conn = get_db_connection()
    root_cats = conn.execute(
        "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order"
    ).fetchall()
    unread = 0
    alert_count = 0
    if "user_id" in session:
        row = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE receiver_id=? AND is_read=0",
            (session["user_id"],),
        ).fetchone()
        unread = row["c"] if row else 0
        alert_row = conn.execute(
            "SELECT COUNT(*) c FROM alert_notifications WHERE user_id=? AND is_seen=0",
            (session["user_id"],),
        ).fetchone()
        alert_count = alert_row["c"] if alert_row else 0
    conn.close()
    return dict(
        current_user=get_current_user(),
        root_categories=root_cats,
        unread_count=unread,
        alert_count=alert_count,
        CONDITION_LABELS=CONDITION_LABELS,
        TYPE_LABELS=TYPE_LABELS,
        REPORT_REASONS=REPORT_REASONS,
        LISTING_STATUS_META=LISTING_STATUS_META,
        VALID_BOOK_YEARS=VALID_BOOK_YEARS,
        parse_book_years=parse_book_years,
        format_book_years=format_book_years,
        format_local_timestamp=format_local_timestamp,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Auth routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            error = "username"
        elif not password:
            error = "password"
        else:
            conn = get_db_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()
            conn.close()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"]  = user["id"]
                session["username"] = user["username"]
                session["role"]     = user["role"]
                flash(f'Chào mừng, {user["full_name"] or user["username"]}!', "success")
                return redirect(url_for("home"))
            error = "invalid"

    return render_template("login.html", error=error)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("home"))

    error = None
    email = request.form.get("email", "").strip().lower()

    if request.method == "POST":
        if not email:
            error = "email"
        else:
            conn = get_db_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE lower(email)=?",
                (email,),
            ).fetchone()

            if user:
                new_password = generate_temporary_password()
                conn.execute(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    (generate_password_hash(new_password), user["id"]),
                )

                try:
                    email_sent = send_new_password_email(user, new_password)
                    conn.commit()
                    if email_sent:
                        flash("Mat khau moi da duoc gui ve email dang ky cua ban.", "success")
                    else:
                        flash(
                            "Mat khau moi da duoc tao. Chua cau hinh SMTP nen hay xem console server.",
                            "warning",
                        )
                    conn.close()
                    return redirect(url_for("login"))
                except Exception:
                    conn.rollback()
                    app.logger.exception("Could not send password reset email")
                    conn.close()
                    error = "send_failed"
            else:
                conn.close()
                error = "not_found"

    return render_template("forgot_password.html", error=error, email=email)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    errors, form = {}, {}
    if request.method == "POST":
        form = {k: v.strip() for k, v in request.form.items()}
        u  = form.get("username", "")
        p  = form.get("password", "")
        rp = form.get("repassword", "")

        if not u or len(u) < 4:
            errors["username"] = "Tên đăng nhập ít nhất 4 ký tự"
        if not p or len(p) < 6:
            errors["password"] = "Mật khẩu ít nhất 6 ký tự"
        if p != rp:
            errors["repassword"] = "Mật khẩu không khớp"
        if not form.get("full_name"):
            errors["full_name"] = "Họ tên không được trống"
        if not form.get("email"):
            errors["email"] = "Email không được trống"

        if not errors:
            conn = get_db_connection()
            if conn.execute("SELECT id FROM users WHERE username=?", (u,)).fetchone():
                errors["username"] = "Tên đăng nhập đã tồn tại"
            else:
                cy = form.get("course_year", "")
                conn.execute(
                    "INSERT INTO users "
                    "(username,password_hash,full_name,email,phone,student_id,faculty,course_year) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        u,
                        generate_password_hash(p),
                        form.get("full_name"),
                        form.get("email"),
                        form.get("phone") or None,
                        form.get("student_id") or None,
                        form.get("faculty") or None,
                        int(cy) if cy.isdigit() else None,
                    ),
                )
                conn.commit()
                conn.close()
                flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
                return redirect(url_for("login"))
            conn.close()

    return render_template("register.html", errors=errors, form=form, FACULTIES=FACULTIES)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────────
# Home
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/home")
@login_required
def home():
    conn = get_db_connection()
    recent = conn.execute("""
        SELECT l.*, b.title, b.author, b.cover_emoji, b.cover_image, b.subject_code,
               u.full_name seller_name, u.username seller_username, u.rating_avg,
               c.name cat_name
        FROM listings l
        JOIN books    b ON b.id = l.book_id
        JOIN users    u ON u.id = l.seller_id
        LEFT JOIN categories c ON c.id = b.category_id
        WHERE l.status='active'
        ORDER BY l.created_at DESC
        LIMIT 12
    """).fetchall()

    popular = conn.execute("""
        SELECT l.*, b.title, b.author, b.cover_emoji, b.cover_image,
               u.full_name seller_name, u.username seller_username
        FROM listings l
        JOIN books b ON b.id = l.book_id
        JOIN users u ON u.id = l.seller_id
        WHERE l.status='active'
        ORDER BY l.views DESC
        LIMIT 6
    """).fetchall()

    stats = conn.execute("""
        SELECT
          (SELECT COUNT(*) FROM listings WHERE status='active') total_listings,
          (SELECT COUNT(*) FROM users    WHERE role='student')  total_users,
          (SELECT COUNT(*) FROM books)                          total_books,
          (SELECT COUNT(*) FROM listings
           WHERE listing_type='free' AND status='active')       free_books
    """).fetchone()

    wl = conn.execute(
        "SELECT listing_id FROM wishlist WHERE user_id=?", (session["user_id"],)
    ).fetchall()
    wishlist_ids = {r["listing_id"] for r in wl}
    conn.close()

    return render_template(
        "home.html",
        recent=recent,
        popular=popular,
        stats=stats,
        wishlist_ids=wishlist_ids,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Listings (browse + filter)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/listings")
@login_required
def listings():
    conn = get_db_connection()

    q           = request.args.get("q", "").strip()
    cat_id      = request.args.get("cat", "")
    ltype       = request.args.get("type", "")
    condition   = request.args.get("condition", "")
    course_years = normalize_book_years(request.args.getlist("year"))
    sort        = request.args.get("sort", "newest")
    page        = max(1, int(request.args.get("page", 1)))
    per_page    = 12

    where  = ["l.status='active'"]
    params = []

    if q:
        where.append("(b.title LIKE ? OR b.author LIKE ? OR b.subject_code LIKE ?)")
        params += [f"%{q}%"] * 3
    if cat_id:
        where.append("(b.category_id=? OR c.parent_id=?)")
        params += [cat_id, cat_id]
    if ltype:
        where.append("l.listing_type=?");   params.append(ltype)
    if condition:
        where.append("l.condition=?");      params.append(condition)
    if course_years:
        where.append(
            "(" + " OR ".join(
                ["instr(',' || ifnull(b.course_year, '') || ',', ?) > 0"] * len(course_years)
            ) + ")"
        )
        params += [f",{year}," for year in course_years]

    where_sql = "WHERE " + " AND ".join(where)
    order_map = {
        "newest":     "l.created_at DESC",
        "oldest":     "l.created_at ASC",
        "price_asc":  "l.price ASC",
        "price_desc": "l.price DESC",
        "popular":    "l.views DESC",
    }
    order_sql = order_map.get(sort, "l.created_at DESC")

    total = conn.execute(
        f"SELECT COUNT(*) c FROM listings l "
        f"JOIN books b ON b.id=l.book_id "
        f"LEFT JOIN categories c ON c.id=b.category_id "
        f"{where_sql}",
        params,
    ).fetchone()["c"]

    rows = conn.execute(
        f"""
        SELECT l.*, b.title, b.author, b.cover_emoji, b.cover_image, b.subject_code,
               b.faculty book_faculty, b.course_year book_year,
               u.full_name seller_name, u.username seller_username, u.rating_avg,
               c.name cat_name, c.icon cat_icon
        FROM listings l
        JOIN books    b ON b.id = l.book_id
        JOIN users    u ON u.id = l.seller_id
        LEFT JOIN categories c ON c.id = b.category_id
        {where_sql}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
        """,
        params + [per_page, (page - 1) * per_page],
    ).fetchall()

    all_cats = conn.execute(
        "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order"
    ).fetchall()
    wl = conn.execute(
        "SELECT listing_id FROM wishlist WHERE user_id=?", (session["user_id"],)
    ).fetchall()
    wishlist_ids = {r["listing_id"] for r in wl}
    conn.close()

    return render_template(
        "listings.html",
        listings=rows,
        total=total,
        page=page,
        pages=(total + per_page - 1) // per_page,
        all_cats=all_cats,
        wishlist_ids=wishlist_ids,
        q=q, cat_id=cat_id, ltype=ltype, condition=condition,
        course_years=course_years, sort=sort,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Listing detail
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/listing/<int:lid>")
@login_required
def listing_detail(lid):
    conn = get_db_connection()
    current_user_id = session["user_id"]
    listing = conn.execute("""
        SELECT l.*, b.title, b.author, b.isbn, b.publisher, b.publish_year,
               b.edition, b.description book_desc, b.cover_emoji, b.cover_image,
               b.subject_code, b.faculty book_faculty, b.course_year book_year,
               u.full_name seller_name, u.username seller_username,
               u.phone seller_phone, u.email seller_email,
               u.faculty seller_faculty, u.rating_avg, u.rating_count,
               c.name cat_name, c.icon cat_icon
        FROM listings l
        JOIN books    b ON b.id = l.book_id
        JOIN users    u ON u.id = l.seller_id
        LEFT JOIN categories c ON c.id = b.category_id
        WHERE l.id=?
    """, (lid,)).fetchone()

    if not listing:
        conn.close()
        flash("Tin đăng không tồn tại.", "danger")
        return redirect(url_for("listings"))

    if not can_view_listing(listing, current_user_id, session.get("role")):
        conn.close()
        flash("Tin đăng này đang chờ duyệt hoặc không còn hiển thị công khai.", "warning")
        return redirect(url_for("profile"))

    if listing["status"] == "active":
        conn.execute("UPDATE listings SET views=views+1 WHERE id=?", (lid,))
        conn.commit()

    related = conn.execute("""
        SELECT l.*, b.title, b.cover_emoji, b.cover_image, u.full_name seller_name
        FROM listings l
        JOIN books b ON b.id = l.book_id
        JOIN users u ON u.id = l.seller_id
        WHERE l.status='active' AND l.id!=?
          AND b.category_id=(SELECT category_id FROM books WHERE id=?)
        LIMIT 4
    """, (lid, listing["book_id"])).fetchall()

    wl = conn.execute(
        "SELECT id FROM wishlist WHERE user_id=? AND listing_id=?",
        (current_user_id, lid),
    ).fetchone()
    seller_summary = get_reputation_summary(conn, listing["seller_id"])
    recent_reviews = conn.execute(
        """
        SELECT r.*, reviewer.full_name reviewer_name, reviewer.username reviewer_username
        FROM reviews r
        JOIN users reviewer ON reviewer.id=r.reviewer_id
        WHERE r.reviewed_id=?
        ORDER BY r.created_at DESC
        LIMIT 3
        """,
        (listing["seller_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "listing_detail.html",
        listing=listing,
        related=related,
        in_wishlist=bool(wl),
        seller_summary=seller_summary,
        recent_reviews=recent_reviews,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Post listing
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/post", methods=["GET", "POST"])
@login_required
def post_listing():
    conn = get_db_connection()
    books = conn.execute(
        "SELECT b.*, c.name cat_name FROM books b "
        "LEFT JOIN categories c ON c.id=b.category_id ORDER BY b.title"
    ).fetchall()
    categories = conn.execute(
        "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order"
    ).fetchall()
    errors = {}

    if request.method == "POST":
        book_id     = request.form.get("book_id", "").strip()
        is_new_book = book_id == "__new__"
        ltype       = request.form.get("listing_type", "").strip()
        price       = request.form.get("price", "0").strip()
        condition   = request.form.get("condition", "").strip()
        notes       = request.form.get("notes", "").strip()
        exchange_for= request.form.get("exchange_for", "").strip()
        cover_image = request.form.get("cover_image", "").strip()
        new_cover_image = request.form.get("new_cover_image", "").strip()
        new_title   = request.form.get("new_title", "").strip()
        new_author  = request.form.get("new_author", "").strip()
        new_cat_id  = request.form.get("new_cat_id", "").strip()
        new_subject = request.form.get("new_subject", "").strip()
        new_years   = request.form.getlist("new_year")

        if (not book_id or is_new_book) and not new_title:
            errors["book"] = "Chọn sách hoặc nhập tên sách mới"
        if not ltype:
            errors["listing_type"] = "Chọn loại tin"
        if not condition:
            errors["condition"] = "Chọn tình trạng sách"
        if ltype == "sell" and (not price or not price.replace(".", "").isdigit()):
            errors["price"] = "Nhập giá hợp lệ"

        if not errors:
            if is_new_book:
                book_id = ""

            if not book_id and new_title:
                cur = conn.execute(
                    "INSERT INTO books(title,author,category_id,subject_code,course_year,cover_image) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        new_title,
                        new_author or None,
                        int(new_cat_id) if new_cat_id.isdigit() else None,
                        new_subject or None,
                        serialize_book_years(new_years),
                        cover_image or new_cover_image or None,
                    ),
                )
                conn.commit()
                book_id = cur.lastrowid
            elif book_id and cover_image:
                conn.execute(
                    "UPDATE books SET cover_image=? WHERE id=?",
                    (cover_image, int(book_id)),
                )
                conn.commit()

            price_val = float(price) if ltype == "sell" else 0
            conn.execute(
                "INSERT INTO listings "
                "(book_id,seller_id,listing_type,price,condition,notes,exchange_for,status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    int(book_id),
                    session["user_id"],
                    ltype, price_val, condition,
                    notes or None,
                    exchange_for or None,
                    "pending",
                ),
            )
            conn.commit()
            conn.close()
            flash("Đăng tin thành công. Tin của bạn đang chờ admin duyệt trước khi hiển thị.", "success")
            return redirect(url_for("profile"))

    conn.close()
    return render_template(
        "post_listing.html",
        books=books,
        categories=categories,
        errors=errors,
        FACULTIES=FACULTIES,
    )


@app.route("/listing/<int:lid>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(lid):
    conn = get_db_connection()
    listing = conn.execute(
        """
        SELECT l.*, b.title, b.author, b.category_id, b.subject_code, b.course_year,
               b.cover_image, b.description book_desc
        FROM listings l
        JOIN books b ON b.id=l.book_id
        WHERE l.id=?
        """,
        (lid,),
    ).fetchone()
    if not can_manage_listing(listing, session["user_id"], session.get("role")):
        conn.close()
        flash("Ban khong co quyen sua tin dang nay.", "danger")
        return redirect(url_for("profile"))

    category_meta = None
    if listing["category_id"]:
        category_meta = conn.execute(
            "SELECT id, parent_id FROM categories WHERE id=?",
            (listing["category_id"],),
        ).fetchone()
        if category_meta and category_meta["parent_id"]:
            listing = dict(listing)
            listing["category_id"] = category_meta["parent_id"]

    categories = conn.execute(
        "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order"
    ).fetchall()
    errors = {}

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        cat_id = request.form.get("category_id", "").strip()
        subject_code = request.form.get("subject_code", "").strip()
        course_years = request.form.getlist("course_year")
        cover_image = request.form.get("cover_image", "").strip()
        ltype = request.form.get("listing_type", "").strip()
        price = request.form.get("price", "0").strip()
        condition = request.form.get("condition", "").strip()
        notes = request.form.get("notes", "").strip()
        exchange_for = request.form.get("exchange_for", "").strip()

        if not title:
            errors["title"] = "Ten sach khong duoc trong"
        if not ltype:
            errors["listing_type"] = "Chon loai tin"
        if not condition:
            errors["condition"] = "Chon tinh trang sach"
        if ltype == "sell" and (not price or not price.replace(".", "").isdigit()):
            errors["price"] = "Nhap gia hop le"

        if not errors:
            conn.execute(
                """
                UPDATE books
                SET title=?, author=?, category_id=?, subject_code=?, course_year=?, cover_image=?
                WHERE id=?
                """,
                (
                    title,
                    author or None,
                    int(cat_id) if cat_id.isdigit() else None,
                    subject_code or None,
                    serialize_book_years(course_years),
                    cover_image or None,
                    listing["book_id"],
                ),
            )
            conn.execute(
                """
                UPDATE listings
                SET listing_type=?, price=?, condition=?, notes=?, exchange_for=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    ltype,
                    float(price) if ltype == "sell" else 0,
                    condition,
                    notes or None,
                    exchange_for or None,
                    lid,
                ),
            )
            conn.commit()
            conn.close()
            flash("Da cap nhat tin dang.", "success")
            return redirect(url_for("listing_detail", lid=lid))

        listing = dict(listing)
        listing.update(
            {
                "title": title,
                "author": author,
                "category_id": int(cat_id) if cat_id.isdigit() else None,
                "subject_code": subject_code,
                "course_year": serialize_book_years(course_years),
                "cover_image": cover_image,
                "listing_type": ltype,
                "price": price,
                "condition": condition,
                "notes": notes,
                "exchange_for": exchange_for,
            }
        )

    conn.close()
    return render_template(
        "edit_listing.html",
        listing=listing,
        categories=categories,
        errors=errors,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Wishlist API
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/wishlist/<int:lid>", methods=["POST"])
@login_required
def toggle_wishlist(lid):
    conn = get_db_connection()
    ex = conn.execute(
        "SELECT id FROM wishlist WHERE user_id=? AND listing_id=?",
        (session["user_id"], lid),
    ).fetchone()
    if ex:
        conn.execute(
            "DELETE FROM wishlist WHERE user_id=? AND listing_id=?",
            (session["user_id"], lid),
        )
        added = False
    else:
        conn.execute(
            "INSERT OR IGNORE INTO wishlist(user_id,listing_id) VALUES (?,?)",
            (session["user_id"], lid),
        )
        added = True
    conn.commit()
    conn.close()
    return jsonify({"added": added})


# ─────────────────────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/messages")
@login_required
def messages():
    conn = get_db_connection()
    uid = session["user_id"]
    convos = conn.execute("""
        SELECT
            CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END other_id,
            u.full_name other_name, u.username other_username,
            l.id listing_id, b.title book_title,
            MAX(m.created_at) last_time,
            SUM(CASE WHEN m.receiver_id=? AND m.is_read=0 THEN 1 ELSE 0 END) unread
        FROM messages m
        JOIN users    u ON u.id=(CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END)
        JOIN listings l ON l.id=m.listing_id
        JOIN books    b ON b.id=l.book_id
        WHERE m.sender_id=? OR m.receiver_id=?
        GROUP BY other_id, m.listing_id
        ORDER BY last_time DESC
    """, (uid,) * 5).fetchall()
    conn.close()
    return render_template("messages.html", convos=convos)


@app.route("/messages/<int:lid>/<int:oid>", methods=["GET", "POST"])
@login_required
def chat(lid, oid):
    conn = get_db_connection()
    uid  = session["user_id"]

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            conn.execute(
                "INSERT INTO messages(listing_id,sender_id,receiver_id,content) VALUES(?,?,?,?)",
                (lid, uid, oid, content),
            )

    conn.execute(
        "UPDATE messages SET is_read=1 WHERE listing_id=? AND sender_id=? AND receiver_id=?",
        (lid, oid, uid),
    )
    conn.commit()

    msgs = conn.execute("""
        SELECT m.*, u.full_name sender_name, u.username sender_username
        FROM messages m
        JOIN users u ON u.id=m.sender_id
        WHERE m.listing_id=?
          AND ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
        ORDER BY m.created_at ASC
    """, (lid, uid, oid, oid, uid)).fetchall()

    listing    = conn.execute(
        "SELECT l.*, b.title, b.cover_emoji, b.cover_image FROM listings l JOIN books b ON b.id=l.book_id WHERE l.id=?",
        (lid,),
    ).fetchone()
    other_user = conn.execute("SELECT * FROM users WHERE id=?", (oid,)).fetchone()
    conn.close()

    return render_template(
        "chat.html",
        msgs=msgs,
        listing=listing,
        other_user=other_user,
        listing_id=lid,
        other_id=oid,
    )


@app.route("/api/messages/<int:lid>/<int:oid>")
@login_required
def chat_messages_api(lid, oid):
    conn = get_db_connection()
    uid = session["user_id"]
    after_id = request.args.get("after_id", "0").strip()
    after_id = int(after_id) if after_id.isdigit() else 0

    conn.execute(
        "UPDATE messages SET is_read=1 WHERE listing_id=? AND sender_id=? AND receiver_id=?",
        (lid, oid, uid),
    )
    conn.commit()

    msgs = conn.execute("""
        SELECT m.*, u.full_name sender_name, u.username sender_username
        FROM messages m
        JOIN users u ON u.id=m.sender_id
        WHERE m.listing_id=?
          AND m.id>?
          AND ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
        ORDER BY m.created_at ASC, m.id ASC
    """, (lid, after_id, uid, oid, oid, uid)).fetchall()
    conn.close()
    return jsonify({"messages": [serialize_message(m, uid) for m in msgs]})


@app.route("/api/messages/<int:lid>/<int:oid>", methods=["POST"])
@login_required
def send_chat_message_api(lid, oid):
    conn = get_db_connection()
    uid = session["user_id"]
    content = (request.get_json(silent=True) or {}).get("content", "").strip()
    if not content:
        conn.close()
        return jsonify({"error": "Nội dung tin nhắn không được để trống."}), 400

    conn.execute(
        "INSERT INTO messages(listing_id,sender_id,receiver_id,content) VALUES(?,?,?,?)",
        (lid, uid, oid, content),
    )
    conn.commit()
    msg = conn.execute("""
        SELECT m.*, u.full_name sender_name, u.username sender_username
        FROM messages m
        JOIN users u ON u.id=m.sender_id
        WHERE m.id = last_insert_rowid()
    """).fetchone()
    conn.close()
    return jsonify({"message": serialize_message(msg, uid)})


# ─────────────────────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/seller/<int:user_id>")
@login_required
def seller_profile(user_id):
    conn = get_db_connection()
    seller = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not seller:
        conn.close()
        flash("Khong tim thay nguoi ban.", "warning")
        return redirect(url_for("listings"))

    reputation = get_reputation_summary(conn, user_id)
    listings = conn.execute(
        """
        SELECT l.*, b.title, b.author, b.cover_image, b.subject_code
        FROM listings l
        JOIN books b ON b.id=l.book_id
        WHERE l.seller_id=? AND l.status='active'
        ORDER BY l.created_at DESC
        LIMIT 12
        """,
        (user_id,),
    ).fetchall()
    reviews = conn.execute(
        """
        SELECT r.*, reviewer.full_name reviewer_name, reviewer.username reviewer_username,
               b.title listing_title
        FROM reviews r
        JOIN users reviewer ON reviewer.id=r.reviewer_id
        JOIN listings l ON l.id=r.listing_id
        JOIN books b ON b.id=l.book_id
        WHERE r.reviewed_id=?
        ORDER BY r.created_at DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()
    reviewable_listings = conn.execute(
        """
        SELECT DISTINCT l.id, b.title
        FROM messages m
        JOIN listings l ON l.id=m.listing_id
        JOIN books b ON b.id=l.book_id
        LEFT JOIN reviews r
            ON r.listing_id=l.id AND r.reviewer_id=?
        WHERE l.seller_id=?
          AND ? != l.seller_id
          AND (m.sender_id=? OR m.receiver_id=?)
          AND r.id IS NULL
        ORDER BY l.created_at DESC
        """,
        (session["user_id"], user_id, session["user_id"], session["user_id"], session["user_id"]),
    ).fetchall()
    conn.close()
    return render_template(
        "seller_profile.html",
        seller=seller,
        reputation=reputation,
        listings=listings,
        reviews=reviews,
        reviewable_listings=reviewable_listings,
    )


@app.route("/seller/<int:user_id>/review", methods=["POST"])
@login_required
def submit_seller_review(user_id):
    conn = get_db_connection()
    seller = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if not seller:
        conn.close()
        flash("Khong tim thay nguoi ban.", "warning")
        return redirect(url_for("listings"))
    if user_id == session["user_id"]:
        conn.close()
        flash("Ban khong the tu danh gia chinh minh.", "warning")
        return redirect(url_for("seller_profile", user_id=user_id))

    listing_id = request.form.get("listing_id", "").strip()
    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()
    if not listing_id.isdigit() or not rating.isdigit():
        conn.close()
        flash("Thong tin danh gia khong hop le.", "warning")
        return redirect(url_for("seller_profile", user_id=user_id))

    eligible = conn.execute(
        """
        SELECT l.id
        FROM listings l
        JOIN messages m ON m.listing_id=l.id
        LEFT JOIN reviews r
            ON r.listing_id=l.id AND r.reviewer_id=?
        WHERE l.id=? AND l.seller_id=? AND r.id IS NULL
          AND (m.sender_id=? OR m.receiver_id=?)
        LIMIT 1
        """,
        (session["user_id"], int(listing_id), user_id, session["user_id"], session["user_id"]),
    ).fetchone()
    stars = int(rating)
    if not eligible or stars < 1 or stars > 5:
        conn.close()
        flash("Ban chua du dieu kien de danh gia giao dich nay.", "warning")
        return redirect(url_for("seller_profile", user_id=user_id))

    conn.execute(
        """
        INSERT INTO reviews(reviewer_id, reviewed_id, listing_id, rating, comment)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session["user_id"], user_id, int(listing_id), stars, comment or None),
    )
    recalculate_user_rating(conn, user_id)
    conn.commit()
    conn.close()
    flash("Da gui danh gia cho nguoi ban.", "success")
    return redirect(url_for("seller_profile", user_id=user_id))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn   = get_db_connection()
    user_id = session["user_id"]
    user   = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    errors = {}

    if request.method == "POST":
        fn = request.form.get("full_name", "").strip()
        em = request.form.get("email", "").strip()
        ph = request.form.get("phone", user["phone"] or "").strip()
        si = request.form.get("student_id", user["student_id"] or "").strip()
        fa = request.form.get("faculty", user["faculty"] or "").strip()
        cy = request.form.get("course_year", str(user["course_year"] or "")).strip()
        bi = request.form.get("bio", user["bio"] or "").strip()
        np = request.form.get("new_password", "").strip()
        cp = request.form.get("current_password", "").strip()

        if not fn: errors["full_name"] = "Họ tên không được trống"
        if not em: errors["email"]     = "Email không được trống"
        if np:
            if not cp:
                errors["current_password"] = "Nhập mật khẩu hiện tại"
            elif not check_password_hash(user["password_hash"], cp):
                errors["current_password"] = "Mật khẩu không đúng"
            elif len(np) < 6:
                errors["new_password"] = "Mật khẩu mới ít nhất 6 ký tự"

        if not errors:
            phash = generate_password_hash(np) if np else user["password_hash"]
            conn.execute(
                "UPDATE users SET full_name=?,email=?,phone=?,student_id=?,"
                "faculty=?,course_year=?,bio=?,password_hash=? WHERE id=?",
                (fn, em, ph or None, si or None, fa or None,
                 int(cy) if cy.isdigit() else None,
                 bi or None, phash, user_id),
            )
            conn.commit()
            flash("Cập nhật thành công!", "success")
            return redirect(url_for("profile"))

    my_listings = conn.execute(
        "SELECT l.*, b.title, b.cover_emoji, b.cover_image FROM listings l "
        "JOIN books b ON b.id=l.book_id WHERE l.seller_id=? ORDER BY l.created_at DESC",
        (user_id,),
    ).fetchall()
    wishlist = conn.execute(
        "SELECT l.*, b.title, b.cover_emoji, b.cover_image, u.full_name seller_name "
        "FROM wishlist w "
        "JOIN listings l ON l.id=w.listing_id "
        "JOIN books b ON b.id=l.book_id "
        "JOIN users u ON u.id=l.seller_id "
        "WHERE w.user_id=? AND l.status='active' ORDER BY w.created_at DESC",
        (user_id,),
    ).fetchall()
    wanted_books = conn.execute(
        "SELECT * FROM wanted_books WHERE user_id=? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    alert_notifications = conn.execute(
        """
        SELECT a.*, wb.query, b.title, l.listing_type, l.price
        FROM alert_notifications a
        JOIN wanted_books wb ON wb.id=a.wanted_book_id
        JOIN listings l ON l.id=a.listing_id
        JOIN books b ON b.id=l.book_id
        WHERE a.user_id=?
        ORDER BY a.created_at DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()
    reputation = get_reputation_summary(conn, user_id)
    conn.execute(
        "UPDATE alert_notifications SET is_seen=1 WHERE user_id=? AND is_seen=0",
        (user_id,),
    )
    conn.commit()
    conn.close()

    return render_template(
        "profile.html",
        user=user,
        my_listings=my_listings,
        wishlist=wishlist,
        wanted_books=wanted_books,
        alert_notifications=alert_notifications,
        reputation=reputation,
        errors=errors,
        FACULTIES=FACULTIES,
    )


@app.route("/wanted-books", methods=["POST"])
@login_required
def create_wanted_book():
    query = request.form.get("query", "").strip()
    if not query:
        flash("Hay nhap ten sach ban can theo doi.", "warning")
        return redirect(url_for("profile") + "#wanted-books")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO wanted_books(user_id, query) VALUES (?, ?)",
        (session["user_id"], query),
    )
    wanted_book_id = conn.execute("SELECT last_insert_rowid() id").fetchone()["id"]
    active_matches = conn.execute(
        """
        SELECT l.id
        FROM listings l
        JOIN books b ON b.id=l.book_id
        WHERE l.status='active'
          AND (
              lower(b.title) LIKE ? OR
              lower(COALESCE(b.author, '')) LIKE ? OR
              lower(COALESCE(b.subject_code, '')) LIKE ? OR
              lower(COALESCE(l.notes, '')) LIKE ?
          )
        """,
        tuple([f"%{query.lower()}%"] * 4),
    ).fetchall()
    for row in active_matches:
        conn.execute(
            """
            INSERT OR IGNORE INTO alert_notifications(user_id, wanted_book_id, listing_id)
            VALUES (?, ?, ?)
            """,
            (session["user_id"], wanted_book_id, row["id"]),
        )
    conn.commit()
    conn.close()
    flash("Da bat theo doi sach mong muon.", "success")
    return redirect(url_for("profile") + "#wanted-books")


@app.route("/wanted-books/<int:wanted_book_id>/delete", methods=["POST"])
@login_required
def delete_wanted_book(wanted_book_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM wanted_books WHERE id=? AND user_id=?",
        (wanted_book_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Da xoa muc theo doi sach.", "info")
    return redirect(url_for("profile") + "#wanted-books")


@app.route("/listing/<int:lid>/close", methods=["POST"])
@login_required
def close_listing(lid):
    conn = get_db_connection()
    listing = conn.execute("SELECT id, seller_id FROM listings WHERE id=?", (lid,)).fetchone()
    if not can_manage_listing(listing, session["user_id"], session.get("role")):
        conn.close()
        flash("Ban khong co quyen dong tin dang nay.", "danger")
        return redirect(url_for("profile"))
    conn.execute("UPDATE listings SET status='closed' WHERE id=?", (lid,))
    conn.commit()
    conn.close()
    flash("Tin đăng đã đóng.", "info")
    return redirect(url_for("profile"))


@app.route("/listing/<int:lid>/delete", methods=["POST"])
@login_required
def delete_listing(lid):
    conn = get_db_connection()
    listing = conn.execute("SELECT id, seller_id FROM listings WHERE id=?", (lid,)).fetchone()
    if not can_manage_listing(listing, session["user_id"], session.get("role")):
        conn.close()
        flash("Ban khong co quyen xoa tin dang nay.", "danger")
        return redirect(url_for("profile"))
    conn.execute("DELETE FROM listings WHERE id=?", (lid,))
    conn.commit()
    conn.close()
    flash("Đã xóa tin đăng.", "info")
    return redirect(url_for("profile"))


# ─────────────────────────────────────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/listing/<int:lid>/cover-image", methods=["POST"])
@login_required
def update_listing_cover_image(lid):
    cover_image = request.form.get("cover_image", "").strip() or None
    conn = get_db_connection()
    listing = conn.execute(
        "SELECT id, seller_id, book_id FROM listings WHERE id=?",
        (lid,),
    ).fetchone()
    if not listing:
        conn.close()
        flash("Khong tim thay tin dang.", "warning")
        return redirect(url_for("profile"))
    if listing["seller_id"] != session["user_id"] and session.get("role") != "admin":
        conn.close()
        flash("Ban khong co quyen cap nhat anh bia cho tin nay.", "danger")
        return redirect(url_for("profile"))

    conn.execute(
        "UPDATE books SET cover_image=? WHERE id=?",
        (cover_image, listing["book_id"]),
    )
    conn.commit()
    conn.close()
    flash("Da cap nhat anh bia sach.", "success")
    return redirect(url_for("profile") + "#my-listings")


@app.route("/listing/<int:lid>/report", methods=["POST"])
@login_required
def report_user(lid):
    conn = get_db_connection()
    listing = conn.execute(
        "SELECT id, seller_id FROM listings WHERE id=?",
        (lid,),
    ).fetchone()
    if not listing:
        conn.close()
        flash("Khong tim thay tin dang de report.", "warning")
        return redirect(url_for("listings"))
    if listing["seller_id"] == session["user_id"]:
        conn.close()
        flash("Ban khong the tu report chinh minh.", "warning")
        return redirect(url_for("listing_detail", lid=lid))

    reason = request.form.get("reason", "").strip()
    details = request.form.get("details", "").strip()
    evidence_url = request.form.get("evidence_url", "").strip()
    if reason not in REPORT_REASONS:
        conn.close()
        flash("Ly do report khong hop le.", "warning")
        return redirect(url_for("listing_detail", lid=lid))

    duplicate = conn.execute(
        """
        SELECT id FROM user_reports
        WHERE reporter_id=? AND reported_user_id=? AND listing_id=? AND status='pending'
        """,
        (session["user_id"], listing["seller_id"], lid),
    ).fetchone()
    if duplicate:
        conn.close()
        flash("Ban da gui report cho tin dang nay roi.", "info")
        return redirect(url_for("listing_detail", lid=lid))

    conn.execute(
        """
        INSERT INTO user_reports(reporter_id, reported_user_id, listing_id, reason, details, evidence_url)
        VALUES (?,?,?,?,?,?)
        """,
        (session["user_id"], listing["seller_id"], lid, reason, details or None, evidence_url or None),
    )
    conn.commit()
    conn.close()
    flash("Da gui report toi admin.", "success")
    return redirect(url_for("listing_detail", lid=lid))


@app.route("/admin/listings/<int:lid>/approve", methods=["POST"])
@login_required
@admin_required
def approve_listing(lid):
    conn = get_db_connection()
    updated = conn.execute(
        """
        UPDATE listings
        SET status='active',
            moderated_by=?,
            moderated_at=CURRENT_TIMESTAMP,
            moderation_note=NULL,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND status='pending'
        """,
        (session["user_id"], lid),
    ).rowcount
    if updated:
        create_alerts_for_listing(conn, lid)
    conn.commit()
    conn.close()
    flash(
        "Đã duyệt tin đăng." if updated else "Không thể duyệt tin đăng này.",
        "success" if updated else "warning",
    )
    return redirect(url_for("admin"))


@app.route("/admin/listings/<int:lid>/reject", methods=["POST"])
@login_required
@admin_required
def reject_listing(lid):
    note = request.form.get("moderation_note", "").strip()
    conn = get_db_connection()
    updated = conn.execute(
        """
        UPDATE listings
        SET status='rejected',
            moderated_by=?,
            moderated_at=CURRENT_TIMESTAMP,
            moderation_note=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND status='pending'
        """,
        (session["user_id"], note or None, lid),
    ).rowcount
    conn.commit()
    conn.close()
    flash(
        "Đã từ chối tin đăng." if updated else "Không thể từ chối tin đăng này.",
        "info" if updated else "warning",
    )
    return redirect(url_for("admin"))


@app.route("/admin/reports/<int:rid>/review", methods=["POST"])
@login_required
@admin_required
def review_report(rid):
    conn = get_db_connection()
    updated = conn.execute(
        """
        UPDATE user_reports
        SET status='reviewed', resolved_by=?, resolved_at=CURRENT_TIMESTAMP
        WHERE id=? AND status='pending'
        """,
        (session["user_id"], rid),
    ).rowcount
    conn.commit()
    conn.close()
    flash(
        "ÄĂ£ Ä'Ă¡nh dấu report lĂ  Ä'Ă£ xem xĂ©t." if updated else "KhĂ´ng thể cập nhật report nĂ y.",
        "success" if updated else "warning",
    )
    return redirect(url_for("admin"))


@app.route("/admin/reports/<int:rid>/dismiss", methods=["POST"])
@login_required
@admin_required
def dismiss_report(rid):
    conn = get_db_connection()
    updated = conn.execute(
        """
        UPDATE user_reports
        SET status='dismissed', resolved_by=?, resolved_at=CURRENT_TIMESTAMP
        WHERE id=? AND status='pending'
        """,
        (session["user_id"], rid),
    ).rowcount
    conn.commit()
    conn.close()
    flash(
        "ÄĂ£ bỏ qua report." if updated else "KhĂ´ng thể cập nhật report nĂ y.",
        "info" if updated else "warning",
    )
    return redirect(url_for("admin"))


@app.route("/admin")
@login_required
@admin_required
def admin():
    conn = get_db_connection()
    stats = conn.execute("""
        SELECT
          (SELECT COUNT(*) FROM users)                               total_users,
          (SELECT COUNT(*) FROM books)                               total_books,
          (SELECT COUNT(*) FROM listings)                            total_listings,
          (SELECT COUNT(*) FROM listings WHERE status='active')      active_listings,
          (SELECT COUNT(*) FROM listings WHERE status='pending')     pending_listings,
          (SELECT COUNT(*) FROM listings WHERE status='rejected')    rejected_listings,
          (SELECT COUNT(*) FROM user_reports WHERE status='pending') pending_reports,
          (SELECT COUNT(*) FROM user_reports)                        total_reports,
          (SELECT COUNT(*) FROM messages)                            total_messages,
          (SELECT COUNT(*) FROM listings
             WHERE moderated_at >= date('now'))                      moderated_today
    """).fetchone()
    recent_users = conn.execute(
        "SELECT * FROM users ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    pending_listings = conn.execute("""
        SELECT l.*, b.title, u.username seller, u.full_name seller_name
        FROM listings l
        JOIN books b ON b.id=l.book_id
        JOIN users u ON u.id=l.seller_id
        WHERE l.status='pending'
        ORDER BY l.created_at ASC
        LIMIT 20
    """).fetchall()
    recent_listings = conn.execute("""
        SELECT l.*, b.title, b.cover_image, u.username seller, u.full_name seller_name
        FROM listings l
        JOIN books b ON b.id=l.book_id
        JOIN users u ON u.id=l.seller_id
        ORDER BY l.created_at DESC LIMIT 10
    """).fetchall()
    listing_type_report = conn.execute("""
        SELECT listing_type, COUNT(*) total
        FROM listings
        GROUP BY listing_type
        ORDER BY total DESC
    """).fetchall()
    faculty_report = conn.execute("""
        SELECT COALESCE(u.faculty, 'Chưa cập nhật') faculty, COUNT(*) total
        FROM listings l
        JOIN users u ON u.id=l.seller_id
        WHERE l.status='active'
        GROUP BY COALESCE(u.faculty, 'Chưa cập nhật')
        ORDER BY total DESC
        LIMIT 8
    """).fetchall()
    top_sellers = conn.execute("""
        SELECT u.username, u.full_name, COUNT(*) total_listings
        FROM listings l
        JOIN users u ON u.id=l.seller_id
        WHERE l.status='active'
        GROUP BY u.id
        ORDER BY total_listings DESC, u.username ASC
        LIMIT 8
    """).fetchall()
    moderation_report = conn.execute("""
        SELECT l.id, b.title, l.status, l.moderated_at, l.moderation_note,
               u.username seller, a.username admin_name
        FROM listings l
        JOIN books b ON b.id=l.book_id
        JOIN users u ON u.id=l.seller_id
        LEFT JOIN users a ON a.id=l.moderated_by
        WHERE l.status IN ('active', 'rejected')
        ORDER BY COALESCE(l.moderated_at, l.updated_at) DESC
        LIMIT 12
    """).fetchall()
    pending_reports = conn.execute("""
        SELECT r.*, reporter.username reporter_username, reporter.full_name reporter_name,
               target.username target_username, target.full_name target_name,
               l.id listing_id, b.title listing_title
        FROM user_reports r
        JOIN users reporter ON reporter.id=r.reporter_id
        JOIN users target   ON target.id=r.reported_user_id
        LEFT JOIN listings l ON l.id=r.listing_id
        LEFT JOIN books b ON b.id=l.book_id
        WHERE r.status='pending'
        ORDER BY r.created_at ASC
        LIMIT 20
    """).fetchall()
    conn.close()
    return render_template(
        "admin.html",
        stats=stats,
        recent_users=recent_users,
        pending_listings=pending_listings,
        recent_listings=recent_listings,
        listing_type_report=listing_type_report,
        faculty_report=faculty_report,
        top_sellers=top_sellers,
        moderation_report=moderation_report,
        pending_reports=pending_reports,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bootstrap_database()
    print("NEU Bookstore dang chay: http://localhost:5000")
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "").lower() == "true",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
