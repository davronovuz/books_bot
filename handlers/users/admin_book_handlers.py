from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging

from loader import dp, user_db, book_db, bot
from data.config import ADMINS
from keyboards.default.book_keyboard import (
    admin_book_main_menu, admin_category_menu, admin_book_menu,
    cancel_button, skip_button, categories_inline_keyboard,
    books_inline_keyboard, confirm_keyboard
)


# =================== STATES ===================

class CategoryState(StatesGroup):
    """Kategoriya qo'shish/tahrirlash state'lari"""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_parent = State()  # YANGI: Subkategoriya uchun
    waiting_for_edit_id = State()
    waiting_for_delete_id = State()


class BookState(StatesGroup):
    """Kitob qo'shish state'lari"""
    waiting_for_category = State()
    waiting_for_subcategory = State()  # YANGI: Subkategoriya
    waiting_for_file = State()  # PDF yoki Audio
    waiting_for_title = State()
    waiting_for_author = State()
    waiting_for_narrator = State()  # YANGI: Audio uchun
    waiting_for_description = State()


class SearchState(StatesGroup):
    """Qidiruv state'i"""
    waiting_for_query = State()


# =================== YORDAMCHI FUNKSIYALAR ===================

async def check_admin_permission(telegram_id: int):
    """Admin huquqini tekshirish"""
    if telegram_id in ADMINS:
        return True
    user = user_db.select_user(telegram_id=telegram_id)
    if not user:
        return False
    return user_db.check_if_admin(user_id=user[0])


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


# =================== ASOSIY MENYU ===================

@dp.message_handler(commands="kitoblar")
async def books_panel(message: types.Message):
    """Kitoblar bo'limiga kirish"""
    if not await check_admin_permission(message.from_user.id):
        await message.reply("🚫 Sizda bu bo'limga kirish huquqi yo'q!")
        return

    await message.answer(
        "📚 <b>Kitoblar boshqaruvi</b>\n\n"
        "Bu bo'limda siz kategoriyalar va kitoblarni boshqarishingiz mumkin.\n"
        "📁 Kategoriyalar - ierarxik tuzilma\n"
        "📖 Kitoblar - PDF va Audio\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_book_main_menu()
    )


# =================== KATEGORIYALAR BO'LIMI ===================

@dp.message_handler(Text(equals="📚 Kategoriyalar"))
async def admin_categories_menu_handler(message: types.Message):
    """Kategoriyalar menyusi"""
    if not await check_admin_permission(message.from_user.id):
        return

    await message.answer(
        "📁 <b>Kategoriyalar boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=admin_category_menu()
    )


# ➕ Kategoriya qo'shish
@dp.message_handler(Text(equals="➕ Kategoriya qo'shish"))
async def start_add_category(message: types.Message, state: FSMContext):
    """Kategoriya qo'shishni boshlash"""
    if not await check_admin_permission(message.from_user.id):
        return

    # Asosiy kategoriyalarni ko'rsatish
    main_categories = book_db.get_main_categories()

    if main_categories:
        keyboard = categories_inline_keyboard(main_categories, action_prefix="parent_cat")
        keyboard.row(types.InlineKeyboardButton("📁 Asosiy kategoriya yaratish", callback_data="parent_cat:none"))

        await message.answer(
            "➕ <b>Yangi kategoriya qo'shish</b>\n\n"
            "Bu subkategoriya bo'lishi kerakmi?\n"
            "Agar ha bo'lsa, asosiy kategoriyani tanlang.\n"
            "Agar yo'q bo'lsa, 'Asosiy kategoriya yaratish' ni bosing.",
            reply_markup=keyboard
        )
        await CategoryState.waiting_for_parent.set()
    else:
        # Hozircha kategoriya yo'q, asosiy yaratamiz
        await message.answer(
            "➕ <b>Yangi kategoriya qo'shish</b>\n\n"
            "📝 Kategoriya nomini kiriting:\n"
            "<i>Masalan: 9-sinf, Adabiyot, Matematika</i>",
            reply_markup=cancel_button()
        )
        await state.update_data(parent_id=None)
        await CategoryState.waiting_for_name.set()


