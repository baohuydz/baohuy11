import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from keep_alive import keep_alive  # 👈 import file keep riêng

# ====== CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"

FB_INFO_API = "https://profile.taphoabill.top/api/fb/getInfo.php"
TIKTOK_LIVE_API = "https://profile.taphoabill.top/api/tiktok/checklive/"
GET_ID_FB_API = "https://ffb.vn/api/tool/get-id-fb"
FB_LIVE_API = "https://phongdq.vn/wp-admin/admin-ajax.php"

# ====== LOG ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot đã sẵn sàng!\n\n"
        "Lệnh:\n"
        "• /checkfb <idfb>\n"
        "• /getidfb <link_or_username>\n"
        "• /checkfblive <idfb>\n"
        "• /checklive <username_tiktok>\n"
    )

async def checkfb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Dùng: /checkfb <id_facebook>")
        return

    fb_id = context.args[0]
    try:
        res = requests.get(FB_INFO_API, params={"id": fb_id}, timeout=15)
        data = res.json()
    except Exception:
        await update.message.reply_text("❌ Lỗi gọi API Facebook!")
        return

    if data.get("status") != "success":
        await update.message.reply_text("❌ Không lấy được info Facebook!")
        return

    info = data["result"]
    name = info.get("first_name", "N/A")
    verified = "✅ Có" if info.get("is_verified") else "❌ Không"
    about = info.get("about", "Không có")
    hometown = info.get("hometown", {}).get("name", "Không rõ")
    avatar = info.get("picture", {}).get("data", {}).get("url")

    text = (
        f"👤 Tên: {name}\n"
        f"🔎 ID: {fb_id}\n"
        f"🔰 Verified: {verified}\n"
        f"🏠 Quê quán: {hometown}\n"
        f"📝 About: {about}"
    )

    if avatar:
        await update.message.reply_photo(photo=avatar, caption=text)
    else:
        await update.message.reply_text(text)

async def getidfb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Dùng: /getidfb <link_or_username>")
        return

    target = context.args[0]
    try:
        res = requests.get(GET_ID_FB_API, params={"idfb": target}, timeout=15)
        data = res.json()
    except Exception:
        await update.message.reply_text("❌ Lỗi gọi API get ID!")
        return

    fb_id = data.get("id") or data.get("result") or data.get("uid")
    if not fb_id:
        await update.message.reply_text("❌ Không lấy được ID Facebook!")
        return

    await update.message.reply_text(f"✅ ID Facebook của bạn là: {fb_id}")

async def checkfblive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Dùng: /checkfblive <idfb>")
        return

    fb_id = context.args[0]
    try:
        res = requests.get(
            FB_LIVE_API,
            params={"action": "check_live_uid", "uid": fb_id},
            timeout=15
        )
        data = res.json()
    except Exception:
        await update.message.reply_text("❌ Lỗi gọi API check live Facebook!")
        return

    is_live = False
    if isinstance(data, dict):
        is_live = data.get("is_live") or data.get("live") or data.get("status") == "live"

    if is_live:
        await update.message.reply_text(f"🔴 ID {fb_id} đang LIVE trên Facebook!")
    else:
        await update.message.reply_text(f"⚫ ID {fb_id} hiện KHÔNG LIVE.")

async def checklive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Dùng: /checklive <username_tiktok>")
        return

    username = context.args[0].replace("@", "")
    try:
        res = requests.get(TIKTOK_LIVE_API, params={"username": username}, timeout=15)
        data = res.json()
    except Exception:
        await update.message.reply_text("❌ Lỗi gọi API TikTok!")
        return

    if data.get("status") != "success":
        await update.message.reply_text("❌ Không lấy được trạng thái live TikTok!")
        return

    result = data.get("result", {})
    is_live = result.get("is_live", False)

    if is_live:
        title = result.get("title", "Không có tiêu đề")
        viewers = result.get("viewer_count", "N/A")
        live_url = result.get("live_url", f"https://www.tiktok.com/@{username}/live")

        text = (
            f"🔴 {username} ĐANG LIVE!\n"
            f"👀 Viewers: {viewers}\n"
            f"📝 Tiêu đề: {title}\n"
            f"🔗 Link: {live_url}"
        )
    else:
        text = f"⚫ {username} hiện tại KHÔNG LIVE."

    await update.message.reply_text(text)

# ====== MAIN ======
def main():
    keep_alive()  # 👈 gọi keep ở đây

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("checkfb", checkfb))
    application.add_handler(CommandHandler("getidfb", getidfb))
    application.add_handler(CommandHandler("checkfblive", checkfblive))
    application.add_handler(CommandHandler("checklive", checklive))

    print("Bot đang chạy...")
    application.run_polling()

if __name__ == "__main__":
    main()
