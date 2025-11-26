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


def format_duration(seconds):
    """Davomiylikni formatlash"""
    if not seconds:
        return "Noma'lum"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


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
        "Kitoblar kutubxonasiga xush kelibsiz! 📖🎧\n\n"
        "Bu yerda siz:\n"
        "📁 Turli kategoriyalardagi kitoblarni\n"
        "📕 PDF kitoblarni yuklab olishingiz\n"
        "🎧 Audio kitoblarni tinglashingiz\n"
        "🔍 Kerakli kitoblarni qidirishingiz mumkin\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=user_main_menu()
    )


# =================== KATEGORIYALAR ===================

@dp.message_handler(Text(equals="📚 Kategoriyalar"))
async def show_categories_to_user(message: types.Message):
    """Foydalanuvchiga asosiy kategoriyalarni ko'rsatish"""
    main_categories = book_db.get_main_categories()

    if not main_categories:
        await message.answer(
            "📂 <b>Hozircha kategoriyalar yo'q.</b>\n\n"
            "Tez orada kitoblar qo'shiladi! 📚",
            reply_markup=user_main_menu()
        )
        return

    keyboard = categories_inline_keyboard(main_categories, action_prefix="user_main_cat", row_width=2)

    text = "📚 <b>Kategoriyalar:</b>\n\n"

    for cat in main_categories:
        book_count = book_db.count_books_by_category(cat[0], include_subcategories=True)
        text += f"📁 {cat[1]} - <b>{book_count}</b> ta kitob\n"

    text += "\n<i>Kategoriyani tanlang:</i>"

    await message.answer(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("user_main_cat:"))
async def show_main_category_content(callback: types.CallbackQuery):
    """Asosiy kategoriya tanlanganda subkategoriya yoki kitoblarni ko'rsatish"""
    main_cat_id = int(callback.data.split(":")[1])
    main_cat = book_db.get_category_by_id(main_cat_id)

    # Subkategoriyalar bormi?
    subcats = book_db.get_subcategories(main_cat_id)

    if subcats:
        # Subkategoriyalar mavjud
        keyboard = categories_inline_keyboard(subcats, action_prefix="user_sub_cat", row_width=2)

        # "Barcha kitoblar" tugmasini qo'shish (agar asosiy kategoriyada ham kitoblar bo'lsa)
        direct_books = book_db.get_books_by_category(main_cat_id, include_subcategories=False)
        if direct_books:
            keyboard.row(types.InlineKeyboardButton(
                f"📚 Barcha kitoblar ({len(direct_books)})",
                callback_data=f"user_cat_books:{main_cat_id}"
            ))

        keyboard.row(types.InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main_cats"))

        text = f"📁 <b>{main_cat[1]}</b>\n\n"
        if main_cat[2]:
            text += f"<i>{main_cat[2]}</i>\n\n"

        text += "<b>Subkategoriyalar:</b>\n\n"
        for sub in subcats:
            sub_book_count = book_db.count_books_by_category(sub[0], include_subcategories=False)
            text += f"📂 {sub[1]} - {sub_book_count} ta kitob\n"

        text += "\n<i>Tanlang:</i>"

        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        # Subkategoriya yo'q, to'g'ridan-to'g'ri kitoblar
        books = book_db.get_books_by_category(main_cat_id)

        if not books:
            await callback.message.edit_text(
                f"📂 <b>{main_cat[1]}</b>\n\n"
                f"Bu kategoriyada hozircha kitoblar yo'q. 😔"
            )
            await callback.answer()
            return

        # PDF va Audio ajratish
        pdf_books = [b for b in books if b[3] == 'pdf']
        audio_books = [b for b in books if b[3] == 'audio']

        keyboard = types.InlineKeyboardMarkup(row_width=1)

        if pdf_books:
            keyboard.row(types.InlineKeyboardButton(
                f"📕 PDF kitoblar ({len(pdf_books)})",
                callback_data=f"user_cat_pdf:{main_cat_id}"
            ))

        if audio_books:
            keyboard.row(types.InlineKeyboardButton(
                f"🎧 Audio kitoblar ({len(audio_books)})",
                callback_data=f"user_cat_audio:{main_cat_id}"
            ))

        keyboard.row(types.InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main_cats"))

        text = f"📁 <b>{main_cat[1]}</b>\n\n"
        if main_cat[2]:
            text += f"<i>{main_cat[2]}</i>\n\n"

        text += f"📖 Jami: <b>{len(books)}</b> ta kitob\n"
        text += f"📕 PDF: {len(pdf_books)} | 🎧 Audio: {len(audio_books)}\n\n"
        text += "<i>Turni tanlang:</i>"

        await callback.message.edit_text(text, reply_markup=keyboard)

    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("user_sub_cat:"))
async def show_subcategory_books(callback: types.CallbackQuery):
    """Subkategoriya kitoblarini ko'rsatish"""
    sub_cat_id = int(callback.data.split(":")[1])
    sub_cat = book_db.get_category_by_id(sub_cat_id)
    books = book_db.get_books_by_category(sub_cat_id)

    if not books:
        await callback.message.edit_text(
            f"📂 <b>{sub_cat[1]}</b>\n\n"
            f"Bu kategoriyada hozircha kitoblar yo'q. 😔"
        )
        await callback.answer()
        return

    # PDF va Audio ajratish
    pdf_books = [b for b in books if b[3] == 'pdf']
    audio_books = [b for b in books if b[3] == 'audio']

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    if pdf_books:
        keyboard.row(types.InlineKeyboardButton(
            f"📕 PDF kitoblar ({len(pdf_books)})",
            callback_data=f"user_cat_pdf:{sub_cat_id}"
        ))

    if audio_books:
        keyboard.row(types.InlineKeyboardButton(
            f"🎧 Audio kitoblar ({len(audio_books)})",
            callback_data=f"user_cat_audio:{sub_cat_id}"
        ))

    # Parent kategoriyaga qaytish
    parent_id = sub_cat[3]  # parent_id
    keyboard.row(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"user_main_cat:{parent_id}"))

    path = book_db.get_category_path(sub_cat_id)

    text = f"📂 <b>{path}</b>\n\n"
    if sub_cat[2]:
        text += f"<i>{sub_cat[2]}</i>\n\n"

    text += f"📖 Jami: <b>{len(books)}</b> ta kitob\n"
    text += f"📕 PDF: {len(pdf_books)} | 🎧 Audio: {len(audio_books)}\n\n"
    text += "<i>Turni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("user_cat_books:"))