@dp.callback_query_handler(lambda c: c.data.startswith("parent_cat:"), state=CategoryState.waiting_for_parent)
async def process_parent_category(callback: types.CallbackQuery, state: FSMContext):
    """Parent kategoriya tanlash"""
    parent_data = callback.data.split(":")[1]

    if parent_data == "none":
        parent_id = None
        await callback.message.edit_text("📁 <b>Asosiy kategoriya yaratiladi</b>")
    else:
        parent_id = int(parent_data)
        parent = book_db.get_category_by_id(parent_id)
        await callback.message.edit_text(f"📂 <b>Subkategoriya yaratiladi:</b> {parent[1]}")

    await state.update_data(parent_id=parent_id)

    await callback.message.answer(
        "📝 <b>Kategoriya nomini kiriting:</b>\n"
        "<i>Masalan: Matematika, Fizika, O'zbek adabiyoti</i>",
        reply_markup=cancel_button()
    )
    await CategoryState.waiting_for_name.set()
    await callback.answer()


@dp.message_handler(state=CategoryState.waiting_for_name)
async def process_category_name(message: types.Message, state: FSMContext):
    """Kategoriya nomini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_category_menu())
        return

    category_name = message.text.strip()
    data = await state.get_data()
    parent_id = data.get('parent_id')

    # Kategoriya mavjudligini tekshirish
    existing = book_db.get_category_by_name(category_name, parent_id)
    if existing:
        await message.answer(
            "⚠️ Bu kategoriya allaqachon mavjud!\n\n"
            "Boshqa nom kiriting yoki bekor qiling:",
            reply_markup=cancel_button()
        )
        return

    await state.update_data(category_name=category_name)

    await message.answer(
        "📝 <b>Kategoriya tavsifini kiriting:</b>\n"
        "<i>Yoki o'tkazib yuborish tugmasini bosing</i>",
        reply_markup=skip_button()
    )
    await CategoryState.waiting_for_description.set()


@dp.message_handler(state=CategoryState.waiting_for_description)
async def process_category_description(message: types.Message, state: FSMContext):
    """Kategoriya tavsifini qabul qilish va saqlash"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_category_menu())
        return

    description = None if message.text == "⏭ O'tkazib yuborish" else message.text.strip()

    data = await state.get_data()
    category_name = data['category_name']
    parent_id = data.get('parent_id')

    user = user_db.select_user(telegram_id=message.from_user.id)

    try:
        book_db.add_category(category_name, user[0], description, parent_id)

        if parent_id:
            parent = book_db.get_category_by_id(parent_id)
            cat_type = f"Subkategoriya: {parent[1]} → {category_name}"
        else:
            cat_type = f"Asosiy kategoriya: {category_name}"

        await message.answer(
            "✅ <b>Kategoriya muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📁 <b>{cat_type}</b>\n"
            f"📝 <b>Tavsif:</b> {description or 'Tavsif yoq'}",
            reply_markup=admin_category_menu()
        )
        logging.info(f"Category added: {category_name} (parent: {parent_id}) by {message.from_user.id}")
    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=admin_category_menu()
        )
        logging.error(f"Error adding category: {e}")

    await state.finish()


# 📋 Kategoriyalar ro'yxati
@dp.message_handler(Text(equals="📋 Kategoriyalar ro'yxati"))
async def list_categories(message: types.Message):
    """Barcha kategoriyalarni ko'rsatish (ierarxik)"""
    if not await check_admin_permission(message.from_user.id):
        return

    main_categories = book_db.get_main_categories()

    if not main_categories:
        await message.answer(
            "📂 <b>Hozircha kategoriyalar yo'q.</b>\n\n"
            "Kategoriya qo'shish uchun '➕ Kategoriya qo'shish' tugmasini bosing.",
            reply_markup=admin_category_menu()
        )
        return

    text = "📚 <b>Barcha kategoriyalar:</b>\n\n"

    for i, cat in enumerate(main_categories, 1):
        book_count = book_db.count_books_by_category(cat[0], include_subcategories=True)
        text += f"{i}. 📁 <b>{cat[1]}</b> - {book_count} ta kitob\n"
        if cat[2]:  # description
            text += f"   📝 <i>{cat[2]}</i>\n"

        # Subkategoriyalarni ko'rsatish
        subcats = book_db.get_subcategories(cat[0])
        if subcats:
            for sub in subcats:
                sub_book_count = book_db.count_books_by_category(sub[0], include_subcategories=False)
                text += f"   └─ 📂 {sub[1]} - {sub_book_count} ta kitob\n"

        text += "\n"

    await message.answer(text, reply_markup=admin_category_menu())


