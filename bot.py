import os
import logging
import html
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import Database
from downloader import VideoDownloader

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8541787529:AAEgFcwuqOoa8zhz6x1zBL-MXbCn66K7Nes")

db = Database()
downloader = VideoDownloader()


def e(text: str) -> str:
    """HTML maxsus belgilardan himoya qilish"""
    return html.escape(str(text))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    db.save_user(user_id, username)
    files = db.get_user_files(user_id)

    if files:
        keyboard = []
        for file in files:
            btn_text = f"🎬 {file['title'][:30]}... [{file['quality']}]"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f"file_{file['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🗑 Barchasini o'chirish", callback_data="clear_all")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"👋 Salom, {e(username)}!\n\n"
            f"📁 <b>Sizning yuborilgan fayllaringiz:</b>\n"
            f"Quyidagi videolardan birini tanlang:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"👋 Salom, {e(username)}!\n\n"
            f"🎥 <b>Video Downloader Bot</b>\n\n"
            f"YouTube yoki Instagram linkini yuboring,\n"
            f"men uni yuklab beraman! ✅\n\n"
            f"<b>Qo'llab-quvvatlanadigan saytlar:</b>\n"
            f"• youtube.com\n"
            f"• youtu.be\n"
            f"• instagram.com",
            parse_mode='HTML'
        )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not any(domain in text for domain in ['youtube.com', 'youtu.be', 'instagram.com']):
        await update.message.reply_text(
            "❌ Noto'g'ri link!\n\n"
            "Iltimos YouTube yoki Instagram linkini yuboring."
        )
        return

    msg = await update.message.reply_text("⏳ Link tekshirilmoqda...")

    try:
        info = await downloader.get_video_info(text)

        if not info:
            await msg.edit_text("❌ Video topilmadi yoki link noto'g'ri.")
            return

        context.user_data['pending_url'] = text
        context.user_data['video_info'] = info

        keyboard = []
        for fmt in info['formats']:
            size_mb = fmt['filesize'] / (1024 * 1024) if fmt['filesize'] else 0
            size_kb = fmt['filesize'] / 1024 if fmt['filesize'] else 0

            if size_mb >= 1:
                size_str = f"{size_mb:.1f} MB"
            else:
                size_str = f"{size_kb:.0f} KB"

            btn_text = f"📹 {fmt['quality']} — {size_str}"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f"quality_{fmt['format_id']}")
            ])

        keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        title = e(info['title'][:50])
        await msg.edit_text(
            f"🎬 <b>{title}</b>\n\n"
            f"⏱ Davomiyligi: {e(info['duration'])}\n"
            f"👁 Ko'rishlar: {e(info['view_count'])}\n\n"
            f"📊 <b>Sifatni tanlang:</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as ex:
        logger.error(f"Error getting video info: {ex}")
        await msg.edit_text(f"❌ Xatolik yuz berdi: {e(str(ex)[:100])}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("quality_"):
        format_id = data.replace("quality_", "")
        url = context.user_data.get('pending_url')
        info = context.user_data.get('video_info')

        if not url or not info:
            await query.edit_message_text("❌ Session muddati tugadi. Linkni qayta yuboring.")
            return

        selected_fmt = next((f for f in info['formats'] if f['format_id'] == format_id), None)
        if not selected_fmt:
            await query.edit_message_text("❌ Sifat topilmadi.")
            return

        await query.edit_message_text(
            f"⬇️ <b>Yuklanmoqda...</b>\n\n"
            f"📹 {e(info['title'][:40])}\n"
            f"🎯 Sifat: {e(selected_fmt['quality'])}\n\n"
            f"Iltimos kuting...",
            parse_mode='HTML'
        )

        try:
            file_path, file_size = await downloader.download_video(url, format_id)

            size_mb = file_size / (1024 * 1024)
            size_kb = file_size / 1024

            if size_mb >= 1:
                size_str = f"{size_mb:.1f} MB"
            else:
                size_str = f"{size_kb:.0f} KB"

            file_id_db = db.save_file(
                user_id=user_id,
                title=info['title'],
                url=url,
                quality=selected_fmt['quality'],
                file_size=size_str,
                format_id=format_id
            )

            with open(file_path, 'rb') as video_file:
                sent = await query.message.reply_video(
                    video=video_file,
                    caption=(
                        f"✅ <b>{e(info['title'][:50])}</b>\n\n"
                        f"📊 Sifat: <code>{e(selected_fmt['quality'])}</code>\n"
                        f"📦 Hajmi: <code>{e(size_str)}</code>"
                    ),
                    parse_mode='HTML',
                    supports_streaming=True
                )

            if sent.video:
                db.update_file_telegram_id(file_id_db, sent.video.file_id)

            os.remove(file_path)

            await query.edit_message_text(
                f"✅ <b>Video muvaffaqiyatli yuborildi!</b>\n\n"
                f"📹 {e(info['title'][:40])}\n"
                f"🎯 {e(selected_fmt['quality'])} — {e(size_str)}",
                parse_mode='HTML'
            )

        except Exception as ex:
            logger.error(f"Download error: {ex}")
            await query.edit_message_text(f"❌ Yuklashda xatolik: {e(str(ex)[:150])}")

    elif data.startswith("file_"):
        file_id = int(data.replace("file_", ""))
        file = db.get_file_by_id(file_id, user_id)

        if not file:
            await query.edit_message_text("❌ Fayl topilmadi.")
            return

        keyboard = [
            [InlineKeyboardButton("📥 Qayta yuklash", callback_data=f"redownload_{file_id}")],
            [InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_{file_id}")],
            [InlineKeyboardButton("🔗 Linkni ko'rish", callback_data=f"showurl_{file_id}")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📁 <b>{e(file['title'][:45])}</b>\n\n"
            f"🎯 Sifat: <code>{e(file['quality'])}</code>\n"
            f"📦 Hajmi: <code>{e(file['file_size'])}</code>\n"
            f"📅 Sana: {e(file['created_at'][:10])}\n\n"
            f"Quyidagi amallardan birini tanlang:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    elif data.startswith("redownload_"):
        file_id = int(data.replace("redownload_", ""))
        file = db.get_file_by_id(file_id, user_id)

        if not file:
            await query.edit_message_text("❌ Fayl topilmadi.")
            return

        if file.get('telegram_file_id'):
            await query.message.reply_video(
                video=file['telegram_file_id'],
                caption=f"✅ <b>{e(file['title'][:50])}</b>\n🎯 {e(file['quality'])} — {e(file['file_size'])}",
                parse_mode='HTML'
            )
            await query.answer("✅ Video yuborildi!")
        else:
            await query.answer("⚠️ Qayta yuklanmoqda...")
            await query.edit_message_text(
                f"⬇️ Qayta yuklanmoqda: {e(file['title'][:40])}...\nIltimos kuting..."
            )
            try:
                file_path, file_size = await downloader.download_video(file['url'], file['format_id'])
                with open(file_path, 'rb') as vf:
                    sent = await query.message.reply_video(
                        video=vf,
                        caption=f"✅ <b>{e(file['title'][:50])}</b>\n🎯 {e(file['quality'])}",
                        parse_mode='HTML'
                    )
                if sent.video:
                    db.update_file_telegram_id(file_id, sent.video.file_id)
                os.remove(file_path)
                await query.edit_message_text("✅ Video yuborildi!")
            except Exception as ex:
                await query.edit_message_text(f"❌ Xatolik: {e(str(ex)[:100])}")

    elif data.startswith("delete_"):
        file_id = int(data.replace("delete_", ""))
        db.delete_file(file_id, user_id)
        await query.edit_message_text("🗑 Fayl o'chirildi.")

    elif data.startswith("showurl_"):
        file_id = int(data.replace("showurl_", ""))
        file = db.get_file_by_id(file_id, user_id)
        if file:
            keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data=f"file_{file_id}")]]
            await query.edit_message_text(
                f"🔗 <b>Video linki:</b>\n<code>{e(file['url'])}</code>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    elif data == "back_to_list":
        files = db.get_user_files(user_id)
        if files:
            keyboard = []
            for f in files:
                btn_text = f"🎬 {f['title'][:30]}... [{f['quality']}]"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"file_{f['id']}")])
            keyboard.append([InlineKeyboardButton("🗑 Barchasini o'chirish", callback_data="clear_all")])
            await query.edit_message_text(
                "📁 <b>Sizning fayllaringiz:</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("📭 Fayllar yo'q. Link yuboring!")

    elif data == "clear_all":
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha, o'chir", callback_data="confirm_clear"),
                InlineKeyboardButton("❌ Yo'q", callback_data="back_to_list")
            ]
        ]
        await query.edit_message_text(
            "⚠️ Barcha fayllarni o'chirishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "confirm_clear":
        db.clear_user_files(user_id)
        await query.edit_message_text("✅ Barcha fayllar o'chirildi!")

    elif data == "cancel":
        await query.edit_message_text("❌ Bekor qilindi. Yangi link yuboring.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>Bot haqida:</b>\n\n"
        "1️⃣ YouTube yoki Instagram linkini yuboring\n"
        "2️⃣ Sifatni tanlang (video hajmi ko'rsatiladi)\n"
        "3️⃣ Video yuklanib sizga yuboriladi\n\n"
        "📌 /start — Menyuga qaytish\n"
        "📌 /help — Yordam\n\n"
        "✅ Barcha yuklab olingan videolar saqlanadi!",
        parse_mode='HTML'
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
