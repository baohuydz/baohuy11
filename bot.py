import sqlite3
import logging
import telebot as tele
# Gọi hàm keep_alive từ file keep_alive.py đã tách
from keep_alive import keep_alive

# --- TỰ ĐỘNG KHỞI CHẠY WEB SERVER ĐỂ GIỮ CHẠY 24/7 ---
keep_alive()

# =====================================================================
# 1. CẤU HÌNH HỆ THỐNG BOT
# =====================================================================
BOT_TOKEN = "6367532329:AAGp-dCbkBs6JHeol5X6bvXEUksG6PwnJ58"  # 🔴 Thay Token Bot Telegram của bạn vào đây
ADMIN_ID = 5736655322              # 🔴 Thay ID Chat Telegram của bạn vào đây (Kiểu số)
PRICE_RD = 500                   # Thiết lập giá bán 1 acc ngẫu nhiên (1,000đ)

# Cấu hình thông tin hỗ trợ
TELEGRAM_GROUP_URL = "https://t.me/your_group_or_channel" 
ADMIN_USERNAME = "your_admin_username" # Username Telegram viết liền không dấu @

# Cấu hình log hệ thống để theo dõi lỗi trên Render Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo instance Bot
bot = tele.TeleBot(BOT_TOKEN)


# =====================================================================
# 2. QUẢN LÝ CƠ SỞ DỮ LIỆU (SQLITE TRÊN RENDER)
# =====================================================================
def get_db_connection():
    conn = sqlite3.connect('/tmp/shop_lienquan.db', timeout=15)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_rd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_info TEXT,
            status TEXT DEFAULT 'con_hang'
        )
    ''')
    # BỎ BIN, ACC, NAME - CHỈ GIỮ LẠI QR_FILE_ID ĐỂ LƯU ẢNH SẾP GỬI
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_qr (
            id INTEGER PRIMARY KEY DEFAULT 1,
            qr_file_id TEXT DEFAULT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO config_qr (id, qr_file_id) VALUES (1, NULL)")
    conn.commit()
    conn.close()

# Chạy khởi tạo database
init_db()

def check_user(user_id, username):
    username_clean = username if username else f"User_{user_id}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, 0)", (user_id, username_clean))
        conn.commit()
    conn.close()


# =====================================================================
# 3. GIAO DIỆN VÀ TÍNH NĂNG KHÁCH HÀNG
# =====================================================================
def get_main_menu_keyboard():
    markup = tele.types.InlineKeyboardMarkup(row_width=2)
    btn_buy = tele.types.InlineKeyboardButton("🛒 Mua Acc Ngẫu Nhiên", callback_data="user_buy_rd")
    btn_stock = tele.types.InlineKeyboardButton("📦 Kiểm Tra Kho", callback_data="user_check_stock")
    btn_balance = tele.types.InlineKeyboardButton("💳 Kiểm Tra Số Dư", callback_data="user_check_balance")
    btn_deposit = tele.types.InlineKeyboardButton("💰 Nạp Tiền Vào Ví", callback_data="user_deposit_select")
    btn_support = tele.types.InlineKeyboardButton("📞 Liên Hệ Admin / Hỗ Trợ", callback_data="user_support")
    
    markup.add(btn_buy, btn_stock, btn_balance, btn_deposit)
    markup.add(btn_support)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    check_user(message.from_user.id, message.from_user.username)
    welcome_text = (
        f"🤖 **CHÀO MỪNG BẠN ĐẾN VỚI SHOP LIÊN QUÂN TỰ ĐỘNG**\n"
        f"──────────────────────────\n"
        f"👋 Xin chào, *{message.from_user.first_name}*!\n"
        f"🎯 Hệ thống cung cấp acc Random uy tín, trả acc tự động 24/7.\n\n"
        f"👇 Vui lòng chọn một chức năng dưới menu để bắt đầu:"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


# =====================================================================
# 4. XỬ LÝ LỆNH /addqr - LƯU FILE ẢNH DO SẾP TỰ GỬI LÊN
# =====================================================================
@bot.message_handler(content_types=['photo'])
def handle_admin_qr_photo(message):
    # Kiểm tra quyền Admin
    if message.from_user.id != ADMIN_ID:
        return

    # Kiểm tra xem có kèm chú thích ảnh là /addqr hay không
    caption = message.caption.strip() if message.caption else ""
    if not caption.startswith("/addqr"):
        return

    status_msg = bot.reply_to(message, "⏳ Đang tiến hành lưu ảnh QR code của sếp vào hệ thống...")
    
    try:
        # Lấy trực tiếp file_id từ ảnh gốc sếp gửi
        target_file_id = message.photo[-1].file_id
        
        # Cập nhật duy nhất cột qr_file_id vào Database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE config_qr SET qr_file_id = ? WHERE id = 1", (target_file_id,))
        conn.commit()
        conn.close()
        
        success_text = (
            f"✅ **LƯU ẢNH QR CODE THÀNH CÔNG**\n"
            f"──────────────────────────\n"
            f"ℹ️ _Kể từ bây giờ, khi khách hàng lên đơn nạp, Bot sẽ lấy nguyên vẹn bức ảnh này gửi trực tiếp cho khách quét._"
        )
        bot.edit_message_text(success_text, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Lỗi khi lưu ảnh QR: {e}")
        bot.edit_message_text(f"❌ Có lỗi phát sinh khi lưu tệp ảnh: `{str(e)}`", message.chat.id, status_msg.message_id, parse_mode="Markdown")


# =====================================================================
# 5. LOGIC TRẢ ẢNH QR GỐC CỦA ADMIN KÈM THÔNG TIN ĐƠN NẠP
# =====================================================================
def send_dynamic_qr(chat_id, user_id, username, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT qr_file_id FROM config_qr WHERE id = 1")
    row = cursor.fetchone()
    
    # Tạo yêu cầu nạp tiền vào danh sách chờ phê duyệt
    cursor.execute("INSERT INTO deposit_requests (user_id, username, amount) VALUES (?, ?, ?)", (user_id, username, amount))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()

    memo = f"NAP {request_id}"
    
    # Bắn thông báo về máy Admin kèm nút duyệt nhanh đơn hàng
    admin_markup = tele.types.InlineKeyboardMarkup()
    btn_approve = tele.types.InlineKeyboardButton("✅ Duyệt Ngay", callback_data=f"adm_pub_approve_{request_id}")
    btn_reject = tele.types.InlineKeyboardButton("❌ Hủy Đơn", callback_data=f"adm_pub_reject_{request_id}")
    admin_markup.add(btn_approve, btn_reject)

    bot.send_message(
        ADMIN_ID, 
        f"🔔 **CÓ ĐƠN NẠP TIỀN ĐANG CHỜ DUYỆT (Mã: #{request_id})**\n\n"
        f"👤 Khách hàng: @{username} (ID: `{user_id}`)\n"
        f"💵 Số tiền: **{int(amount):,}đ**\n"
        f"📝 Nội dung sếp cần kiểm tra: `{memo}`\n\n"
        f"Vui lòng check biến động số dư tài khoản trước khi bấm Duyệt!",
        reply_markup=admin_markup, parse_mode="Markdown"
    )

    # Gửi thông tin chuyển khoản cho Khách hàng
    user_text = (
        f"✨ **ĐƠN NẠP TIỀN CỦA BẠN (Mã: #{request_id})** ✨\n"
        f"──────────────────────────\n"
        f"💵 Số tiền: **{int(amount):,} VNĐ**\n"
        f"📝 Nội dung chuyển khoản bắt buộc: `{memo}`\n\n"
        f"📌 **HƯỚNG DẪN CHUYỂN KHOẢN:**\n"
        f"1. Quét mã QR trong ảnh đính kèm để tiến hành chuyển khoản.\n"
        f"2. Ghi chính xác nội dung chuyển khoản là `{memo}` (Không tự ý sửa chữ).\n"
        f"3. Hệ thống sẽ tự động cộng ví cho bạn ngay sau khi Admin phê duyệt đơn hàng!"
    )
    user_markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu Chính", callback_data="user_back_to_main_from_photo"))

    # Kiểm tra xem Admin đã tải ảnh QR nào lên chưa
    if row and row['qr_file_id']:
        # Gửi trực tiếp file ảnh gốc bằng file_id
        bot.send_photo(chat_id, row['qr_file_id'], caption=user_text, reply_markup=user_markup, parse_mode="Markdown")
    else:
        # Nếu chưa có ảnh trong database, thông báo text cho khách đỡ lỗi
        bot.send_message(chat_id, f"⚠️ Shop chưa cập nhật ảnh mã QR nhận tiền.\n\n{user_text}", reply_markup=user_markup, parse_mode="Markdown")

def process_custom_amount(message):
    try:
        amount = float(message.text.strip())
        if amount < 1000:
            bot.reply_to(message, "❌ Số tiền nạp tối thiểu phải từ **1,000đ** trở lên. Vui lòng vào lại Menu để thử lại.")
            return
        username = message.from_user.username if message.from_user.username else f"User_{message.from_user.id}"
        send_dynamic_qr(message.chat.id, message.from_user.id, username, amount)
    except ValueError:
        bot.reply_to(message, "❌ Lỗi định dạng chữ số. Vui lòng nhập số tiền bằng ký tự số (Ví dụ: 50000).")


# =====================================================================
# 6. XỬ LÝ SỰ KIỆN NÚT BẤM (CALLBACK QUERY)
# =====================================================================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    user_id = call.from_user.id
    username = call.from_user.username if call.from_user.username else f"User_{user_id}"
    data = call.data

    # --- PHÂN HỆ KHÁCH HÀNG ---
    if data == "user_back_to_main":
        welcome_text = "🤖 **CHÀO MỪNG BẠN ĐẾN VỚI SHOP LIÊN QUÂN TỰ ĐỘNG**\n──────────────────────────\n👇 Vui lòng chọn một chức năng dưới menu để bắt đầu:"
        bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

    elif data == "user_check_balance":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()['balance']
        conn.close()
        text = f"💳 **THÔNG TIN TÀI KHOẢN CỦA BẠN**\n──────────────────────────\n👤 Tên tài khoản: @{username}\n🆔 ID Telegram: `{user_id}`\n💵 Số dư hiện tại: **{int(balance):,} VNĐ**"
        markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("💰 Nạp Tiền Ngay", callback_data="user_deposit_select")).add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu", callback_data="user_back_to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "user_check_stock":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM stock_rd WHERE status = 'con_hang'")
        count = cursor.fetchone()['total']
        conn.close()
        text = f"📦 **THÔNG TIN KHO HÀNG HIỆN TẠI**\n──────────────────────────\n🏷 Sản phẩm: **Acc Liên Quân Random**\n💵 Giá bán lẻ: **{PRICE_RD:,}đ / acc**\n⚡ Tình trạng kho: Còn **{count}** tài khoản"
        markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("🛒 Mua Liền Tay", callback_data="user_buy_rd")).add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu", callback_data="user_back_to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "user_support":
        text = f"📞 **TRUNG TÂM HỖ TRỢ KHÁCH HÀNG**\n──────────────────────────\n👤 **Admin Chăm Sóc:** @{ADMIN_USERNAME}\n⏰ Thời gian hỗ trợ: 08:00 - 23:00 hàng ngày."
        markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("💬 Tham Gia Nhóm Telegram Shop", url=TELEGRAM_GROUP_URL)).add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu", callback_data="user_back_to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "user_deposit_select":
        text = "💰 **CHỌN MỆNH GIÁ CẦN NẠP VÀO VÍ**\n──────────────────────────\nVui lòng chọn một trong các mệnh giá nhanh bên dưới hoặc bấm **Tự nhập số tiền** để xem thông tin tài khoản chuyển khoản:"
        markup = tele.types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            tele.types.InlineKeyboardButton("💵 10,000đ", callback_data="user_dep_fix_10000"),
            tele.types.InlineKeyboardButton("💵 20,000đ", callback_data="user_dep_fix_20000"),
            tele.types.InlineKeyboardButton("💵 50,000đ", callback_data="user_dep_fix_50000"),
            tele.types.InlineKeyboardButton("💵 100,000đ", callback_data="user_dep_fix_100000")
        )
        markup.add(tele.types.InlineKeyboardButton("✍️ Tự nhập số tiền mong muốn", callback_data="user_dep_custom"))
        markup.add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu", callback_data="user_back_to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("user_dep_fix_"):
        amount = float(data.split('_')[3])
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_dynamic_qr(call.message.chat.id, user_id, username, amount)

    elif data == "user_dep_custom":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "✍️ Sếp vui lòng **nhập số tiền bằng số** cần nạp vào ô chát (Ví dụ: `35000`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_custom_amount)

    elif data == "user_back_to_main_from_photo":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        welcome_text = "🤖 **CHÀO MỪNG BẠN ĐẾN VỚI SHOP LIÊN QUÂN TỰ ĐỘNG**\n──────────────────────────\n👇 Vui lòng chọn một chức năng dưới menu để bắt đầu:"
        bot.send_message(call.message.chat.id, welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

    elif data == "user_buy_rd":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()['balance']
        
        if balance < PRICE_RD:
            conn.close()
            text = f"❌ **GIAO DỊCH THẤT BẠI**\n──────────────────────────\nSố dư tài khoản không đủ.\n💵 Giá 1 acc: **{PRICE_RD:,}đ**\n💳 Ví của bạn: **{int(balance):,}đ**"
            markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("💰 Nạp Tiền Ngay", callback_data="user_deposit_select")).add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu", callback_data="user_back_to_main"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            return
            
        cursor.execute("SELECT id, account_info FROM stock_rd WHERE status = 'con_hang' LIMIT 1")
        acc = cursor.fetchone()
        
        if not acc:
            conn.close()
            text = "😭 **HẾT HÀNG MẤT RỒI**\n──────────────────────────\nHiện tại kho hàng ngẫu nhiên vừa hết sạch hàng. Hãy liên hệ Admin để bổ sung!"
            markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("⬅️ Quay Lại", callback_data="user_back_to_main"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            return
            
        acc_id, acc_info = acc['id'], acc['account_info']
        new_balance = balance - PRICE_RD
        
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        cursor.execute("UPDATE stock_rd SET status = 'da_ban' WHERE id = ?", (acc_id,))
        conn.commit()
        conn.close()
        
        success_msg = f"🎉 **MUA TÀI KHOẢN THÀNH CÔNG** 🎉\n──────────────────────────\n🔑 **Thông tin tài khoản:**\n`{acc_info}`\n──────────────────────────\n💵 Số tiền đã trừ: -{PRICE_RD:,}đ\n💳 Số dư còn lại: **{int(new_balance):,}đ**"
        markup = tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("⬅️ Quay Lại Menu Chính", callback_data="user_back_to_main"))
        bot.edit_message_text(success_msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # --- PHÂN HỆ QUẢN TRỊ ADMIN ---
    if data.startswith("adm_") or data.startswith("panel_"):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Lỗi: Bạn không có quyền Admin!", show_alert=True)
            return

    if data.startswith("adm_pub_"):
        parts = data.split('_')
        action = parts[2] 
        request_id = int(parts[3])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, amount, status FROM deposit_requests WHERE id = ?", (request_id,))
        req = cursor.fetchone()
        
        if not req or req['status'] != 'pending':
            conn.close()
            bot.edit_message_text(f"⚠️ Đơn hàng #{request_id} đã được xử lý từ trước.", call.message.chat.id, call.message.message_id)
            return
            
        target_user_id = req['user_id']
        amount = req['amount']
        
        if action == "approve":
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user_id))
            cursor.execute("UPDATE deposit_requests SET status = 'approved' WHERE id = ?", (request_id,))
            conn.commit()
            conn.close()
            bot.edit_message_text(f"✅ Đã duyệt thành công và cộng **+{int(amount):,}đ** cho đơn số #`{request_id}`.", call.message.chat.id, call.message.message_id)
            try: bot.send_message(target_user_id, f"🎉 Đơn nạp tiền #{request_id} thành công! Tài khoản của bạn được cộng **+{int(amount):,}đ**.")
            except Exception: pass
        elif action == "reject":
            cursor.execute("UPDATE deposit_requests SET status = 'rejected' WHERE id = ?", (request_id,))
            conn.commit()
            conn.close()
            bot.edit_message_text(f"❌ Đã huỷ và từ chối duyệt đơn số #`{request_id}`.", call.message.chat.id, call.message.message_id)
            try: bot.send_message(target_user_id, f"❌ Yêu cầu nạp đơn số **#{request_id}** đã bị Admin từ chối phê duyệt.")
            except Exception: pass

    elif data == "panel_view_pending":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, amount FROM deposit_requests WHERE status = 'pending' ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            bot.answer_callback_query(call.id, "🎉 Không có đơn nạp nào đang chờ duyệt!", show_alert=True)
            return
        text = "📥 **DANH SÁCH ĐƠN CHỜ DUYỆT CẬP NHẬT:**\n\n"
        markup = tele.types.InlineKeyboardMarkup(row_width=2)
        for row in rows:
            text += f"🔹 Đơn `#{row['id']}` - Khách: @{row['username']} - **{int(row['amount']):,}đ**\n"
            markup.add(tele.types.InlineKeyboardButton(f"✅ Duyệt #{row['id']}", callback_data=f"adm_pub_approve_{row['id']}"), tele.types.InlineKeyboardButton(f"❌ Huỷ #{row['id']}", callback_data=f"adm_pub_reject_{row['id']}"))
        markup.add(tele.types.InlineKeyboardButton("⬅️ Quay lại", callback_data="panel_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "panel_guide_acc":
        guide_text = "➕ **CÁCH THÊM ACC HÀNG LOẠT**\n\nSếp gửi tin nhắn định dạng văn bản thường như sau:\n`/addacc`\n`taikhoan1|matkhau1`\n`taikhoan2|matkhau2`"
        bot.edit_message_text(guide_text, call.message.chat.id, call.message.message_id, reply_markup=tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("⬅️ Quay lại", callback_data="panel_main")), parse_mode="Markdown")

    elif data == "panel_guide_qr":
        guide_text = "⚙️ **CÁCH ĐỔI ẢNH QR MỚI**\n\nSếp đính kèm tệp ảnh mã ngân hàng mới của sếp rồi gửi thẳng vào đây, kèm theo ở phần mô tả nội dung caption chữ: `/addqr`. Hệ thống sẽ tự động đồng bộ ảnh gốc!"
        bot.edit_message_text(guide_text, call.message.chat.id, call.message.message_id, reply_markup=tele.types.InlineKeyboardMarkup().add(tele.types.InlineKeyboardButton("⬅️ Quay lại", callback_data="panel_main")), parse_mode="Markdown")

    elif data == "panel_main":
        markup = tele.types.InlineKeyboardMarkup(row_width=1)
        markup.add(tele.types.InlineKeyboardButton("📥 Xem đơn nạp chờ duyệt", callback_data="panel_view_pending"), tele.types.InlineKeyboardButton("➕ Cách thêm Acc hàng loạt", callback_data="panel_guide_acc"), tele.types.InlineKeyboardButton("⚙️ Cách đổi cấu hình QR Bank", callback_data="panel_guide_qr"))
        bot.edit_message_text("⚙️ **TRUNG TÂM ĐIỀU HÀNH ADMIN SHOP**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")


# =====================================================================
# 7. LỆNH VĂN BẢN (COMMANDS) DÀNH CHO ADMIN
# =====================================================================
@bot.message_handler(commands=['admin_panel'])
def admin_panel_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    markup = tele.types.InlineKeyboardMarkup(row_width=1)
    markup.add(tele.types.InlineKeyboardButton("📥 Xem đơn nạp chờ duyệt", callback_data="panel_view_pending"), tele.types.InlineKeyboardButton("➕ Cách thêm Acc hàng loạt", callback_data="panel_guide_acc"), tele.types.InlineKeyboardButton("⚙️ Cách đổi cấu hình QR Bank", callback_data="panel_guide_qr"))
    bot.reply_to(message, "⚙️ **TRUNG TÂM ĐIỀU HÀNH ADMIN SHOP**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['addacc'])
def addacc_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    lines = args[1].strip().split('\n')
    added_count = 0
    conn = get_db_connection()
    cursor = conn.cursor()
    for line in lines:
        acc_info = line.strip()
        if acc_info:
            cursor.execute("INSERT INTO stock_rd (account_info) VALUES (?)", (acc_info,))
            added_count += 1
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Đã nạp thành công **{added_count}** tài khoản mới vào kho hàng.")


# =====================================================================
# 8. KHỞI CHẠY ĐỘNG CƠ POLLING
# =====================================================================
if __name__ == '__main__':
    logger.info("Bot đang kết nối với máy chủ Render...")
    try: bot.delete_webhook(drop_pending_updates=True)
    except Exception: pass
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