async def show_all_category_books(callback: types.CallbackQuery):
    """Kategoriya va subkategoriyalarining barcha kitoblarini ko'rsatish"""
    cat_id = int(callback.data.split(":")[1])
    cat = book_db.get_category_by_id(cat_id)
    books = book_db.get_books_by_category(cat_id, include_subcategories=True)

    if not books:
        await callback.answer("Bu kategoriyada kitoblar yo'q!", show_alert=True)
        return

    # PDF va Audio ajratish
    pdf_books = [b for b in books if b[3] == 'pdf']
    audio_books = [b for b in books if b[3] == 'audio']

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    if pdf_books:
        keyboard.row(types.InlineKeyboardButton(
            f"📕 PDF kitoblar ({len(pdf_books)})",
            callback_data=f"user_cat_pdf:{cat_id}:all"
        ))

    if audio_books:
        keyboard.row(types.InlineKeyboardButton(
            f"🎧 Audio kitoblar ({len(audio_books)})",
            callback_data=f"user_cat_audio:{cat_id}:all"
        ))

    keyboard.row(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"user_main_cat:{cat_id}"))

    text = f"📁 <b>{cat[1]} - Barcha kitoblar</b>\n\n"
    text += f"📖 Jami: <b>{len(books)}</b> ta kitob\n"
    text += f"📕 PDF: {len(pdf_books)} | 🎧 Audio: {len(audio_books)}\n\n"
    text += "<i>Turni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("user_cat_pdf:"))
