import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telegram
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai

# Simple HTTP Server for Render Health Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your AI Social Media Manager. Send /generate <topic> to create content.")

async def generate_post(update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("Please provide a topic. Example: /generate AI Trends")
        return
    await update.message.reply_text("Generating post with Gemini 1.5 Pro...")
    prompt = f"Create an engaging Facebook post about: {topic}. Include hashtags and emojis."
    response = model.generate_content(prompt)
    await update.message.reply_text(f"Draft Post:\n\n{response.text}")

def main():
    # Start Health Check Server in Background Thread
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    # Start Telegram Bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate_post))
    app.run_polling()

if __name__ == "__main__":
    main()
