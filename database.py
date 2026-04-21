"""
database.py
===========
Quản lý kết nối SQLite, định nghĩa schema và seed dữ liệu mẫu
cho NEU Bookstore.
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(
        os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", os.path.dirname(__file__)),
        "neu_bookstore.db",
    ),
)


# -----------------------------------------------------------------------------
# Kết nối
# -----------------------------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """Trả về kết nối SQLite với row_factory = Row."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# -----------------------------------------------------------------------------
# Khởi tạo schema
# -----------------------------------------------------------------------------

SCHEMA_SQL = """
-- Bảng người dùng
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    full_name     TEXT,
    email         TEXT,
    phone         TEXT,
    latitude      REAL,
    longitude     REAL,
    location_updated_at TIMESTAMP,
    student_id    TEXT    UNIQUE,
    faculty       TEXT,
    course_year   INTEGER,
    role          TEXT    DEFAULT 'student' CHECK(role IN ('student','admin')),
    bio           TEXT,
    rating_avg    REAL    DEFAULT 0,
    rating_count  INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng danh mục sách (phân cấp 2 tầng)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    slug        TEXT    UNIQUE NOT NULL,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    icon        TEXT    DEFAULT '📚',
    description TEXT,
    sort_order  INTEGER DEFAULT 0
);

-- Bảng thông tin sách
CREATE TABLE IF NOT EXISTS books (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    author       TEXT,
    isbn         TEXT,
    publisher    TEXT,
    publish_year INTEGER,
    edition      TEXT,
    category_id  INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    faculty      TEXT,
    course_year  INTEGER,
    subject_code TEXT,
    description  TEXT,
    cover_image  TEXT,
    cover_emoji  TEXT    DEFAULT '📖',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng tin đăng bán / trao đổi
CREATE TABLE IF NOT EXISTS listings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id      INTEGER REFERENCES books(id)    ON DELETE CASCADE,
    seller_id    INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    listing_type TEXT    NOT NULL CHECK(listing_type IN ('sell','exchange','free')),
    price        REAL    DEFAULT 0,
    condition    TEXT    NOT NULL
                 CHECK(condition IN ('new','like_new','good','fair','poor')),
    notes        TEXT,
    status       TEXT    DEFAULT 'active'
                 CHECK(status IN ('pending','active','rejected','sold','reserved','closed')),
    exchange_for TEXT,
    moderated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    moderated_at TIMESTAMP,
    moderation_note TEXT,
    views        INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng tin nhắn giữa người dùng
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id  INTEGER REFERENCES listings(id)  ON DELETE CASCADE,
    sender_id   INTEGER REFERENCES users(id)     ON DELETE CASCADE,
    receiver_id INTEGER REFERENCES users(id)     ON DELETE CASCADE,
    content     TEXT    NOT NULL,
    is_read     INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng yêu thích
CREATE TABLE IF NOT EXISTS wishlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, listing_id)
);

-- Bảng đánh giá người dùng
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    reviewed_id INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    listing_id  INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    rating      INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reviewer_id, listing_id)
);

CREATE TABLE IF NOT EXISTS user_reports (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    listing_id       INTEGER REFERENCES listings(id) ON DELETE SET NULL,
    reason           TEXT NOT NULL,
    details          TEXT,
    evidence_url     TEXT,
    status           TEXT DEFAULT 'pending'
                     CHECK(status IN ('pending','reviewed','dismissed')),
    resolved_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolved_at      TIMESTAMP,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wanted_books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    query       TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_notifications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER REFERENCES users(id) ON DELETE CASCADE,
    wanted_book_id INTEGER REFERENCES wanted_books(id) ON DELETE CASCADE,
    listing_id     INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    is_seen        INTEGER DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(wanted_book_id, listing_id)
);
"""


# -----------------------------------------------------------------------------
# Dữ liệu mẫu
# -----------------------------------------------------------------------------