# 🗑 Kategoriya o'chirish
@dp.message_handler(Text(equals="🗑 Kategoriya o'chirish"))
async def start_delete_category(message: types.Message):
    """Kategoriya o'chirishni boshlash"""
    if not await check_admin_permission(message.from_user.id):
        return

    categories = book_db.get_all_categories()

    if not categories:
        await message.answer(
            "📂 Hozircha kategoriyalar yo'q.",
            reply_markup=admin_category_menu()
        )
        return

    keyboard = categories_inline_keyboard(categories, action_prefix="delete_cat")

    await message.answer(
        "🗑 <b>O'chirish uchun kategoriyani tanlang:</b>\n\n"
        "⚠️ <i>Kategoriya o'chirilsa, undagi barcha subkategoriyalar va kitoblar ham o'chiriladi!</i>",
        reply_markup=keyboard
    )


# =================== KITOBLAR BO'LIMI ===================

@dp.message_handler(Text(equals="📖 Kitoblar"))
async def admin_books_menu_handler(message: types.Message):
    """Kitoblar menyusi"""
    if not await check_admin_permission(message.from_user.id):
        return

    await message.answer(
        "📖 <b>Kitoblar boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=admin_book_menu()
    )


# ➕ Kitob qo'shish
@dp.message_handler(Text(equals="➕ Kitob qo'shish"))
async def start_add_book(message: types.Message, state: FSMContext):
    """Kitob qo'shishni boshlash"""
    if not await check_admin_permission(message.from_user.id):
        return

    main_categories = book_db.get_main_categories()

    if not main_categories:
        await message.answer(
            "⚠️ <b>Avval kategoriya qo'shing!</b>\n\n"
            "Kitob qo'shish uchun kamida bitta kategoriya bo'lishi kerak.",
            reply_markup=admin_book_menu()
        )
        return

    keyboard = categories_inline_keyboard(main_categories, action_prefix="add_book_main_cat")

    await message.answer(
        "➕ <b>Yangi kitob qo'shish</b>\n\n"
        "📁 Asosiy kategoriyani tanlang:",
        reply_markup=keyboard
    )
    await BookState.waiting_for_category.set()


@dp.callback_query_handler(lambda c: c.data.startswith("add_book_main_cat:"), state=BookState.waiting_for_category)
async def process_main_category_for_book(callback: types.CallbackQuery, state: FSMContext):
    """Asosiy kategoriya tanlangandan keyin subkategoriya so'rash"""
    main_cat_id = int(callback.data.split(":")[1])
    main_cat = book_db.get_category_by_id(main_cat_id)

    # Subkategoriyalar bormi?
    subcats = book_db.get_subcategories(main_cat_id)

    if subcats:
        # Subkategoriyalar mavjud
        keyboard = categories_inline_keyboard(subcats, action_prefix="add_book_sub_cat")
        keyboard.row(types.InlineKeyboardButton(
            f"📁 {main_cat[1]} ga qo'shish",
            callback_data=f"add_book_cat:{main_cat_id}"
        ))

        await callback.message.edit_text(
            f"📁 <b>{main_cat[1]}</b>\n\n"
            f"📂 Subkategoriyani tanlang yoki asosiy kategoriyaga qo'shing:",
            reply_markup=keyboard
        )
        await BookState.waiting_for_subcategory.set()
    else:
        # Subkategoriya yo'q, to'g'ridan-to'g'ri file so'raymiz
        await state.update_data(category_id=main_cat_id)
        await callback.message.edit_text(
            f"✅ Kategoriya: <b>{main_cat[1]}</b>\n\n"
            "📎 Endi kitobni yuklang (PDF yoki Audio):"
        )

        await callback.message.answer(
            "📤 <b>Faylni yuklang:</b>\n"
            "• PDF kitob\n"
            "• Audio kitob (MP3, M4A, OGG)",
            reply_markup=cancel_button()
        )
        await BookState.waiting_for_file.set()

    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("add_book_sub_cat:"), state=BookState.waiting_for_subcategory)
