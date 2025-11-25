from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging

from loader import dp, user_db, book_db, bot
from keyboards.default.book_keyboard import (
    user_main_menu, categories_inline_keyboard,
    books_inline_keyboard, back_button, book_detail_keyboard
)


# =================== STATES ===================

class UserSearchState(StatesGroup):
    """User qidiruv state'i"""
    waiting_for_query = State()


# =================== YORDAMCHI FUNKSIYALAR ===================

def format_file_size(size_bytes):
    """Fayl hajmini formatlash"""
    if size_bytes is None:
        return "Noma'lum"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# =================== START COMMAND ===================

@dp.message_handler(commands="start")
async def user_start(message: types.Message):
    """User uchun /start"""
    telegram_id = message.from_user.id
    username = message.from_user.username or "User"

    # Foydalanuvchini database'ga qo'shish
    if not user_db.select_user(telegram_id=telegram_id):
        user_db.add_user(telegram_id=telegram_id, username=username)
        logging.info(f"New user registered: {telegram_id} (@{username})")

    # Faol holatga keltirish
    user_db.update_user_last_active(telegram_id)
    user_db.activate_user(telegram_id)

    await message.answer(
        f"📚 <b>Assalomu alaykum, {message.from_user.first_name}!</b>\n\n"
        "Kitoblar kutubxonasiga xush kelibsiz! 📖\n\n"
        "Bu yerda siz:\n"
        "📁 Turli kategoriyalardagi kitoblarni\n"
        "🔍 Kerakli kitoblarni qidirishingiz\n"
        "📥 PDF formatda yuklab olishingiz mumkin\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=user_main_menu()
    )


# =================== KATEGORIYALAR ===================

@dp.message_handler(Text(equals="📚 Kategoriyalar"))
async def show_categories_to_user(message: types.Message):
    """Foydalanuvchiga kategoriyalarni ko'rsatish"""
    categories = book_db.get_all_categories()

    if not categories:
        await message.answer(
            "📂 <b>Hozircha kategoriyalar yo'q.</b>\n\n"
            "Tez orada kitoblar qo'shiladi! 📚",
            reply_markup=user_main_menu()
        )
        return

    keyboard = categories_inline_keyboard(categories, action_prefix="user_cat", row_width=2)

    text = "📚 <b>Kategoriyalar:</b>\n\n"
    text += "<i>Quyidagi kategoriyalardan birini tanlang:</i>"

    await message.answer(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("user_cat:"))
async def show_books_in_category(callback: types.CallbackQuery):
    """Kategoriya bo'yicha kitoblarni ko'rsatish"""
    category_id = int(callback.data.split(":")[1])
    category = book_db.get_category_by_id(category_id)
    books = book_db.get_books_by_category(category_id)

    if not books:
        await callback.message.edit_text(
            f"📂 <b>{category[1]}</b>\n\n"
            f"Bu kategoriyada hozircha kitoblar yo'q. 😔"
        )
        await callback.answer()
        return

    keyboard = books_inline_keyboard(books, action_prefix="user_book")

    text = f"📁 <b>{category[1]}</b>\n\n"
    if category[2]:  # description
        text += f"<i>{category[2]}</i>\n\n"
    text += f"📖 Kitoblar soni: <b>{len(books)}</b>\n\n"
    text += "<i>Kitobni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# =================== KITOB TAFSILOTLARI VA YUKLAB OLISH ===================

@dp.callback_query_handler(lambda c: c.data.startswith("user_book:"))
async def show_book_details(callback: types.CallbackQuery):
    """Kitob tafsilotlarini ko'rsatish"""
    book_id = int(callback.data.split(":")[1])
    book = book_db.get_book_by_id(book_id)

    if not book:
        await callback.message.edit_text("❌ Kitob topilmadi!")
        await callback.answer()
        return

    text = f"📖 <b>{book[1]}</b>\n\n"

    if book[4]:  # author
        text += f"✍️ <b>Muallif:</b> {book[4]}\n"

    text += f"📁 <b>Kategoriya:</b> {book[-1]}\n"  # category_name

    if book[6]:  # file_size
        text += f"📦 <b>Hajmi:</b> {format_file_size(book[6])}\n"

    text += f"📥 <b>Yuklab olishlar:</b> {book[8]} marta\n"

    if book[5]:  # description
        text += f"\n📝 <b>Tavsif:</b>\n<i>{book[5]}</i>\n"

    keyboard = book_detail_keyboard(book_id)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("download_book:"))