SEED_CATEGORIES = [
    # Cấp 1
    (1,  "Môn Học Đại Cương", "dai-cuong", None, "🎓", "Các môn đại cương toàn trường", 1),
    (2,  "Khoa Kinh Tế", "kinh-te", None, "📊", "Sách chuyên ngành Kinh tế học", 2),
    (3,  "Khoa Quản Trị Kinh Doanh", "quan-tri", None, "💼", "Sách chuyên ngành Quản trị kinh doanh", 3),
    (4,  "Khoa Tài Chính – Ngân Hàng", "tai-chinh", None, "🏦", "Sách chuyên ngành Tài chính – Ngân hàng", 4),
    (5,  "Khoa Kế Toán – Kiểm Toán", "ke-toan", None, "📒", "Sách chuyên ngành Kế toán", 5),
    (6,  "Khoa Hệ Thống Thông Tin", "httt", None, "💻", "Sách chuyên ngành Hệ thống thông tin", 6),
    (7,  "Khoa Marketing", "marketing", None, "📢", "Sách chuyên ngành Marketing", 7),
    (8,  "Khoa Luật Kinh Tế", "luat", None, "⚖️", "Sách chuyên ngành Luật kinh tế", 8),
    (9,  "Khoa Bất Động Sản", "bat-dong-san", None, "🏠", "Sách chuyên ngành Bất động sản", 9),
    (10, "Khoa Thống Kê", "thong-ke", None, "📈", "Sách chuyên ngành Thống kê", 10),
    (25, "Khoa Công nghệ thông tin",     "cong-nghe-thong-tin",                None, "💻", "Sách chuyên ngành Công nghệ thông tin", 11),
    (26, "Khoa Bảo hiểm",                "bao-hiem",                            None, "🛡️", "Sách chuyên ngành Bảo hiểm", 12),
    (27, "Khoa Bất động sản và Kinh tế tài nguyên", "bat-dong-san-va-kinh-te-tai-nguyen", None, "🏙️", "Sách chuyên ngành Bất động sản và Kinh tế tài nguyên", 13),
    (28, "Khoa Đầu tư",                  "dau-tu",                              None, "📈", "Sách chuyên ngành Đầu tư", 14),
    (29, "Khoa Du lịch và Khách sạn",    "du-lich-va-khach-san",                None, "🏨", "Sách chuyên ngành Du lịch và Khách sạn", 15),
    (30, "Khoa Hệ thống thông tin quản lý", "he-thong-thong-tin-quan-ly",      None, "🗂️", "Sách chuyên ngành Hệ thống thông tin quản lý", 16),
    (31, "Khoa Kế hoạch và Phát triển",  "ke-hoach-va-phat-trien",              None, "🧭", "Sách chuyên ngành Kế hoạch và Phát triển", 17),
    (32, "Khoa Khoa học Cơ sở",          "khoa-hoc-co-so",                      None, "🧪", "Sách nền tảng Khoa học Cơ sở", 18),
    (33, "Khoa Khoa học dữ liệu và Trí tuệ nhân tạo", "khoa-hoc-du-lieu-va-tri-tue-nhan-tao", None, "🤖", "Sách chuyên ngành Khoa học dữ liệu và Trí tuệ nhân tạo", 19),
    (34, "Khoa Khoa học quản lý",        "khoa-hoc-quan-ly",                    None, "📚", "Sách chuyên ngành Khoa học quản lý", 20),
    (35, "Khoa Kinh tế học",             "kinh-te-hoc",                         None, "📊", "Sách chuyên ngành Kinh tế học", 21),
    (36, "Khoa Kinh tế và Quản lý nguồn nhân lực", "kinh-te-va-quan-ly-nguon-nhan-luc", None, "👥", "Sách chuyên ngành Kinh tế và Quản lý nguồn nhân lực", 22),
    (37, "Khoa Luật",                    "khoa-luat",                           None, "⚖️", "Sách chuyên ngành Luật", 23),
    (38, "Khoa Lý luận chính trị",       "ly-luan-chinh-tri",                   None, "🏛️", "Sách chuyên ngành Lý luận chính trị", 24),
    (39, "Khoa Môi trường, Biến đổi khí hậu và Đô thị", "moi-truong-bien-doi-khi-hau-va-do-thi", None, "🌿", "Sách chuyên ngành Môi trường, Biến đổi khí hậu và Đô thị", 25),
    (40, "Khoa Ngoại ngữ Kinh tế",       "ngoai-ngu-kinh-te",                   None, "🌍", "Sách chuyên ngành Ngoại ngữ Kinh tế", 26),
    (41, "Khoa Toán kinh tế",            "toan-kinh-te",                        None, "🔢", "Sách chuyên ngành Toán kinh tế", 27),
    (42, "Viện Đào tạo Quốc tế",         "vien-dao-tao-quoc-te",                None, "🌐", "Chương trình và học liệu của Viện Đào tạo Quốc tế", 28),
    (43, "Viện Đào tạo Tiên tiến, Chất lượng cao và POHE", "vien-dao-tao-tien-tien-chat-luong-cao-va-pohe", None, "🎓", "Học liệu của các chương trình Tiên tiến, Chất lượng cao và POHE", 29),
    (44, "Viện Kế toán - Kiểm toán",     "vien-ke-toan-kiem-toan",              None, "🧾", "Sách chuyên ngành của Viện Kế toán - Kiểm toán", 30),
    (45, "Viện Ngân hàng - Tài chính",   "vien-ngan-hang-tai-chinh",            None, "🏦", "Sách chuyên ngành của Viện Ngân hàng - Tài chính", 31),
    (46, "Viện Quản trị Kinh doanh",     "vien-quan-tri-kinh-doanh",            None, "💼", "Sách chuyên ngành của Viện Quản trị Kinh doanh", 32),
    (47, "Viện Thương mại và Kinh tế quốc tế", "vien-thuong-mai-va-kinh-te-quoc-te", None, "🚢", "Sách chuyên ngành của Viện Thương mại và Kinh tế quốc tế", 33),
    # Cấp 2 – con của Đại cương (parent_id=1)
    (11, "Toán Cao Cấp & XSTK", "toan", 1, "🔢", "Toán cao cấp, Xác suất thống kê", 1),
    (12, "Kinh Tế Chính Trị", "ktct", 1, "🏛️", "Kinh tế chính trị Mác-Lênin", 2),
    (13, "Triết Học Mác-Lênin", "triet-hoc", 1, "🤔", "Triết học Mác-Lênin", 3),
    (14, "Pháp Luật Đại Cương", "phap-luat", 1, "📜", "Pháp luật đại cương", 4),
    (15, "Tiếng Anh", "tieng-anh", 1, "🌍", "Tiếng Anh thương mại, IELTS, TOEIC", 5),
    (16, "Tin Học Đại Cương", "tin-hoc", 1, "🖥️", "Tin học đại cương, Office", 6),
    (17, "Lịch Sử Đảng", "ls-dang", 1, "🇻🇳", "Lịch sử Đảng Cộng sản Việt Nam", 7),
    (18, "Tư Tưởng Hồ Chí Minh", "tthcm", 1, "⭐", "Tư tưởng Hồ Chí Minh", 8),
    # Cấp 2 – con của Kinh tế (parent_id=2)
    (19, "Kinh Tế Vi Mô", "vi-mo", 2, "🔍", "Kinh tế vi mô", 1),
    (20, "Kinh Tế Vĩ Mô", "vi-mo-2", 2, "🌐", "Kinh tế vĩ mô", 2),
    (21, "Kinh Tế Quốc Tế", "kt-quoc-te", 2, "✈️", "Kinh tế quốc tế", 3),
    # Cấp 2 – con của Tài chính (parent_id=4)
    (22, "Tài Chính Doanh Nghiệp", "tcdn", 4, "💰", "Tài chính doanh nghiệp", 1),
    (23, "Ngân Hàng Thương Mại", "nhtm", 4, "🏧", "Nghiệp vụ ngân hàng", 2),
    (24, "Thị Trường Chứng Khoán", "chung-khoan", 4, "📉", "Chứng khoán & đầu tư", 3),
]