async def process_subcategory_for_book(callback: types.CallbackQuery, state: FSMContext):
    """Subkategoriya tanlangandan keyin file so'rash"""
    sub_cat_id = int(callback.data.split(":")[1])
    sub_cat = book_db.get_category_by_id(sub_cat_id)

    await state.update_data(category_id=sub_cat_id)

    path = book_db.get_category_path(sub_cat_id)

    await callback.message.edit_text(
        f"✅ Kategoriya: <b>{path}</b>\n\n"
        "📎 Endi kitobni yuklang (PDF yoki Audio):"
    )

    await callback.message.answer(
        "📤 <b>Faylni yuklang:</b>\n"
        "• PDF kitob\n"
        "• Audio kitob (MP3, M4A, OGG)",
        reply_markup=cancel_button()
    )
    await BookState.waiting_for_file.set()
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("add_book_cat:"), state=BookState.waiting_for_subcategory)
async def process_direct_category_for_book(callback: types.CallbackQuery, state: FSMContext):
    """To'g'ridan-to'g'ri asosiy kategoriyaga qo'shish"""
    cat_id = int(callback.data.split(":")[1])
    cat = book_db.get_category_by_id(cat_id)

    await state.update_data(category_id=cat_id)

    await callback.message.edit_text(
        f"✅ Kategoriya: <b>{cat[1]}</b>\n\n"
        "📎 Endi kitobni yuklang (PDF yoki Audio):"
    )

    await callback.message.answer(
        "📤 <b>Faylni yuklang:</b>\n"
        "• PDF kitob\n"
        "• Audio kitob (MP3, M4A, OGG)",
        reply_markup=cancel_button()
    )
    await BookState.waiting_for_file.set()
    await callback.answer()


@dp.message_handler(content_types=[types.ContentType.DOCUMENT, types.ContentType.AUDIO],
                    state=BookState.waiting_for_file)
async def process_book_file(message: types.Message, state: FSMContext):
    """PDF yoki Audio faylni qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_book_menu())
        return

    file_id = None
    file_size = None
    file_name = None
    file_type = None
    duration = None

    # PDF tekshirish
    if message.document and message.document.mime_type == 'application/pdf':
        file_id = message.document.file_id
        file_size = message.document.file_size
        file_name = message.document.file_name
        file_type = 'pdf'

    # Audio tekshirish
    elif message.audio:
        file_id = message.audio.file_id
        file_size = message.audio.file_size
        file_name = message.audio.file_name or message.audio.title or "Audio kitob"
        duration = message.audio.duration
        file_type = 'audio'

    # Audio document sifatida
    elif message.document and message.document.mime_type in ['audio/mpeg', 'audio/mp3', 'audio/m4a', 'audio/ogg']:
        file_id = message.document.file_id
        file_size = message.document.file_size
        file_name = message.document.file_name
        file_type = 'audio'

    else:
        await message.answer(
            "⚠️ <b>Noto'g'ri fayl turi!</b>\n\n"
            "Iltimos, PDF yoki Audio fayl yuboring.",
            reply_markup=cancel_button()
        )
        return

    await state.update_data(
        file_id=file_id,
        file_size=file_size,
        file_name=file_name,
        file_type=file_type,
        duration=duration
    )

    emoji = "📕" if file_type == 'pdf' else "🎧"
    type_name = "PDF" if file_type == 'pdf' else "Audio"

    msg = (
        f"✅ <b>{type_name} yuklandi!</b>\n"
        f"{emoji} Fayl: {file_name}\n"
        f"📦 Hajmi: {format_file_size(file_size)}\n"
    )

    if duration:
        msg += f"⏱ Davomiyligi: {format_duration(duration)}\n"

    msg += "\n📝 Endi kitob nomini kiriting:"

    await message.answer(msg, reply_markup=cancel_button())
    await BookState.waiting_for_title.set()


@dp.message_handler(state=BookState.waiting_for_title)
async def process_book_title(message: types.Message, state: FSMContext):
    """Kitob nomini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_book_menu())
        return

    title = message.text.strip()
    await state.update_data(title=title)

    await message.answer(
        "✍️ <b>Muallif nomini kiriting:</b>\n"
        "<i>Yoki o'tkazib yuborish tugmasini bosing</i>",
        reply_markup=skip_button()
    )
    await BookState.waiting_for_author.set()