async def download_book(callback: types.CallbackQuery):
    """Kitobni yuklab berish"""
    book_id = int(callback.data.split(":")[1])
    book = book_db.get_book_by_id(book_id)

    if not book:
        await callback.answer("❌ Kitob topilmadi!", show_alert=True)
        return

    try:
        # Yuklab olishlar sonini oshirish
        book_db.increment_download_count(book_id)

        # Kitobni yuborish
        await callback.message.answer_document(
            document=book[2],  # file_id
            caption=f"📖 <b>{book[1]}</b>\n"
                    f"{'✍️ ' + book[4] if book[4] else ''}\n"
                    f"📁 {book[-1]}\n\n"
                    f"✅ Yuklab olindi!",
        )

        await callback.answer("✅ Kitob yuborildi!", show_alert=True)
        logging.info(f"Book downloaded: {book[1]} by user {callback.from_user.id}")

    except Exception as e:
        await callback.answer("❌ Kitobni yuborishda xatolik!", show_alert=True)
        logging.error(f"Error downloading book: {e}")


# =================== QIDIRUV ===================

@dp.message_handler(Text(equals="🔍 Kitob qidirish"))
async def start_user_search(message: types.Message, state: FSMContext):
    """Qidiruv boshlash"""
    await message.answer(
        "🔍 <b>Kitob qidirish</b>\n\n"
        "Kitob yoki muallif nomini kiriting:\n"
        "<i>Masalan: Matematika, Alisher Navoiy, O'zbekiston tarixi</i>",
        reply_markup=back_button()
    )
    await UserSearchState.waiting_for_query.set()


@dp.message_handler(state=UserSearchState.waiting_for_query)
async def process_user_search(message: types.Message, state: FSMContext):
    """Qidiruv so'rovini qayta ishlash"""
    if message.text == "🔙 Orqaga":
        await state.finish()
        await message.answer("🏠 Bosh menyu", reply_markup=user_main_menu())
        return

    query = message.text.strip()

    try:
        results = book_db.search_books(query)

        if not results:
            await message.answer(
                f"❌ <b>'{query}'</b> bo'yicha hech narsa topilmadi.\n\n"
                f"💡 <i>Boshqa so'z bilan qidirib ko'ring yoki kategoriyalarni ko'ring.</i>",
                reply_markup=user_main_menu()
            )
            await state.finish()
            return

        keyboard = books_inline_keyboard(results[:20], action_prefix="user_book")

        text = f"🔍 <b>Qidiruv natijasi: '{query}'</b>\n\n"
        text += f"✅ Topildi: <b>{len(results)}</b> ta kitob\n\n"

        if len(results) > 20:
            text += f"<i>Birinchi 20 ta kitob ko'rsatilmoqda</i>\n\n"

        text += "<i>Kitobni tanlang:</i>"

        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        await message.answer(
            f"❌ Qidirishda xatolik yuz berdi.\n\n"
            f"Iltimos, qaytadan urinib ko'ring.",
            reply_markup=user_main_menu()
        )
        logging.error(f"Error searching books: {e}")

    await state.finish()


# =================== MASHHUR KITOBLAR ===================

@dp.message_handler(Text(equals="⭐️ Mashhur kitoblar"))
async def show_popular_books(message: types.Message):
    """Eng mashhur kitoblarni ko'rsatish"""
    popular_books = book_db.get_popular_books(15)

    if not popular_books:
        await message.answer(
            "📚 Hozircha mashhur kitoblar yo'q.",
            reply_markup=user_main_menu()
        )
        return

    keyboard = books_inline_keyboard(popular_books, action_prefix="user_book")

    text = "⭐️ <b>Eng mashhur kitoblar</b>\n\n"
    text += f"📖 Eng ko'p yuklab olingan {len(popular_books)} ta kitob:\n\n"
    text += "<i>Kitobni tanlang:</i>"

    await message.answer(text, reply_markup=keyboard)


# =================== STATISTIKA ===================

