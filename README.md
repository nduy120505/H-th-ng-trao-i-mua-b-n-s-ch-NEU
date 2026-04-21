# NEU Bookstore

San giao dich sach cho sinh vien NEU, xay dung bang Flask + SQLite.

## Chay local

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

Ung dung mac dinh chay tai `http://localhost:5000`.

Tai khoan demo:

| Username | Password | Vai tro |
| --- | --- | --- |
| `admin` | `admin123` | Admin |
| `sv001` | `123456` | Sinh vien |
| `sv002` | `123456` | Sinh vien |
| `sv003` | `123456` | Sinh vien |

## Deploy len Railway

Project da duoc chuan bi san cho Railway voi:

- `requirements.txt`
- `Procfile` dung `gunicorn app:app`
- Ho tro `PORT`, `SECRET_KEY`, `DATABASE_PATH`
- Tu dong init/migrate SQLite khi app khoi dong

### 1. Day code len GitHub

```bash
git init
git add .
git commit -m "Prepare Railway deploy"
git branch -M main
git remote add origin <repo-url>
git push -u origin main
```

### 2. Tao service tren Railway

1. Vao Railway, chon `New Project`.
2. Chon `Deploy from GitHub repo`.
3. Chon repo cua ban.

Railway se tu nhan Python app va chay lenh trong `Procfile`.

### 3. Tao volume de luu SQLite

Neu khong tao volume, file SQLite se mat khi redeploy.

Trong project Railway:

1. Chon `New` -> `Volume`.
2. Gan volume vao service web.
3. Lay mount path, vi du `/data`.

### 4. Them environment variables

Trong service web, them:

```env
SECRET_KEY=mot_chuoi_bi_mat_rat_dai
DATABASE_PATH=/data/neu_bookstore.db
FLASK_DEBUG=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=true
```

`DATABASE_PATH` nen tro vao volume mount path de du lieu khong bi mat.

### 5. Redeploy

Sau khi them volume va env vars, bam `Deploy` lai.

### 6. Mo domain

Railway se cap 1 domain dang:

```text
https://ten-app.up.railway.app
```

Neu muon dung domain rieng:

1. Vao tab `Settings` -> `Domains`
2. Them custom domain
3. Cau hinh DNS theo huong dan cua Railway

## Bien moi truong ho tro

| Bien | Bat buoc | Mo ta |
| --- | --- | --- |
| `PORT` | Khong | Railway tu cap |
| `SECRET_KEY` | Nen co | Khoa session Flask |
| `DATABASE_PATH` | Nen co | Duong dan file SQLite |
| `FLASK_DEBUG` | Khong | De `false` khi production |
| `SMTP_HOST` | Khong | SMTP server de gui mat khau moi khi quen mat khau |
| `SMTP_PORT` | Khong | Cong SMTP, mac dinh `587` |
| `SMTP_USERNAME` | Khong | Tai khoan dang nhap SMTP |
| `SMTP_PASSWORD` | Khong | Mat khau/app password SMTP |
| `SMTP_FROM` | Khong | Dia chi nguoi gui email |
| `SMTP_USE_TLS` | Khong | `true` de dung STARTTLS, `false` de dung SMTP_SSL |

## Luu y production

- SQLite phu hop demo, MVP, noi bo.
- Neu nguoi dung tang nhieu, nen doi sang PostgreSQL.
- Chat hien tai la polling 3 giay, chua phai WebSocket that.

## Cau truc chinh

```text
app.py
database.py
templates/
static/
requirements.txt
Procfile
```
