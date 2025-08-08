from config.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    ver = conn.execute(text("SELECT VERSION()")).scalar()
    who = conn.execute(text("SELECT CURRENT_USER()")).scalar()
    db  = conn.execute(text("SELECT DATABASE()")).scalar()
    ok  = conn.execute(text("SELECT 1")).scalar()
    print("version:", ver)
    print("user:", who)
    print("db:", db)
    print("select1:", ok)
