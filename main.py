from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from keep_alive import keep_alive
import os
import json

load_dotenv()
keep_alive()

API_TOKEN = os.getenv("API_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

ADMINS = [6486825926, 7575041003]

# === FAYL FUNKSIYALARI ===

def load_codes():
    try:
        with open("anime_posts.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_codes(data):
    with open("anime_posts.json", "w") as f:
        json.dump(data, f, indent=4)

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# === YORDAMCHI ===

def is_user_admin(user_id):
    return user_id in ADMINS

async def is_user_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# === FSM HOLATLAR ===

class AdminStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_remove = State()
    waiting_for_admin_id = State()

# === /start ===

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    users = load_users()
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_users(users)

    if await is_user_subscribed(message.from_user.id):
        buttons = [[KeyboardButton("📢 Reklama"), KeyboardButton("💼 Homiylik")]]
        if is_user_admin(message.from_user.id):
            buttons.append([KeyboardButton("🛠 Admin panel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await message.answer("✅ Obuna bor. Kodni yuboring:", reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Kanal", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
        ).add(
            InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")
        )
        await message.answer("❗ Iltimos, kanalga obuna bo‘ling:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(callback_query: types.CallbackQuery):
    if await is_user_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("✅ Obuna tekshirildi. Kod yuboring.")
    else:
        await callback_query.answer("❗ Hali ham obuna emassiz!", show_alert=True)

# === FOYDALI MENYULAR ===

@dp.message_handler(lambda m: m.text == "📢 Reklama")
async def reklama_handler(message: types.Message):
    await message.answer("Reklama uchun: @DiyorbekPTMA")

@dp.message_handler(lambda m: m.text == "💼 Homiylik")
async def homiy_handler(message: types.Message):
    await message.answer("Homiylik uchun karta: `8800904257677885`")

@dp.message_handler(lambda m: m.text == "🛠 Admin panel")
async def admin_handler(message: types.Message):
    if is_user_admin(message.from_user.id):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton("➕ Kod qo‘shish"), KeyboardButton("📄 Kodlar ro‘yxati")
        )
        markup.add(
            KeyboardButton("❌ Kodni o‘chirish"), KeyboardButton("📊 Statistika")
        )
        markup.add(
            KeyboardButton("👤 Admin qo‘shish"), KeyboardButton("🔙 Orqaga")
        )
        await message.answer("👮‍♂️ Admin paneliga xush kelibsiz!", reply_markup=markup)
    else:
        await message.answer("⛔ Siz admin emassiz!")

@dp.message_handler(lambda m: m.text == "🔙 Orqaga")
async def back_to_menu(message: types.Message):
    buttons = [[KeyboardButton("📢 Reklama"), KeyboardButton("💼 Homiylik")]]
    if is_user_admin(message.from_user.id):
        buttons.append([KeyboardButton("🛠 Admin panel")])
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=markup)

# === ➕ Kod qo‘shish ===

@dp.message_handler(lambda m: m.text == "➕ Kod qo‘shish")
async def start_add_code(message: types.Message):
    await message.answer("➕ Yangi kod va post ID ni yuboring. Masalan: 47 1000")
    await AdminStates.waiting_for_code.set()

@dp.message_handler(state=AdminStates.waiting_for_code)
async def add_code_handler(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("❌ Noto‘g‘ri format! Masalan: 47 1000")
        return
    code, msg_id = parts
    anime_posts = load_codes()
    anime_posts[code] = {"channel": CHANNEL_USERNAME, "message_id": int(msg_id)}
    save_codes(anime_posts)
    await message.answer(f"✅ Kod qo‘shildi: {code} → {msg_id}")
    await state.finish()

# === ❌ Kodni o‘chirish ===

@dp.message_handler(lambda m: m.text == "❌ Kodni o‘chirish")
async def start_remove_code(message: types.Message):
    await message.answer("🗑 O‘chirmoqchi bo‘lgan kodni yuboring:")
    await AdminStates.waiting_for_remove.set()

@dp.message_handler(state=AdminStates.waiting_for_remove)
async def remove_code_handler(message: types.Message, state: FSMContext):
    code = message.text.strip()
    anime_posts = load_codes()
    if code in anime_posts:
        del anime_posts[code]
        save_codes(anime_posts)
        await message.answer(f"✅ Kod o‘chirildi: {code}")
    else:
        await message.answer("❌ Bunday kod yo‘q.")
    await state.finish()

# === 📄 Kodlar ro‘yxati ===

@dp.message_handler(lambda m: m.text == "📄 Kodlar ro‘yxati")
async def list_codes_handler(message: types.Message):
    anime_posts = load_codes()
    if not anime_posts:
        await message.answer("📂 Hozircha hech qanday kod yo‘q.")
    else:
        text = "📄 Kodlar ro‘yxati:\n"
        for code, info in anime_posts.items():
            text += f"🔢 {code} — ID: {info['message_id']}\n"
        await message.answer(text)

# === 📊 Statistika ===

@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stat_handler(message: types.Message):
    try:
        chat = await bot.get_chat(CHANNEL_USERNAME)
        members = await bot.get_chat_members_count(chat.id)
        codes = load_codes()
        users = load_users()
        await message.answer(f"📊 Obunachilar: {members}\n📦 Kodlar soni: {len(codes)} ta\n👥 Foydalanuvchilar: {len(users)} ta")
    except:
        await message.answer("⚠️ Statistika olishda xatolik!")

# === 👤 Admin qo‘shish ===

@dp.message_handler(lambda m: m.text == "👤 Admin qo‘shish")
async def start_add_admin(message: types.Message):
    await message.answer("🆔 Yangi adminning Telegram ID raqamini yuboring:")
    await AdminStates.waiting_for_admin_id.set()

@dp.message_handler(state=AdminStates.waiting_for_admin_id)
async def add_admin_handler(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if user_id.isdigit():
        user_id = int(user_id)
        if user_id not in ADMINS:
            ADMINS.append(user_id)
            await message.answer(f"✅ Admin qo‘shildi: `{user_id}`")
        else:
            await message.answer("⚠️ Bu foydalanuvchi allaqachon admin.")
    else:
        await message.answer("❌ Noto‘g‘ri ID!")
    await state.finish()

# === 🔢 Kod bilan javob berish ===

@dp.message_handler(lambda msg: msg.text.strip().isdigit())
async def handle_code(message: types.Message):
    code = message.text.strip()
    if not await is_user_subscribed(message.from_user.id):
        await message.answer("❗ Koddan foydalanish uchun avval kanalga obuna bo‘ling.")
        return
    anime_posts = load_codes()
    if code in anime_posts:
        info = anime_posts[code]
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=info["channel"],
            message_id=info["message_id"],
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📥 Yuklab olish", url=f"https://t.me/{info['channel'].strip('@')}/{info['message_id']}")
            )
        )
    else:
        await message.answer("❌ Bunday kod topilmadi. Iltimos, to‘g‘ri kod yuboring.")

# === BOTNI ISHGA TUSHURISH ===

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
