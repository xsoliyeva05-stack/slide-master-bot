import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from io import BytesIO

# API KALITLAR
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")

genai.configure(api_key=GEMINI_KEY)

bot = Bot(token=TOKEN)
dp = Dispatcher()

class SlaydStates(StatesGroup):
    ism_familiya = State()
    mavzu = State()

def main_menu():
    button = [[KeyboardButton(text="🚀 Slayd yaratish")]]
    return ReplyKeyboardMarkup(keyboard=button, resize_keyboard=True)

def get_pexels_image(query):
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    headers = {"Authorization": PEXELS_KEY}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            if data['photos']: return data['photos'][0]['src']['large']
    except: return None
    return None

async def create_pptx(topic, slides_data, full_name):
    prs = Presentation()
    
    # 1-SLAYD: TITUL (DIZAYN BILAN)
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = topic.upper()
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 51, 102) # To'q ko'k
    title.text_frame.paragraphs[0].font.bold = True
    
    subtitle.text = f"Tayyorladi: {full_name}\nSlayd Master AI orqali yaratildi"
    subtitle.text_frame.paragraphs[0].font.size = Pt(24)
    
    # ASOSIY SLAYDLAR
    for slide_info in slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        
        # Sarlavha dizayni
        title_shape = slide.shapes.title
        title_shape.text = slide_info['title']
        for p in title_shape.text_frame.paragraphs:
            p.font.color.rgb = RGBColor(0, 102, 204) # Moviy
            p.font.size = Pt(36)
            p.font.bold = True
        
        # Matn dizayni
        body_shape = slide.placeholders[1]
        body_shape.text = slide_info['content']
        for p in body_shape.text_frame.paragraphs:
            p.font.size = Pt(18)
            
        # Rasm qo'shish
        img_url = get_pexels_image(slide_info['title'])
        if img_url:
            try:
                img_data = BytesIO(requests.get(img_url).content)
                slide.shapes.add_picture(img_data, Inches(5.8), Inches(1.5), Inches(4), Inches(3.5))
            except: pass
            
    file_stream = BytesIO()
    prs.save(file_stream)
    file_stream.seek(0)
    return file_stream

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Salom {message.from_user.first_name}! Slayd yasashni boshlash uchun tugmani bosing.", reply_markup=main_menu())

@dp.message(F.text == "🚀 Slayd yaratish")
async def start_slayd(message: types.Message, state: FSMContext):
    await message.answer("Slaydda chiqishi uchun ism va familiyangizni yozing:")
    await state.set_state(SlaydStates.ism_familiya)

@dp.message(SlaydStates.ism_familiya)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(ism=message.text)
    await message.answer("Slayd qaysi mavzuda bo'lsin?")
    await state.set_state(SlaydStates.mavzu)

@dp.message(SlaydStates.mavzu)
async def get_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_name = data['ism']
    topic = message.text
    status = await message.answer("🎨 Dizayn berilmoqda va matn yozilmoqda... Iltimos kuting.")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"Mavzu: {topic}. 5 ta slayd uchun sarlavha va matn tayyorla. Format: Sarlavha | Matn"
        response = model.generate_content(prompt)
        
        raw_text = response.text.split("\n")
        slides_data = []
        for line in raw_text:
            if "|" in line:
                t, c = line.split("|", 1)
                slides_data.append({"title": t.strip(), "content": c.strip()})
        
        if not slides_data:
            slides_data = [{"title": topic, "content": response.text[:500]}]

        pptx = await create_pptx(topic, slides_data, user_name)
        await bot.send_document(
            message.chat.id, 
            types.BufferedInputFile(pptx.read(), filename=f"{topic}.pptx"),
            caption=f"✅ Slayd tayyor!\n👤 Muallif: {user_name}"
        )
        await status.delete()
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
        await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