async def show_pdf_books(callback: types.CallbackQuery):
    """PDF kitoblarni ko'rsatish"""
    parts = callback.data.split(":")
    cat_id = int(parts[1])
    include_subs = len(parts) > 2 and parts[2] == "all"

    cat = book_db.get_category_by_id(cat_id)
    books = book_db.get_books_by_category(cat_id, file_type='pdf', include_subcategories=include_subs)

    if not books:
        await callback.answer("PDF kitoblar yo'q!", show_alert=True)
        return

    # Orqaga callback - dinamik
    if cat[3] is not None:  # subkategoriya
        back_callback = f"user_sub_cat:{cat_id}"
    else:  # asosiy kategoriya
        back_callback = f"user_main_cat:{cat_id}"

    keyboard = books_inline_keyboard(books, action_prefix="user_book", back_callback=back_callback)

    path = book_db.get_category_path(cat_id)

    text = f"📕 <b>{path} - PDF kitoblar</b>\n\n"
    text += f"📖 Topildi: <b>{len(books)}</b> ta PDF kitob\n\n"
    text += "<i>Kitobni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("user_cat_audio:"))
async def show_audio_books(callback: types.CallbackQuery):
    """Audio kitoblarni ko'rsatish"""
    parts = callback.data.split(":")
    cat_id = int(parts[1])
    include_subs = len(parts) > 2 and parts[2] == "all"

    cat = book_db.get_category_by_id(cat_id)
    books = book_db.get_books_by_category(cat_id, file_type='audio', include_subcategories=include_subs)

    if not books:
        await callback.answer("Audio kitoblar yo'q!", show_alert=True)
        return

    # Orqaga callback - dinamik
    if cat[3] is not None:  # subkategoriya
        back_callback = f"user_sub_cat:{cat_id}"
    else:  # asosiy kategoriya
        back_callback = f"user_main_cat:{cat_id}"

    keyboard = books_inline_keyboard(books, action_prefix="user_book", back_callback=back_callback)

    path = book_db.get_category_path(cat_id)

    text = f"🎧 <b>{path} - Audio kitoblar</b>\n\n"
    text += f"📖 Topildi: <b>{len(books)}</b> ta audio kitob\n\n"
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

    emoji = "📕" if book[3] == 'pdf' else "🎧"
    type_name = "PDF" if book[3] == 'pdf' else "Audio"

    text = f"{emoji} <b>{book[1]}</b>\n\n"

    if book[4]:  # author
        text += f"✍️ <b>Muallif:</b> {book[4]}\n"

    if book[5]:  # narrator (audio uchun)
        text += f"🎙 <b>Hikoyachi:</b> {book[5]}\n"

    text += f"📁 <b>Kategoriya:</b> {book[-1]}\n"  # category_name

    if book[9]:  # file_size
        text += f"📦 <b>Hajmi:</b> {format_file_size(book[9])}\n"

    if book[8]:  # duration (audio uchun)
        text += f"⏱ <b>Davomiyligi:</b> {format_duration(book[8])}\n"

    text += f"📥 <b>Yuklab olishlar:</b> {book[10]} marta\n"

    if book[7]:  # description
        text += f"\n📝 <b>Tavsif:</b>\n<i>{book[7]}</i>\n"

    keyboard = book_detail_keyboard(book_id, book[3])  # file_type ham yuboramiz

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("download_book:"))
async def download_book(callback: types.CallbackQuery):
    """Kitobni yuklab berish (PDF yoki Audio)"""
    book_id = int(callback.data.split(":")[1])
    book = book_db.get_book_by_id(book_id)

    if not book:
        await callback.answer("❌ Kitob topilmadi!", show_alert=True)
        return

    try:
        # Yuklab olishlar sonini oshirish
        book_db.increment_download_count(book_id)

        emoji = "📕" if book[3] == 'pdf' else "🎧"
        type_name = "PDF" if book[3] == 'pdf' else "Audio"

        caption = f"{emoji} <b>{book[1]}</b>\n"

        if book[4]:
            caption += f"✍️ {book[4]}\n"
        if book[5]:
            caption += f"🎙 {book[5]}\n"

        caption += f"📁 {book[-1]}\n\n"

        if book[3] == 'pdf':
            caption += "✅ PDF kitob yuborildi!"
            # PDF yuborish
            await callback.message.answer_document(
                document=book[2],  # file_id
                caption=caption
            )
        else:
            caption += "✅ Audio kitob yuborildi!"
            # Audio yuborish
            await callback.message.answer_audio(
                audio=book[2],  # file_id
                caption=caption,
                title=book[1],
                performer=book[4] or book[5] or "Nomalum"
            )

        await callback.answer(f"✅ {type_name} yuborildi!", show_alert=True)
        logging.info(f"{type_name} book downloaded: {book[1]} by user {callback.from_user.id}")

    except Exception as e:
        await callback.answer("❌ Yuborishda xatolik!", show_alert=True)
        logging.error(f"Error downloading book: {e}")


