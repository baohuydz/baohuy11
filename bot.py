import sqlite3
import logging
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG
# ==========================================
TOKEN = '6367532329:AAHtfx-U0Jl0fByEtXEisrm6zh7lRC4kIew'                    # Thay bằng Token Bot của bạn
ADMIN_ID = 5736655322                       # Thay bằng ID Telegram cá nhân của bạn
SUPPORT_URL = 'https://t.me/baohuyno1' # Link Telegram để khách hàng liên hệ
# ==========================================

# --- BỘ NHỚ TẠM THỜI (Lưu trạng thái người dùng đang làm gì) ---
WAITING_FOR_AMOUNT = {}
WAITING_FOR_QR = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
conn.commit()

# --- GIAO DIỆN MENU CHÍNH ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    WAITING_FOR_AMOUNT.pop(user_id, None) # Hủy trạng thái chờ nhập tiền nếu có
    
    keyboard = [
        [InlineKeyboardButton("💳 Nạp tiền", callback_data='menu_nap')],
        [InlineKeyboardButton("💰 Số dư", callback_data='balance')],
        [InlineKeyboardButton("🛒 Mua Acc (1,000đ)", callback_data='buy')],
        [InlineKeyboardButton("📦 Kho hàng", callback_data='stock')],
        [InlineKeyboardButton("🎧 Admin hỗ trợ", url=SUPPORT_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("🖥 **HỆ THỐNG LIÊN QUÂN**\nChào mừng bạn đến với shop tự động!", reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.edit_text("🖥 **HỆ THỐNG LIÊN QUÂN**\nChào mừng bạn đến với shop tự động!", reply_markup=reply_markup, parse_mode='Markdown')

# --- TRUNG TÂM XỬ LÝ NÚT BẤM ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # 1. Menu nạp tiền (Thêm nút nạp tùy chỉnh)
    if data == 'menu_nap':
        cursor.execute("SELECT value FROM settings WHERE key='qr_file_id'")
        row = cursor.fetchone()
        
        keyboard = [
            [InlineKeyboardButton("10k", callback_data='nap_10000'), InlineKeyboardButton("50k", callback_data='nap_50000')],
            [InlineKeyboardButton("100k", callback_data='nap_100000'), InlineKeyboardButton("200k", callback_data='nap_200000')],
            [InlineKeyboardButton("✍️ Nhập số tiền khác", callback_data='nap_custom')],
            [InlineKeyboardButton("« Quay lại", callback_data='back_start')]
        ]
        
        if row:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=user_id, photo=row[0],
                caption="💳 **Quét mã QR ngân hàng và chọn mệnh giá nạp:**",
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("💵 Chọn mệnh giá nạp (Admin chưa cấu hình QR):", reply_markup=InlineKeyboardMarkup(keyboard))
            
    # 2. Xử lý nút "Nhập số tiền khác"
    elif data == 'nap_custom':
        WAITING_FOR_AMOUNT[user_id] = True
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user_id, 
            text="✍️ **Vui lòng nhắn số tiền bạn muốn nạp vào đây:**\n_(Chỉ ghi số, ví dụ nạp 25k thì nhắn: 25000)_", 
            parse_mode='Markdown'
        )
    
    # 3. Khách chọn mệnh giá có sẵn
    elif data.startswith('nap_') and data != 'nap_custom':
        amount = data.split('_')[1]
        current_time = int(time.time())
        
        admin_keyboard = [[
            InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{user_id}_{amount}_{current_time}"),
            InlineKeyboardButton("❌ Hủy", callback_data=f"deny_{user_id}")
        ]]
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **YÊU CẦU NẠP TIỀN (Hạn 20 phút)**\n- Khách: `{user_id}`\n- Số tiền: {int(amount):,}đ",
            reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode='Markdown'
        )
        
        msg = f"✅ Đã gửi yêu cầu nạp **{int(amount):,}đ** đến Admin.\n⚠️ Lưu ý: Yêu cầu tự hủy sau 20 phút!"
        if query.message.photo:
            await query.message.delete()
            await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
        else:
            await query.edit_message_text(msg, parse_mode='Markdown')

    # ... [CÁC NÚT BẤM KHÁC GIỮ NGUYÊN] ...
    elif data == 'balance':
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        bal = row[0] if row else 0
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        await query.edit_message_text(f"💰 Số dư: **{bal:,}đ**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'buy':
        price = 1000  
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        bal = cursor.fetchone()[0] if cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone() else 0
        
        cursor.execute("SELECT id, data FROM accounts ORDER BY id ASC LIMIT 1")
        row_acc = cursor.fetchone()
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        
        if bal < price:
            await query.edit_message_text("❌ Không đủ tiền! Vui lòng nạp thêm.", reply_markup=InlineKeyboardMarkup(keyboard))
        elif not row_acc:
            await query.edit_message_text("❌ Hệ thống đang hết hàng.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            acc_id, acc_data = row_acc
            new_bal = bal - price
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id))
            cursor.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
            conn.commit()
            await query.edit_message_text(f"🎉 **MUA THÀNH CÔNG!**\n\nTài khoản của bạn:\n`{acc_data}`\n\n_Số dư còn lại: {new_bal:,}đ_", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'stock':
        count = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        await query.edit_message_text(f"📦 Trong kho còn: **{count}** acc.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'back_start':
        if query.message.photo:
            await query.message.delete()
            await start(update, context)
        else:
            await start(update, context)

    # Nút Admin duyệt/hủy
    elif data.startswith('approve_'):
        if user_id != ADMIN_ID: return
        _, uid, amt, created_time = data.split('_')
        uid, amt, created_time = int(uid), int(amt), int(created_time)
        
        if int(time.time()) - created_time > 1200:
            await query.edit_message_text("❌ **ĐÃ HỦY:** Yêu cầu nạp tiền quá hạn 20 phút!")
            try: await context.bot.send_message(chat_id=uid, text="⚠️ Đơn nạp bị hủy do Admin không duyệt trong vòng 20 phút. Vui lòng tạo lại.")
            except Exception: pass
            return
            
        cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        conn.commit()
        await query.edit_message_text(f"✅ Đã duyệt {amt:,}đ cho ID: `{uid}`", parse_mode='Markdown')
        try: await context.bot.send_message(chat_id=uid, text=f"🎉 Tài khoản được cộng **{amt:,}đ** từ Admin!")
        except Exception: pass

    elif data.startswith('deny_'):
        if user_id != ADMIN_ID: return
        uid = int(data.split('_')[1])
        await query.edit_message_text(f"❌ Đã từ chối đơn của ID: `{uid}`", parse_mode='Markdown')
        try: await context.bot.send_message(chat_id=uid, text="⚠️ Yêu cầu nạp tiền của bạn bị từ chối.")
        except Exception: pass


# --- BẮT SỐ TIỀN KHÁCH NHẬP TÙY CHỈNH ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Nếu người dùng đang ở trạng thái chờ nhập số tiền
    if WAITING_FOR_AMOUNT.get(user_id):
        if text.isdigit() and int(text) >= 1000:
            amount = int(text)
            WAITING_FOR_AMOUNT[user_id] = False # Xóa trạng thái chờ
            current_time = int(time.time())
            
            admin_keyboard = [[
                InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{user_id}_{amount}_{current_time}"),
                InlineKeyboardButton("❌ Hủy", callback_data=f"deny_{user_id}")
            ]]
            
            # Gửi yêu cầu tùy chỉnh cho Admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 **YÊU CẦU NẠP TÙY CHỈNH (Hạn 20 phút)**\n- Khách: `{user_id}`\n- Số tiền: {amount:,}đ",
                reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Đã gửi yêu cầu nạp **{amount:,}đ** đến Admin.\n⚠️ Lưu ý: Yêu cầu tự hủy sau 20 phút!", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Số tiền không hợp lệ. Vui lòng chỉ nhập số và tối thiểu là 1000 (Ví dụ: 15000).")


# --- LỆNH ADMIN ---
async def add_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return 
    acc_data = " ".join(context.args)
    if not acc_data:
        await update.message.reply_text(r"⚠️ Cú pháp: `/addacc tk\|mk`", parse_mode='Markdown')
        return
    cursor.execute("INSERT INTO accounts (data) VALUES (?)", (acc_data,))
    conn.commit()
    total = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    await update.message.reply_text(f"✅ Đã thêm acc.\n📦 Tổng kho: **{total}**", parse_mode='Markdown')

# BƯỚC 1: Admin gõ lệnh /addqr
async def cmd_addqr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    WAITING_FOR_QR[ADMIN_ID] = True
    await update.message.reply_text("📸 Hãy gửi ảnh mã QR thanh toán của bạn lên đây (chỉ cần gửi ảnh, không cần gõ thêm chữ).")

# BƯỚC 2: Admin gửi ảnh lên
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        # Kiểm tra xem có đang ở trạng thái chờ nhận ảnh QR không (Hoặc gửi ảnh kèm caption cũ vẫn nhận)
        is_waiting = WAITING_FOR_QR.get(user_id, False)
        is_caption = update.message.caption and update.message.caption.strip().startswith('/addqr')
        
        if is_waiting or is_caption:
            file_id = update.message.photo[-1].file_id # Lấy ảnh chất lượng cao nhất
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('qr_file_id', ?)", (file_id,))
            conn.commit()
            
            WAITING_FOR_QR[user_id] = False # Xóa trạng thái
            await update.message.reply_text("✅ Đã lưu ảnh mã QR mới thành công vào hệ thống!")

# --- KHỞI CHẠY BOT BẤT ĐỒNG BỘ ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addacc", add_acc))
    app.add_handler(CommandHandler("addqr", cmd_addqr)) # Bắt lệnh /addqr
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo)) # Bắt sự kiện gửi ảnh
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)) # Bắt tin nhắn chữ (số tiền)
    app.add_handler(CallbackQueryHandler(button_handler))
    
    await app.initialize()
    await app.updater.start_polling(allowed_updates=["message", "callback_query"])
    await app.start()
    
    print("--- 🚀 Bot Shop đang chạy (Có Nạp tùy chỉnh & Add QR thông minh) ---")
    try:
        while True: await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.stop()
        await app.updater.stop()

if __name__ == '__main__':
    try:
        from keep_alive import keep_alive
        keep_alive()
    except ImportError:
        pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot đã tắt.")
