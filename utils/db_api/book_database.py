from .database import Database
from datetime import datetime
import logging


class BookDatabase(Database):
    def create_tables(self):
        """Kategoriyalar va kitoblar jadvallarini yaratish"""

        # Kategoriyalar jadvali
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

        # Kitoblar jadvali
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

    # =================== BULK INSERT ===================

    def add_books_bulk(self, books_list: list):
        """Ko'p kitobni bir vaqtda qo'shish (loop bilan)

        books_list formati:
        [
            (title, file_id, file_type, category_id, author, narrator, description, duration, file_size, uploaded_by),
            ...
        ]
        """
        added = 0
        for book in books_list:
            try:
                sql = """
                INSERT INTO Books (title, file_id, file_type, category_id, author, narrator, 
                                  description, duration, file_size, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.execute(sql, parameters=book, commit=True)
                added += 1
            except Exception as e:
                logging.error(f"Error adding book {book[0]}: {e}")
                continue
        return added

    # =================== KATEGORIYALAR ===================

    def add_category(self, name: str, created_by: int, description: str = None, parent_id: int = None):
        """Yangi kategoriya qo'shish"""
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
        """Faqat asosiy kategoriyalarni olish"""
        sql = "SELECT * FROM Categories WHERE parent_id IS NULL ORDER BY name"
        return self.execute(sql, fetchall=True)

    def get_subcategories(self, parent_id: int):
        """Subkategoriyalarni olish"""
        sql = "SELECT * FROM Categories WHERE parent_id = ? ORDER BY name"
        return self.execute(sql, parameters=(parent_id,), fetchall=True)

    def has_subcategories(self, category_id: int):
        """Subkategoriyalar bormi?"""
        sql = "SELECT COUNT(*) FROM Categories WHERE parent_id = ?"
        result = self.execute(sql, parameters=(category_id,), fetchone=True)
        return result[0] > 0 if result else False

    def get_category_by_id(self, category_id: int):
        """ID bo'yicha kategoriya"""
        sql = "SELECT * FROM Categories WHERE id = ?"
        return self.execute(sql, parameters=(category_id,), fetchone=True)

    def get_category_by_name(self, name: str, parent_id: int = None):
        """Nom bo'yicha kategoriya"""
        if parent_id is not None:
            sql = "SELECT * FROM Categories WHERE name = ? AND parent_id = ?"
            return self.execute(sql, parameters=(name, parent_id), fetchone=True)
        else:
            sql = "SELECT * FROM Categories WHERE name = ? AND parent_id IS NULL"
            return self.execute(sql, parameters=(name,), fetchone=True)

    def delete_category(self, category_id: int):
        """Kategoriyani o'chirish"""
        sql = "DELETE FROM Categories WHERE id = ?"
        self.execute(sql, parameters=(category_id,), commit=True)

    def update_category_name(self, category_id: int, new_name: str):
        """Kategoriya nomini yangilash"""
        sql = "UPDATE Categories SET name = ? WHERE id = ?"
        self.execute(sql, parameters=(new_name, category_id), commit=True)

    def update_category_description(self, category_id: int, new_description: str):
        """Kategoriya tavsifini yangilash"""
        sql = "UPDATE Categories SET description = ? WHERE id = ?"
        self.execute(sql, parameters=(new_description, category_id), commit=True)

    def count_categories(self):
        """Kategoriyalar soni"""
        sql = "SELECT COUNT(*) FROM Categories"
        result = self.execute(sql, fetchone=True)
        return result[0] if result else 0

    def get_category_path(self, category_id: int):
        """Kategoriya yo'li (Asosiy → Sub)"""
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
        """Bitta kitob qo'shish"""
        sql = """
        INSERT INTO Books (title, file_id, file_type, category_id, author, narrator, 
                          description, duration, file_size, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.execute(sql, parameters=(title, file_id, file_type, category_id, author,
                                      narrator, description, duration, file_size, uploaded_by),
                     commit=True)

    def get_all_books(self, file_type: str = None):
        """Barcha kitoblar"""
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
        """Kategoriya bo'yicha kitoblar"""
        if file_type:
            sql = "SELECT * FROM Books WHERE category_id = ? AND file_type = ? ORDER BY title"
            return self.execute(sql, parameters=(category_id, file_type), fetchall=True)
        else:
            sql = "SELECT * FROM Books WHERE category_id = ? ORDER BY title"
            return self.execute(sql, parameters=(category_id,), fetchall=True)

    def get_book_by_id(self, book_id: int):
        """ID bo'yicha kitob"""
        sql = """
        SELECT Books.*, Categories.name as category_name 
        FROM Books 
        JOIN Categories ON Books.category_id = Categories.id
        WHERE Books.id = ?
        """
        return self.execute(sql, parameters=(book_id,), fetchone=True)

    def get_book_by_file_id(self, file_id: str):
        """File ID bo'yicha kitob (dublikat tekshirish uchun)"""
        sql = "SELECT * FROM Books WHERE file_id = ?"
        return self.execute(sql, parameters=(file_id,), fetchone=True)

    def search_books(self, query: str, file_type: str = None):
        """Kitob qidirish"""
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
            return self.execute(sql, parameters=(search_query, search_query, search_query, file_type), fetchall=True)
        else:
            sql = """
            SELECT Books.*, Categories.name as category_name 
            FROM Books 
            JOIN Categories ON Books.category_id = Categories.id
            WHERE Books.title LIKE ? OR Books.author LIKE ? OR Books.narrator LIKE ?
            ORDER BY Books.title
            """
            return self.execute(sql, parameters=(search_query, search_query, search_query), fetchall=True)

    def delete_book(self, book_id: int):
        """Kitobni o'chirish"""
        sql = "DELETE FROM Books WHERE id = ?"
        self.execute(sql, parameters=(book_id,), commit=True)

    def delete_books_bulk(self, book_ids: list):
        """Ko'p kitobni o'chirish"""
        deleted = 0
        for book_id in book_ids:
            try:
                self.delete_book(book_id)
                deleted += 1
            except:
                continue
        return deleted

    def increment_download_count(self, book_id: int):
        """Yuklab olishlar sonini oshirish"""
        sql = "UPDATE Books SET download_count = download_count + 1 WHERE id = ?"
        self.execute(sql, parameters=(book_id,), commit=True)

    def count_books(self, file_type: str = None):
        """Kitoblar soni"""
        if file_type:
            sql = "SELECT COUNT(*) FROM Books WHERE file_type = ?"
            result = self.execute(sql, parameters=(file_type,), fetchone=True)
        else:
            sql = "SELECT COUNT(*) FROM Books"
            result = self.execute(sql, fetchone=True)
        return result[0] if result else 0

    def count_books_by_category(self, category_id: int, file_type: str = None):
        """Kategoriya bo'yicha kitoblar soni"""
        if file_type:
            sql = "SELECT COUNT(*) FROM Books WHERE category_id = ? AND file_type = ?"
            result = self.execute(sql, parameters=(category_id, file_type), fetchone=True)
        else:
            sql = "SELECT COUNT(*) FROM Books WHERE category_id = ?"
            result = self.execute(sql, parameters=(category_id,), fetchone=True)
        return result[0] if result else 0

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

    # =================== KITOBNI YANGILASH ===================

    def update_book_title(self, book_id: int, new_title: str):
        """Kitob nomini yangilash"""
        sql = "UPDATE Books SET title = ? WHERE id = ?"
        self.execute(sql, parameters=(new_title, book_id), commit=True)

    def update_book_author(self, book_id: int, new_author: str):
        """Muallif nomini yangilash"""
        sql = "UPDATE Books SET author = ? WHERE id = ?"
        self.execute(sql, parameters=(new_author, book_id), commit=True)

    def update_book_narrator(self, book_id: int, new_narrator: str):
        """Hikoyachi nomini yangilash"""
        sql = "UPDATE Books SET narrator = ? WHERE id = ?"
        self.execute(sql, parameters=(new_narrator, book_id), commit=True)

    def update_book_description(self, book_id: int, new_description: str):
        """Tavsifni yangilash"""
        sql = "UPDATE Books SET description = ? WHERE id = ?"
        self.execute(sql, parameters=(new_description, book_id), commit=True)

    def update_book_category(self, book_id: int, new_category_id: int):
        """Kategoriyani yangilash"""
        sql = "UPDATE Books SET category_id = ? WHERE id = ?"
        self.execute(sql, parameters=(new_category_id, book_id), commit=True)

    def update_book_file(self, book_id: int, file_id: str, file_type: str, file_size: int = None, duration: int = None):
        """Faylni yangilash"""
        sql = "UPDATE Books SET file_id = ?, file_type = ?, file_size = ?, duration = ? WHERE id = ?"
        self.execute(sql, parameters=(file_id, file_type, file_size, duration, book_id), commit=True)

    # =================== STATISTIKA ===================

    def get_statistics(self):
        """To'liq statistika"""
        stats = {
            'total_categories': self.count_categories(),
            'main_categories': len(self.get_main_categories() or []),
            'total_books': self.count_books(),
            'pdf_books': self.count_books('pdf'),
            'audio_books': self.count_books('audio'),
        }
        return stats