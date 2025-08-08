# service/app_gallery.py
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
    if (!confirm(`선택된 ${{selected.size}}개를 삭제할까요?`)) return;  // ← 여기만 수정!
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
    // 삭제된 카드 제거
    (data.deleted_ids || []).forEach(id => {{
      document.querySelector(`.card[data-id="${{id}}"]`)?.remove();
    }});
    // 선택 상태 초기화
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
    deleted_ids = []
    missing_ids = []
    for _id in ids:
        row = db.get(Upload, _id)
        if not row:
            missing_ids.append(_id)
            continue
        file_path = row.path if row.path else os.path.join(UPLOAD_DIR, row.filename)
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            # 파일 삭제 실패해도 DB는 제거
            pass
        db.delete(row)
        deleted_ids.append(_id)
    db.commit()
    return JSONResponse({"ok": True, "deleted_ids": deleted_ids, "missing_ids": missing_ids})

study_gallery = {
  "prefix": "/gallery",
  "tags": ["Library"],
  "urls": [
    {
      "methods": ["GET"],
      "path": "/",
      "summary": "이미지 갤러리",
      "description": "DB의 업로드 목록을 카드 그리드로 표시 (+ 라이트박스, 선택 삭제)",
      "endpoint": gallery,
    },
    {
      "methods": ["DELETE"],
      "path": "/{item_id}",
      "summary": "이미지 삭제(단건)",
      "description": "파일과 DB 레코드를 함께 삭제",
      "endpoint": delete_upload,
    },
    {
      "methods": ["POST"],
      "path": "/bulk-delete",
      "summary": "이미지 삭제(다건)",
      "description": "여러 ID를 받아 파일과 DB 레코드를 일괄 삭제",
      "endpoint": bulk_delete,
    },
  ]
}
