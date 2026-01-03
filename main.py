import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from io import BytesIO

# API KALITLAR
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")

# AI sozlamalari - YANGI MODEL
genai.configure(api_key=GEMINI_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Rasm qidirish funksiyasi
def get_pexels_image(query):
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    headers = {"Authorization": PEXELS_KEY}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            if data['photos']:
                return data['photos'][0]['src']['large']
    except:
        return None
    return None

# Slaydni yaratish funksiyasi
async def create_pptx(topic, slides_data, user_full_name):
    prs = Presentation()
    
    # 1-SLAYD: TITUL (Mavzu va Ism-Familiya)
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = topic.upper()
    subtitle.text = f"Tayyorladi: {user_full_name}\nSlayd AI Bot orqali yaratildi"
    
    # ASOSIY SLAYDLAR
    for slide_info in slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        
        # Sarlavha dizayni
        title_shape = slide.shapes.title
        title_shape.text = slide_info['title']
        
        # Matn dizayni
        body_shape = slide.placeholders[1]
        body_shape.text = slide_info['content']
        
        # Rasm qo'shish
        img_url = get_pexels_image(slide_info['title'])
        if img_url:
            try:
                img_data = BytesIO(requests.get(img_url).content)
                slide.shapes.add_picture(img_data, Inches(5.5), Inches(1.5), Inches(4), Inches(3.5))
            except:
                pass
            
    file_stream = BytesIO()
    prs.save(file_stream)
    file_stream.seek(0)
    return file_stream

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!\n\nMavzu yuboring, men sizga ism-familiyangiz tushirilgan chiroyli slayd yasab beraman.")

@dp.message()
async def handle_message(message: types.Message):
    user_name = message.from_user.full_name # Telegramdagi ism-familiyasini oladi
    status = await message.answer("🎨 Slayd dizayni tayyorlanmoqda. AI matn yozmoqda...")
    
    try:
        prompt = f"Mavzu: {message.text}. Ushbu mavzuda 5 ta slayddan iborat prezentatsiya uchun sarlavha va matn tayyorlab ber. Javob formati: Sarlavha | Matn shaklida bo'lsin."
        response = ai_model.generate_content(prompt)
        
        raw_text = response.text.split("\n")
        slides_data = []
        for line in raw_text:
            if "|" in line:
                parts = line.split("|", 1)
                slides_data.append({"title": parts[0].strip(), "content": parts[1].strip()})
        
        if not slides_data:
             slides_data = [{"title": message.text, "content": response.text[:500]}]

        pptx_file = await create_pptx(message.text, slides_data, user_name)
        
        await bot.send_document(
            message.chat.id, 
            types.BufferedInputFile(pptx_file.read(), filename=f"{message.text}.pptx"),
            caption=f"✅ Slayd tayyor!\n👤 Muallif: {user_name}"
        )
        await status.delete()
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
