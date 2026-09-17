import os
import requests
import telegram
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai

# API Keys & Tokens (Environment variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# Telegram Handlers
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your AI Social Media Manager. Send /generate <topic> to create content.")

async def generate_post(update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("Please provide a topic. Example: /generate AI Trends")
        return

    await update.message.reply_text("Generating post with Gemini 1.5 Pro...")
    
    prompt = f"Create an engaging Facebook post about: {topic}. Include relevant hashtags and emojis."
    response = model.generate_content(prompt)
    generated_text = response.text

    # Human-in-the-loop confirmation message
    await update.message.reply_text(f"Draft Post:\n\n{generated_text}\n\nReply with /publish to post on Facebook Page.")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate_post))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()