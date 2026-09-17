import os
import threading
import requests
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
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Store last generated post temporarily
last_generated_post = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your AI Social Media Manager.\n\nCommands:\n/generate <topic> - Draft a post\n/publish - Post the draft to Facebook Page")

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("Please provide a topic. Example: /generate AI Trends")
        return
        
    await update.message.reply_text("Generating post with Gemini...")
    
    try:
        # Standard model name used here
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Create an engaging Facebook post about: {topic}. Include relevant hashtags and emojis."
        )
        post_content = response.text
        last_generated_post[user_id] = post_content
        
        await update.message.reply_text(f"📝 **Draft Post:**\n\n{post_content}\n\n👉 Send /publish to post this to Facebook.")
    except Exception as e:
        await update.message.reply_text(f"Error generating content: {e}")

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    post_content = last_generated_post.get(user_id)
    
    if not post_content:
        await update.message.reply_text("No draft found! Please generate a post first using /generate <topic>.")
        return

    await update.message.reply_text("Publishing to Facebook Page...")
    
    # Meta Graph API Request
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {
        'message': post_content,
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        await update.message.reply_text("🎉 Successfully published to your Facebook Page!")
    else:
        await update.message.reply_text(f"Failed to publish. Error: {res.json()}")

def main():
    # Start Web Server for Render in background thread
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    # Start Telegram Bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate_post))
    app.add_handler(CommandHandler("publish", publish_post))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
