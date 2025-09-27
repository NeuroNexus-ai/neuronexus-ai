# app/main.py

from fastapi import FastAPI
from app.db import Base, engine   # 👈 استورد Base و engine من db.py

# أنشئ تطبيق FastAPI
app = FastAPI()

# ⚡ استدعاء إنشاء الجداول (مرة وحدة عند بدء التشغيل)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