SEED_BOOKS = [
    ("Giáo Trình Toán Cao Cấp – Tập 1", "Nguyễn Đình Trí", "9786045891001", "NXB Giáo Dục", 2022, "Tái bản lần 5", 11, None, 1, "MATH101", "Đại số tuyến tính và giải tích", "📐", None),
    ("Giáo Trình Toán Cao Cấp – Tập 2", "Nguyễn Đình Trí", "9786045891002", "NXB Giáo Dục", 2022, "Tái bản lần 5", 11, None, 1, "MATH102", "Tích phân và phương trình vi phân", "📐", None),
    ("Xác Suất Thống Kê", "Đào Hữu Hồ", "9786045892001", "NXB ĐHQG HN", 2021, "Lần 3", 11, None, 2, "STAT101", "Xác suất thống kê ứng dụng kinh tế", "📊", None),
    ("Kinh Tế Chính Trị Mác-Lênin", "Bộ GD&ĐT", "9786045893001", "NXB Chính Trị QG", 2021, "Lần 1", 12, None, 1, "KTCT101", "Giáo trình mới 2021", "🏛️", None),
    ("Triết Học Mác-Lênin", "Bộ GD&ĐT", "9786045893002", "NXB Chính Trị QG", 2021, "Lần 1", 13, None, 1, "TRHH101", "Giáo trình triết học chính thức", "🤔", None),
    ("Pháp Luật Đại Cương", "Nguyễn Văn Động", "9786045894001", "NXB Tư Pháp", 2020, "Lần 2", 14, None, 1, "PLDC101", "Pháp luật đại cương khối KT", "📜", None),
    ("English for Business Communication", "Simon Sweeney", "9780521754491", "Cambridge UP", 2018, "3rd Edition", 15, None, 1, "ENG101", "Tiếng Anh thương mại nâng cao", "🌍", None),
    ("Kinh Tế Vi Mô", "Vũ Kim Dũng", "9786045895001", "NXB Lao Động", 2023, "Lần 4", 19, "Khoa Kinh Tế", 1, "ECO101", "Kinh tế vi mô cơ bản và nâng cao", "🔍", None),
    ("Kinh Tế Vĩ Mô", "N. Gregory Mankiw", "9780357722527", "Cengage Learning", 2022, "10th Edition", 20, "Khoa Kinh Tế", 2, "ECO201", "Principles of Macroeconomics", "🌐", None),
    ("Quản Trị Học", "Nguyễn Thị Liên Diệp", "9786045896001", "NXB Lao Động", 2022, "Lần 6", 3, "Khoa Quản Trị", 1, "QTKD101", "Quản trị học căn bản", "💼", None),
    ("Marketing Căn Bản", "Philip Kotler", "9780135197035", "Pearson", 2021, "16th Edition", 7, "Khoa Marketing", 2, "MKT101", "Principles of Marketing", "📢", None),
    ("Tài Chính Doanh Nghiệp", "Trần Ngọc Thơ", "9786045897001", "NXB Thống Kê", 2022, "Lần 3", 22, "Khoa TC-NH", 2, "TCDN201", "Corporate Finance cơ bản và nâng cao", "💰", None),
    ("Kế Toán Tài Chính", "Ngô Thế Chi", "9786045898001", "NXB Tài Chính", 2023, "Lần 5", 5, "Khoa Kế Toán", 2, "KT201", "Kế toán tài chính doanh nghiệp", "📒", None),
    ("Cơ Sở Dữ Liệu", "Nguyễn Bá Tường", "9786045899001", "NXB ĐHQG HN", 2021, "Lần 2", 6, "Khoa HTTT", 1, "IT201", "Cơ sở dữ liệu quan hệ", "💻", None),
    ("Luật Kinh Tế", "Dương Đăng Huệ", "9786045900001", "NXB Tư Pháp", 2022, "Lần 3", 8, "Khoa Luật", 1, "LAW201", "Luật kinh tế dành cho sinh viên NEU", "⚖️", None),
    ("Nguyên Lý Kế Toán", "Nguyễn Văn Công", "9786045901001", "NXB Tài Chính", 2021, "Lần 4", 5, "Khoa Kế Toán", 1, "KT101", "Nguyên lý kế toán cơ bản", "📒", None),
    ("Thị Trường Chứng Khoán", "Phan Thị Bích Nguyệt", "9786045902001", "NXB Tài Chính", 2023, "Lần 2", 24, "Khoa TC-NH", 3, "FIN301", "Phân tích và đầu tư chứng khoán", "📉", None),
    ("Quản Trị Marketing", "Philip Kotler", "9780135716953", "Pearson", 2022, "16th Edition", 7, "Khoa Marketing", 3, "MKT301", "Marketing Management", "📢", None),
]

