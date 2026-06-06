import sqlite3
import logging
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG (THAY ĐỔI TẠI ĐÂY)
# ==========================================
TOKEN = '6367532329:AAF3m_jaRXRjqhzuHf_FdSgFrmZNjApJ6v8'                    # Thay bằng Token Bot của bạn
ADMIN_ID = 5736655322                       # Thay bằng ID Telegram cá nhân của bạn
SUPPORT_URL = 'https://t.me/baohuyno1' # Link Telegram để khách hàng liên hệ
# ==========================================

# 1. THIẾT LẬP LOG & DATABASE
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
conn.commit()

# 2. GIAO DIỆN MENU CHÍNH
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# 3. TRUNG TÂM XỬ LÝ NÚT BẤM
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # [NẠP TIỀN] - Hiện QR và Mệnh giá
    if data == 'menu_nap':
        cursor.execute("SELECT value FROM settings WHERE key='qr_file_id'")
        row = cursor.fetchone()
        
        keyboard = [
            [InlineKeyboardButton("10k", callback_data='nap_10000'), InlineKeyboardButton("50k", callback_data='nap_50000')],
            [InlineKeyboardButton("100k", callback_data='nap_100000'), InlineKeyboardButton("200k", callback_data='nap_200000')],
            [InlineKeyboardButton("« Quay lại", callback_data='back_start')]
        ]
        
        if row:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.message.chat_id, photo=row[0],
                caption="💳 **Quét mã QR ngân hàng và chọn mệnh giá nạp:**",
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("💵 Chọn mệnh giá nạp (Admin chưa cấu hình QR):", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # [NẠP TIỀN] - Gửi yêu cầu cho Admin (Hạn 20 phút)
    elif data.startswith('nap_'):
        amount = data.split('_')[1]
        current_time = int(time.time())
        
        admin_keyboard = [[
            InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{user_id}_{amount}_{current_time}"),
            InlineKeyboardButton("❌ Hủy đơn", callback_data=f"deny_{user_id}")
        ]]
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **YÊU CẦU NẠP TIỀN (Hạn 20 phút)**\n- Khách: `{user_id}`\n- Số tiền: {int(amount):,}đ",
            reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode='Markdown'
        )
        
        msg = "✅ Đã gửi yêu cầu nạp tiền đến Admin.\n⚠️ Lưu ý: Yêu cầu tự hủy sau 20 phút!"
        if query.message.photo:
            await query.message.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text=msg)
        else:
            await query.edit_message_text(msg)

    # [XEM SỐ DƯ]
    elif data == 'balance':
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        bal = row[0] if row else 0
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        await query.edit_message_text(f"💰 Số dư: **{bal:,}đ**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # [MUA TÀI KHOẢN]
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

    # [XEM TỒN KHO]
    elif data == 'stock':
        count = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        await query.edit_message_text(f"📦 Trong kho còn: **{count}** acc.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # [QUAY LẠI MENU CHÍNH]
    elif data == 'back_start':
        if query.message.photo:
            await query.message.delete()
            await start(update, context)
        else:
            await start(update, context)

    # [ADMIN] - Duyệt tiền (Kiểm tra hết hạn 20p)
    elif data.startswith('approve_'):
        if user_id != ADMIN_ID: return
            
        _, uid, amt, created_time = data.split('_')
        uid, amt, created_time = int(uid), int(amt), int(created_time)
        
        if int(time.time()) - created_time > 1200:
            await query.edit_message_text("❌ **ĐÃ HỦY:** Yêu cầu nạp tiền quá hạn 20 phút!")
            try: await context.bot.send_message(chat_id=uid, text="⚠️ Đơn nạp bị hủy do quá hạn 20 phút. Vui lòng tạo lại.")
            except Exception: pass
            return
            
        cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        conn.commit()
        
        await query.edit_message_text(f"✅ Đã duyệt {amt:,}đ cho ID: `{uid}`", parse_mode='Markdown')
        try: await context.bot.send_message(chat_id=uid, text=f"🎉 Tài khoản được cộng **{amt:,}đ** từ Admin!")
        except Exception: pass

    # [ADMIN] - Từ chối tiền
    elif data.startswith('deny_'):
        if user_id != ADMIN_ID: return
        uid = int(data.split('_')[1])
        await query.edit_message_text(f"❌ Đã từ chối đơn của ID: `{uid}`", parse_mode='Markdown')
        try: await context.bot.send_message(chat_id=uid, text="⚠️ Yêu cầu nạp tiền của bạn bị từ chối.")
        except Exception: pass

# 4. LỆNH QUẢN TRỊ ADMIN (Thêm Acc & Cập nhật QR)
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

async def add_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('qr_file_id', ?)", (file_id,))
        conn.commit()
        await update.message.reply_text("✅ Đã cập nhật ảnh QR thành công!")
    else:
        await update.message.reply_text("⚠️ Gửi 1 ảnh kèm caption `/addqr`.")

# 5. KHỞI CHẠY BOT BẤT ĐỒNG BỘ
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addacc", add_acc))
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex('^/addqr'), add_qr))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    await app.initialize()
    await app.updater.start_polling(allowed_updates=["message", "callback_query"])
    await app.start()
    
    print("--- 🚀 Bot Shop đang chạy ổn định trên luồng Async ---")
    try:
        while True: await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.stop()
        await app.updater.stop()

if __name__ == '__main__':
    # Bật Server Keep Alive chống ngủ đông
    try:
        from keep_alive import keep_alive
        keep_alive()
        print("--- 🌐 Keep Alive Web Server: HOẠT ĐỘNG ---")
    except ImportError:
        print("--- ⚠️ Bỏ qua Keep Alive do không tìm thấy file ---")

    # Xử lý vòng lặp Event Loop độc lập cho Python 3.14+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot đã tắt.")
