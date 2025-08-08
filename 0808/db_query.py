# db_query.py
from config.db import SessionLocal
from sqlalchemy import select
from service.models import Upload

def main():
    with SessionLocal() as db:
        rows = db.execute(
            select(Upload).order_by(Upload.id.desc()).limit(3)
        ).scalars().all()

        for r in rows:
            print(r.id, r.txt, r.filename, r.path, r.created_at)
        print("total:", len(rows))

if __name__ == "__main__":
    main()
