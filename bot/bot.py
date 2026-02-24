import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = os.getenv("ALLOWED_USER_IDS", "")
PR_AGENT_URL = os.getenv("PR_AGENT_URL", "")
DR_AGENT_URL = os.getenv("DR_AGENT_URL", "")

allowed = set()
for x in [s.strip() for s in ALLOWED_USER_IDS.split(",") if s.strip()]:
    try:
        allowed.add(int(x))
    except ValueError:
        pass


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    if not allowed:
        return True  # if empty, allow all (not recommended)
    return user.id in allowed


def pick_agent(cluster: str) -> str:
    c = cluster.lower()
    if c == "pr":
        return PR_AGENT_URL
    if c == "dr":
        return DR_AGENT_URL
    return ""


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    await update.message.reply_text(f"Your Telegram user id: {user.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Unauthorized.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /status pr|dr")
        return

    cluster = context.args[0].lower()
    base = pick_agent(cluster)
    if not base:
        await update.message.reply_text("Unknown cluster. Use pr or dr.")
        return

    try:
        r = requests.get(f"{base}/status", timeout=15)
        await update.message.reply_text(r.text[:3500])
    except Exception as e:
        await update.message.reply_text(f"Error calling agent: {e}")


async def failures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Unauthorized.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /failures pr|dr")
        return

    cluster = context.args[0].lower()
    base = pick_agent(cluster)
    if not base:
        await update.message.reply_text("Unknown cluster. Use pr or dr.")
        return

    try:
        r = requests.get(f"{base}/failures", timeout=20)
        await update.message.reply_text(r.text[:3500])
    except Exception as e:
        await update.message.reply_text(f"Error calling agent: {e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("failures", failures))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()