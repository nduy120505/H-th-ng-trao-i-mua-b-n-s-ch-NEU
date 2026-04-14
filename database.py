"""
database.py
===========
Quáº£n lĂ½ káº¿t ná»‘i SQLite, Ä‘á»‹nh nghÄ©a schema vĂ  seed dá»¯ liá»‡u máº«u
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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Káº¿t ná»‘i
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_db_connection() -> sqlite3.Connection:
    """Tráº£ vá» káº¿t ná»‘i SQLite vá»›i row_factory = Row."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Khá»Ÿi táº¡o schema
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SCHEMA_SQL = """
-- Báº£ng ngÆ°á»i dĂ¹ng
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    full_name     TEXT,
    email         TEXT,
    phone         TEXT,
    student_id    TEXT    UNIQUE,
    faculty       TEXT,
    course_year   INTEGER,
    role          TEXT    DEFAULT 'student' CHECK(role IN ('student','admin')),
    bio           TEXT,
    rating_avg    REAL    DEFAULT 0,
    rating_count  INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Báº£ng danh má»¥c sĂ¡ch (phĂ¢n cáº¥p 2 táº§ng)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    slug        TEXT    UNIQUE NOT NULL,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    icon        TEXT    DEFAULT 'đŸ“',
    description TEXT,
    sort_order  INTEGER DEFAULT 0
);

-- Báº£ng thĂ´ng tin sĂ¡ch
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
    cover_emoji  TEXT    DEFAULT 'đŸ“–',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Báº£ng tin Ä‘Äƒng bĂ¡n / trao Ä‘á»•i
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

-- Báº£ng tin nháº¯n giá»¯a ngÆ°á»i dĂ¹ng
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id  INTEGER REFERENCES listings(id)  ON DELETE CASCADE,
    sender_id   INTEGER REFERENCES users(id)     ON DELETE CASCADE,
    receiver_id INTEGER REFERENCES users(id)     ON DELETE CASCADE,
    content     TEXT    NOT NULL,
    is_read     INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Báº£ng yĂªu thĂ­ch
CREATE TABLE IF NOT EXISTS wishlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, listing_id)
);

-- Báº£ng Ä‘Ă¡nh giĂ¡ ngÆ°á»i dĂ¹ng
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    reviewed_id INTEGER REFERENCES users(id)    ON DELETE CASCADE,
    listing_id  INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    rating      INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
"""


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Dá»¯ liá»‡u máº«u
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SEED_CATEGORIES = [
    # Cáº¥p 1
    (1,  "MĂ´n Há»c Äáº¡i CÆ°Æ¡ng",           "dai-cuong",    None, "đŸ“", "CĂ¡c mĂ´n Ä‘áº¡i cÆ°Æ¡ng toĂ n trÆ°á»ng",           1),
    (2,  "Khoa Kinh Táº¿",                "kinh-te",      None, "đŸ“", "SĂ¡ch chuyĂªn ngĂ nh Kinh táº¿ há»c",           2),
    (3,  "Khoa Quáº£n Trá»‹ Kinh Doanh",    "quan-tri",     None, "đŸ’¼", "SĂ¡ch chuyĂªn ngĂ nh Quáº£n trá»‹ kinh doanh",   3),
    (4,  "Khoa TĂ i ChĂ­nh â€“ NgĂ¢n HĂ ng",  "tai-chinh",    None, "đŸ¦", "SĂ¡ch chuyĂªn ngĂ nh TĂ i chĂ­nh â€“ NgĂ¢n hĂ ng", 4),
    (5,  "Khoa Káº¿ ToĂ¡n â€“ Kiá»ƒm ToĂ¡n",    "ke-toan",      None, "đŸ“’", "SĂ¡ch chuyĂªn ngĂ nh Káº¿ toĂ¡n",               5),
    (6,  "Khoa Há»‡ Thá»‘ng ThĂ´ng Tin",     "httt",         None, "đŸ’»", "SĂ¡ch chuyĂªn ngĂ nh Há»‡ thá»‘ng thĂ´ng tin",    6),
    (7,  "Khoa Marketing",              "marketing",    None, "đŸ“¢", "SĂ¡ch chuyĂªn ngĂ nh Marketing",             7),
    (8,  "Khoa Luáº­t Kinh Táº¿",           "luat",         None, "â–ï¸", "SĂ¡ch chuyĂªn ngĂ nh Luáº­t kinh táº¿",          8),
    (9,  "Khoa Báº¥t Äá»™ng Sáº£n",           "bat-dong-san", None, "đŸ ", "SĂ¡ch chuyĂªn ngĂ nh Báº¥t Ä‘á»™ng sáº£n",          9),
    (10, "Khoa Thá»‘ng KĂª",               "thong-ke",     None, "đŸ“ˆ", "SĂ¡ch chuyĂªn ngĂ nh Thá»‘ng kĂª",              10),
    # Cáº¥p 2 â€“ con cá»§a Äáº¡i cÆ°Æ¡ng (parent_id=1)
    (11, "ToĂ¡n Cao Cáº¥p & XSTK",         "toan",          1,  "đŸ”¢", "ToĂ¡n cao cáº¥p, XĂ¡c suáº¥t thá»‘ng kĂª",         1),
    (12, "Kinh Táº¿ ChĂ­nh Trá»‹",           "ktct",          1,  "đŸ›ï¸", "Kinh táº¿ chĂ­nh trá»‹ MĂ¡c-LĂªnin",              2),
    (13, "Triáº¿t Há»c MĂ¡c-LĂªnin",         "triet-hoc",     1,  "đŸ¤”", "Triáº¿t há»c MĂ¡c-LĂªnin",                     3),
    (14, "PhĂ¡p Luáº­t Äáº¡i CÆ°Æ¡ng",         "phap-luat",     1,  "đŸ“œ", "PhĂ¡p luáº­t Ä‘áº¡i cÆ°Æ¡ng",                     4),
    (15, "Tiáº¿ng Anh",                   "tieng-anh",     1,  "đŸŒ", "Tiáº¿ng Anh thÆ°Æ¡ng máº¡i, IELTS, TOEIC",      5),
    (16, "Tin Há»c Äáº¡i CÆ°Æ¡ng",           "tin-hoc",       1,  "đŸ–¥ï¸", "Tin há»c Ä‘áº¡i cÆ°Æ¡ng, Office",                6),
    (17, "Lá»‹ch Sá»­ Äáº£ng",               "ls-dang",       1,  "đŸ‡»đŸ‡³", "Lá»‹ch sá»­ Äáº£ng Cá»™ng sáº£n Viá»‡t Nam",          7),
    (18, "TÆ° TÆ°á»Ÿng Há»“ ChĂ­ Minh",       "tthcm",         1,  "â­",  "TÆ° tÆ°á»Ÿng Há»“ ChĂ­ Minh",                   8),
    # Cáº¥p 2 â€“ con cá»§a Kinh táº¿ (parent_id=2)
    (19, "Kinh Táº¿ Vi MĂ´",              "vi-mo",          2,  "đŸ”", "Kinh táº¿ vi mĂ´",                           1),
    (20, "Kinh Táº¿ VÄ© MĂ´",              "vi-mo-2",        2,  "đŸŒ", "Kinh táº¿ vÄ© mĂ´",                           2),
    (21, "Kinh Táº¿ Quá»‘c Táº¿",            "kt-quoc-te",     2,  "âœˆï¸", "Kinh táº¿ quá»‘c táº¿",                         3),
    # Cáº¥p 2 â€“ con cá»§a TĂ i chĂ­nh (parent_id=4)
    (22, "TĂ i ChĂ­nh Doanh Nghiá»‡p",     "tcdn",           4,  "đŸ’°", "TĂ i chĂ­nh doanh nghiá»‡p",                  1),
    (23, "NgĂ¢n HĂ ng ThÆ°Æ¡ng Máº¡i",       "nhtm",           4,  "đŸ§", "Nghiá»‡p vá»¥ ngĂ¢n hĂ ng",                     2),
    (24, "Thá»‹ TrÆ°á»ng Chá»©ng KhoĂ¡n",     "chung-khoan",    4,  "đŸ“‰", "Chá»©ng khoĂ¡n & Ä‘áº§u tÆ°",                    3),
]