# =================== QIDIRUV ===================

@dp.message_handler(Text(equals="🔍 Kitob qidirish"))
async def start_user_search(message: types.Message, state: FSMContext):
    """Qidiruv boshlash"""
    await message.answer(
        "🔍 <b>Kitob qidirish</b>\n\n"
        "Kitob, muallif yoki hikoyachi nomini kiriting:\n"
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

        pdf_results = [b for b in results if b[3] == 'pdf']
        audio_results = [b for b in results if b[3] == 'audio']

        keyboard = types.InlineKeyboardMarkup(row_width=1)

        if pdf_results:
            keyboard.row(types.InlineKeyboardButton(
                f"📕 PDF natijalar ({len(pdf_results)})",
                callback_data=f"search_results_pdf:{query}"
            ))

        if audio_results:
            keyboard.row(types.InlineKeyboardButton(
                f"🎧 Audio natijalar ({len(audio_results)})",
                callback_data=f"search_results_audio:{query}"
            ))

        text = f"🔍 <b>Qidiruv natijasi: '{query}'</b>\n\n"
        text += f"✅ Topildi: <b>{len(results)}</b> ta kitob\n"
        text += f"📕 PDF: {len(pdf_results)} | 🎧 Audio: {len(audio_results)}\n\n"
        text += "<i>Turni tanlang:</i>"

        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        await message.answer(
            f"❌ Qidirishda xatolik yuz berdi.\n\n"
            f"Iltimos, qaytadan urinib ko'ring.",
            reply_markup=user_main_menu()
        )
        logging.error(f"Error searching books: {e}")

    await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith("search_results_pdf:"))
async def show_pdf_search_results(callback: types.CallbackQuery):
    """PDF qidiruv natijalarini ko'rsatish"""
    query = callback.data.replace("search_results_pdf:", "")
    results = book_db.search_books(query, file_type='pdf')

    keyboard = books_inline_keyboard(results[:20], action_prefix="user_book", back_callback="back_to_main")

    text = f"🔍 📕 <b>PDF natijalar: '{query}'</b>\n\n"
    text += f"✅ Topildi: <b>{len(results)}</b> ta PDF kitob\n\n"

    if len(results) > 20:
        text += f"<i>Birinchi 20 ta ko'rsatilmoqda</i>\n\n"

    text += "<i>Kitobni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("search_results_audio:"))
async def show_audio_search_results(callback: types.CallbackQuery):
    """Audio qidiruv natijalarini ko'rsatish"""
    query = callback.data.replace("search_results_audio:", "")
    results = book_db.search_books(query, file_type='audio')

    keyboard = books_inline_keyboard(results[:20], action_prefix="user_book", back_callback="back_to_main")

    text = f"🔍 🎧 <b>Audio natijalar: '{query}'</b>\n\n"
    text += f"✅ Topildi: <b>{len(results)}</b> ta audio kitob\n\n"

    if len(results) > 20:
        text += f"<i>Birinchi 20 ta ko'rsatilmoqda</i>\n\n"

    text += "<i>Kitobni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# =================== MASHHUR KITOBLAR ===================

@dp.message_handler(Text(equals="⭐️ Mashhur kitoblar"))
async def show_popular_books(message: types.Message):
    """Eng mashhur kitoblarni ko'rsatish"""
    popular_pdf = book_db.get_popular_books(10, 'pdf')
    popular_audio = book_db.get_popular_books(10, 'audio')

    if not popular_pdf and not popular_audio:
        await message.answer(
            "📚 Hozircha mashhur kitoblar yo'q.",
            reply_markup=user_main_menu()
        )
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    if popular_pdf:
        keyboard.row(types.InlineKeyboardButton(
            f"📕 Mashhur PDF kitoblar ({len(popular_pdf)})",
            callback_data="popular_pdf"
        ))

    if popular_audio:
        keyboard.row(types.InlineKeyboardButton(
            f"🎧 Mashhur Audio kitoblar ({len(popular_audio)})",
            callback_data="popular_audio"
        ))

    text = "⭐️ <b>Eng mashhur kitoblar</b>\n\n"
    text += "<i>Turni tanlang:</i>"

    await message.answer(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "popular_pdf")
