# 프로젝트에 필요한 패키지 한 번에 설치 (권장)
python -m pip install -U "fastapi[standard]" "sqlalchemy>=2.0" pymysql python-dotenv python-multipart aiofiles
# 실행 예시
# uvicorn main:app --reload

uv init
# uv(피피엠 대체)로 한 번에 추가 — 런타임 의존성
uv add "fastapi[standard]" "sqlalchemy>=2.0" pymysql python-dotenv python-multipart aiofiles
uv add fastapi --extra standard
# (선택) 개발용 도구들
uv add -D ruff black mypy pytest pytest-asyncio httpx

# 실행 예시
uv run uvicorn main:app --reload

# ✅ FastAPI 이미지 갤러리 × MariaDB 연동 – 기초부터 끝까지 (한 번에 복붙용)

────────────────────────────────────────────────────────────────────────
[0] SQL: DB/유저/테이블 만들기 (HeidiSQL의 쿼리 탭에서 순서대로 실행)
────────────────────────────────────────────────────────────────────────
-- 0-1) 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS image_db
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 0-2) 로컬 전용 사용자(이미 있다면 ALTER USER로 비번만 변경)
CREATE USER IF NOT EXISTS 'image_user'@'localhost' IDENTIFIED BY '비밀번호';
GRANT ALL PRIVILEGES ON image_db.* TO 'image_user'@'localhost';
FLUSH PRIVILEGES;

-- 0-3) 테이블 생성
USE image_db;
CREATE TABLE IF NOT EXISTS `uploads` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `txt` VARCHAR(255) NOT NULL,
  `filename` VARCHAR(255) NOT NULL,
  `path` VARCHAR(500) NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (옵션) 동작 확인용 샘플 1건
INSERT INTO uploads (txt, filename, path)
VALUES ('테스트 업로드', 'sample-uuid.png', 'uploaded_images/sample-uuid.png');

SELECT * FROM uploads ORDER BY id DESC LIMIT 3;


────────────────────────────────────────────────────────────────────────
[1] 프로젝트 디렉터리 구조 (필요 폴더/파일 만들기)
────────────────────────────────────────────────────────────────────────
your-project/ 
├─ main.py
├─ .env
├─ .gitignore
├─ config/
│  ├─ __init__.py
│  ├─ info.py
│  └─ db.py
├─ controller/
│  ├─ __init__.py
│  └─ root.py
├─ service/
│  ├─ __init__.py
│  ├─ models.py
│  ├─ app02.py
│  └─ app_gallery.py
├─ static/
│  └─ index.html
└─ uploaded_images/        # (비어 있어도 됨, 업로드 저장 폴더)

# 패키지 디렉터리(config/controller/service)는 __init__.py(빈 파일) 반드시 포함
# 뭔지 모르겠지만 안해도 작동함 뭐임?


────────────────────────────────────────────────────────────────────────
[2] .gitignore / .env
────────────────────────────────────────────────────────────────────────
# .gitignore
.env
__pycache__/
*.pyc

# .env (비밀번호는 원문 그대로, 특수문자 인코딩 불필요)
DB_USER=image_user
DB_PASS=여기에_비밀번호
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=image_db


────────────────────────────────────────────────────────────────────────
[3] 의존성 설치 (둘 중 택1)
────────────────────────────────────────────────────────────────────────
# (A) pip
python -m pip install -U "fastapi[standard]" "sqlalchemy>=2.0" pymysql python-dotenv python-multipart aiofiles

# (B) uv
uv add "fastapi[standard]" "sqlalchemy>=2.0" pymysql python-dotenv python-multipart aiofiles


────────────────────────────────────────────────────────────────────────
[4] 코드 파일 전체
────────────────────────────────────────────────────────────────────────
# config/info.py
api_config = {
  "title": "UV API",
  "version": "0.0.1",
  "docs_url": "/api_docs",
  "redoc_url": None,
}

# config/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL

load_dotenv()

DB_USER = os.getenv("DB_USER", "image_user")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "image_db")

url = URL.create(
    "mysql+pymysql",
    username=DB_USER,
    password=DB_PASS,   # .env 원문 그대로
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)

engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# controller/root.py
from service.app02 import study02
from service.app_gallery import study_gallery
apps = [study02, study_gallery]

# service/models.py
from sqlalchemy import Column, Integer, String, DateTime, func
from config.db import Base

class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, index=True)
    txt = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    path = Column(String(500))
    created_at = Column(DateTime, server_default=func.current_timestamp())