SEED_BOOKS = [
    ("GiĂ¡o TrĂ¬nh ToĂ¡n Cao Cáº¥p â€“ Táº­p 1",       "Nguyá»…n ÄĂ¬nh TrĂ­",     "9786045891001", "NXB GiĂ¡o Dá»¥c",       2022, "TĂ¡i báº£n láº§n 5", 11, None,              1, "MATH101", "Äáº¡i sá»‘ tuyáº¿n tĂ­nh vĂ  giáº£i tĂ­ch",            "đŸ“", None),
    ("GiĂ¡o TrĂ¬nh ToĂ¡n Cao Cáº¥p â€“ Táº­p 2",       "Nguyá»…n ÄĂ¬nh TrĂ­",     "9786045891002", "NXB GiĂ¡o Dá»¥c",       2022, "TĂ¡i báº£n láº§n 5", 11, None,              1, "MATH102", "TĂ­ch phĂ¢n vĂ  phÆ°Æ¡ng trĂ¬nh vi phĂ¢n",         "đŸ“", None),
    ("XĂ¡c Suáº¥t Thá»‘ng KĂª",                      "ÄĂ o Há»¯u Há»“",          "9786045892001", "NXB ÄHQG HN",        2021, "Láº§n 3",         11, None,              2, "STAT101", "XĂ¡c suáº¥t thá»‘ng kĂª á»©ng dá»¥ng kinh táº¿",        "đŸ“", None),
    ("Kinh Táº¿ ChĂ­nh Trá»‹ MĂ¡c-LĂªnin",           "Bá»™ GD&ÄT",            "9786045893001", "NXB ChĂ­nh Trá»‹ QG",   2021, "Láº§n 1",         12, None,              1, "KTCT101", "GiĂ¡o trĂ¬nh má»›i 2021",                       "đŸ›ï¸", None),
    ("Triáº¿t Há»c MĂ¡c-LĂªnin",                   "Bá»™ GD&ÄT",            "9786045893002", "NXB ChĂ­nh Trá»‹ QG",   2021, "Láº§n 1",         13, None,              1, "TRHH101", "GiĂ¡o trĂ¬nh triáº¿t há»c chĂ­nh thá»©c",           "đŸ¤”", None),
    ("PhĂ¡p Luáº­t Äáº¡i CÆ°Æ¡ng",                   "Nguyá»…n VÄƒn Äá»™ng",     "9786045894001", "NXB TÆ° PhĂ¡p",        2020, "Láº§n 2",         14, None,              1, "PLDC101", "PhĂ¡p luáº­t Ä‘áº¡i cÆ°Æ¡ng khá»‘i KT",               "đŸ“œ", None),
    ("English for Business Communication",    "Simon Sweeney",       "9780521754491", "Cambridge UP",        2018, "3rd Edition",   15, None,              1, "ENG101",  "Tiáº¿ng Anh thÆ°Æ¡ng máº¡i nĂ¢ng cao",             "đŸŒ", None),
    ("Kinh Táº¿ Vi MĂ´",                         "VÅ© Kim DÅ©ng",         "9786045895001", "NXB Lao Äá»™ng",        2023, "Láº§n 4",         19, "Khoa Kinh Táº¿",    1, "ECO101",  "Kinh táº¿ vi mĂ´ cÆ¡ báº£n vĂ  nĂ¢ng cao",         "đŸ”", None),
    ("Kinh Táº¿ VÄ© MĂ´",                         "N. Gregory Mankiw",   "9780357722527", "Cengage Learning",    2022, "10th Edition",  20, "Khoa Kinh Táº¿",    2, "ECO201",  "Principles of Macroeconomics",              "đŸŒ", None),
    ("Quáº£n Trá»‹ Há»c",                          "Nguyá»…n Thá»‹ LiĂªn Diá»‡p","9786045896001", "NXB Lao Äá»™ng",        2022, "Láº§n 6",          3, "Khoa Quáº£n Trá»‹",   1, "QTKD101", "Quáº£n trá»‹ há»c cÄƒn báº£n",                     "đŸ’¼", None),
    ("Marketing CÄƒn Báº£n",                     "Philip Kotler",       "9780135197035", "Pearson",             2021, "16th Edition",   7, "Khoa Marketing",  2, "MKT101",  "Principles of Marketing",                  "đŸ“¢", None),
    ("TĂ i ChĂ­nh Doanh Nghiá»‡p",                "Tráº§n Ngá»c ThÆ¡",       "9786045897001", "NXB Thá»‘ng KĂª",        2022, "Láº§n 3",         22, "Khoa TC-NH",      2, "TCDN201", "Corporate Finance cÆ¡ báº£n vĂ  nĂ¢ng cao",     "đŸ’°", None),
    ("Káº¿ ToĂ¡n TĂ i ChĂ­nh",                     "NgĂ´ Tháº¿ Chi",         "9786045898001", "NXB TĂ i ChĂ­nh",       2023, "Láº§n 5",          5, "Khoa Káº¿ ToĂ¡n",    2, "KT201",   "Káº¿ toĂ¡n tĂ i chĂ­nh doanh nghiá»‡p",           "đŸ“’", None),
    ("CÆ¡ Sá»Ÿ Dá»¯ Liá»‡u",                         "Nguyá»…n BĂ¡ TÆ°á»ng",     "9786045899001", "NXB ÄHQG HN",         2021, "Láº§n 2",          6, "Khoa HTTT",       1, "IT201",   "CÆ¡ sá»Ÿ dá»¯ liá»‡u quan há»‡",                   "đŸ’»", None),
    ("Luáº­t Kinh Táº¿",                           "DÆ°Æ¡ng ÄÄƒng Huá»‡",      "9786045900001", "NXB TÆ° PhĂ¡p",        2022, "Láº§n 3",          8, "Khoa Luáº­t",       1, "LAW201",  "Luáº­t kinh táº¿ dĂ nh cho sinh viĂªn NEU",      "â–ï¸", None),
    ("NguyĂªn LĂ½ Káº¿ ToĂ¡n",                     "Nguyá»…n VÄƒn CĂ´ng",     "9786045901001", "NXB TĂ i ChĂ­nh",       2021, "Láº§n 4",          5, "Khoa Káº¿ ToĂ¡n",    1, "KT101",   "NguyĂªn lĂ½ káº¿ toĂ¡n cÆ¡ báº£n",                "đŸ“’", None),
    ("Thá»‹ TrÆ°á»ng Chá»©ng KhoĂ¡n",                "Phan Thá»‹ BĂ­ch Nguyá»‡t","9786045902001", "NXB TĂ i ChĂ­nh",       2023, "Láº§n 2",         24, "Khoa TC-NH",      3, "FIN301",  "PhĂ¢n tĂ­ch vĂ  Ä‘áº§u tÆ° chá»©ng khoĂ¡n",         "đŸ“‰", None),
    ("Quáº£n Trá»‹ Marketing",                    "Philip Kotler",       "9780135716953", "Pearson",             2022, "16th Edition",   7, "Khoa Marketing",  3, "MKT301",  "Marketing Management",                     "đŸ“¢", None),
]