@dp.message_handler(state=BookState.waiting_for_author)
async def process_book_author(message: types.Message, state: FSMContext):
    """Muallif nomini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_book_menu())
        return

    author = None if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(author=author)

    # Agar audio bo'lsa, hikoyachi so'raymiz
    data = await state.get_data()
    if data.get('file_type') == 'audio':
        await message.answer(
            "🎙 <b>Hikoyachi (narrator) nomini kiriting:</b>\n"
            "<i>Yoki o'tkazib yuborish tugmasini bosing</i>",
            reply_markup=skip_button()
        )
        await BookState.waiting_for_narrator.set()
    else:
        # PDF uchun to'g'ridan-to'g'ri tavsif
        await message.answer(
            "📝 <b>Kitob haqida qisqacha tavsif kiriting:</b>\n"
            "<i>Yoki o'tkazib yuborish tugmasini bosing</i>",
            reply_markup=skip_button()
        )
        await BookState.waiting_for_description.set()


@dp.message_handler(state=BookState.waiting_for_narrator)
async def process_book_narrator(message: types.Message, state: FSMContext):
    """Hikoyachi nomini qabul qilish (audio uchun)"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_book_menu())
        return

    narrator = None if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(narrator=narrator)

    await message.answer(
        "📝 <b>Kitob haqida qisqacha tavsif kiriting:</b>\n"
        "<i>Yoki o'tkazib yuborish tugmasini bosing</i>",
        reply_markup=skip_button()
    )
    await BookState.waiting_for_description.set()


@dp.message_handler(state=BookState.waiting_for_description)
async def process_book_description(message: types.Message, state: FSMContext):
    """Kitob tavsifini qabul qilish va saqlash"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_book_menu())
        return

    description = None if message.text == "⏭ O'tkazib yuborish" else message.text.strip()

    data = await state.get_data()
    user = user_db.select_user(telegram_id=message.from_user.id)

    try:
        book_db.add_book(
            title=data['title'],
            file_id=data['file_id'],
            category_id=data['category_id'],
            uploaded_by=user[0],
            file_type=data['file_type'],
            author=data.get('author'),
            narrator=data.get('narrator'),
            description=description,
            duration=data.get('duration'),
            file_size=data.get('file_size')
        )

        category_path = book_db.get_category_path(data['category_id'])

        emoji = "📕" if data['file_type'] == 'pdf' else "🎧"
        type_name = "PDF" if data['file_type'] == 'pdf' else "Audio"

        msg = (
            f"✅ <b>{type_name} kitob muvaffaqiyatli qo'shildi!</b>\n\n"
            f"{emoji} <b>Nom:</b> {data['title']}\n"
            f"✍️ <b>Muallif:</b> {data.get('author') or 'Nomalum'}\n"
        )

        if data.get('narrator'):
            msg += f"🎙 <b>Hikoyachi:</b> {data['narrator']}\n"

        msg += f"📁 <b>Kategoriya:</b> {category_path}\n"
        msg += f"📦 <b>Hajmi:</b> {format_file_size(data.get('file_size'))}\n"

        if data.get('duration'):
            msg += f"⏱ <b>Davomiyligi:</b> {format_duration(data['duration'])}"

        await message.answer(msg, reply_markup=admin_book_menu())
        logging.info(f"{type_name} book added: {data['title']} by {message.from_user.id}")
    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=admin_book_menu()
        )
        logging.error(f"Error adding book: {e}")

    await state.finish()


# 📋 Barcha kitoblar
@dp.message_handler(Text(equals="📋 Barcha kitoblar"))
async def list_all_books(message: types.Message):
    """Barcha kitoblarni ko'rsatish"""
    if not await check_admin_permission(message.from_user.id):
        return

    books = book_db.get_all_books()

    if not books:
        await message.answer(
            "📚 <b>Hozircha kitoblar yo'q.</b>\n\n"
            "Kitob qo'shish uchun '➕ Kitob qo'shish' tugmasini bosing.",
            reply_markup=admin_book_menu()
        )
        return

    pdf_count = book_db.count_books('pdf')
    audio_count = book_db.count_books('audio')

    text = (
        f"📖 <b>Jami kitoblar: {len(books)}</b>\n"
        f"📕 PDF: {pdf_count} | 🎧 Audio: {audio_count}\n\n"
    )

    for i, book in enumerate(books[:15], 1):
        emoji = "📕" if book[3] == 'pdf' else "🎧"  # file_type
        text += f"{i}. {emoji} <b>{book[1]}</b>\n"

        if book[4]:  # author
            text += f"   ✍️ {book[4]}\n"
        if book[5]:  # narrator
            text += f"   🎙 {book[5]}\n"

        text += f"   📁 {book[-1]}\n"  # category_name
        text += f"   📥 {book[10]} marta yuklab olindi\n\n"  # download_count

    if len(books) > 15:
        text += f"\n<i>... va yana {len(books) - 15} ta kitob</i>"

    await message.answer(text, reply_markup=admin_book_menu())


