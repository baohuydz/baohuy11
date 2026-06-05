import sqlite3
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH ---
TOKEN = '6367532329:AAGp-dCbkBs6JHeol5X6bvXEUksG6PwnJ58'      # Token lấy từ @BotFather
ADMIN_ID = 5736655322         # Thay ID Telegram của bạn vào đây
SUPPORT_URL = 'https://t.me/baohuyno1'  # Thay link Telegram cá nhân của bạn để hỗ trợ
# ----------------

# Thiết lập log hệ thống
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Khởi tạo Database SQLite (Lưu trữ vĩnh viễn)
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
conn.commit()

# --- GIAO DIỆN MENU CHÍNH ---
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

# --- XỬ LÝ NÚT BẤM (CALLBACK QUERY) ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # 1. Menu chọn mệnh giá nạp
    if data == 'menu_nap':
        cursor.execute("SELECT value FROM settings WHERE key='qr_file_id'")
        row = cursor.fetchone()
        
        keyboard = [
            [InlineKeyboardButton("10k", callback_data='nap_10000'), InlineKeyboardButton("50k", callback_data='nap_50000')],
            [InlineKeyboardButton("100k", callback_data='nap_100000'), InlineKeyboardButton("200k", callback_data='nap_200000')],
            [InlineKeyboardButton("« Quay lại", callback_data='back_start')]
        ]
        
        if row:
            await query.message.delete() # Xóa menu chữ để gửi ảnh QR kèm menu mới
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=row[0],
                caption="💳 **Quét mã QR ngân hàng bên trên và chọn đúng mệnh giá bạn muốn nạp dưới đây:**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("💵 Chọn mệnh giá nạp (Admin chưa cấu hình ảnh QR bằng lệnh /addqr):", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # 2. Khách hàng chọn một mệnh giá nạp cụ thể (Cải tiến chèn Timestamp thời gian gửi)
    elif data.startswith('nap_'):
        amount = data.split('_')[1]
        current_time = int(time.time()) # Lưu mốc giây hiện tại
        
        # Chèn thời gian hiện tại vào cuối callback_data của nút duyệt
        admin_keyboard = [[
            InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{user_id}_{amount}_{current_time}"),
            InlineKeyboardButton("❌ Hủy đơn", callback_data=f"deny_{user_id}")
        ]]
        
        # Gửi thông báo trực tiếp đến tài khoản Admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **YÊU CẦU NẠP TIỀN (Hạn chót 20 phút)**\n- Khách hàng ID: `{user_id}`\n- Số tiền: {int(amount):,}đ\n\n*Hệ thống sẽ tự hủy quyền duyệt sau 20 phút nữa để đảm bảo an toàn!*",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown'
        )
        
        # Phản hồi cho người dùng tùy thuộc giao diện trước đó là ảnh hay chữ
        if query.message.photo:
            await query.message.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text="✅ Đã gửi yêu cầu nạp tiền đến Admin.\n⚠️ Lưu ý: Yêu cầu của bạn chỉ có hiệu lực kiểm tra và duyệt trong vòng 20 phút!")
        else:
            await query.edit_message_text("✅ Đã gửi yêu cầu nạp tiền đến Admin.\n⚠️ Lưu ý: Yêu cầu của bạn chỉ có hiệu lực kiểm tra và duyệt trong vòng 20 phút!")

    # 3. Kiểm tra số dư tài khoản khách
    elif data == 'balance':
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        bal = row[0] if row else 0
        
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        await query.edit_message_text(f"💰 Số dư hiện tại của bạn là: **{bal:,}đ**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # 4. Logic xử lý mua tài khoản (Giá cố định 1,000đ)
    elif data == 'buy':
        price = 1000  
        
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row_user = cursor.fetchone()
        bal = row_user[0] if row_user else 0
        
        cursor.execute("SELECT id, data FROM accounts ORDER BY id ASC LIMIT 1")
        row_acc = cursor.fetchone()
        
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        
        if bal < price:
            await query.edit_message_text("❌ Tài khoản của bạn không đủ tiền! Vui lòng nạp thêm.", reply_markup=InlineKeyboardMarkup(keyboard))
        elif not row_acc:
            await query.edit_message_text("❌ Hệ thống hiện tại đang hết hàng, vui lòng quay lại sau.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            acc_id, acc_data = row_acc
            new_balance = bal - price
            
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, user_id))
            cursor.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
            conn.commit()
            
            await query.edit_message_text(f"🎉 **MUA TÀI KHOẢN THÀNH CÔNG!**\n\nThông tin tài khoản của bạn:\n`{acc_data}`\n\n_Số dư còn lại: {new_balance:,}đ_", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # 5. Xem số lượng tồn kho
    elif data == 'stock':
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        keyboard = [[InlineKeyboardButton("« Quay lại", callback_data='back_start')]]
        await query.edit_message_text(f"📦 Số lượng tài khoản hiện có trong kho: **{count}** acc.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # 6. Quay lại menu chính và dọn dẹp tin nhắn ảnh cũ
    elif data == 'back_start':
        if query.message.photo:
            await query.message.delete()
            keyboard = [
                [InlineKeyboardButton("💳 Nạp tiền", callback_data='menu_nap')],
                [InlineKeyboardButton("💰 Số dư", callback_data='balance')],
                [InlineKeyboardButton("🛒 Mua Acc (1,000đ)", callback_data='buy')],
                [InlineKeyboardButton("📦 Kho hàng", callback_data='stock')],
                [InlineKeyboardButton("🎧 Admin hỗ trợ", url=SUPPORT_URL)]
            ]
            await context.bot.send_message(chat_id=query.message.chat_id, text="🖥 **HỆ THỐNG LIÊN QUÂN**\nChào mừng bạn đến với shop tự động!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await start(update, context)

    # 7. Admin bấm nút Duyệt Cộng Tiền (Cải tiến check thời gian quá 20 phút)
    elif data.startswith('approve_'):
        if user_id != ADMIN_ID:
            return
            
        _, uid, amt, created_time = data.split('_')
        uid, amt, created_time = int(uid), int(amt), int(created_time)
        
        # 20 phút = 1200 giây
        if int(time.time()) - created_time > 1200:
            await query.edit_message_text("❌ **ĐƠN QUÁ HẠN:** Yêu cầu nạp tiền này đã quá hạn 20 phút. Hệ thống đã tự động từ chối lệnh duyệt này!")
            try:
                await context.bot.send_message(chat_id=uid, text="⚠️ **THÔNG BÁO QUÁ HẠN:** Yêu cầu nạp tiền của bạn đã bị hủy do Admin không duyệt trong vòng 20 phút. Vui lòng tạo lại đơn nạp mới.")
            except Exception:
                pass
            return
            
        # Nếu hợp lệ trong 20 phút -> Tiến hành cộng tiền
        cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        conn.commit()
        
        await query.edit_message_text(f"✅ Đã duyệt cộng thành công {amt:,}đ cho thành viên có ID: `{uid}`", parse_mode='Markdown')
        try:
            await context.bot.send_message(chat_id=uid, text=f"🎉 **THÔNG BÁO NẠP TIỀN**\nTài khoản của bạn đã được cộng thành công **{amt:,}đ** từ Admin!")
        except Exception:
            pass

    # 8. Admin bấm nút Từ Chối / Hủy Đơn của khách
    elif data.startswith('deny_'):
        if user_id != ADMIN_ID:
            return
        uid = int(data.split('_')[1])
        
        await query.edit_message_text(f"❌ Bạn đã chủ động từ chối yêu cầu nạp tiền của thành viên: `{uid}`", parse_mode='Markdown')
        try:
            await context.bot.send_message(chat_id=uid, text="⚠️ **THÔNG BÁO HỦY ĐƠN**\nYêu cầu nạp tiền của bạn đã bị từ chối bởi Admin. Vui lòng liên hệ hỗ trợ nếu có sai sót.")
        except Exception:
            pass

# --- LỆNH QUẢN TRỊ ADMIN (ẨN HOÀN TOÀN VỚI NGƯỜI THƯỜNG) ---

# Thêm tài khoản: /addacc thien2k6thicau|thienngonzai2k6
async def add_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return 
        
    acc_data = " ".join(context.args)
    if not acc_data:
        await update.message.reply_text("⚠️ Cú pháp: `/addacc tài_khoản\|mật_khẩu`", parse_mode='Markdown')
        return
        
    cursor.execute("INSERT INTO accounts (data) VALUES (?)", (acc_data,))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM accounts")
    total = cursor.fetchone()[0]
    await update.message.reply_text(f"✅ Đã thêm tài khoản thành công vào kho SQLite.\n📦 Số lượng acc hiện tại: **{total}**", parse_mode='Markdown')

# Thêm hoặc Đổi ảnh QR nạp tiền: Gửi ảnh kèm dòng mô tả (caption) ghi chữ /addqr
async def add_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('qr_file_id', ?)", (file_id,))
        conn.commit()
        await update.message.reply_text("✅ Đã cập nhật ảnh mã QR mới thành công vào Database!")
    else:
        await update.message.reply_text("⚠️ Vui lòng gửi một bức ảnh và điền chữ `/addqr` vào nội dung mô tả (caption) của bức ảnh đó.")

# --- KHỞI CHẠY BOT ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addacc", add_acc))
    
    # Bắt riêng trường hợp Admin gửi ảnh kèm chữ /addqr trong caption mô tả ảnh
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex('^/addqr'), add_qr))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("--- Hệ thống Bot Shop Liên Quân hoạt động bảo mật 24/24 ---")
    app.run_polling()