SEED_USERS = [
    ("sv001", "123456", "Nguyá»…n VÄƒn An",    "an.nv@st.neu.edu.vn",    "0912345678", "SV2021001", "Khoa Kinh Táº¿",              2021),
    ("sv002", "123456", "Tráº§n Thá»‹ BĂ¬nh",    "binh.tt@st.neu.edu.vn",  "0923456789", "SV2022002", "Khoa Quáº£n Trá»‹ Kinh Doanh",  2022),
    ("sv003", "123456", "LĂª Quang CÆ°á»ng",   "cuong.lq@st.neu.edu.vn", "0934567890", "SV2020003", "Khoa TĂ i ChĂ­nh â€“ NgĂ¢n HĂ ng",2020),
]

# (book_id, user_idx 0/1/2, type, price, condition, notes, exchange_for, views)
SEED_LISTINGS = [
    (1,  0, "sell",     45000,  "like_new", "CĂ²n má»›i 95%, khĂ´ng ghi chĂº",               None,                  12),
    (2,  0, "sell",     35000,  "good",     "CĂ³ gáº¡ch chĂ¢n má»™t sá»‘ chá»—",                  None,                  8),
    (3,  1, "exchange", 0,      "like_new", "Äá»•i láº¥y sĂ¡ch Kinh táº¿ vi mĂ´",               "Kinh Táº¿ Vi MĂ´",       5),
    (4,  1, "sell",     120000, "new",      "Má»›i 100%, cĂ²n seal",                       None,                  20),
    (5,  2, "free",     0,      "fair",     "Táº·ng miá»…n phĂ­, tá»± Ä‘áº¿n láº¥y",               None,                  3),
    (6,  2, "sell",     80000,  "good",     "SĂ¡ch báº£n tiáº¿ng Anh chĂ­nh hĂ£ng",            None,                  15),
    (7,  0, "sell",     55000,  "like_new", "Há»c xong khĂ´ng dĂ¹ng ná»¯a",                  None,                  7),
    (8,  1, "sell",     40000,  "good",     "CĂ³ highlight cĂ¡c pháº§n quan trá»ng",         None,                  9),
    (9,  2, "exchange", 0,      "like_new", "Äá»•i láº¥y sĂ¡ch káº¿ toĂ¡n nÄƒm 2",              "Káº¿ ToĂ¡n TĂ i ChĂ­nh",   4),
    (10, 0, "sell",     150000, "new",      "Mua nháº§m khĂ´ng dĂ¹ng, bĂ¡n ráº»",             None,                  18),
]


