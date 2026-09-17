import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from google import genai

# Render Health Check Server setup
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your AI Social Media Manager. Send /generate <topic> to create content.")

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("Please provide a topic. Example: /generate AI Trends")
        return
        
    await update.message.reply_text("Generating post with Gemini...")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Create an engaging Facebook post about: {topic}. Include relevant hashtags and emojis."
        )
        await update.message.reply_text(f"Draft Post:\n\n{response.text}")
    except Exception as e:
        await update.message.reply_text(f"Error generating content: {e}")

def main():
    # Start Web Server for Render in background thread
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    # Start Telegram Bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate_post))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