SEED_USERS = [
    ("sv001", "123456", "Nguyễn Văn An", "an.nv@st.neu.edu.vn", "0362710976", "SV2021001", "Khoa Kinh Tế", 2021),
    ("sv002", "123456", "Trần Thị Bình", "binh.tt@st.neu.edu.vn", "0362710976", "SV2022002", "Khoa Quản Trị Kinh Doanh", 2022),
    ("sv003", "123456", "Lê Quang Cường", "cuong.lq@st.neu.edu.vn", "0362710976", "SV2020003", "Khoa Tài Chính – Ngân Hàng", 2020),
]

# (book_id, user_idx 0/1/2, type, price, condition, notes, exchange_for, views)
SEED_LISTINGS = [
    (1, 0, "sell", 45000, "like_new", "Còn mới 95%, không ghi chú", None, 12),
    (2, 0, "sell", 35000, "good", "Có gạch chân một số chỗ", None, 8),
    (3, 1, "exchange", 0, "like_new", "Đổi lấy sách Kinh tế vi mô", "Kinh Tế Vi Mô", 5),
    (4, 1, "sell", 120000, "new", "Mới 100%, còn seal", None, 20),
    (5, 2, "free", 0, "fair", "Tặng miễn phí, tự đến lấy", None, 3),
    (6, 2, "sell", 80000, "good", "Sách bản tiếng Anh chính hãng", None, 15),
    (7, 0, "sell", 55000, "like_new", "Học xong không dùng nữa", None, 7),
    (8, 1, "sell", 40000, "good", "Có highlight các phần quan trọng", None, 9),
    (9, 2, "exchange", 0, "like_new", "Đổi lấy sách kế toán năm 2", "Kế Toán Tài Chính", 4),
    (10, 0, "sell", 150000, "new", "Mua nhầm không dùng, bán rẻ", None, 18),
]


