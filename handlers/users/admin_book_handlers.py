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
    waiting_for_edit_id = State()
    waiting_for_delete_id = State()


class BookState(StatesGroup):
    """Kitob qo'shish state'lari"""
    waiting_for_category = State()
    waiting_for_pdf = State()
    waiting_for_title = State()
    waiting_for_author = State()
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


# =================== ASOSIY MENYU ===================

@dp.message_handler(commands="kitoblar")
async def books_panel(message: types.Message):
    """Kitoblar bo'limiga kirish"""
    telegram_id = message.from_user.id

    if not await check_admin_permission(telegram_id):
        await message.reply("❌ Sizda bu bo'limga kirish huquqi yo'q!")
        return

    await message.answer(
        "📚 <b>Kitoblar boshqaruvi</b>\n\n"
        "Bu bo'limda siz kategoriyalar va kitoblarni boshqarishingiz mumkin.\n"
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

    await message.answer(
        "➕ <b>Yangi kategoriya qo'shish</b>\n\n"
        "📝 Kategoriya nomini kiriting:\n"
        "<i>Masalan: 9-sinf, 6-sinf, Adabiyot, Matematika</i>",
        reply_markup=cancel_button()
    )
    await CategoryState.waiting_for_name.set()


@dp.message_handler(state=CategoryState.waiting_for_name)
async def process_category_name(message: types.Message, state: FSMContext):
    """Kategoriya nomini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_category_menu())
        return

    category_name = message.text.strip()

    # Kategoriya mavjudligini tekshirish
    existing = book_db.get_category_by_name(category_name)
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

    user = user_db.select_user(telegram_id=message.from_user.id)

    try:
        book_db.add_category(category_name, user[0], description)

        await message.answer(
            "✅ <b>Kategoriya muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📁 <b>Nom:</b> {category_name}\n"
            f"📝 <b>Tavsif:</b> {description or 'Tavsif yoq'}",
            reply_markup=admin_category_menu()
        )
        logging.info(f"Category added: {category_name} by {message.from_user.id}")
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
    """Barcha kategoriyalarni ko'rsatish"""
    if not await check_admin_permission(message.from_user.id):
        return

    categories = book_db.get_all_categories()

    if not categories:
        await message.answer(
            "📂 <b>Hozircha kategoriyalar yo'q.</b>\n\n"
            "Kategoriya qo'shish uchun '➕ Kategoriya qo'shish' tugmasini bosing.",
            reply_markup=admin_category_menu()
        )
        return

    text = "📚 <b>Barcha kategoriyalar:</b>\n\n"

    for i, cat in enumerate(categories, 1):
        book_count = book_db.count_books_by_category(cat[0])
        text += f"{i}. 📁 <b>{cat[1]}</b> - {book_count} ta kitob\n"
        if cat[2]:  # description
            text += f"   📝 <i>{cat[2]}</i>\n"
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
        "⚠️ <i>Kategoriya o'chirilsa, undagi barcha kitoblar ham o'chiriladi!</i>",
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

    categories = book_db.get_all_categories()

    if not categories:
        await message.answer(
            "⚠️ <b>Avval kategoriya qo'shing!</b>\n\n"
            "Kitob qo'shish uchun kamida bitta kategoriya bo'lishi kerak.",
            reply_markup=admin_book_menu()
        )
        return

    keyboard = categories_inline_keyboard(categories, action_prefix="add_book_cat")

    await message.answer(
        "➕ <b>Yangi kitob qo'shish</b>\n\n"
        "📁 Kitob uchun kategoriyani tanlang:",
        reply_markup=keyboard
    )
    await BookState.waiting_for_category.set()


@dp.callback_query_handler(lambda c: c.data.startswith("add_book_cat:"), state=BookState.waiting_for_category)
async def process_book_category(callback: types.CallbackQuery, state: FSMContext):
    """Kategoriya tanlanganidan keyin PDF so'rash"""
    category_id = int(callback.data.split(":")[1])
    category = book_db.get_category_by_id(category_id)

    await state.update_data(category_id=category_id)

    await callback.message.edit_text(
        f"✅ Kategoriya tanlandi: <b>{category[1]}</b>\n\n"
        "📎 Endi kitobni PDF formatda yuboring:"
    )

    await callback.message.answer(
        "📤 <b>Kitobni PDF formatda yuklang:</b>",
        reply_markup=cancel_button()
    )

    await BookState.waiting_for_pdf.set()
    await callback.answer()


@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=BookState.waiting_for_pdf)
async def process_book_pdf(message: types.Message, state: FSMContext):
    """PDF faylni qabul qilish"""
    if not message.document or message.document.mime_type != 'application/pdf':
        await message.answer(
            "⚠️ <b>Iltimos, faqat PDF fayl yuboring!</b>",
            reply_markup=cancel_button()
        )
        return

    file_id = message.document.file_id
    file_size = message.document.file_size
    file_name = message.document.file_name

    await state.update_data(file_id=file_id, file_size=file_size, original_name=file_name)

    await message.answer(
        f"✅ <b>PDF yuklandi!</b>\n"
        f"📄 Fayl: {file_name}\n"
        f"📦 Hajmi: {format_file_size(file_size)}\n\n"
        f"📝 Endi kitob nomini kiriting:",
        reply_markup=cancel_button()
    )
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
            author=data.get('author'),
            description=description,
            file_size=data.get('file_size')
        )

        category = book_db.get_category_by_id(data['category_id'])

        await message.answer(
            "✅ <b>Kitob muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📖 <b>Nom:</b> {data['title']}\n"
            f"✍️ <b>Muallif:</b> {data.get('author') or 'Nomalum'}\n"
            f"📁 <b>Kategoriya:</b> {category[1]}\n"
            f"📦 <b>Hajmi:</b> {format_file_size(data.get('file_size'))}",
            reply_markup=admin_book_menu()
        )
        logging.info(f"Book added: {data['title']} by {message.from_user.id}")
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

    text = f"📖 <b>Jami kitoblar: {len(books)}</b>\n\n"

    for i, book in enumerate(books[:15], 1):  # Faqat 15 ta kitob
        text += f"{i}. 📕 <b>{book[1]}</b>\n"
        if book[4]:  # author
            text += f"   ✍️ {book[4]}\n"
        text += f"   📁 {book[-1]}\n"  # category_name
        text += f"   📥 {book[8]} marta yuklab olindi\n\n"

    if len(books) > 15:
        text += f"\n<i>... va yana {len(books) - 15} ta kitob</i>"

    await message.answer(text, reply_markup=admin_book_menu())