@dp.message_handler(Text(equals="📊 Statistika"))
async def show_user_statistics(message: types.Message):
    """User uchun statistika"""
    try:
        total_categories = book_db.count_categories()
        total_books = book_db.count_books()

        text = (
            "📊 <b>Kutubxona statistikasi</b>\n\n"
            f"📁 Kategoriyalar: <b>{total_categories}</b>\n"
            f"📖 Kitoblar: <b>{total_books}</b>\n\n"
        )

        # Eng mashhur 5 ta kitob
        popular = book_db.get_popular_books(5)
        if popular:
            text += "⭐️ <b>TOP-5 mashhur kitoblar:</b>\n\n"
            for i, book in enumerate(popular, 1):
                text += f"{i}. {book[1]}\n"
                text += f"   📥 {book[8]} marta yuklab olindi\n\n"

        await message.answer(text, reply_markup=user_main_menu())

    except Exception as e:
        await message.answer(
            "❌ Statistikani yuklashda xatolik",
            reply_markup=user_main_menu()
        )
        logging.error(f"Error showing user statistics: {e}")


# =================== YORDAM ===================

@dp.message_handler(Text(equals="ℹ️ Yordam"))
async def show_help(message: types.Message):
    """Yordam bo'limi"""
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "📚 <b>Kategoriyalar</b> - Barcha kategoriyalarni ko'ring\n"
        "🔍 <b>Kitob qidirish</b> - Kitob yoki muallif nomini qidiring\n"
        "⭐️ <b>Mashhur kitoblar</b> - Eng ko'p yuklab olingan kitoblar\n"
        "📊 <b>Statistika</b> - Kutubxona haqida ma'lumot\n\n"
        "<b>Qanday foydalanish:</b>\n"
        "1️⃣ Kategoriyalar bo'limiga kiring\n"
        "2️⃣ Kerakli kategoriyani tanlang\n"
        "3️⃣ Kitobni tanlang va tafsilotlarni ko'ring\n"
        "4️⃣ 'Yuklab olish' tugmasini bosing\n\n"
        "✅ Kitob PDF formatda yuboriladi!\n\n"
        "❓ Savollar bo'lsa, admin bilan bog'laning."
    )

    await message.answer(text, reply_markup=user_main_menu())


# =================== ORQAGA TUGMASI ===================

@dp.message_handler(Text(equals="🔙 Orqaga"), state="*")
async def back_to_user_main(message: types.Message, state: FSMContext):
    """Bosh menyuga qaytish"""
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    await message.answer(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=user_main_menu()
    )


# =================== CALLBACK HANDLERS ===================

@dp.callback_query_handler(lambda c: c.data == "back_to_categories")
async def back_to_categories_callback(callback: types.CallbackQuery):
    """Kategoriyalarga qaytish"""
    categories = book_db.get_all_categories()
    keyboard = categories_inline_keyboard(categories, action_prefix="user_cat", row_width=2)

    text = "📚 <b>Kategoriyalar:</b>\n\n"
    text += "<i>Quyidagi kategoriyalardan birini tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "back_to_books")
async def back_to_books_callback(callback: types.CallbackQuery):
    """Kitoblarga qaytish - callback.message.text dan kategoriya ID ni olish"""
    # Bu holda foydalanuvchi kategoriyalarga qaytishi kerak
    categories = book_db.get_all_categories()
    keyboard = categories_inline_keyboard(categories, action_prefix="user_cat", row_width=2)

    text = "📚 <b>Kategoriyalar:</b>\n\n"
    text += "<i>Quyidagi kategoriyalardan birini tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main_callback(callback: types.CallbackQuery):
    """Bosh menyuga qaytish"""
    await callback.message.delete()
    await callback.message.answer(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=user_main_menu()
    )
    await callback.answer()


# =================== USER AKTIVLIGINI YANGILASH ===================

@dp.message_handler()
async def update_user_activity(message: types.Message):
    """Har bir xabarda userning aktivligini yangilash"""
    try:
        telegram_id = message.from_user.id
        user = user_db.select_user(telegram_id=telegram_id)

        if user:
            user_db.update_user_last_active(telegram_id)
    except Exception as e:
        logging.error(f"Error updating user activity: {e}")