# 🗑 Kitob o'chirish
@dp.message_handler(Text(equals="🗑 Kitob o'chirish"))
async def start_delete_book(message: types.Message):
    """Kitob o'chirishni boshlash"""
    if not await check_admin_permission(message.from_user.id):
        return

    categories = book_db.get_main_categories()

    if not categories:
        await message.answer(
            "📂 Avval kategoriya qo'shing!",
            reply_markup=admin_book_menu()
        )
        return

    keyboard = categories_inline_keyboard(categories, action_prefix="delete_book_cat")

    await message.answer(
        "🗑 <b>Avval kategoriyani tanlang:</b>",
        reply_markup=keyboard
    )


# =================== STATISTIKA ===================

@dp.message_handler(Text(equals="📊 Statistika"))
async def show_admin_statistics(message: types.Message):
    """Admin statistikasini ko'rsatish"""
    if not await check_admin_permission(message.from_user.id):
        return

    try:
        stats = book_db.get_statistics()
        total_users = user_db.count_users()
        active_users = user_db.count_active_users()

        text = (
            "📊 <b>Statistika</b>\n\n"
            "<b>👥 Foydalanuvchilar:</b>\n"
            f"   • Jami: {total_users}\n"
            f"   • Faol: {active_users}\n\n"
            "<b>📚 Kitoblar tizimi:</b>\n"
            f"   • Kategoriyalar: {stats['total_categories']}\n"
            f"   ├─ Asosiy: {stats['main_categories']}\n"
            f"   └─ Subkategoriyalar: {stats['total_categories'] - stats['main_categories']}\n\n"
            f"   • Kitoblar: {stats['total_books']}\n"
            f"   ├─ 📕 PDF: {stats['pdf_books']}\n"
            f"   └─ 🎧 Audio: {stats['audio_books']}\n\n"
        )

        # Eng mashhur kitoblar
        popular_pdf = book_db.get_popular_books(3, 'pdf')
        popular_audio = book_db.get_popular_books(3, 'audio')

        if popular_pdf:
            text += "<b>⭐️ Eng mashhur PDF kitoblar:</b>\n"
            for i, book in enumerate(popular_pdf, 1):
                text += f"{i}. {book[1]} - <b>{book[10]}</b> marta\n"
            text += "\n"

        if popular_audio:
            text += "<b>🎵 Eng mashhur Audio kitoblar:</b>\n"
            for i, book in enumerate(popular_audio, 1):
                text += f"{i}. {book[1]} - <b>{book[10]}</b> marta\n"

        await message.answer(text, reply_markup=admin_book_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}", reply_markup=admin_book_main_menu())
        logging.error(f"Error showing statistics: {e}")


# =================== QIDIRUV ===================

@dp.message_handler(Text(equals="🔍 Kitob qidirish"))
async def start_admin_search(message: types.Message, state: FSMContext):
    """Admin uchun qidiruv"""
    if not await check_admin_permission(message.from_user.id):
        return

    await message.answer(
        "🔍 <b>Kitob qidirish</b>\n\n"
        "Kitob, muallif yoki hikoyachi nomini kiriting:",
        reply_markup=cancel_button()
    )
    await SearchState.waiting_for_query.set()