# 🗑 Kitob o'chirish
@dp.message_handler(Text(equals="🗑 Kitob o'chirish"))
async def start_delete_book(message: types.Message):
    """Kitob o'chirishni boshlash"""
    if not await check_admin_permission(message.from_user.id):
        return

    categories = book_db.get_all_categories()

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
        total_categories = book_db.count_categories()
        total_books = book_db.count_books()
        total_users = user_db.count_users()
        active_users = user_db.count_active_users()

        text = (
            "📊 <b>Statistika</b>\n\n"
            "<b>👥 Foydalanuvchilar:</b>\n"
            f"   • Jami: {total_users}\n"
            f"   • Faol: {active_users}\n\n"
            "<b>📚 Kitoblar tizimi:</b>\n"
            f"   • Kategoriyalar: {total_categories}\n"
            f"   • Kitoblar: {total_books}\n\n"
        )

        # Eng mashhur kitoblar
        popular = book_db.get_popular_books(5)
        if popular:
            text += "<b>⭐️ Eng mashhur kitoblar:</b>\n\n"
            for i, book in enumerate(popular, 1):
                text += f"{i}. {book[1]} - <b>{book[8]}</b> marta\n"

        # Kategoriyalar bo'yicha statistika
        categories = book_db.get_all_categories()
        if categories:
            text += "\n<b>📁 Kategoriyalar bo'yicha:</b>\n\n"
            for cat in categories[:5]:
                count = book_db.count_books_by_category(cat[0])
                text += f"• {cat[1]}: {count} ta kitob\n"

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
        "Kitob yoki muallif nomini kiriting:",
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

        text = f"🔍 <b>Qidiruv natijasi: '{query}'</b>\n\n"
        text += f"Topildi: {len(results)} ta kitob\n\n"

        for i, book in enumerate(results[:10], 1):
            text += f"{i}. 📕 <b>{book[1]}</b>\n"
            if book[4]:
                text += f"   ✍️ {book[4]}\n"
            text += f"   📁 {book[-1]}\n"
            text += f"   📥 {book[8]} marta yuklab olindi\n\n"

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
    book_count = book_db.count_books_by_category(category_id)

    await callback.message.edit_text(
        f"⚠️ <b>Rostdan ham o'chirmoqchimisiz?</b>\n\n"
        f"📁 <b>Kategoriya:</b> {category[1]}\n"
        f"📖 <b>Kitoblar soni:</b> {book_count}\n\n"
        f"❗️ <i>Bu kategoriya va undagi barcha kitoblar o'chiriladi!</i>",
        reply_markup=confirm_keyboard(f"delete_cat_{category_id}")
    )
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("delete_book_cat:"))
async def show_books_for_delete(callback: types.CallbackQuery):
    """Kategoriya bo'yicha kitoblarni ko'rsatish (o'chirish uchun)"""
    category_id = int(callback.data.split(":")[1])
    books = book_db.get_books_by_category(category_id)

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