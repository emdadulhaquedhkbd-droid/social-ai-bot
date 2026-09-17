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

client = genai.Client(api_key=GEMINI_API_KEY)
last_generated_post = {}

# ১. উদাহরণ হিসেবে পোস্ট সেভ করার ফাংশন
async def train_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_learn = " ".join(context.args)
    if not text_to_learn:
        await update.message.reply_text("দয়া করে শেখানোর জন্য কোনো পোস্টের টেক্সট বা লিংক দিন।\nউদাহরণ: /train [পোস্টের টেক্সট]")
        return
        
    with open("sample_posts.txt", "a", encoding="utf-8") as f:
        f.write(text_to_learn + "\n---\n")
        
    await update.message.reply_text("✅ ধন্যবাদ! এই পোস্টের রাইটিং স্টাইলটি আমি শিখে নিলাম। পরবর্তী পোস্ট তৈরির সময় আমি এই স্টাইল ফলো করব।")

# ২. স্টাইলগুলো লোড করার হেল্পার ফাংশন
def get_saved_examples():
    if os.path.exists("sample_posts.txt"):
        with open("sample_posts.txt", "r", encoding="utf-8") as f:
            return f.read()
    return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I am your AI Social Media Manager.\n\n"
        "Commands:\n"
        "/train <text/link> - আমাকে আপনার পছন্দের পোস্টের স্টাইল শেখান\n"
        "/generate <topic> - নতুন বাংলা পোস্ট তৈরি করুন\n"
        "/publish - ড্রাফট পোস্টটি ফেসবুক পেজে পাবলিশ করুন"
    )

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("দয়া করে একটি টপিক দিন। যেমন: /generate আর্টিফিশিয়াল ইন্টেলিজেন্স")
        return
        
    await update.message.reply_text("Gemini আপনার শেখানো স্টাইলে বাংলায় পোস্ট তৈরি করছে...")
    
    # জমানো উদাহরণগুলো পড়া
    learned_styles = get_saved_examples()
    
    # প্রম্পটটি বাংলায় এবং শেখানো স্টাইলের ওপর ভিত্তি করে সাজানো
    prompt = (
        f"You are a professional social media manager writing engaging Facebook posts in BANGLA (বাংলা).\n\n"
        f"Here are some examples of posts that the user likes and wants you to mimic the writing style, tone, and formatting of:\n"
        f"--- SAMPLE STYLES ---\n"
        f"{learned_styles}\n"
        f"--- END SAMPLE STYLES ---\n\n"
        f"Task: Create a fresh, highly engaging Facebook post in BANGLA about the topic: '{topic}'.\n"
        f"Rules:\n"
        f"1. Write strictly in fluent Bangla.\n"
        f"2. Match the tone, formatting, and emoji usage of the sample styles provided above.\n"
        f"3. Do NOT use any Markdown formatting like asterisks (** or *), bold syntax, or headings.\n"
        f"4. Keep it natural, conversational, and direct-publish ready for Facebook."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt
        )
        post_content = response.text
        last_generated_post[user_id] = post_content
        
        await update.message.reply_text(
            f"📝 **Draft Post (Bangla):**\n\n{post_content}\n\n👉 Send /publish to post this to Facebook."
        )
    except Exception as e:
        await update.message.reply_text(f"Error generating content: {e}")

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    post_content = last_generated_post.get(user_id)
    
    if not post_content:
        await update.message.reply_text("No draft found! Please generate a post first using /generate <topic>.")
        return

    await update.message.reply_text("Publishing to Facebook Page...")
    
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
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("train", train_bot)) # নতুন কমান্ড
    app.add_handler(CommandHandler("generate", generate_post))
    app.add_handler(CommandHandler("publish", publish_post))
    
    print("Bot is polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
