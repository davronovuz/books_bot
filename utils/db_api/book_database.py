from .database import Database
from datetime import datetime


class BookDatabase(Database):
    def create_tables(self):
        """Kategoriyalar va kitoblar jadvallarini yaratish"""

        # Kategoriyalar jadvali (Subkategoriya qo'llab-quvvatlaydi)
        sql_categories = """
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            description TEXT NULL,
            parent_id INTEGER NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES Categories(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES Users(id) ON DELETE CASCADE
        );
        """
        self.execute(sql_categories, commit=True)

        # Kitoblar jadvali (PDF va Audio ikkalasi ham)
        sql_books = """
        CREATE TABLE IF NOT EXISTS Books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(500) NOT NULL,
            file_id VARCHAR(500) NOT NULL,
            file_type VARCHAR(10) NOT NULL DEFAULT 'pdf',
            category_id INTEGER NOT NULL,
            author VARCHAR(255) NULL,
            narrator VARCHAR(255) NULL,
            description TEXT NULL,
            duration INTEGER NULL,
            file_size INTEGER NULL,
            uploaded_by INTEGER NOT NULL,
            download_count INTEGER DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES Categories(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES Users(id) ON DELETE CASCADE
        );
        """
        self.execute(sql_books, commit=True)

    # =================== KATEGORIYALAR ===================

    def add_category(self, name: str, created_by: int, description: str = None, parent_id: int = None):
        """Yangi kategoriya yoki subkategoriya qo'shish"""
        sql = """
        INSERT INTO Categories (name, description, parent_id, created_by)
        VALUES (?, ?, ?, ?)
        """
        self.execute(sql, parameters=(name, description, parent_id, created_by), commit=True)

    def get_all_categories(self):
        """Barcha kategoriyalarni olish"""
        sql = "SELECT * FROM Categories ORDER BY parent_id, name"
        return self.execute(sql, fetchall=True)

    def get_main_categories(self):
        """Faqat asosiy kategoriyalarni olish (parent_id = NULL)"""
        sql = "SELECT * FROM Categories WHERE parent_id IS NULL ORDER BY name"
        return self.execute(sql, fetchall=True)

    def get_subcategories(self, parent_id: int):
        """Berilgan kategoriyaning subkategoriyalarini olish"""
        sql = "SELECT * FROM Categories WHERE parent_id = ? ORDER BY name"
        return self.execute(sql, parameters=(parent_id,), fetchall=True)

    def has_subcategories(self, category_id: int):
        """Kategoriyaning subkategoriyalari bormi?"""
        sql = "SELECT COUNT(*) FROM Categories WHERE parent_id = ?"
        count = self.execute(sql, parameters=(category_id,), fetchone=True)[0]
        return count > 0

    def get_category_by_id(self, category_id: int):
        """ID bo'yicha kategoriyani olish"""
        sql = "SELECT * FROM Categories WHERE id = ?"
        return self.execute(sql, parameters=(category_id,), fetchone=True)

    def get_category_by_name(self, name: str, parent_id: int = None):
        """Nom bo'yicha kategoriyani olish"""
        if parent_id is not None:
            sql = "SELECT * FROM Categories WHERE name = ? AND parent_id = ?"
            return self.execute(sql, parameters=(name, parent_id), fetchone=True)
        else:
            sql = "SELECT * FROM Categories WHERE name = ?"
            return self.execute(sql, parameters=(name,), fetchone=True)

    def delete_category(self, category_id: int):
        """Kategoriyani o'chirish (barcha subkategoriyalar ham o'chiriladi)"""
        sql = "DELETE FROM Categories WHERE id = ?"
        self.execute(sql, parameters=(category_id,), commit=True)

    def update_category(self, category_id: int, name: str = None, description: str = None):
        """Kategoriyani yangilash"""
        if name:
            sql = "UPDATE Categories SET name = ? WHERE id = ?"
            self.execute(sql, parameters=(name, category_id), commit=True)
        if description:
            sql = "UPDATE Categories SET description = ? WHERE id = ?"
            self.execute(sql, parameters=(description, category_id), commit=True)

    def count_categories(self):
        """Kategoriyalar sonini hisoblash"""
        sql = "SELECT COUNT(*) FROM Categories"
        return self.execute(sql, fetchone=True)[0]

    def is_main_category(self, category_id: int):
        """Asosiy kategoriya ekanligini tekshirish"""
        category = self.get_category_by_id(category_id)
        return category and category[3] is None  # parent_id is NULL

    def get_category_path(self, category_id: int):
        """Kategoriya yo'lini olish (Asosiy → Sub → Sub-sub)"""
        path = []
        current_id = category_id

        while current_id:
            category = self.get_category_by_id(current_id)
            if category:
                path.insert(0, category[1])  # name
                current_id = category[3]  # parent_id
            else:
                break

        return " → ".join(path) if path else ""

    # =================== KITOBLAR ===================

    def add_book(self, title: str, file_id: str, category_id: int, uploaded_by: int,
                 file_type: str = 'pdf', author: str = None, narrator: str = None,
                 description: str = None, duration: int = None, file_size: int = None):
        """Yangi kitob qo'shish (PDF yoki Audio)"""
        sql = """
        INSERT INTO Books (title, file_id, file_type, category_id, author, narrator, 
                          description, duration, file_size, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.execute(sql, parameters=(title, file_id, file_type, category_id, author,
                                      narrator, description, duration, file_size, uploaded_by),
                     commit=True)

    def get_all_books(self, file_type: str = None):
        """Barcha kitoblarni olish (ixtiyoriy: faqat PDF yoki Audio)"""
        if file_type:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            WHERE Books.file_type = ?
            ORDER BY Books.created_at DESC
            """
            return self.execute(sql, parameters=(file_type,), fetchall=True)
        else:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            ORDER BY Books.created_at DESC
            """
            return self.execute(sql, fetchall=True)

    def get_books_by_category(self, category_id: int, file_type: str = None):
        """Kategoriya bo'yicha kitoblarni olish"""
        if file_type:
            sql = """
            SELECT * FROM Books 
            WHERE category_id = ? AND file_type = ?
            ORDER BY title
            """
            return self.execute(sql, parameters=(category_id, file_type), fetchall=True)
        else:
            sql = """
            SELECT * FROM Books 
            WHERE category_id = ?
            ORDER BY title
            """
            return self.execute(sql, parameters=(category_id,), fetchall=True)

    def get_book_by_id(self, book_id: int):
        """ID bo'yicha kitobni olish"""
        sql = """
        SELECT Books.*, Categories.name as category_name 
        FROM Books 
        JOIN Categories ON Books.category_id = Categories.id
        WHERE Books.id = ?
        """
        return self.execute(sql, parameters=(book_id,), fetchone=True)

    def search_books(self, query: str, file_type: str = None):
        """Kitob qidirish (nom, muallif va hikoyachi bo'yicha)"""
        search_query = f"%{query}%"

        if file_type:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            WHERE (Books.title LIKE ? OR Books.author LIKE ? OR Books.narrator LIKE ?)
              AND Books.file_type = ?
            ORDER BY Books.title
            """
            return self.execute(sql, parameters=(search_query, search_query, search_query, file_type),
                                fetchall=True)
        else:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            WHERE Books.title LIKE ? OR Books.author LIKE ? OR Books.narrator LIKE ?
            ORDER BY Books.title
            """
            return self.execute(sql, parameters=(search_query, search_query, search_query),
                                fetchall=True)

    def delete_book(self, book_id: int):
        """Kitobni o'chirish"""
        sql = "DELETE FROM Books WHERE id = ?"
        self.execute(sql, parameters=(book_id,), commit=True)

    def increment_download_count(self, book_id: int):
        """Yuklab olishlar sonini oshirish"""
        sql = "UPDATE Books SET download_count = download_count + 1 WHERE id = ?"
        self.execute(sql, parameters=(book_id,), commit=True)

    def count_books(self, file_type: str = None):
        """Kitoblar sonini hisoblash"""
        if file_type:
            sql = "SELECT COUNT(*) FROM Books WHERE file_type = ?"
            return self.execute(sql, parameters=(file_type,), fetchone=True)[0]
        else:
            sql = "SELECT COUNT(*) FROM Books"
            return self.execute(sql, fetchone=True)[0]

    def count_books_by_category(self, category_id: int, file_type: str = None, include_subcategories: bool = True):
        """Kategoriya bo'yicha kitoblar sonini hisoblash"""
        if include_subcategories:
            # Subkategoriyalarni ham hisoblash
            category_ids = [category_id]
            subcats = self.get_subcategories(category_id)
            category_ids.extend([sub[0] for sub in subcats])

            placeholders = ','.join('?' * len(category_ids))

            if file_type:
                sql = f"SELECT COUNT(*) FROM Books WHERE category_id IN ({placeholders}) AND file_type = ?"
                params = category_ids + [file_type]
            else:
                sql = f"SELECT COUNT(*) FROM Books WHERE category_id IN ({placeholders})"
                params = category_ids

            return self.execute(sql, parameters=tuple(params), fetchone=True)[0]
        else:
            # Faqat o'sha kategoriya
            if file_type:
                sql = "SELECT COUNT(*) FROM Books WHERE category_id = ? AND file_type = ?"
                return self.execute(sql, parameters=(category_id, file_type), fetchone=True)[0]
            else:
                sql = "SELECT COUNT(*) FROM Books WHERE category_id = ?"
                return self.execute(sql, parameters=(category_id,), fetchone=True)[0]

    def get_popular_books(self, limit: int = 10, file_type: str = None):
        """Eng ko'p yuklab olingan kitoblar"""
        if file_type:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            WHERE Books.file_type = ?
            ORDER BY Books.download_count DESC
            LIMIT ?
            """
            return self.execute(sql, parameters=(file_type, limit), fetchall=True)
        else:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            ORDER BY Books.download_count DESC
            LIMIT ?
            """
            return self.execute(sql, parameters=(limit,), fetchall=True)

    # =================== STATISTIKA ===================

    def get_statistics(self):
        """To'liq statistikani olish"""
        stats = {
            'total_categories': self.count_categories(),
            'main_categories': len(self.get_main_categories()),
            'total_books': self.count_books(),
            'pdf_books': self.count_books('pdf'),
            'audio_books': self.count_books('audio'),
        }
        return stats