def init_db() -> None:
    """Táº¡o báº£ng vĂ  seed dá»¯ liá»‡u máº«u náº¿u chÆ°a tá»“n táº¡i."""
    conn = get_db_connection()
    cur  = conn.cursor()

    # Táº¡o báº£ng
    cur.executescript(SCHEMA_SQL)
    ensure_db_schema(conn)

    # Seed danh má»¥c
    cur.executemany(
        "INSERT OR IGNORE INTO categories "
        "(id,name,slug,parent_id,icon,description,sort_order) VALUES (?,?,?,?,?,?,?)",
        SEED_CATEGORIES,
    )

    # Seed sĂ¡ch
    cur.executemany(
        "INSERT OR IGNORE INTO books "
        "(title,author,isbn,publisher,publish_year,edition,"
        " category_id,faculty,course_year,subject_code,description,cover_emoji,cover_image) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        SEED_BOOKS,
    )

    # TĂ i khoáº£n admin
    cur.execute(
        "INSERT OR IGNORE INTO users (username,password_hash,full_name,email,role) "
        "VALUES (?,?,?,?,?)",
        ("admin", generate_password_hash("admin123"),
         "Quáº£n trá»‹ viĂªn NEU", "admin@neu.edu.vn", "admin"),
    )

    # TĂ i khoáº£n sinh viĂªn demo
    for uname, pwd, fname, email, phone, sid, faculty, year in SEED_USERS:
        cur.execute(
            "INSERT OR IGNORE INTO users "
            "(username,password_hash,full_name,email,phone,student_id,faculty,course_year,role) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (uname, generate_password_hash(pwd), fname, email, phone, sid, faculty, year, "student"),
        )

    # Tin Ä‘Äƒng máº«u
    user_ids = [
        cur.execute("SELECT id FROM users WHERE username=?", (u[0],)).fetchone()[0]
        for u in SEED_USERS
    ]
    for book_id, u_idx, ltype, price, cond, notes, exch, views in SEED_LISTINGS:
        cur.execute(
            "INSERT OR IGNORE INTO listings "
            "(book_id,seller_id,listing_type,price,condition,notes,exchange_for,views) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (book_id, user_ids[u_idx], ltype, price, cond, notes, exch, views),
        )

    conn.commit()
    conn.close()
    print("âœ… Database khá»Ÿi táº¡o thĂ nh cĂ´ng!")


def ensure_db_schema(conn: sqlite3.Connection | None = None) -> None:
    """BĂ¡Â»â€¢ sung schema cho database Ă„â€˜ang tĂ¡Â»â€œn tĂ¡ÂºÂ¡i."""
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

    conn.commit()
    if close_conn:
        conn.close()


if __name__ == "__main__":
    init_db()

