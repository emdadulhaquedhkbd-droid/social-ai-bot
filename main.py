import os
import threading
import requests
import io
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

# Store last generated post & image URL temporarily
last_generated_post = {}

async def train_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_learn = " ".join(context.args)
    if not text_to_learn:
        await update.message.reply_text("দয়া করে শেখানোর জন্য কোনো পোস্টের টেক্সট দিন।\nউদাহরণ: /train [পোস্টের টেক্সট]")
        return
        
    with open("sample_posts.txt", "a", encoding="utf-8") as f:
        f.write(text_to_learn + "\n---\n")
        
    await update.message.reply_text("✅ ধন্যবাদ! এই পোস্টের রাইটিং স্টাইলটি আমি শিখে নিলাম।")

def get_saved_examples():
    if os.path.exists("sample_posts.txt"):
        with open("sample_posts.txt", "r", encoding="utf-8") as f:
            return f.read()
    return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I am your AI Social Media Manager.\n\n"
        "Commands:\n"
        "/train <text> - আমাকে আপনার পছন্দের পোস্টের স্টাইল শেখান\n"
        "/generate <topic> - ছবি ও হ্যাশট্যাগসহ বাংলা পোস্ট তৈরি করুন\n"
        "/publish - ড্রাফট পোস্ট ও ছবি ফেসবুকে পাবলিশ করুন"
    )

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("দয়া করে একটি টপিক দিন। যেমন: /generate আর্টিফিশিয়াল ইন্টেলিজেন্স")
        return
        
    await update.message.reply_text("Gemini বাংলা পোস্ট এবং প্রাসঙ্গিক ইমেজ জেনারেট করছে...")
    
    learned_styles = get_saved_examples()
    
    prompt = (
        f"You are a professional social media manager writing Facebook posts in BANGLA (বাংলা).\n\n"
        f"--- SAMPLE STYLES ---\n"
        f"{learned_styles}\n"
        f"--- END SAMPLE STYLES ---\n\n"
        f"Task: Create a Facebook post in BANGLA about: '{topic}'.\n"
        f"Rules:\n"
        f"1. Write strictly in fluent Bangla matching the sample styles.\n"
        f"2. Add 5 to 8 highly relevant and trending hashtags (both Bangla and English) at the end.\n"
        f"3. Do NOT use any Markdown formatting like asterisks (** or *).\n"
        f"4. At the very last line of your output, write a brief English image prompt suitable for AI image generation, formatted strictly as: IMAGE_PROMPT: <english description>."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt
        )
        full_output = response.text
        
        # Extract post content and image prompt
        image_prompt = "technology concept art, realistic, high quality"
        if "IMAGE_PROMPT:" in full_output:
            parts = full_output.split("IMAGE_PROMPT:")
            post_content = parts[0].strip()
            image_prompt = parts[1].strip()
        else:
            post_content = full_output.strip()
            
        # Pollinations AI দিয়ে ইমেজ জেনারেশন URL
        encoded_prompt = requests.utils.quote(image_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
        
        # ড্রাফট সেভ রাখা
        last_generated_post[user_id] = {
            "text": post_content,
            "image_url": image_url
        }
        
        # টেলিগ্রামে ছবি ও ক্যাプション পাঠানো
        await update.message.reply_photo(
            photo=image_url,
            caption=f"📝 **Draft Post (Bangla):**\n\n{post_content}\n\n👉 Send /publish to post this to Facebook Page."
        )
        
    except Exception as e:
        await update.message.reply_text(f"Error generating content: {e}")

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    draft = last_generated_post.get(user_id)
    
    if not draft:
        await update.message.reply_text("No draft found! Please generate a post first using /generate <topic>.")
        return

    await update.message.reply_text("Publishing post with image to Facebook Page...")
    
    # Meta Graph API দিয়ে ফটো এবং ক্যাপশন একত্রে পোস্ট করার এন্ডপয়েন্ট
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    payload = {
        'caption': draft["text"],
        'url': draft["image_url"],
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        await update.message.reply_text("🎉 Successfully published post and image to your Facebook Page!")
    else:
        await update.message.reply_text(f"Failed to publish. Error: {res.json()}")

def main():
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("train", train_bot))
    app.add_handler(CommandHandler("generate", generate_post))
    app.add_handler(CommandHandler("publish", publish_post))
    
    print("Bot is polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