@dp.message_handler(state=SearchState.waiting_for_query)
async def process_admin_search(message: types.Message, state: FSMContext):
    """Qidiruv so'rovini qayta ishlash"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_book_main_menu())
        return

    query = message.text.strip()

    try:
        results = book_db.search_books(query)

        if not results:
            await message.answer(
                f"❌ <b>'{query}'</b> bo'yicha hech narsa topilmadi.",
                reply_markup=admin_book_main_menu()
            )
            await state.finish()
            return

        pdf_results = [b for b in results if b[3] == 'pdf']
        audio_results = [b for b in results if b[3] == 'audio']

        text = f"🔍 <b>Qidiruv natijasi: '{query}'</b>\n\n"
        text += f"✅ Topildi: {len(results)} ta kitob\n"
        text += f"📕 PDF: {len(pdf_results)} | 🎧 Audio: {len(audio_results)}\n\n"

        for i, book in enumerate(results[:10], 1):
            emoji = "📕" if book[3] == 'pdf' else "🎧"
            text += f"{i}. {emoji} <b>{book[1]}</b>\n"

            if book[4]:  # author
                text += f"   ✍️ {book[4]}\n"
            if book[5]:  # narrator
                text += f"   🎙 {book[5]}\n"

            text += f"   📁 {book[-1]}\n"
            text += f"   📥 {book[10]} marta yuklab olindi\n\n"

        if len(results) > 10:
            text += f"\n<i>... va yana {len(results) - 10} ta kitob</i>"

        await message.answer(text, reply_markup=admin_book_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}", reply_markup=admin_book_main_menu())
        logging.error(f"Error searching books: {e}")

    await state.finish()


# =================== ORQAGA TUGMALARI ===================

@dp.message_handler(Text(equals="🔙 Orqaga"))
async def back_to_main(message: types.Message, state: FSMContext):
    """Orqaga"""
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    if await check_admin_permission(message.from_user.id):
        await message.answer(
            "📚 <b>Kitoblar boshqaruvi</b>",
            reply_markup=admin_book_main_menu()
        )


# =================== CALLBACK HANDLERS ===================

@dp.callback_query_handler(lambda c: c.data.startswith("delete_cat:"))
async def handle_delete_category_callback(callback: types.CallbackQuery):
    """Kategoriya o'chirish callback"""
    category_id = int(callback.data.split(":")[1])
    category = book_db.get_category_by_id(category_id)
    book_count = book_db.count_books_by_category(category_id, include_subcategories=True)
    has_subs = book_db.has_subcategories(category_id)

    warning = "❗️ <i>Bu kategoriya"
    if has_subs:
        warning += ", undagi barcha subkategoriyalar"
    warning += " va kitoblar o'chiriladi!</i>"

    await callback.message.edit_text(
        f"⚠️ <b>Rostdan ham o'chirmoqchimisiz?</b>\n\n"
        f"📁 <b>Kategoriya:</b> {category[1]}\n"
        f"📖 <b>Kitoblar soni:</b> {book_count}\n\n"
        f"{warning}",
        reply_markup=confirm_keyboard(f"delete_cat_{category_id}")
    )
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("delete_book_cat:"))
async def show_books_for_delete(callback: types.CallbackQuery):
    """Kategoriya bo'yicha kitoblarni ko'rsatish (o'chirish uchun)"""
    category_id = int(callback.data.split(":")[1])
    books = book_db.get_books_by_category(category_id, include_subcategories=True)

    if not books:
        await callback.message.edit_text("📂 Bu kategoriyada kitoblar yo'q!")
        await callback.answer()
        return

    keyboard = books_inline_keyboard(books, action_prefix="confirm_delete_book", show_delete=True)

    await callback.message.edit_text(
        "🗑 <b>O'chirish uchun kitobni tanlang:</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("confirm_yes:"))
async def handle_confirm_delete(callback: types.CallbackQuery):
    """O'chirishni tasdiqlash"""
    action = callback.data.split(":")[1]

    try:
        if action.startswith("delete_cat_"):
            category_id = int(action.replace("delete_cat_", ""))
            category = book_db.get_category_by_id(category_id)

            book_db.delete_category(category_id)
            await callback.message.edit_text(
                f"✅ Kategoriya '<b>{category[1]}</b>' muvaffaqiyatli o'chirildi!"
            )
            logging.info(f"Category deleted: {category[1]}")

        elif action.startswith("delete_book_"):
            book_id = int(action.replace("delete_book_", ""))
            book = book_db.get_book_by_id(book_id)

            book_db.delete_book(book_id)
            await callback.message.edit_text(
                f"✅ Kitob '<b>{book[1]}</b>' muvaffaqiyatli o'chirildi!"
            )
            logging.info(f"Book deleted: {book[1]}")

    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {str(e)}")
        logging.error(f"Error deleting: {e}")

    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("confirm_no:"))
async def handle_cancel_delete(callback: types.CallbackQuery):
    """O'chirishni bekor qilish"""
    await callback.message.edit_text("❌ O'chirish bekor qilindi")
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "cancel")
async def handle_cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    """Bekor qilish callback"""
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    await callback.message.edit_text("❌ Bekor qilindi")
    await callback.answer()


@dp.message_handler(Text(equals="❌ Bekor qilish"), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    """Bekor qilish handler"""
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    await message.answer("❌ Bekor qilindi", reply_markup=admin_book_main_menu())