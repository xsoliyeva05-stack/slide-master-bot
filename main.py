import os, asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import google.generativeai as genai
from utils import create_pptx

# SOZLAMALAR
TOKEN = os.getenv("BOT_TOKEN")
genai.configure(api_key=os.getenv("GEMINI_KEY"))
# 404 xatosini bermaydigan stabil model
model = genai.GenerativeModel('gemini-pro')

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
    await message.answer("Mavzuni kiriting:")
    await state.set_state(SlaydStates.mavzu)

@dp.message(SlaydStates.mavzu)
async def get_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    status = await message.answer("⌛ AI ishlamoqda...")
    
    try:
        prompt = f"{message.text} mavzusida 5 ta slayd uchun sarlavha va matn ber. Format: Sarlavha | Matn"
        response = model.generate_content(prompt)
        
        slides_data = []
        for line in response.text.split("\n"):
            if "|" in line:
                t, c = line.split("|", 1)
                slides_data.append({"title": t.strip(), "content": c.strip()})
        
        if not slides_data:
            slides_data = [{"title": message.text, "content": response.text[:500]}]

        pptx = create_pptx(message.text, slides_data, data['muallif'])
        await bot.send_document(
            message.chat.id, 
            types.BufferedInputFile(pptx.read(), filename=f"{message.text}.pptx"),
            caption=f"✅ Tayyor!\n👤 Muallif: {data['muallif']}"
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    
    await status.delete()
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