def sync_seed_data(conn: sqlite3.Connection) -> None:
    """Đồng bộ dữ liệu seed cốt lõi vào database hiện có."""
    cur = conn.cursor()

    for category_id, name, slug, parent_id, icon, description, sort_order in SEED_CATEGORIES:
        cur.execute(
            """
            INSERT OR IGNORE INTO categories (id, name, slug, parent_id, icon, description, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (category_id, name, slug, parent_id, icon, description, sort_order),
        )
        cur.execute(
            """
            UPDATE categories
            SET name=?, slug=?, parent_id=?, icon=?, description=?, sort_order=?
            WHERE id=?
            """,
            (name, slug, parent_id, icon, description, sort_order, category_id),
        )

    for index, (title, author, isbn, publisher, publish_year, edition, category_id, faculty, course_year,
                subject_code, description, cover_emoji, cover_image) in enumerate(SEED_BOOKS, start=1):
        cur.execute(
            """
            INSERT OR IGNORE INTO books
            (id, title, author, isbn, publisher, publish_year, edition, category_id, faculty,
             course_year, subject_code, description, cover_emoji, cover_image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (index, title, author, isbn, publisher, publish_year, edition, category_id, faculty,
             course_year, subject_code, description, cover_emoji, cover_image),
        )
        cur.execute(
            """
            UPDATE books
            SET title=?, author=?, isbn=?, publisher=?, publish_year=?, edition=?, category_id=?,
                faculty=?, course_year=?, subject_code=?, description=?, cover_emoji=?, cover_image=?
            WHERE id=?
            """,
            (title, author, isbn, publisher, publish_year, edition, category_id, faculty, course_year,
             subject_code, description, cover_emoji, cover_image, index),
        )

    demo_locations = {
        "sv001": (21.0006, 105.8421),
        "sv002": (20.9987, 105.8443),
        "sv003": (21.0048, 105.8468),
    }
    for uname, pwd, fname, email, phone, sid, faculty, year in SEED_USERS:
        lat, lng = demo_locations.get(uname, (None, None))
        cur.execute(
            """
            INSERT OR IGNORE INTO users
            (username, password_hash, full_name, email, phone, latitude, longitude, student_id, faculty, course_year, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uname, generate_password_hash(pwd), fname, email, phone, lat, lng, sid, faculty, year, "student"),
        )
        cur.execute(
            """
            UPDATE users
            SET full_name=?, email=?, phone=?, latitude=COALESCE(latitude, ?),
                longitude=COALESCE(longitude, ?), student_id=?, faculty=?, course_year=?
            WHERE username=?
            """,
            (fname, email, phone, lat, lng, sid, faculty, year, uname),
        )

    cur.execute(
        """
        INSERT OR IGNORE INTO users (username, password_hash, full_name, email, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("admin", generate_password_hash("admin123"), "Quản trị viên NEU", "admin@neu.edu.vn", "admin"),
    )
    cur.execute(
        """
        UPDATE users
        SET full_name=?, email=?, role=?
        WHERE username=?
        """,
        ("Quản trị viên NEU", "admin@neu.edu.vn", "admin", "admin"),
    )

    user_ids = [
        cur.execute("SELECT id FROM users WHERE username=?", (u[0],)).fetchone()[0]
        for u in SEED_USERS
    ]
    for listing_id, (book_id, u_idx, ltype, price, cond, notes, exch, views) in enumerate(SEED_LISTINGS, start=1):
        seller_id = user_ids[u_idx]
        cur.execute(
            """
            INSERT OR IGNORE INTO listings
            (id, book_id, seller_id, listing_type, price, condition, notes, exchange_for, views)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (listing_id, book_id, seller_id, ltype, price, cond, notes, exch, views),
        )
        cur.execute(
            """
            UPDATE listings
            SET book_id=?, seller_id=?, listing_type=?, price=?, condition=?, notes=?, exchange_for=?, views=?
            WHERE id=?
            """,
            (book_id, seller_id, ltype, price, cond, notes, exch, views, listing_id),
        )


def init_db() -> None:
    """Tạo bảng và seed dữ liệu mẫu nếu chưa tồn tại."""
    conn = get_db_connection()
    cur  = conn.cursor()

    # Tạo bảng
    cur.executescript(SCHEMA_SQL)
    ensure_db_schema(conn)

    sync_seed_data(conn)

    conn.commit()
    conn.close()
    print("Database khoi tao thanh cong!")


def ensure_db_schema(conn: sqlite3.Connection | None = None) -> None:
    """Bổ sung schema cho database đang tồn tại."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_reports (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
            reported_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            listing_id       INTEGER REFERENCES listings(id) ON DELETE SET NULL,
            reason           TEXT NOT NULL,
            details          TEXT,
            evidence_url     TEXT,
            status           TEXT DEFAULT 'pending'
                             CHECK(status IN ('pending','reviewed','dismissed')),
            resolved_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            resolved_at      TIMESTAMP,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wanted_books (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query       TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_notifications (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER REFERENCES users(id) ON DELETE CASCADE,
            wanted_book_id INTEGER REFERENCES wanted_books(id) ON DELETE CASCADE,
            listing_id     INTEGER REFERENCES listings(id) ON DELETE CASCADE,
            is_seen        INTEGER DEFAULT 0,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(wanted_book_id, listing_id)
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_unique_reviewer_listing
        ON reviews(reviewer_id, listing_id)
    """)
    report_cols = {
        row["name"] for row in cur.execute("PRAGMA table_info(user_reports)").fetchall()
    }
    if "evidence_url" not in report_cols:
        cur.execute("ALTER TABLE user_reports ADD COLUMN evidence_url TEXT")

    book_cols = {
        row["name"] for row in cur.execute("PRAGMA table_info(books)").fetchall()
    }
    if "cover_image" not in book_cols:
        cur.execute("ALTER TABLE books ADD COLUMN cover_image TEXT")

    user_cols = {
        row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()
    }
    if "latitude" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN latitude REAL")
    if "longitude" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN longitude REAL")
    if "location_updated_at" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN location_updated_at TIMESTAMP")

    listing_cols = {
        row["name"] for row in cur.execute("PRAGMA table_info(listings)").fetchall()
    }
    if not listing_cols:
        if close_conn:
            conn.close()
        return

    create_sql_row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='listings'"
    ).fetchone()
    create_sql = (create_sql_row["sql"] if create_sql_row else "") or ""
    needs_rebuild = "pending" not in create_sql or "moderated_by" not in create_sql

    if "moderated_by" not in listing_cols:
        cur.execute("ALTER TABLE listings ADD COLUMN moderated_by INTEGER")
    if "moderated_at" not in listing_cols:
        cur.execute("ALTER TABLE listings ADD COLUMN moderated_at TIMESTAMP")
    if "moderation_note" not in listing_cols:
        cur.execute("ALTER TABLE listings ADD COLUMN moderation_note TEXT")

    if needs_rebuild:
        cur.executescript("""
        CREATE TABLE listings_new (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id         INTEGER REFERENCES books(id) ON DELETE CASCADE,
            seller_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
            listing_type    TEXT NOT NULL CHECK(listing_type IN ('sell','exchange','free')),
            price           REAL DEFAULT 0,
            condition       TEXT NOT NULL
                            CHECK(condition IN ('new','like_new','good','fair','poor')),
            notes           TEXT,
            status          TEXT DEFAULT 'active'
                            CHECK(status IN ('pending','active','rejected','sold','reserved','closed')),
            exchange_for    TEXT,
            moderated_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            moderated_at    TIMESTAMP,
            moderation_note TEXT,
            views           INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO listings_new (
            id, book_id, seller_id, listing_type, price, condition, notes, status,
            exchange_for, moderated_by, moderated_at, moderation_note, views, created_at, updated_at
        )
        SELECT
            id, book_id, seller_id, listing_type, price, condition, notes, status,
            exchange_for, moderated_by, moderated_at, moderation_note, views, created_at, updated_at
        FROM listings;
        DROP TABLE listings;
        ALTER TABLE listings_new RENAME TO listings;
        """)

    sync_seed_data(conn)
    conn.commit()
    if close_conn:
        conn.close()


if __name__ == "__main__":
    init_db()