async def show_popular_pdf(callback: types.CallbackQuery):
    """Mashhur PDF kitoblarni ko'rsatish"""
    popular_books = book_db.get_popular_books(15, 'pdf')

    keyboard = books_inline_keyboard(popular_books, action_prefix="user_book", back_callback="back_to_main")

    text = "⭐️ 📕 <b>Eng mashhur PDF kitoblar</b>\n\n"
    text += f"📖 TOP-{len(popular_books)} eng ko'p yuklab olingan PDF kitoblar\n\n"
    text += "<i>Kitobni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "popular_audio")
async def show_popular_audio(callback: types.CallbackQuery):
    """Mashhur Audio kitoblarni ko'rsatish"""
    popular_books = book_db.get_popular_books(15, 'audio')

    keyboard = books_inline_keyboard(popular_books, action_prefix="user_book", back_callback="back_to_main")

    text = "⭐️ 🎧 <b>Eng mashhur Audio kitoblar</b>\n\n"
    text += f"📖 TOP-{len(popular_books)} eng ko'p tinglanilgan audio kitoblar\n\n"
    text += "<i>Kitobni tanlang:</i>"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# =================== STATISTIKA ===================

@dp.message_handler(Text(equals="📊 Statistika"))
async def show_user_statistics(message: types.Message):
    """User uchun statistika"""
    try:
        stats = book_db.get_statistics()

        text = (
            "📊 <b>Kutubxona statistikasi</b>\n\n"
            f"📁 Kategoriyalar: <b>{stats['total_categories']}</b>\n"
            f"   ├─ Asosiy: {stats['main_categories']}\n"
            f"   └─ Subkategoriyalar: {stats['total_categories'] - stats['main_categories']}\n\n"
            f"📖 Kitoblar: <b>{stats['total_books']}</b>\n"
            f"   ├─ 📕 PDF: {stats['pdf_books']}\n"
            f"   └─ 🎧 Audio: {stats['audio_books']}\n\n"
        )

        # Eng mashhur kitoblar
        popular_pdf = book_db.get_popular_books(3, 'pdf')
        popular_audio = book_db.get_popular_books(3, 'audio')

        if popular_pdf:
            text += "⭐️ <b>TOP-3 PDF kitoblar:</b>\n"
            for i, book in enumerate(popular_pdf, 1):
                text += f"{i}. {book[1]} - {book[10]} marta\n"
            text += "\n"

        if popular_audio:
            text += "🎵 <b>TOP-3 Audio kitoblar:</b>\n"
            for i, book in enumerate(popular_audio, 1):
                text += f"{i}. {book[1]} - {book[10]} marta\n"

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
        "🔍 <b>Kitob qidirish</b> - Kitob, muallif yoki hikoyachi nomini qidiring\n"
        "⭐️ <b>Mashhur kitoblar</b> - Eng ko'p yuklab olingan kitoblar\n"
        "📊 <b>Statistika</b> - Kutubxona haqida ma'lumot\n\n"
        "<b>Qanday foydalanish:</b>\n"
        "1️⃣ Kategoriyalar bo'limiga kiring\n"
        "2️⃣ Kerakli kategoriyani tanlang\n"
        "3️⃣ PDF yoki Audio turini tanlang\n"
        "4️⃣ Kitobni tanlang va tafsilotlarni ko'ring\n"
        "5️⃣ 'Yuklab olish' tugmasini bosing\n\n"
        "✅ PDF kitoblar - yuklab olish\n"
        "✅ Audio kitoblar - tinglash\n\n"
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

@dp.callback_query_handler(lambda c: c.data == "back_to_main_cats")
async def back_to_main_categories(callback: types.CallbackQuery):
    """Asosiy kategoriyalarga qaytish"""
    main_categories = book_db.get_main_categories()
    keyboard = categories_inline_keyboard(main_categories, action_prefix="user_main_cat", row_width=2)

    text = "📚 <b>Kategoriyalar:</b>\n\n"

    for cat in main_categories:
        book_count = book_db.count_books_by_category(cat[0], include_subcategories=True)
        text += f"📁 {cat[1]} - <b>{book_count}</b> ta kitob\n"

    text += "\n<i>Kategoriyani tanlang:</i>"

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