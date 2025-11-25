from .database import Database
from datetime import datetime


class BookDatabase(Database):
    def create_tables(self):
        """Kategoriyalar va kitoblar jadvallarini yaratish"""

        # Kategoriyalar jadvali
        sql_categories = """
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER NOT NULL,
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
            category_id INTEGER NOT NULL,
            author VARCHAR(255) NULL,
            description TEXT NULL,
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

    def add_category(self, name: str, created_by: int, description: str = None):
        """Yangi kategoriya qo'shish"""
        sql = """
        INSERT INTO Categories (name, description, created_by)
        VALUES (?, ?, ?)
        """
        self.execute(sql, parameters=(name, description, created_by), commit=True)

    def get_all_categories(self):
        """Barcha kategoriyalarni olish"""
        sql = "SELECT * FROM Categories ORDER BY name"
        return self.execute(sql, fetchall=True)

    def get_category_by_id(self, category_id: int):
        """ID bo'yicha kategoriyani olish"""
        sql = "SELECT * FROM Categories WHERE id = ?"
        return self.execute(sql, parameters=(category_id,), fetchone=True)

    def get_category_by_name(self, name: str):
        """Nom bo'yicha kategoriyani olish"""
        sql = "SELECT * FROM Categories WHERE name = ?"
        return self.execute(sql, parameters=(name,), fetchone=True)

    def delete_category(self, category_id: int):
        """Kategoriyani o'chirish"""
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

    # =================== KITOBLAR ===================

    def add_book(self, title: str, file_id: str, category_id: int, uploaded_by: int,
                 author: str = None, description: str = None, file_size: int = None):
        """Yangi kitob qo'shish"""
        sql = """
        INSERT INTO Books (title, file_id, category_id, author, description, file_size, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute(sql, parameters=(title, file_id, category_id, author, description,
                                      file_size, uploaded_by), commit=True)

    def get_all_books(self):
        """Barcha kitoblarni olish"""
        sql = """
        SELECT Books.*, Categories.name as category_name 
        FROM Books 
        JOIN Categories ON Books.category_id = Categories.id
        ORDER BY Books.created_at DESC
        """
        return self.execute(sql, fetchall=True)

    def get_books_by_category(self, category_id: int):
        """Kategoriya bo'yicha kitoblarni olish"""
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

    def search_books(self, query: str):
        """Kitob qidirish (nom bo'yicha)"""
        sql = """
        SELECT Books.*, Categories.name as category_name 
        FROM Books 
        JOIN Categories ON Books.category_id = Categories.id
        WHERE Books.title LIKE ? OR Books.author LIKE ?
        ORDER BY Books.title
        """
        search_query = f"%{query}%"
        return self.execute(sql, parameters=(search_query, search_query), fetchall=True)

    def delete_book(self, book_id: int):
        """Kitobni o'chirish"""
        sql = "DELETE FROM Books WHERE id = ?"
        self.execute(sql, parameters=(book_id,), commit=True)

    def increment_download_count(self, book_id: int):
        """Yuklab olishlar sonini oshirish"""
        sql = "UPDATE Books SET download_count = download_count + 1 WHERE id = ?"
        self.execute(sql, parameters=(book_id,), commit=True)

    def count_books(self):
        """Kitoblar sonini hisoblash"""
        sql = "SELECT COUNT(*) FROM Books"
        return self.execute(sql, fetchone=True)[0]

    def count_books_by_category(self, category_id: int):
        """Kategoriya bo'yicha kitoblar sonini hisoblash"""
        sql = "SELECT COUNT(*) FROM Books WHERE category_id = ?"
        return self.execute(sql, parameters=(category_id,), fetchone=True)[0]

    def get_popular_books(self, limit: int = 10):
        """Eng ko'p yuklab olingan kitoblar"""
        sql = """
        SELECT Books.*, Categories.name as category_name 
        FROM Books 
        JOIN Categories ON Books.category_id = Categories.id
        ORDER BY Books.download_count DESC
        LIMIT ?
        """
        return self.execute(sql, parameters=(limit,), fetchall=True)