from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# =================== ADMIN KEYBOARDS ===================

def admin_book_main_menu():
    """Admin kitoblar bo'limi asosiy menyu"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📚 Kategoriyalar"),
        KeyboardButton("📖 Kitoblar"),
    )
    keyboard.add(
        KeyboardButton("📊 Statistika"),
        KeyboardButton("🔍 Kitob qidirish"),
    )
    keyboard.add(
        KeyboardButton("🔙 Ortga qaytish")
    )
    return keyboard


def admin_category_menu():
    """Admin kategoriyalar menyu"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("➕ Kategoriya qo'shish"),
        KeyboardButton("📋 Kategoriyalar ro'yxati"),
    )
    keyboard.add(
        KeyboardButton("✏️ Kategoriya tahrirlash"),
        KeyboardButton("🗑 Kategoriya o'chirish"),
    )
    keyboard.add(
        KeyboardButton("🔙 Orqaga")
    )
    return keyboard


def admin_book_menu():
    """Admin kitoblar menyu"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("➕ Kitob qo'shish"),
        KeyboardButton("📋 Barcha kitoblar"),
    )
    keyboard.add(
        KeyboardButton("✏️ Kitob tahrirlash"),
        KeyboardButton("🗑 Kitob o'chirish"),
    )
    keyboard.add(
        KeyboardButton("🔙 Orqaga")
    )
    return keyboard


def cancel_button():
    """Bekor qilish tugmasi"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Bekor qilish"))
    return keyboard


def skip_button():
    """O'tkazib yuborish tugmasi"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("⏭ O'tkazib yuborish"),
        KeyboardButton("❌ Bekor qilish")
    )
    return keyboard


# =================== INLINE KEYBOARDS ===================

def categories_inline_keyboard(categories, action_prefix="select_cat", row_width=2):
    """Kategoriyalar inline keyboard (asosiy va subkategoriyalar uchun)"""
    keyboard = InlineKeyboardMarkup(row_width=row_width)

    if not categories:
        keyboard.add(InlineKeyboardButton("📂 Kategoriyalar yo'q", callback_data="no_data"))
        return keyboard

    for cat in categories:
        # cat[0] = id, cat[1] = name, cat[3] = parent_id
        # Asosiy kategoriya uchun 📁, subkategoriya uchun 📂
        try:
            if cat[3] is None:  # parent_id is None
                emoji = "📁"
            else:
                emoji = "📂"
        except:
            # Agar parent_id ustuni yo'q bo'lsa (eski database)
            emoji = "📁"

        keyboard.insert(
            InlineKeyboardButton(
                text=f"{emoji} {cat[1]}",
                callback_data=f"{action_prefix}:{cat[0]}"
            )
        )

    keyboard.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"))

    return keyboard


def books_inline_keyboard(books, action_prefix="get_book", show_delete=False, back_callback="back_to_main_cats"):
    """Kitoblar inline keyboard (PDF va Audio uchun turli emoji)"""
    keyboard = InlineKeyboardMarkup(row_width=1)

    if not books:
        keyboard.add(InlineKeyboardButton("📚 Kitoblar yo'q", callback_data="no_data"))
        return keyboard

    for book in books:
        # book[0] = id, book[1] = title, book[3] = file_type
        book_title = book[1][:40] + "..." if len(book[1]) > 40 else book[1]

        # PDF yoki Audio emoji
        try:
            emoji = "📕" if book[3] == 'pdf' else "🎧"
        except:
            # Agar file_type ustuni yo'q bo'lsa (eski database)
            emoji = "📖"

        if show_delete:
            keyboard.row(
                InlineKeyboardButton(
                    text=f"{emoji} {book_title}",
                    callback_data=f"book_info:{book[0]}"
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=f"delete_book:{book[0]}"
                )
            )
        else:
            keyboard.add(
                InlineKeyboardButton(
                    text=f"{emoji} {book_title}",
                    callback_data=f"{action_prefix}:{book[0]}"
                )
            )

    keyboard.add(InlineKeyboardButton("🔙 Orqaga", callback_data=back_callback))

    return keyboard


def confirm_keyboard(action_id):
    """Tasdiqlash keyboard"""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"confirm_yes:{action_id}"),
        InlineKeyboardButton("❌ Yo'q", callback_data=f"confirm_no:{action_id}")
    )
    return keyboard


def book_detail_keyboard(book_id, file_type='pdf'):
    """Kitob tafsilotlari keyboard (PDF yoki Audio)"""
    keyboard = InlineKeyboardMarkup()

    # PDF uchun "Yuklab olish", Audio uchun "Tinglash"
    if file_type == 'pdf':
        button_text = "📥 Yuklab olish"
    else:
        button_text = "🎵 Tinglash"

    keyboard.add(
        InlineKeyboardButton(button_text, callback_data=f"download_book:{book_id}")
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main_cats")
    )
    return keyboard


# =================== USER KEYBOARDS ===================

def user_main_menu():
    """User asosiy menyu"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📚 Kategoriyalar"),
        KeyboardButton("🔍 Kitob qidirish"),
    )
    keyboard.add(
        KeyboardButton("⭐️ Mashhur kitoblar"),
        KeyboardButton("📊 Statistika"),
    )
    keyboard.add(
        KeyboardButton("ℹ️ Yordam")
    )
    return keyboard


def back_button():
    """Orqaga tugmasi"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Orqaga"))
    return keyboard


def pagination_keyboard(current_page, total_pages, prefix="page"):
    """Sahifalash keyboard"""
    keyboard = InlineKeyboardMarkup(row_width=5)

    buttons = []

    # Oldingi sahifa
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}:{current_page - 1}"))

    # Sahifa raqamlari
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))

    # Keyingi sahifa
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}:{current_page + 1}"))

    keyboard.row(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"))

    return keyboard