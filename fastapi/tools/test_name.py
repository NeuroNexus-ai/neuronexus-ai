# Path from repo root: fastapi\tools\test_name.py
import base64, json
from pathlib import Path
from tkinter import Tk, filedialog

# اخفي نافذة Tk الرئيسية
Tk().withdraw()

# افتح نافذة اختيار ملف
file_path = filedialog.askopenfilename(
    title="اختر ملف للرفع",
    filetypes=[("All Files", "*.*")]
)

if not file_path:
    print("لم يتم اختيار أي ملف")
    exit()

path = Path(file_path)
data = path.read_bytes()
b64 = base64.b64encode(data).decode("utf-8")

# حدد prefix حسب الامتداد
ext = path.suffix.lower()
if ext == ".png":
    prefix = "data:image/png;base64,"
elif ext in (".jpg", ".jpeg"):
    prefix = "data:image/jpeg;base64,"
elif ext == ".pdf":
    prefix = "data:application/pdf;base64,"
elif ext == ".wav":
    prefix = "data:audio/wav;base64,"
else:
    prefix = "data:application/octet-stream;base64,"

payload = {"content_b64": prefix + b64}

# اطبع JSON مرتب
print(json.dumps(payload, indent=2, ensure_ascii=False))