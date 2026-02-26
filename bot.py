import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from keep_alive import keep_alive

# ====== LOGGING ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== CONFIG ======
BOT_TOKEN = os.getenv("8080338995:AAGxFfuzRzsjl_qsnCSK-2JZvBwy_B3NjRY")

FB_INFO_API = "https://profile.taphoabill.top/api/fb/getInfo.php"
TIKTOK_LIVE_API = "https://profile.taphoabill.top/api/tiktok/checklive/"
GET_ID_FB_API = "https://ffb.vn/api/tool/get-id-fb"
FB_LIVE_API = "https://phongdq.vn/wp-admin/admin-ajax.php"

# ====== HELPER ======
async def fetch_api(url, params=None, method="GET"):
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        if method == "POST":
            res = await client.post(url, data=params)
        else:
            res = await client.get(url, params=params)

        try:
            return res.json()
        except:
            return {"raw": res.text}

# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    text = (
        f"👋 Chào {name}!\n\n"
        "🤖 Lệnh hỗ trợ:\n"
        "• /checkfb <idfb>\n"
        "• /getidfb <link>\n"
        "• /checkfblive <idfb>\n"
        "• /checklive <username_tiktok>\n"
    )
    await update.message.reply_text(text)

async def checkfb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Dùng: /checkfb <idfb>")

    fb_id = context.args[0]
    await update.message.reply_text("⏳ Đang lấy thông tin Facebook...")

    try:
        data = await fetch_api(FB_INFO_API, {"id": fb_id})
        if data.get("status") != "success":
            return await update.message.reply_text("❌ Không tìm thấy thông tin.")

        info = data.get("result", {})
        name = info.get("first_name", "N/A")
        verified = "✅" if info.get("is_verified") else "❌"
        hometown = info.get("hometown", {}).get("name", "Không rõ") if info.get("hometown") else "Không rõ"
        avatar = info.get("picture", {}).get("data", {}).get("url")

        caption = (
            f"👤 Tên: {name}\n"
            f"🆔 ID: {fb_id}\n"
            f"🔰 Tích xanh: {verified}\n"
            f"🏠 Quê quán: {hometown}"
        )

        if avatar:
            await update.message.reply_photo(photo=avatar, caption=caption)
        else:
            await update.message.reply_text(caption)

    except Exception as e:
        logger.error(f"Lỗi checkfb: {e}")
        await update.message.reply_text("❌ Lỗi API Facebook.")

async def getidfb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Dùng: /getidfb <link>")

    link = context.args[0]
    await update.message.reply_text("⏳ Đang lấy ID Facebook...")

    try:
        data = await fetch_api(GET_ID_FB_API, {"idfb": link})
        fb_id = data.get("id") or data.get("uid") or data.get("result")

        if fb_id:
            await update.message.reply_text(f"✅ ID Facebook: `{fb_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Không lấy được ID.")

    except Exception as e:
        logger.error(f"Lỗi getidfb: {e}")
        await update.message.reply_text("❌ API get ID lỗi.")

async def checkfblive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Dùng: /checkfblive <idfb>")

    fb_id = context.args[0]
    await update.message.reply_text("⏳ Đang check Facebook LIVE...")

    try:
        data = await fetch_api(FB_LIVE_API, {
            "action": "check_live_facebook",
            "id": fb_id
        }, method="POST")

        if "live" in str(data).lower():
            await update.message.reply_text(f"🔴 Facebook ID {fb_id} đang LIVE!")
        else:
            await update.message.reply_text(f"⚫ Facebook ID {fb_id} không live.")

    except Exception as e:
        logger.error(f"Lỗi checkfblive: {e}")
        await update.message.reply_text("❌ API Facebook LIVE lỗi.")

async def checklive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Dùng: /checklive <username>")

    username = context.args[0].replace("@", "")
    await update.message.reply_text("⏳ Đang check TikTok LIVE...")

    try:
        data = await fetch_api(TIKTOK_LIVE_API, {"username": username})
        if data.get("status") == "success":
            res = data.get("result", {})
            if res.get("is_live"):
                msg = (
                    f"🔴 {username} ĐANG LIVE!\n"
                    f"👀 View: {res.get('viewer_count')}\n"
                    f"🔗 {res.get('live_url')}"
                )
            else:
                msg = f"⚫ {username} hiện không live."
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ Không check được TikTok.")

    except Exception as e:
        logger.error(f"Lỗi checklive: {e}")
        await update.message.reply_text("❌ API TikTok lỗi.")

# ====== MAIN ======
def main():
    if not BOT_TOKEN:
        print("❌ Thiếu TELEGRAM_TOKEN trong Render!")
        return

    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkfb", checkfb))
    app.add_handler(CommandHandler("getidfb", getidfb))
    app.add_handler(CommandHandler("checkfblive", checkfblive))
    app.add_handler(CommandHandler("checklive", checklive))

    print("🚀 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
