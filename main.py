import os, asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import google.generativeai as genai
from utils import create_pptx

# --- SOZLAMALAR (Siz bergan "iplar") ---
# Bot Tokeningiz
TOKEN = "8461901986:AAHIQLMa1RckCqGCU71PJuJZCCnfKdWjYXk"
# Gemini API Kalitingiz
GEMINI_KEY = "AIzaSyBtUB1yq7lZqF29RPozUiIpj0DT9Rh5eU8"

genai.configure(api_key=GEMINI_KEY)
# 404 xatosini bermaydigan, aniq yo'nalishli model nomi
model = genai.GenerativeModel('models/gemini-1.5-flash')

bot = Bot(token=TOKEN)
dp = Dispatcher()

class SlaydStates(StatesGroup):
    ism = State()
    mavzu = State()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    
    kb = [
        [types.KeyboardButton(text="🚀 Slayd yaratish")],
        [types.KeyboardButton(text="👥 Do'stlarni taklif qilish")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(f"Xush kelibsiz! 👋\nSizning referal havolangiz:\n{ref_link}", reply_markup=keyboard)

@dp.message(F.text == "👥 Do'stlarni taklif qilish")
async def share_ref(message: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"Botni ulashing:\n{ref_link}")

@dp.message(F.text == "🚀 Slayd yaratish")
async def start_slayd(message: types.Message, state: FSMContext):
    await message.answer("Slaydda muallif kim bo'lsin? (Ism-familiya):")
    await state.set_state(SlaydStates.ism)

@dp.message(SlaydStates.ism)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(muallif=message.text)
    await message.answer("Mavzuni kiriting (Masalan: Amir Temur hayoti):")
    await state.set_state(SlaydStates.mavzu)

@dp.message(SlaydStates.mavzu)
async def get_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    status = await message.answer("⌛ AI ishlamoqda, slayd tayyorlanyapti...")
    
    try:
        # Promptni kuchaytirdik
        prompt = f"{message.text} mavzusida 5 ta slayd uchun matn tayyorla. Har bir slaydni 'Sarlavha | Matn' formatida yoz."
        response = model.generate_content(prompt)
        
        slides_data = []
        for line in response.text.split("\n"):
            if "|" in line:
                parts = line.split("|", 1)
                slides_data.append({"title": parts[0].strip(), "content": parts[1].strip()})
        
        if not slides_data:
            slides_data = [{"title": message.text, "content": response.text[:500]}]

        pptx_file = create_pptx(message.text, slides_data, data['muallif'])
        await bot.send_document(
            message.chat.id, 
            types.BufferedInputFile(pptx_file.read(), filename=f"{message.text}.pptx"),
            caption=f"✅ Slayd tayyor!\n👤 Muallif: {data['muallif']}\n✨ AI tomonidan yaratildi."
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await status.delete()
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
