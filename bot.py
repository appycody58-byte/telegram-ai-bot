import os
import logging
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from groq import Groq
import yt_dlp
import tempfile
import os.path

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Environment Variables ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN and GROQ_API_KEY must be set as environment variables")

client = Groq(api_key=GROQ_API_KEY)

# ---------------- AI Chat ----------------
async def ai_reply(user_message: str) -> str:
    try:
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a powerful, helpful, and intelligent AI assistant. "
                        "Be clear, useful, and direct. "
                        "You can help with questions, explanations, coding, ideas, and general tasks."
                    )
                },
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Sorry, I had a problem thinking. Please try again."

# ---------------- Commands ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚀 **Feature-Rich AI Bot is Online!**\n\n"
        "I can:\n"
        "• Chat with AI intelligence\n"
        "• Download videos/audio\n"
        "• Manage groups (admin tools)\n"
        "• Help with many tasks\n\n"
        "Type /help to see all commands."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "**Available Commands:**\n\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/ai <question> - Ask the AI anything\n"
        "/download <url> - Download video/audio\n\n"
        "**Group Admin Commands** (Bot must be admin):\n"
        "/ban - Ban a user (reply to message)\n"
        "/kick - Kick a user\n"
        "/mute - Mute a user\n"
        "/unmute - Unmute a user\n"
        "/warn - Warn a user\n\n"
        "Just send a normal message and I will reply with AI."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /ai your question here")
        return
    question = " ".join(context.args)
    await update.message.reply_text("🧠 Thinking...")
    reply = await ai_reply(question)
    await update.message.reply_text(reply)

# ---------------- Downloader ----------------
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /download <video url>")
        return

    url = context.args[0]
    await update.message.reply_text("💾 Downloading... Please wait.")

    try:
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": "%(title)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "max_filesize": 50 * 1024 * 1024,  # 50MB limit for free tiers
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts["outtmpl"] = os.path.join(tmpdir, "%(title)s.%(ext)s")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            # Send the file
            with open(filename, "rb") as f:
                await update.message.reply_video(video=f, caption=info.get("title", "Downloaded"))

    except Exception as e:
        logger.error(f"Download error: {e}")
        await update.message.reply_text(
            f"❌ Download failed.\nPossible reasons: private video, too large, or unsupported site.\nError: {str(e)[:200]}"
        )

# ---------------- Group Admin Tools ----------------
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message to ban them.")
        return
    try:
        user = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🚫 Banned {user.full_name}")
    except Exception as e:
        await update.message.reply_text(f"Failed to ban: {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message to kick them.")
        return
    try:
        user = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🐎 Kicked {user.full_name}")
    except Exception as e:
        await update.message.reply_text(f"Failed to kick: {e}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message to mute them.")
        return
    try:
        user = update.message.reply_to_message.from_user
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)
        await update.message.reply_text(f"🔇 Muted {user.full_name}")
    except Exception as e:
        await update.message.reply_text(f"Failed to mute: {e}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message to unmute them.")
        return
    try:
        user = update.message.reply_to_message.from_user
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)
        await update.message.reply_text(f"🔊 Unmuted {user.full_name}")
    except Exception as e:
        await update.message.reply_text(f"Failed to unmute: {e}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message to warn them.")
        return
    user = update.message.reply_to_message.from_user
    await update.message.reply_text(f"⚠️ Warning issued to {user.full_name}")

# ---------------- Normal Messages → AI ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text:
        reply = await ai_reply(update.message.text)
        await update.message.reply_text(reply)

# ---------------- Main ----------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("download", download_command))

    # Admin
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))

    # Normal text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Feature-rich bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
