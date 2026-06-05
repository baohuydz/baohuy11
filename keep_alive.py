import logging
from flask import Flask
from threading import Thread

# Vô hiệu hóa log chi tiết của Flask để tránh làm rác terminal trên Render
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "Hệ thống Shop Liên Quân đang hoạt động ổn định 24/7!", 200

def run():
    # Render chỉ định cổng qua biến môi trường PORT, mặc định chạy cổng 8080 nếu chạy local
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
