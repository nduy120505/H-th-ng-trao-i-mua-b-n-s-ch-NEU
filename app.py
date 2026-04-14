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
from functools import wraps
from datetime import datetime, timedelta

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

FACULTIES = [
    "Khoa Kinh Tế",
    "Khoa Quản Trị Kinh Doanh",
    "Khoa Tài Chính – Ngân Hàng",
    "Khoa Kế Toán – Kiểm Toán",
    "Khoa Hệ Thống Thông Tin",
    "Khoa Marketing",
    "Khoa Luật Kinh Tế",
    "Khoa Bất Động Sản",
    "Khoa Thống Kê",
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


def can_view_listing(listing, user_id, role):
    if not listing:
        return False
    return listing["status"] == "active" or listing["seller_id"] == user_id or role == "admin"


def format_local_timestamp(value, fmt="%H:%M"):
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S") + timedelta(hours=7)
        return dt.strftime(fmt)
    except ValueError:
        return value


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
    if "user_id" in session:
        row = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE receiver_id=? AND is_read=0",
            (session["user_id"],),
        ).fetchone()
        unread = row["c"] if row else 0
    conn.close()
    return dict(
        current_user=get_current_user(),
        root_categories=root_cats,
        unread_count=unread,
        CONDITION_LABELS=CONDITION_LABELS,
        TYPE_LABELS=TYPE_LABELS,
        REPORT_REASONS=REPORT_REASONS,
        LISTING_STATUS_META=LISTING_STATUS_META,
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
    faculty     = request.args.get("faculty", "")
    course_year = request.args.get("year", "")
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
    if faculty:
        where.append("b.faculty=?");        params.append(faculty)
    if course_year and course_year.isdigit():
        where.append("b.course_year=?");    params.append(int(course_year))

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
        "SELECT * FROM categories ORDER BY parent_id NULLS FIRST, sort_order"
    ).fetchall()
    faculties = conn.execute(
        "SELECT DISTINCT faculty FROM books WHERE faculty IS NOT NULL ORDER BY faculty"
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
        faculties=faculties,
        wishlist_ids=wishlist_ids,
        q=q, cat_id=cat_id, ltype=ltype, condition=condition,
        faculty=faculty, course_year=course_year, sort=sort,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Listing detail
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/listing/<int:lid>")
@login_required
def listing_detail(lid):
    conn = get_db_connection()
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

    if not can_view_listing(listing, session["user_id"], session.get("role")):
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
        (session["user_id"], lid),
    ).fetchone()
    conn.close()

    return render_template(
        "listing_detail.html",
        listing=listing,
        related=related,
        in_wishlist=bool(wl),
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
        "SELECT * FROM categories ORDER BY parent_id NULLS FIRST, sort_order"
    ).fetchall()
    errors = {}

    if request.method == "POST":
        book_id     = request.form.get("book_id", "").strip()
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
        new_year    = request.form.get("new_year", "").strip()

        if not book_id and not new_title:
            errors["book"] = "Chọn sách hoặc nhập tên sách mới"
        if not ltype:
            errors["listing_type"] = "Chọn loại tin"
        if not condition:
            errors["condition"] = "Chọn tình trạng sách"
        if ltype == "sell" and (not price or not price.replace(".", "").isdigit()):
            errors["price"] = "Nhập giá hợp lệ"

        if not errors:
            if not book_id and new_title:
                cur = conn.execute(
                    "INSERT INTO books(title,author,category_id,subject_code,course_year,cover_image) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        new_title,
                        new_author or None,
                        int(new_cat_id) if new_cat_id.isdigit() else None,
                        new_subject or None,
                        int(new_year) if new_year.isdigit() else None,
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

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn   = get_db_connection()
    user   = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    errors = {}

    if request.method == "POST":
        fn = request.form.get("full_name", "").strip()
        em = request.form.get("email", "").strip()
        ph = request.form.get("phone", "").strip()
        si = request.form.get("student_id", "").strip()
        fa = request.form.get("faculty", "").strip()
        cy = request.form.get("course_year", "").strip()
        bi = request.form.get("bio", "").strip()
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
                 bi or None, phash, session["user_id"]),
            )
            conn.commit()
            flash("Cập nhật thành công!", "success")
            return redirect(url_for("profile"))

    my_listings = conn.execute(
        "SELECT l.*, b.title, b.cover_emoji, b.cover_image FROM listings l "
        "JOIN books b ON b.id=l.book_id WHERE l.seller_id=? ORDER BY l.created_at DESC",
        (session["user_id"],),
    ).fetchall()
    wishlist = conn.execute(
        "SELECT l.*, b.title, b.cover_emoji, b.cover_image, u.full_name seller_name "
        "FROM wishlist w "
        "JOIN listings l ON l.id=w.listing_id "
        "JOIN books b ON b.id=l.book_id "
        "JOIN users u ON u.id=l.seller_id "
        "WHERE w.user_id=? AND l.status='active' ORDER BY w.created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "profile.html",
        user=user,
        my_listings=my_listings,
        wishlist=wishlist,
        errors=errors,
        FACULTIES=FACULTIES,
    )


@app.route("/listing/<int:lid>/close", methods=["POST"])
@login_required
def close_listing(lid):
    conn = get_db_connection()
    conn.execute(
        "UPDATE listings SET status='closed' WHERE id=? AND seller_id=?",
        (lid, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Tin đăng đã đóng.", "info")
    return redirect(url_for("profile"))


@app.route("/listing/<int:lid>/delete", methods=["POST"])
@login_required
def delete_listing(lid):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM listings WHERE id=? AND seller_id=?",
        (lid, session["user_id"]),
    )
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
        "ÄĂ£ Ä‘Ă¡nh dáº¥u report lĂ  Ä‘Ă£ xem xĂ©t." if updated else "KhĂ´ng thá»ƒ cáº­p nháº­t report nĂ y.",
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
        "ÄĂ£ bá» qua report." if updated else "KhĂ´ng thá»ƒ cáº­p nháº­t report nĂ y.",
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
    print("🚀 NEU Bookstore đang chạy → http://localhost:5000")
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "").lower() == "true",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