# service/app02.py  (업로드 + DB INSERT + 파일 읽기)
from fastapi import Form, File, UploadFile, Depends
from fastapi.responses import FileResponse
from typing import Annotated
import os, shutil, mimetypes
from uuid import uuid4

from sqlalchemy.orm import Session
from config.db import get_db
from service.models import Upload

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get(txt: str):
    return {"result": txt}

def post(
    txt: Annotated[str, Form(...)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
    fileName = f"{uuid4().hex}.{ext}"
    filePath = os.path.join(UPLOAD_DIR, fileName)

    with open(filePath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    row = Upload(txt=txt, filename=fileName, path=filePath)
    db.add(row)
    db.commit()
    db.refresh(row)

    return {"id": row.id, "result": txt, "filename": fileName, "path": filePath}

def read(fileName: str):
    filePath = os.path.join(UPLOAD_DIR, fileName)
    mediaType, _ = mimetypes.guess_type(filePath)
    headers = {"Content-Disposition": f"inline; filename='{fileName}'"}
    return FileResponse(path=filePath, filename=fileName, media_type=mediaType or "application/octet-stream", headers=headers)

study02 = {
  "prefix": "/s2",
  "tags": ["CRUD 2 연습"],
  "urls": [
    {"methods": ["GET"],  "path": "/",     "summary": "기본 조회", "description": "CRUD 기본 정보를 조회합니다.", "endpoint": get},
    {"methods": ["POST"], "path": "/",     "summary": "데이터 수정", "description": "이미지 업로드 + DB 저장",    "endpoint": post},
    {"methods": ["GET"],  "path": "/read", "summary": "파일 읽기", "description": "저장된 파일을 읽어옵니다.",     "endpoint": read},
  ]
}

# service/app_gallery.py  (갤러리 + 단건/다건 삭제 + 라이트박스)
import os
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from config.db import get_db
from service.models import Upload

UPLOAD_DIR = "uploaded_images"

def gallery(db: Session = Depends(get_db)):
    rows = db.query(Upload).order_by(Upload.id.desc()).limit(100).all()

    cards = []
    for r in rows:
        cards.append(f"""
        <div class="card" data-id="{r.id}">
          <input type="checkbox" class="sel" data-id="{r.id}" title="선택">
          <button class="del" title="삭제" aria-label="삭제" data-id="{r.id}">🗑</button>
          <img src="/uploads/{r.filename}" alt="{r.txt}">
          <div class="meta">
            <p>{r.txt}</p>
            <small>{r.created_at}</small>
          </div>
        </div>
        """)

    html = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Image Library</title>
<style>
  body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;padding:20px;background:#f7f7f7}}
  h1{{margin:0 0 16px}}
  .toolbar{{display:flex;gap:12px;align-items:center;margin:0 0 14px}}
  .toolbar button{{padding:8px 12px;border:none;border-radius:8px;background:#ef4444;color:#fff;cursor:pointer}}
  .toolbar button:disabled{{opacity:.5;cursor:not-allowed}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}}
  .card{{position:relative;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
  .card img{{width:100%;height:160px;object-fit:cover;display:block;cursor:pointer}}
  .card .meta{{padding:10px}}
  .card p{{margin:0 0 6px;font-weight:600}}
  .card small{{color:#666}}
  .card .del{{position:absolute;top:8px;right:8px;background:rgba(0,0,0,.6);color:#fff;border:none;border-radius:8px;cursor:pointer;padding:4px 8px}}
  .card .del:hover{{background:rgba(0,0,0,.85)}}
  .card .sel{{position:absolute;top:10px;left:10px;width:18px;height:18px;accent-color:#3b82f6;}}
  /* Lightbox */
  .lightbox{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:1000}}
  .lightbox.hidden{{display:none}}
  .lightbox .backdrop{{position:absolute;inset:0;background:rgba(0,0,0,.7)}}
  .lightbox img{{position:relative;max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.4)}}
  .lightbox button{{position:absolute;top:16px;right:16px;font-size:24px;line-height:1;background:#000;color:#fff;border:none;border-radius:8px;padding:6px 10px;cursor:pointer;opacity:.85}}
  .lightbox button:hover{{opacity:1}}
</style>
</head><body>
<h1>📚 Image Library</h1>

<div class="toolbar">
  <label><input type="checkbox" id="sel-all"> 전체선택</label>
  <button id="del-selected" disabled>선택삭제</button>
</div>

<div class="grid">
{(''.join(cards)) or '<p>아직 업로드가 없습니다.</p>'}
</div>

<!-- Lightbox overlay -->
<div id="lb" class="lightbox hidden" aria-modal="true" role="dialog">
  <div class="backdrop" aria-hidden="true"></div>
  <img id="lb-img" alt="">
  <button id="lb-close" aria-label="닫기">×</button>
</div>

<script>
  // 선택 상태 관리
  const selected = new Set();
  const grid = document.querySelector('.grid');
  const btnDelSelected = document.getElementById('del-selected');
  const selAll = document.getElementById('sel-all');

  function refreshToolbar() {{
    btnDelSelected.disabled = selected.size === 0;
  }}

  // 개별 체크박스 토글
  grid?.addEventListener('change', (e) => {{
    const cb = e.target.closest('.sel');
    if (!cb) return;
    const id = cb.dataset.id;
    if (cb.checked) selected.add(id); else selected.delete(id);
    refreshToolbar();
  }});

  // 전체선택 토글
  selAll?.addEventListener('change', () => {{
    const cbs = document.querySelectorAll('.card .sel');
    selected.clear();
    cbs.forEach(cb => {{
      cb.checked = selAll.checked;
      if (selAll.checked) selected.add(cb.dataset.id);
    }});
    refreshToolbar();
  }});

  // 선택삭제
  btnDelSelected?.addEventListener('click', async () => {{
    if (selected.size === 0) return;
    if (!confirm(`선택된 ${{selected.size}}개를 삭제할까요?`)) return;
    const ids = Array.from(selected).map(x => parseInt(x, 10));
    const res = await fetch('/gallery/bulk-delete', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ ids }})
    }});
    if (!res.ok) {{
      const msg = await res.text().catch(() => '');
      alert('삭제 실패\\n' + msg);
      return;
    }}
    const data = await res.json();
    (data.deleted_ids || []).forEach(id => {{
      document.querySelector(`.card[data-id="${{id}}"]`)?.remove();
    }});
    selected.clear();
    selAll.checked = false;
    refreshToolbar();
    if ((data.missing_ids || []).length) {{
      alert('존재하지 않거나 이미 삭제된 항목: ' + data.missing_ids.join(', '));
    }}
  }});

  // 단건 삭제 버튼
  document.addEventListener('click', async (e) => {{
    const btn = e.target.closest('.del');
    if (!btn) return;
    const id = btn.dataset.id;
    if (!confirm('이 이미지를 삭제할까요?')) return;
    const res = await fetch(`/gallery/${{id}}`, {{ method: 'DELETE' }});
    if (res.ok) {{
      document.querySelector(`.card[data-id="${{id}}"]`)?.remove();
      selected.delete(String(id));
      refreshToolbar();
    }} else {{
      const msg = await res.text().catch(() => '');
      alert('삭제 실패\\n' + msg);
    }}
  }});

  // 라이트박스
  document.addEventListener('click', (e) => {{
    const img = e.target.closest('.card img');
    if (img) {{
      openLightbox(img.getAttribute('src'), img.getAttribute('alt') || 'image');
      return;
    }}
    if (e.target.id === 'lb-close' || e.target.classList.contains('backdrop')) closeLightbox();
  }});
  document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') closeLightbox(); }});
  function openLightbox(src, alt) {{
    const lb = document.getElementById('lb');
    const lbImg = document.getElementById('lb-img');
    lbImg.src = src; lbImg.alt = alt; lb.classList.remove('hidden');
  }}
  function closeLightbox() {{
    const lb = document.getElementById('lb');
    const lbImg = document.getElementById('lb-img');
    lbImg.src = ''; lb.classList.add('hidden');
  }}
</script>
</body></html>"""
    return HTMLResponse(html)

def delete_upload(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Upload, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    file_path = row.path if row.path else os.path.join(UPLOAD_DIR, row.filename)
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    db.delete(row)
    db.commit()
    return JSONResponse({"ok": True, "deleted_id": item_id})

class BulkDeleteIn(BaseModel):
    ids: list[int]

def bulk_delete(payload: BulkDeleteIn, db: Session = Depends(get_db)):
    ids = payload.ids or []
    if not ids:
        raise HTTPException(status_code=400, detail="ids is empty")
    deleted_ids, missing_ids = [], []
    for _id in ids:
        row = db.get(Upload, _id)
        if not row:
            missing_ids.append(_id); continue
        file_path = row.path if row.path else os.path.join(UPLOAD_DIR, row.filename)
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        db.delete(row); deleted_ids.append(_id)
    db.commit()
    return JSONResponse({"ok": True, "deleted_ids": deleted_ids, "missing_ids": missing_ids})

study_gallery = {
  "prefix": "/gallery",
  "tags": ["Library"],
  "urls": [
    {"methods": ["GET"],    "path": "/",          "summary": "이미지 갤러리", "description": "DB 업로드 목록 카드 그리드(+라이트박스, 선택 삭제)", "endpoint": gallery},
    {"methods": ["DELETE"], "path": "/{item_id}", "summary": "이미지 삭제(단건)", "description": "파일과 DB 레코드를 함께 삭제",             "endpoint": delete_upload},
    {"methods": ["POST"],   "path": "/bulk-delete","summary": "이미지 삭제(다건)", "description": "여러 ID 일괄 삭제",                       "endpoint": bulk_delete},
  ]
}

# static/index.html (업로드 폼 + 드래그&드롭 + 미리보기 + AJAX + 갤러리 버튼 /gallery/ 로 통일)
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>이미지 업로드</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
  <header class="max-w-3xl mx-auto px-4 pt-10">
    <h1 class="text-3xl font-bold tracking-tight text-slate-900">📤 이미지 업로드</h1>
    <p class="text-slate-600 mt-1">텍스트와 이미지를 업로드하면 <a href="/gallery/" class="underline hover:no-underline text-blue-600">갤러리</a>에서 확인할 수 있어요.</p>
  </header>

  <main class="max-w-3xl mx-auto px-4 py-8">
    <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-200 p-6">
      <div class="mb-6">
        <h2 class="text-lg font-semibold text-slate-900">요청 내용</h2>
        <p class="text-sm text-slate-500 mt-1">이미지는 PNG/JPG/WebP 권장, 10MB 이하</p>
      </div>

      <form id="uploadForm" action="/s2/" method="post" enctype="multipart/form-data" class="space-y-5">
        <div>
          <label for="txt" class="block text-sm font-medium text-slate-700">설명(텍스트)</label>
          <input id="txt" name="txt" type="text" placeholder="예) 제주도 바다"
                 class="mt-1 w-full rounded-xl border-slate-300 focus:border-blue-500 focus:ring-blue-500">
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">이미지 파일</label>
          <div id="dropzone"
               class="relative flex flex-col items-center justify-center px-6 py-10 border-2 border-dashed rounded-2xl
                      text-slate-500 hover:text-slate-700 border-slate-300 hover:border-slate-400 cursor-pointer
                      transition-colors bg-slate-50/60">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mb-2" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M3 15l4-4a3 3 0 014 0l1 1 3-3a3 3 0 014 0l2 2M14 15h6m-3-3v6" />
            </svg>
            <div class="text-center">
              <p class="text-sm"><span class="font-semibold">클릭</span>하거나 파일을 <span class="font-semibold">여기로 드래그</span>하세요</p>
              <p class="text-xs text-slate-400 mt-1">PNG, JPG, JPEG, WEBP • 최대 10MB</p>
            </div>
            <input id="file" name="file" type="file" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" />
          </div>

          <div id="previewWrap" class="hidden mt-3">
            <div class="flex items-center gap-3">
              <img id="previewImg" alt="미리보기" class="w-28 h-28 object-cover rounded-xl ring-1 ring-slate-200">
              <div class="text-sm">
                <p id="fileName" class="font-medium text-slate-800"></p>
                <p id="fileSize" class="text-slate-500"></p>
                <button id="clearBtn" type="button"
                        class="mt-2 inline-flex items-center gap-1 text-slate-600 hover:text-slate-800">
                  선택 해제
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <button id="submitBtn" type="submit"
                  class="inline-flex items-center justify-center px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium
                         hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50">
            업로드
          </button>
          <button type="button" onclick="window.location.href='/gallery/'"
                  class="inline-flex items-center justify-center px-5 py-2.5 rounded-xl bg-slate-700 text-white font-medium
                         hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-500">
            갤러리 열기 →
          </button>
        </div>
      </form>

      <div id="result" class="mt-6 hidden">
        <div class="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
          <p class="text-sm text-slate-700"><span class="font-semibold">성공!</span> 업로드가 완료되었습니다.</p>
          <div class="text-sm text-slate-600 mt-2 space-y-1">
            <div>파일명: <code id="resName" class="text-slate-800"></code></div>
            <div>읽기 링크: <a id="resLink" href="#" target="_blank" class="text-blue-600 underline">열기</a></div>
            <div>갤러리: <a href="/gallery/" class="text-blue-600 underline">/gallery/</a></div>
          </div>
        </div>
      </div>

      <div id="toast" class="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 hidden">
        <div class="bg-slate-900 text-white px-4 py-2 rounded-full shadow-lg text-sm">업로드 중...</div>
      </div>
    </div>
  </main>

  <script>
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('file');
    const dropzone = document.getElementById('dropzone');
    const previewWrap = document.getElementById('previewWrap');
    const previewImg = document.getElementById('previewImg');
    const fileNameEl = document.getElementById('fileName');
    const fileSizeEl = document.getElementById('fileSize');
    const clearBtn = document.getElementById('clearBtn');
    const submitBtn = document.getElementById('submitBtn');
    const resultBox = document.getElementById('result');
    const resName = document.getElementById('resName');
    const resLink = document.getElementById('resLink');
    const toast = document.getElementById('toast');
    const MAX_SIZE = 10 * 1024 * 1024;

    function handleFiles(files) {
      const f = files && files[0];
      if (!f) return;
      if (!f.type.startsWith('image/')) { alert('이미지 파일을 선택하세요.'); return; }
      if (f.size > MAX_SIZE) { alert('파일 용량은 10MB 이하여야 합니다.'); return; }
      const reader = new FileReader();
      reader.onload = e => {
        previewImg.src = e.target.result;
        previewWrap.classList.remove('hidden');
        fileNameEl.textContent = f.name;
        fileSizeEl.textContent = (f.size/1024/1024).toFixed(2) + ' MB';
      };
      reader.readAsDataURL(f);
    }
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
    ['dragenter','dragover'].forEach(evt =>
      dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('ring-2','ring-blue-400'); })
    );
    ['dragleave','drop'].forEach(evt =>
      dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('ring-2','ring-blue-400'); })
    );
    dropzone.addEventListener('drop', e => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length) {
        fileInput.files = dt.files;
        handleFiles(dt.files);
      }
    });
    clearBtn.addEventListener('click', () => {
      fileInput.value = '';
      previewImg.src = '';
      previewWrap.classList.add('hidden');
    });
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const txt = form.txt.value.trim();
      const f = fileInput.files[0];
      if (!txt) return alert('설명을 입력하세요.');
      if (!f) return alert('이미지 파일을 선택하세요.');
      submitBtn.disabled = true;
      toast.classList.remove('hidden');
      try {
        const fd = new FormData();
        fd.append('txt', txt);
        fd.append('file', f);
        const res = await fetch('/s2/', { method: 'POST', body: fd });
        if (!res.ok) throw new Error('업로드 실패');
        const data = await res.json();
        resultBox.classList.remove('hidden');
        resName.textContent = data.filename || '(이름 없음)';
        const link = `/s2/read?fileName=${encodeURIComponent(data.filename)}`;
        resLink.href = link;
        form.reset();
        previewWrap.classList.add('hidden');
        // window.location.href = '/gallery/';  // 자동 이동 원하면 주석 해제
      } catch (err) {
        console.error(err);
        alert('업로드 중 오류가 발생했습니다.');
      } finally {
        submitBtn.disabled = false;
        toast.classList.add('hidden');
      }
    });
  </script>
</body>
</html>

# main.py  (정적 서빙 + 라우터 등록)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import info
from controller import root

app = FastAPI(**info.api_config)

# 루트의 study dict들을 라우터로 변환/등록
from fastapi import APIRouter
for link in root.apps:
    route = APIRouter(prefix=link["prefix"], tags=link["tags"])
    for item in link["urls"]:
        route.add_api_route(**item)
    app.include_router(route)

# 정적/업로드 서빙 (구체적인 경로 먼저)
app.mount("/uploads", StaticFiles(directory="uploaded_images"), name="uploads")
app.mount("/", StaticFiles(directory="static", html=True), name="static")


────────────────────────────────────────────────────────────────────────
[5] 실행 & 테스트
────────────────────────────────────────────────────────────────────────
# 실행 (둘 중 택1)
uv run uvicorn main:app --reload
# 또는
uvicorn main:app --reload

# 브라우저에서 확인
http://localhost:8000/          # 업로드 폼
http://localhost:8000/gallery/  # 갤러리
http://localhost:8000/api_docs  # Swagger UI

# 업로드 후
SELECT * FROM uploads ORDER BY id DESC LIMIT 5;  -- DB에서도 확인
# 정적 파일 직접 확인
http://localhost:8000/uploads/<응답의 filename>
