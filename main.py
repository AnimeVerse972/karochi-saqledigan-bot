from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from keep_alive import keep_alive
from pymongo import MongoClient
import os

# === YUKLAMALAR ===
load_dotenv()
keep_alive()

API_TOKEN = os.getenv("API_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "telegram_bot")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_collection = db["users"]
codes_collection = db["anime_posts"]

ADMINS = [6486825926, 7575041003]

# === MONGODB FUNKSIYALARI ===
def load_users():
    return [doc["user_id"] for doc in users_collection.find({}, {"_id": 0})]

def save_user(user_id):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

def load_codes():
    codes = {}
    for doc in codes_collection.find():
        codes[doc["code"]] = {"channel": doc["channel"], "message_id": doc["message_id"]}
    return codes

def save_code(code, channel, message_id):
    codes_collection.update_one({"code": code}, {"$set": {"channel": channel, "message_id": message_id}}, upsert=True)

def remove_code(code):
    codes_collection.delete_one({"code": code})

def count_users():
    return users_collection.count_documents({})

def count_codes():
    return codes_collection.count_documents({})

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

# === START ===
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    save_user(message.from_user.id)

    if await is_user_subscribed(message.from_user.id):
        buttons = [[KeyboardButton("\ud83d\udce2 Reklama"), KeyboardButton("\ud83d\udcbc Homiylik")]]
        if is_user_admin(message.from_user.id):
            buttons.append([KeyboardButton("\ud83d\udee0 Admin panel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await message.answer("\u2705 Obuna bor. Kodni yuboring:", reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Kanal", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
        ).add(
            InlineKeyboardButton("\u2705 Tekshirish", callback_data="check_sub")
        )
        await message.answer("\u2757 Iltimos, kanalga obuna bo\u2018ling:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(callback_query: types.CallbackQuery):
    if await is_user_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("\u2705 Obuna tekshirildi. Kod yuboring.")
    else:
        await callback_query.answer("\u2757 Hali ham obuna emassiz!", show_alert=True)

# === MENYU ===
@dp.message_handler(lambda m: m.text == "\ud83d\udce2 Reklama")
async def reklama_handler(message: types.Message):
    await message.answer("Reklama uchun: @DiyorbekPTMA")

@dp.message_handler(lambda m: m.text == "\ud83d\udcbc Homiylik")
async def homiy_handler(message: types.Message):
    await message.answer("Homiylik uchun karta: `8800904257677885`")

@dp.message_handler(lambda m: m.text == "\ud83d\udee0 Admin panel")
async def admin_handler(message: types.Message):
    if is_user_admin(message.from_user.id):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("\u2795 Kod qo\u2018shish"), KeyboardButton("\ud83d\udcc4 Kodlar ro\u2018yxati"))
        markup.add(KeyboardButton("\u274c Kodni o\u2018chirish"), KeyboardButton("\ud83d\udcca Statistika"))
        markup.add(KeyboardButton("\ud83d\udc64 Admin qo\u2018shish"), KeyboardButton("\ud83d\udd19 Orqaga"))
        await message.answer("\ud83d\udc6e\u200d\u2642\ufe0f Admin paneliga xush kelibsiz!", reply_markup=markup)
    else:
        await message.answer("\u26d4 Siz admin emassiz!")

@dp.message_handler(lambda m: m.text == "\ud83d\udd19 Orqaga")
async def back_to_menu(message: types.Message):
    buttons = [[KeyboardButton("\ud83d\udce2 Reklama"), KeyboardButton("\ud83d\udcbc Homiylik")]]
    if is_user_admin(message.from_user.id):
        buttons.append([KeyboardButton("\ud83d\udee0 Admin panel")])
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("\ud83c\udfe0 Asosiy menyuga qaytdingiz.", reply_markup=markup)

# === KOD QO'SHISH ===
@dp.message_handler(lambda m: m.text == "\u2795 Kod qo\u2018shish")
async def start_add_code(message: types.Message):
    await message.answer("\u2795 Yangi kod va post ID ni yuboring. Masalan: 47 1000")
    await AdminStates.waiting_for_code.set()

@dp.message_handler(state=AdminStates.waiting_for_code)
async def add_code_handler(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("\u274c Noto\u2018g\u2018ri format! Masalan: 47 1000")
        return
    code, msg_id = parts
    save_code(code, CHANNEL_USERNAME, int(msg_id))
    await message.answer(f"\u2705 Kod qo\u2018shildi: {code} → {msg_id}")
    await state.finish()

# === KOD O'CHIRISH ===
@dp.message_handler(lambda m: m.text == "\u274c Kodni o\u2018chirish")
async def start_remove_code(message: types.Message):
    await message.answer("\ud83d\uddd1 O\u2018chirmoqchi bo\u2018lgan kodni yuboring:")
    await AdminStates.waiting_for_remove.set()

@dp.message_handler(state=AdminStates.waiting_for_remove)
async def remove_code_handler(message: types.Message, state: FSMContext):
    code = message.text.strip()
    remove_code(code)
    await message.answer(f"\u2705 Kod o\u2018chirildi: {code}")
    await state.finish()

# === KODLAR RO'YXATI ===
@dp.message_handler(lambda m: m.text == "\ud83d\udcc4 Kodlar ro\u2018yxati")
async def list_codes_handler(message: types.Message):
    codes = load_codes()
    if not codes:
        await message.answer("\ud83d\udcc2 Hozircha hech qanday kod yo\u2018q.")
    else:
        text = "\ud83d\udcc4 Kodlar ro\u2018yxati:\n"
        for code, info in codes.items():
            text += f"\ud83d\udd22 {code} — ID: {info['message_id']}\n"
        await message.answer(text)

# === STATISTIKA ===
@dp.message_handler(lambda m: m.text == "\ud83d\udcca Statistika")
async def stat_handler(message: types.Message):
    try:
        chat = await bot.get_chat(CHANNEL_USERNAME)
        members = await bot.get_chat_members_count(chat.id)
        await message.answer(f"\ud83d\udcca Obunachilar: {members}\n\ud83d\udce6 Kodlar soni: {count_codes()} ta\n\ud83d\udc65 Foydalanuvchilar: {count_users()} ta")
    except:
        await message.answer("\u26a0\ufe0f Statistika olishda xatolik!")

# === ADMIN QO'SHISH ===
@dp.message_handler(lambda m: m.text == "\ud83d\udc64 Admin qo\u2018shish")
async def start_add_admin(message: types.Message):
    await message.answer("\ud83c\udd94 Yangi adminning Telegram ID raqamini yuboring:")
    await AdminStates.waiting_for_admin_id.set()

@dp.message_handler(state=AdminStates.waiting_for_admin_id)
async def add_admin_handler(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if user_id.isdigit():
        user_id = int(user_id)
        if user_id not in ADMINS:
            ADMINS.append(user_id)
            await message.answer(f"\u2705 Admin qo\u2018shildi: `{user_id}`")
        else:
            await message.answer("\u26a0\ufe0f Bu foydalanuvchi allaqachon admin.")
    else:
        await message.answer("\u274c Noto\u2018g\u2018ri ID!")
    await state.finish()

# === KODNI QABUL QILISH ===
@dp.message_handler(lambda msg: msg.text.strip().isdigit())
async def handle_code(message: types.Message):
    code = message.text.strip()
    if not await is_user_subscribed(message.from_user.id):
        await message.answer("\u2757 Koddan foydalanish uchun avval kanalga obuna bo\u2018ling.")
        return
    codes = load_codes()
    if code in codes:
        info = codes[code]
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=info["channel"],
            message_id=info["message_id"],
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("\ud83d\udcc5 Yuklab olish", url=f"https://t.me/{info['channel'].strip('@')}/{info['message_id']}")
            )
        )
    else:
        await message.answer("\u274c Bunday kod topilmadi. Iltimos, to\u2018g\u2018ri kod yuboring.")

# === BOTNI ISHGA TUSHURISH ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
