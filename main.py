import os
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- تنظیمات ---
TOKEN = os.getenv("BOT_TOKEN")
MERCHANT_ID = os.getenv("MERCHANT_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DB_NAME = "database.db"

# --- دیتابیس ---
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT 'free',
    expiry TEXT,
    ref_id TEXT
)
''')
conn.commit()

# --- توابع کمکی ---
def solve_trig(text):
    return "حل مثلثاتی: sin(30) = 0.5"

def solve_triangle(text):
    return "مساحت مثلث = ½ × پایه × ارتفاع"

# --- پرداخت ---
async def payment_callback(call: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = call.from_user.id
    amount = 50000
    description = "اشتراک VIP مثلث‌یار AI"
    bot_username = (await context.bot.get_me()).username
    callback_url = f"https://t.me/{bot_username}?start=verify"

    payload = {
        'merchant_id': MERCHANT_ID,
        'amount': amount * 10,
        'description': description,
        'callback_url': callback_url
    }
    try:
        r = requests.post('https://api.zarinpal.com/pg/v4/payment/request.json', json=payload)
        data = r.json()
        if data['data']['code'] == 100:
            authority = data['data']['authority']
            url = f"https://www.zarinpal.com/pg/StartPay/{authority}"
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("پرداخت", url=url)]])
            await context.bot.edit_message_text(
                f"مبلغ: {amount:,} تومان\nلینک پرداخت:",
                call.message.chat.id, call.message.message_id,
                reply_markup=markup
            )
            cursor.execute("UPDATE users SET ref_id=? WHERE user_id=?", (authority, user_id))
            conn.commit()
        else:
            await context.bot.answer_callback_query(call.id, "خطا در پرداخت!")
    except Exception as e:
        await context.bot.answer_callback_query(call.id, "سرور پرداخت در دسترس نیست.")

# --- حل سوالات ---
async def solve(message: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = message.from_user.id
    cursor.execute("SELECT status, expiry FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, status) VALUES (?, 'free')", (user_id,))
        conn.commit()

    text = message.text
    if any(func in text for func in ['sin', 'cos', 'tan']):
        response = solve_trig(text)
    elif 'مثلث' in text:
        response = solve_triangle(text)
    else:
        response = "سوال مثلثاتی بنویسید!"
    
    await context.bot.reply_to(message, response)

# --- پنل ادمین ---
async def admin_panel(message: Update, context: ContextTypes.DEFAULT_TYPE):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users WHERE status='vip'")
    vip_count = cursor.fetchone()[0]
    await context.bot.reply_to(message, f"پنل ادمین\n\nکاربران VIP: {vip_count}\nدرآمد تقریبی: نامشخص")

# --- اجرای ربات ---
app = Application.builder().token(TOKEN).build()
app.add_handler(CallbackQueryHandler(payment_callback, pattern="^pay$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, solve))
app.add_handler(CommandHandler("admin", admin_panel))

print("مثلث‌یار AI Pro در حال اجراست...")
app.run_polling()
