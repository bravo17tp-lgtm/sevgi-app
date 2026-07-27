"""Telegram bot — faqat ro'yxatdan o'tish/tasdiqlash va Mini App'ni ochish uchun."""

import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from . import db

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
APP_URL = os.environ.get("APP_URL", "")  # masalan https://sizning-servis.onrender.com


def open_app_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💞 Ochish", web_app=WebAppInfo(url=APP_URL))]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if user is None:
        if user_id == ADMIN_ID:
            db.create_user(user_id, update.effective_user.first_name, status="approved", is_admin=True)
            await update.message.reply_text(
                "Xush kelibsiz, admin! Ilovani pastdagi tugma orqali oching. 💞",
                reply_markup=open_app_kb(),
            )
            return
        db.create_user(user_id, update.effective_user.first_name, status="pending")
        await update.message.reply_text("So'rovingiz yuborildi, tasdiqlanishini kuting. ⏳")
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"""🆕 *Yangi kirish so'rovi*

👤 Ism: {update.effective_user.first_name}
📛 Username: @{update.effective_user.username or 'yo\'q'}
🆔 ID: `{user_id}`""",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user_id}"),
                        InlineKeyboardButton("🟡 Kutish", callback_data=f"hold_{user_id}"),
                        InlineKeyboardButton("❌ Rad etish", callback_data=f"deny_{user_id}"),
                        InlineKeyboardButton("⛔ Ban", callback_data=f"ban_{user_id}"),
                    ]]),
                )
            except Exception:
                pass
        return

    if user["status"] == "pending":
        await update.message.reply_text("So'rovingiz hali ko'rib chiqilmoqda. ⏳")
        return
    if user["status"] == "denied":
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Qayta yuborish", callback_data=f"resend_{user_id}")]])
        await update.message.reply_text("Kechirasiz, kirish so'rovingiz rad etilgan.",reply_markup=kb)
        return
    if user["status"] == "banned":
        await update.message.reply_text("🚫 Siz bloklangansiz.")
        return

    await update.message.reply_text(
        f"Xush kelibsiz, {user['name']}! 🌷", reply_markup=open_app_kb()
    )


async def approve_deny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, uid = query.data.split("_")
    uid = int(uid)
    target = db.get_user(uid)
    if not target:
        await query.edit_message_text("Foydalanuvchi topilmadi.")
        return

    if action == "approve":
        db.set_user_status(uid, "approved")
        await query.edit_message_text(f"✅ {target['name']} tasdiqlandi.")
        await context.bot.send_message(
            uid, "So'rovingiz tasdiqlandi! 🎉", reply_markup=open_app_kb()
        )
    elif action=="hold":
        db.set_user_status(uid,"pending")
        await query.edit_message_text(f"🟡 {target['name']} kutishga qoldirildi.")
        await context.bot.send_message(uid,"⏳ So'rovingiz qayta ko'rib chiqiladi.")
    elif action=="deny":
        db.set_user_status(uid, "denied")
        await query.edit_message_text(f"❌ {target['name']} rad etildi.")
        await context.bot.send_message(uid, "Kechirasiz, kirish so'rovingiz rad etildi.")

    elif action=="resend":
        db.resend_request(uid)
    elif action=="ban":
        db.set_user_status(uid,"banned")
        await query.edit_message_text(f"⛔ {target['name']} ban qilindi.")
        await context.bot.send_message(uid,"🚫 Siz ushbu botdan foydalanishingiz bloklandi.")


def build_bot_app() -> Application:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(approve_deny, pattern="^(approve|deny|ban|hold|resend)_"))
    return application
