import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Hệ thống Bot Shop Liên Quân đang hoạt động trực tuyến trên Render!"

def run():
    # Nhận PORT động do Render cấp, nếu không có sẽ mặc định chạy 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
