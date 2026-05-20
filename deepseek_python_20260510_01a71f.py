import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import json
import os
import hashlib
import random
import string
from datetime import datetime, timedelta
import sqlite3
import threading
import time
import queue

class MoscowElectronicSchool:
    def __init__(self):
        self.setup_database()
        self.setup_ui()
        self.current_user = None
        self.current_role = None
        self.card_reader_queue = queue.Queue()
        
    def setup_database(self):
        """Инициализация базы данных SQLite"""
        self.conn = sqlite3.connect('mesh_school.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Создаем таблицы
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS students (
                user_id TEXT PRIMARY KEY,
                class_name TEXT,
                parent_id TEXT,
                birth_date TEXT,
                health_group TEXT,
                allergies TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (parent_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS teachers (
                user_id TEXT PRIMARY KEY,
                subjects TEXT,
                classes TEXT,
                education TEXT,
                experience TEXT,
                cabinet TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS parents (
                user_id TEXT PRIMARY KEY,
                children TEXT,
                work_place TEXT,
                position TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS moscow_cards (
                card_uid TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                card_number TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0,
                daily_limit REAL DEFAULT 300,
                active BOOLEAN DEFAULT 1,
                issued_date TEXT,
                last_used TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                lesson_number INTEGER NOT NULL,
                time_start TEXT NOT NULL,
                time_end TEXT NOT NULL,
                subject TEXT NOT NULL,
                teacher_id TEXT,
                room TEXT,
                FOREIGN KEY (teacher_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT,
                comment TEXT,
                teacher_id TEXT,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (teacher_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS homework (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                teacher_id TEXT,
                FOREIGN KEY (teacher_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                date TEXT NOT NULL,
                present BOOLEAN NOT NULL,
                entry_time TEXT,
                exit_time TEXT,
                FOREIGN KEY (student_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS canteen_menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS canteen_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                item TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL,
                FOREIGN KEY (student_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user TEXT NOT NULL,
                to_user TEXT NOT NULL,
                subject TEXT,
                text TEXT NOT NULL,
                date TEXT NOT NULL,
                read BOOLEAN DEFAULT 0,
                FOREIGN KEY (from_user) REFERENCES users(id),
                FOREIGN KEY (to_user) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                message TEXT NOT NULL,
                read BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                action TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')
        
        self.conn.commit()
        
        # Создаем администратора по умолчанию, если база пустая
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        if self.cursor.fetchone()[0] == 0:
            self.create_admin()
            self.create_demo_data()
    
    def create_admin(self):
        """Создание администратора по умолчанию"""
        admin_pass = self.hash_password("admin123")
        self.cursor.execute('''
            INSERT INTO users (id, password, role, full_name, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', admin_pass, 'admin', 'Администратор Системы', 'admin@school.mos.ru', '+79000000000'))
        self.conn.commit()
    
    def create_demo_data(self):
        """Создание демонстрационных данных"""
        # Создаем учителей
        teachers = [
            ('teacher1', 'teacher123', 'Петрова Мария Ивановна', 'petrova@school.mos.ru', '+79001111111',
             '["Математика", "Физика"]', '["1А", "9В"]', 'МГУ', '15 лет', '101'),
            ('teacher2', 'teacher123', 'Сидоров Алексей Владимирович', 'sidorov@school.mos.ru', '+79002222222',
             '["Русский язык", "Литература"]', '["5Б"]', 'МПГУ', '8 лет', '205'),
            ('teacher3', 'teacher123', 'Козлова Анна Сергеевна', 'kozlova@school.mos.ru', '+79003333333',
             '["Информатика", "Программирование"]', '["11А"]', 'МФТИ', '10 лет', '405'),
        ]
        
        for teacher_data in teachers:
            hashed_pass = self.hash_password(teacher_data[1])
            self.cursor.execute('''
                INSERT INTO users (id, password, role, full_name, email, phone)
                VALUES (?, ?, 'teacher', ?, ?, ?)
            ''', (teacher_data[0], hashed_pass, teacher_data[2], teacher_data[3], teacher_data[4]))
            
            self.cursor.execute('''
                INSERT INTO teachers (user_id, subjects, classes, education, experience, cabinet)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (teacher_data[0], teacher_data[5], teacher_data[6], teacher_data[7], teacher_data[8], teacher_data[9]))
        
        # Создаем родителей
        parents = [
            ('parent1', 'parent123', 'Иванова Елена Петровна', 'ivanova@parent.mos.ru', '+79008888881',
             '["student1"]', 'ОАО Технологии', 'Бухгалтер'),
            ('parent2', 'parent123', 'Петров Сергей Иванович', 'petrov@parent.mos.ru', '+79008888882',
             '["student2"]', 'ИП Петров', 'Предприниматель'),
        ]
        
        for parent_data in parents:
            hashed_pass = self.hash_password(parent_data[1])
            self.cursor.execute('''
                INSERT INTO users (id, password, role, full_name, email, phone)
                VALUES (?, ?, 'parent', ?, ?, ?)
            ''', (parent_data[0], hashed_pass, parent_data[2], parent_data[3], parent_data[4]))
            
            self.cursor.execute('''
                INSERT INTO parents (user_id, children, work_place, position)
                VALUES (?, ?, ?, ?)
            ''', (parent_data[0], parent_data[5], parent_data[6], parent_data[7]))
        
        # Создаем учеников
        students = [
            ('student1', 'student123', 'Иванов Петр', 'ivanov.p@student.mos.ru', '+79004444441',
             '1А', 'parent1', '2015-03-15', 'основная', ''),
            ('student2', 'student123', 'Петрова Анна', 'petrova.a@student.mos.ru', '+79004444442',
             '1А', 'parent2', '2015-07-22', 'подготовительная', 'пыльца'),
        ]
        
        for student_data in students:
            hashed_pass = self.hash_password(student_data[1])
            self.cursor.execute('''
                INSERT INTO users (id, password, role, full_name, email, phone)
                VALUES (?, ?, 'student', ?, ?, ?)
            ''', (student_data[0], hashed_pass, student_data[2], student_data[3], student_data[4]))
            
            self.cursor.execute('''
                INSERT INTO students (user_id, class_name, parent_id, birth_date, health_group, allergies)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_data[0], student_data[5], student_data[6], student_data[7], student_data[8], student_data[9]))
            
            # Выдаем карты Москвёнок
            card_uid = f"A{random.randint(100000, 999999)}"
            card_number = f"9644{random.randint(100000000000, 999999999999)}"
            
            self.cursor.execute('''
                INSERT INTO moscow_cards (card_uid, user_id, card_number, balance, daily_limit, active, issued_date)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (card_uid, student_data[0], card_number, random.randint(500, 2000), random.randint(300, 800),
                 datetime.now().strftime('%Y-%m-%d')))
        
        # Добавляем демо-оценки
        subjects = ['Математика', 'Русский язык', 'Литература', 'Физика']
        for student_id in ['student1', 'student2']:
            for subject in subjects:
                for _ in range(random.randint(5, 10)):
                    grade = random.randint(2, 5)
                    date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d')
                    grade_type = random.choice(['контрольная', 'самостоятельная', 'домашняя', 'ответ у доски'])
                    
                    self.cursor.execute('''
                        INSERT INTO grades (student_id, subject, grade, date, type, comment, teacher_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (student_id, subject, grade, date, grade_type, 'Хорошая работа', 'teacher1'))
        
        # Добавляем меню столовой на сегодня
        today = datetime.now().strftime('%Y-%m-%d')
        menu_items = [
            ("Борщ", 65.00, "супы"),
            ("Куриный суп", 55.00, "супы"),
            ("Гречка с котлетой", 85.00, "горячее"),
            ("Макароны с сыром", 45.00, "горячее"),
            ("Салат Цезарь", 60.00, "салаты"),
            ("Компот", 15.00, "напитки"),
            ("Чай", 10.00, "напитки"),
            ("Булочка", 20.00, "выпечка"),
        ]
        
        for name, price, category in menu_items:
            self.cursor.execute('''
                INSERT INTO canteen_menu (date, name, price, category)
                VALUES (?, ?, ?, ?)
            ''', (today, name, price, category))
        
        # Генерируем расписание
        self.generate_schedule()
        
        # Добавляем посещаемость
        for student_id in ['student1', 'student2']:
            for i in range(10):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                present = random.choice([True, True, True, False])  # 75% шанс присутствия
                entry_time = f"{random.randint(8, 9):02d}:{random.randint(0, 59):02d}" if present else None
                
                self.cursor.execute('''
                    INSERT INTO attendance (student_id, date, present, entry_time)
                    VALUES (?, ?, ?, ?)
                ''', (student_id, date, present, entry_time))
        
        self.conn.commit()
    
    def generate_schedule(self):
        """Генерация расписания для всех классов"""
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        times = [
            ("08:30", "09:15"),
            ("09:25", "10:10"),
            ("10:30", "11:15"),
            ("11:35", "12:20"),
            ("12:40", "13:25"),
            ("13:45", "14:30"),
            ("14:40", "15:25")
        ]
        
        schedule_data = {
            "1А": {
                "Понедельник": [("Математика", "teacher1"), ("Русский язык", "teacher2"), ("Чтение", "teacher2"), ("Окружающий мир", "teacher1")],
                "Вторник": [("Математика", "teacher1"), ("ИЗО", "teacher2"), ("Музыка", "teacher2"), ("Физкультура", "teacher3")],
                "Среда": [("Русский язык", "teacher2"), ("Математика", "teacher1"), ("Чтение", "teacher2"), ("Окружающий мир", "teacher1")],
                "Четверг": [("Физкультура", "teacher3"), ("Русский язык", "teacher2"), ("Математика", "teacher1"), ("ИЗО", "teacher2")],
                "Пятница": [("Чтение", "teacher2"), ("Математика", "teacher1"), ("Музыка", "teacher2"), ("Окружающий мир", "teacher1")],
            },
            "5Б": {
                "Понедельник": [("Математика", "teacher1"), ("Русский язык", "teacher2"), ("Литература", "teacher2"), ("История", "teacher1"), ("Биология", "teacher3")],
                "Вторник": [("География", "teacher1"), ("Математика", "teacher1"), ("Английский язык", "teacher3"), ("Русский язык", "teacher2"), ("Физкультура", "teacher3")],
                "Среда": [("Литература", "teacher2"), ("Математика", "teacher1"), ("История", "teacher1"), ("Биология", "teacher3"), ("Английский язык", "teacher3")],
                "Четверг": [("Русский язык", "teacher2"), ("География", "teacher1"), ("Математика", "teacher1"), ("Литература", "teacher2"), ("Физкультура", "teacher3")],
                "Пятница": [("История", "teacher1"), ("Английский язык", "teacher3"), ("Русский язык", "teacher2"), ("Биология", "teacher3"), ("Математика", "teacher1")],
            },
            "9В": {
                "Понедельник": [("Алгебра", "teacher1"), ("Геометрия", "teacher1"), ("Физика", "teacher1"), ("Химия", "teacher3"), ("Биология", "teacher3")],
                "Вторник": [("История", "teacher2"), ("Обществознание", "teacher2"), ("Английский язык", "teacher3"), ("Информатика", "teacher3"), ("Физкультура", "teacher3")],
                "Среда": [("Алгебра", "teacher1"), ("Геометрия", "teacher1"), ("Физика", "teacher1"), ("Химия", "teacher3"), ("Литература", "teacher2")],
                "Четверг": [("Биология", "teacher3"), ("История", "teacher2"), ("Алгебра", "teacher1"), ("Английский язык", "teacher3"), ("Информатика", "teacher3")],
                "Пятница": [("Обществознание", "teacher2"), ("Физика", "teacher1"), ("Геометрия", "teacher1"), ("Химия", "teacher3"), ("Физкультура", "teacher3")],
            },
            "11А": {
                "Понедельник": [("Алгебра", "teacher1"), ("Геометрия", "teacher1"), ("Физика", "teacher1"), ("Информатика", "teacher3"), ("Программирование", "teacher3")],
                "Вторник": [("Русский язык", "teacher2"), ("Литература", "teacher2"), ("Обществознание", "teacher2"), ("Английский язык", "teacher3"), ("Физкультура", "teacher3")],
                "Среда": [("Алгебра", "teacher1"), ("Геометрия", "teacher1"), ("Физика", "teacher1"), ("Программирование", "teacher3"), ("Информатика", "teacher3")],
                "Четверг": [("Литература", "teacher2"), ("Русский язык", "teacher2"), ("Алгебра", "teacher1"), ("Английский язык", "teacher3"), ("Обществознание", "teacher2")],
                "Пятница": [("Физика", "teacher1"), ("Геометрия", "teacher1"), ("Программирование", "teacher3"), ("Информатика", "teacher3"), ("Физкультура", "teacher3")],
            }
        }
        
        for class_name, days_schedule in schedule_data.items():
            for day, lessons in days_schedule.items():
                for i, (subject, teacher_id) in enumerate(lessons):
                    if i < len(times):
                        time_start, time_end = times[i]
                        self.cursor.execute('''
                            INSERT INTO schedule (class_name, day_of_week, lesson_number, time_start, time_end, subject, teacher_id, room)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (class_name, day, i + 1, time_start, time_end, subject, teacher_id, f"Каб. {random.randint(100, 400)}"))
        
        self.conn.commit()
    
    def hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def setup_ui(self):
        """Настройка графического интерфейса"""
        self.root = tk.Tk()
        self.root.title("Московская Электронная Школа (МЭШ) v3.0")
        self.root.geometry("1400x900")
        
        # Стили
        self.setup_styles()
        
        # Главный контейнер
        self.main_container = tk.Frame(self.root, bg='#f0f0f0')
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель
        self.setup_header()
        
        # Боковое меню
        self.setup_sidebar()
        
        # Основная область
        self.setup_main_area()
        
        # Строка состояния
        self.setup_status_bar()
        
        # Показываем экран входа
        self.show_login_screen()
    
    def setup_styles(self):
        """Настройка стилей ttk"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настройка цветов
        self.colors = {
            'primary': '#2196F3',      # Синий
            'secondary': '#4CAF50',    # Зеленый
            'warning': '#FF9800',      # Оранжевый
            'danger': '#f44336',       # Красный
            'dark': '#333333',         # Темно-серый
            'light': '#f5f5f5',        # Светло-серый
            'white': '#ffffff',        # Белый
            'bg': '#e8edf2',          # Фон
            'card_bg': '#ffffff',      # Фон карточек
        }
    
    def setup_header(self):
        """Верхняя панель с информацией"""
        self.header = tk.Frame(self.main_container, bg=self.colors['primary'], height=80)
        self.header.pack(fill=tk.X, side=tk.TOP)
        self.header.pack_propagate(False)
        
        # Логотип и название
        logo_frame = tk.Frame(self.header, bg=self.colors['primary'])
        logo_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.title_label = tk.Label(logo_frame, text="🏫 МЭШ", 
                                   font=('Arial', 24, 'bold'),
                                   bg=self.colors['primary'],
                                   fg='white')
        self.title_label.pack(side=tk.LEFT)
        
        self.subtitle_label = tk.Label(logo_frame, text="Московская Электронная Школа",
                                      font=('Arial', 12),
                                      bg=self.colors['primary'],
                                      fg='white')
        self.subtitle_label.pack(side=tk.LEFT, padx=10)
        
        # Информация о пользователе (справа)
        self.user_info_frame = tk.Frame(self.header, bg=self.colors['primary'])
        self.user_info_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        
        self.user_name_label = tk.Label(self.user_info_frame, text="",
                                       font=('Arial', 12, 'bold'),
                                       bg=self.colors['primary'],
                                       fg='white')
        self.user_name_label.pack(side=tk.TOP, anchor='e')
        
        self.user_role_label = tk.Label(self.user_info_frame, text="",
                                       font=('Arial', 10),
                                       bg=self.colors['primary'],
                                       fg='white')
        self.user_role_label.pack(side=tk.TOP, anchor='e')
        
        # Часы
        self.clock_label = tk.Label(self.header, text="",
                                   font=('Arial', 12),
                                   bg=self.colors['primary'],
                                   fg='white')
        self.clock_label.pack(side=tk.RIGHT, padx=20)
        self.update_clock()
    
    def setup_sidebar(self):
        """Боковое меню навигации"""
        self.sidebar = tk.Frame(self.main_container, bg=self.colors['dark'], width=250)
        self.sidebar.pack(fill=tk.Y, side=tk.LEFT)
        self.sidebar.pack_propagate(False)
        
        # Заголовок меню
        menu_header = tk.Label(self.sidebar, text="МЕНЮ",
                              font=('Arial', 14, 'bold'),
                              bg=self.colors['dark'],
                              fg='white',
                              pady=20)
        menu_header.pack(fill=tk.X)
        
        # Контейнер для кнопок меню
        self.menu_buttons_frame = tk.Frame(self.sidebar, bg=self.colors['dark'])
        self.menu_buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопка выхода
        self.logout_btn = tk.Button(self.sidebar, text="🚪 Выйти",
                                   command=self.logout,
                                   bg=self.colors['danger'],
                                   fg='white',
                                   font=('Arial', 10, 'bold'),
                                   relief='flat',
                                   pady=10)
        self.logout_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    
    def setup_main_area(self):
        """Основная рабочая область"""
        self.main_area = tk.Frame(self.main_container, bg=self.colors['bg'])
        self.main_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Заголовок раздела
        self.section_header = tk.Label(self.main_area, text="",
                                      font=('Arial', 18, 'bold'),
                                      bg=self.colors['bg'],
                                      fg=self.colors['dark'],
                                      pady=15)
        self.section_header.pack(fill=tk.X, padx=20)
        
        # Контейнер для контента
        self.content_frame = tk.Frame(self.main_area, bg=self.colors['bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    def setup_status_bar(self):
        """Строка состояния внизу"""
        self.status_bar = tk.Frame(self.main_container, bg=self.colors['dark'], height=30)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        
        # Статус подключения к считывателю
        self.reader_status = tk.Label(self.status_bar, text="🟢 Считыватель Ирон Логик подключен",
                                     bg=self.colors['dark'],
                                     fg='white',
                                     font=('Arial', 9))
        self.reader_status.pack(side=tk.LEFT, padx=10)
        
        # Статус базы данных
        self.db_status = tk.Label(self.status_bar, text="💾 База данных активна",
                                 bg=self.colors['dark'],
                                 fg='white',
                                 font=('Arial', 9))
        self.db_status.pack(side=tk.RIGHT, padx=10)
    
    def update_clock(self):
        """Обновление часов"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=f"🕐 {current_time}")
        self.root.after(1000, self.update_clock)
    
    def clear_content(self):
        """Очистка основной области"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def clear_sidebar(self):
        """Очистка бокового меню"""
        for widget in self.menu_buttons_frame.winfo_children():
            widget.destroy()
    
    def add_menu_button(self, text, command, icon="📌"):
        """Добавление кнопки в боковое меню"""
        btn = tk.Button(self.menu_buttons_frame, text=f"{icon} {text}",
                       command=command,
                       bg=self.colors['dark'],
                       fg='white',
                       font=('Arial', 11),
                       relief='flat',
                       anchor='w',
                       padx=20,
                       pady=12,
                       activebackground=self.colors['primary'],
                       activeforeground='white')
        btn.pack(fill=tk.X, pady=2)
        
        # Ховер эффект
        def on_enter(e):
            btn.config(bg=self.colors['primary'])
        def on_leave(e):
            btn.config(bg=self.colors['dark'])
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def show_login_screen(self):
        """Показать экран входа"""
        self.clear_content()
        self.clear_sidebar()
        self.sidebar.pack_forget()  # Скрываем меню
        
        self.section_header.config(text="🔑 Вход в систему МЭШ")
        
        # Центрируем форму входа
        login_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        login_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Карточка входа
        card = tk.Frame(login_frame, bg='white', relief='raised', borderwidth=2)
        card.pack(padx=20, pady=20)
        
        # Логотип
        logo_label = tk.Label(card, text="🏫", font=('Arial', 48), bg='white')
        logo_label.pack(pady=20)
        
        title_label = tk.Label(card, text="МЭШ - Вход в систему",
                              font=('Arial', 16, 'bold'), bg='white')
        title_label.pack(pady=10)
        
        # Поля ввода
        tk.Label(card, text="Логин:", font=('Arial', 11), bg='white').pack(pady=5)
        self.login_entry = tk.Entry(card, font=('Arial', 12), width=30)
        self.login_entry.pack(pady=5, padx=30)
        
        tk.Label(card, text="Пароль:", font=('Arial', 11), bg='white').pack(pady=5)
        self.password_entry = tk.Entry(card, font=('Arial', 12), show="•", width=30)
        self.password_entry.pack(pady=5, padx=30)
        
        # Кнопка входа
        login_btn = tk.Button(card, text="Войти", command=self.login,
                            bg=self.colors['primary'], fg='white',
                            font=('Arial', 12, 'bold'),
                            padx=30, pady=10, relief='flat')
        login_btn.pack(pady=20)
        
        # Информация о тестовых пользователях
        info_text = """
        Тестовые пользователи:
        Администратор: admin / admin123
        Учитель: teacher1 / teacher123
        Ученик: student1 / student123
        Родитель: parent1 / parent123
        """
        
        tk.Label(card, text=info_text, font=('Arial', 9), bg='white', 
                fg='gray', justify='left').pack(pady=10, padx=20)
        
        # Привязка Enter к кнопке входа
        self.root.bind('<Return>', lambda e: self.login())
    
    def login(self):
        """Авторизация пользователя"""
        username = self.login_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль!")
            return
        
        # Проверяем существование пользователя
        self.cursor.execute('''
            SELECT id, password, role, full_name 
            FROM users 
            WHERE id = ?
        ''', (username,))
        
        user = self.cursor.fetchone()
        
        if user and user[1] == self.hash_password(password):
            self.current_user = {
                'id': user[0],
                'role': user[2],
                'full_name': user[3]
            }
            self.current_role = user[2]
            
            # Обновляем информацию в заголовке
            self.user_name_label.config(text=f"👤 {user[3]}")
            self.user_role_label.config(text=f"📋 {self.get_role_display(user[2])}")
            
            # Показываем боковое меню
            self.sidebar.pack(fill=tk.Y, side=tk.LEFT, before=self.main_area)
            
            # Загружаем меню в зависимости от роли
            self.load_role_menu()
            
            # Загружаем дашборд
            self.show_dashboard()
            
            # Логируем вход
            self.log_action('login', f'Пользователь {username} вошел в систему')
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль!")
    
    def logout(self):
        """Выход из системы"""
        self.log_action('logout', f'Пользователь {self.current_user["id"]} вышел из системы')
        self.current_user = None
        self.current_role = None
        
        # Очищаем информацию пользователя
        self.user_name_label.config(text="")
        self.user_role_label.config(text="")
        
        # Возвращаемся к экрану входа
        self.show_login_screen()
    
    def get_role_display(self, role):
        """Получить отображение роли"""
        roles = {
            'admin': 'Администратор',
            'teacher': 'Учитель',
            'student': 'Ученик',
            'parent': 'Родитель'
        }
        return roles.get(role, role)
    
    def load_role_menu(self):
        """Загрузка меню в зависимости от роли"""
        self.clear_sidebar()
        
        if self.current_role == 'admin':
            self.load_admin_menu()
        elif self.current_role == 'teacher':
            self.load_teacher_menu()
        elif self.current_role == 'student':
            self.load_student_menu()
        elif self.current_role == 'parent':
            self.load_parent_menu()
    
    def load_admin_menu(self):
        """Меню администратора"""
        menu_items = [
            ("Дашборд", self.show_dashboard, "📊"),
            ("Пользователи", self.manage_users, "👥"),
            ("Карты Москвёнок", self.manage_cards, "💳"),
            ("Классы", self.manage_classes, "🏫"),
            ("Расписание", self.manage_schedule, "📅"),
            ("Терминал столовой", self.canteen_terminal, "🍽️"),
            ("Отчеты", self.show_reports, "📈"),
            ("Логи системы", self.show_logs, "📝"),
            ("Настройки", self.system_settings, "⚙️"),
        ]
        
        for text, command, icon in menu_items:
            self.add_menu_button(text, command, icon)
    
    def load_teacher_menu(self):
        """Меню учителя"""
        menu_items = [
            ("Дашборд", self.show_dashboard, "📊"),
            ("Мое расписание", self.show_teacher_schedule, "📅"),
            ("Журнал оценок", self.show_grades_journal, "📝"),
            ("Домашние задания", self.manage_homework, "📚"),
            ("Посещаемость", self.mark_attendance, "✅"),
            ("Мои классы", self.show_my_classes, "👥"),
            ("Сообщения", self.show_messages, "📨"),
            ("Отчеты", self.show_teacher_reports, "📈"),
        ]
        
        for text, command, icon in menu_items:
            self.add_menu_button(text, command, icon)
    
    def load_student_menu(self):
        """Меню ученика"""
        menu_items = [
            ("Дашборд", self.show_dashboard, "📊"),
            ("Мое расписание", self.show_student_schedule, "📅"),
            ("Мои оценки", self.show_student_grades, "📊"),
            ("Домашние задания", self.show_student_homework, "📚"),
            ("Моя карта", self.show_student_card, "💳"),
            ("Посещаемость", self.show_student_attendance, "📋"),
            ("Сообщения", self.show_messages, "📨"),
            ("Достижения", self.show_achievements, "🏆"),
        ]
        
        for text, command, icon in menu_items:
            self.add_menu_button(text, command, icon)
    
    def load_parent_menu(self):
        """Меню родителя"""
        menu_items = [
            ("Дашборд", self.show_dashboard, "📊"),
            ("Мои дети", self.show_my_children, "👶"),
            ("Успеваемость", self.show_children_grades, "📊"),
            ("Расписание", self.show_children_schedule, "📅"),
            ("Карты Москвёнок", self.manage_children_cards, "💳"),
            ("Питание", self.show_canteen_menu, "🍽️"),
            ("Сообщения", self.show_messages, "📨"),
            ("Справки", self.request_documents, "📄"),
        ]
        
        for text, command, icon in menu_items:
            self.add_menu_button(text, command, icon)
    
    def show_dashboard(self):
        """Показать дашборд"""
        self.clear_content()
        self.section_header.config(text=f"📊 Дашборд - {self.current_user['full_name']}")
        
        # Создаем сетку для карточек
        cards_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Карточка с информацией о пользователе
        info_card = tk.Frame(cards_frame, bg='white', relief='raised', borderwidth=1)
        info_card.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        tk.Label(info_card, text="👤 Информация", font=('Arial', 14, 'bold'),
                bg='white', fg=self.colors['dark']).pack(pady=10)
        
        tk.Label(info_card, text=f"Имя: {self.current_user['full_name']}",
                font=('Arial', 11), bg='white').pack(anchor='w', padx=20, pady=5)
        
        tk.Label(info_card, text=f"Роль: {self.get_role_display(self.current_role)}",
                font=('Arial', 11), bg='white').pack(anchor='w', padx=20, pady=5)
        
        tk.Label(info_card, text=f"Дата: {datetime.now().strftime('%d.%m.%Y')}",
                font=('Arial', 11), bg='white').pack(anchor='w', padx=20, pady=5)
        
        # Кнопка смены пароля
        tk.Button(info_card, text="🔒 Сменить пароль", command=self.change_password_dialog,
                 bg=self.colors['warning'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=5).pack(pady=10)
        
        # Карточка с быстрыми действиями
        actions_card = tk.Frame(cards_frame, bg='white', relief='raised', borderwidth=1)
        actions_card.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        
        tk.Label(actions_card, text="⚡ Быстрые действия", font=('Arial', 14, 'bold'),
                bg='white', fg=self.colors['dark']).pack(pady=10)
        
        if self.current_role == 'admin':
            actions = [
                ("Добавить пользователя", self.add_user_dialog),
                ("Выдать карту", self.issue_card_dialog),
                ("Просмотр логов", self.show_logs),
            ]
        elif self.current_role == 'teacher':
            actions = [
                ("Выставить оценку", self.add_grade_dialog),
                ("Задать ДЗ", self.add_homework_dialog),
                ("Отметить посещаемость", self.mark_attendance),
            ]
        elif self.current_role == 'student':
            actions = [
                ("Посмотреть оценки", self.show_student_grades),
                ("Расписание на сегодня", self.show_student_schedule),
                ("Моя карта", self.show_student_card),
            ]
        elif self.current_role == 'parent':
            actions = [
                ("Оценки детей", self.show_children_grades),
                ("Пополнить карту", self.top_up_card_dialog),
                ("Меню столовой", self.show_canteen_menu),
            ]
        
        for text, command in actions:
            btn = tk.Button(actions_card, text=text, command=command,
                          bg=self.colors['primary'], fg='white',
                          font=('Arial', 10), relief='flat',
                          padx=15, pady=8)
            btn.pack(pady=5, padx=20, fill=tk.X)
        
        # Настройка весов для сетки
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)
    
    def change_password_dialog(self):
        """Диалог смены пароля"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Сменить пароль")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="СМЕНА ПАРОЛЯ", font=('Arial', 14, 'bold'), pady=10).pack()
        
        tk.Label(dialog, text="Текущий пароль:", font=('Arial', 11)).pack(pady=5)
        old_pass_entry = tk.Entry(dialog, show="•", font=('Arial', 11))
        old_pass_entry.pack(pady=5)
        
        tk.Label(dialog, text="Новый пароль:", font=('Arial', 11)).pack(pady=5)
        new_pass_entry = tk.Entry(dialog, show="•", font=('Arial', 11))
        new_pass_entry.pack(pady=5)
        
        tk.Label(dialog, text="Подтвердите пароль:", font=('Arial', 11)).pack(pady=5)
        confirm_pass_entry = tk.Entry(dialog, show="•", font=('Arial', 11))
        confirm_pass_entry.pack(pady=5)
        
        def change_password():
            old_pass = old_pass_entry.get()
            new_pass = new_pass_entry.get()
            confirm_pass = confirm_pass_entry.get()
            
            if not all([old_pass, new_pass, confirm_pass]):
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return
            
            # Проверяем текущий пароль
            self.cursor.execute("SELECT password FROM users WHERE id = ?", (self.current_user['id'],))
            current_hash = self.cursor.fetchone()[0]
            
            if current_hash != self.hash_password(old_pass):
                messagebox.showerror("Ошибка", "Неверный текущий пароль!")
                return
            
            if new_pass != confirm_pass:
                messagebox.showerror("Ошибка", "Пароли не совпадают!")
                return
            
            if len(new_pass) < 6:
                messagebox.showerror("Ошибка", "Пароль должен быть не менее 6 символов!")
                return
            
            # Обновляем пароль
            new_hash = self.hash_password(new_pass)
            self.cursor.execute("UPDATE users SET password = ? WHERE id = ?", 
                              (new_hash, self.current_user['id']))
            self.conn.commit()
            
            self.log_action('password_changed', f'Пользователь {self.current_user["id"]} изменил пароль')
            messagebox.showinfo("Успех", "Пароль успешно изменен!")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Сохранить", command=change_password,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def change_login_dialog(self, user_id):
        """Диалог смены логина"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Изменить логин")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        self.cursor.execute("SELECT full_name FROM users WHERE id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        tk.Label(dialog, text=f"ИЗМЕНИТЬ ЛОГИН: {user[0]}", font=('Arial', 14, 'bold'), pady=10).pack()
        
        tk.Label(dialog, text="Текущий логин:", font=('Arial', 11)).pack(pady=5)
        tk.Label(dialog, text=user_id, font=('Arial', 11, 'bold'), fg=self.colors['primary']).pack()
        
        tk.Label(dialog, text="Новый логин:", font=('Arial', 11)).pack(pady=5)
        new_login_entry = tk.Entry(dialog, font=('Arial', 11))
        new_login_entry.pack(pady=5)
        
        tk.Label(dialog, text="Пароль для подтверждения:", font=('Arial', 11)).pack(pady=5)
        confirm_pass_entry = tk.Entry(dialog, show="•", font=('Arial', 11))
        confirm_pass_entry.pack(pady=5)
        
        def change_login():
            new_login = new_login_entry.get().strip()
            confirm_pass = confirm_pass_entry.get()
            
            if not new_login or not confirm_pass:
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return
            
            # Проверяем пароль
            self.cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
            current_hash = self.cursor.fetchone()[0]
            
            if current_hash != self.hash_password(confirm_pass):
                messagebox.showerror("Ошибка", "Неверный пароль!")
                return
            
            # Проверяем, не занят ли новый логин
            self.cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (new_login,))
            if self.cursor.fetchone()[0] > 0:
                messagebox.showerror("Ошибка", "Этот логин уже занят!")
                return
            
            try:
                # Обновляем логин (ID пользователя)
                self.cursor.execute("UPDATE users SET id = ? WHERE id = ?", (new_login, user_id))
                
                # Обновляем связанные таблицы
                tables_to_update = [
                    ("students", "user_id"),
                    ("teachers", "user_id"),
                    ("parents", "user_id"),
                    ("moscow_cards", "user_id"),
                    ("grades", "student_id"),
                    ("grades", "teacher_id"),
                    ("attendance", "student_id"),
                    ("messages", "from_user"),
                    ("messages", "to_user"),
                    ("canteen_purchases", "student_id"),
                    ("homework", "teacher_id"),
                    ("schedule", "teacher_id"),
                ]
                
                for table, column in tables_to_update:
                    try:
                        self.cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {column} = ?", 
                                          (new_login, user_id))
                    except:
                        pass
                
                self.conn.commit()
                
                self.log_action('login_changed', f'Пользователь {user_id} изменил логин на {new_login}')
                
                # Если это текущий пользователь, обновляем сессию
                if user_id == self.current_user['id']:
                    self.current_user['id'] = new_login
                
                messagebox.showinfo("Успех", "Логин успешно изменен!")
                dialog.destroy()
                self.manage_users()
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Ошибка базы данных: {e}")
        
        tk.Button(dialog, text="💾 Сохранить", command=change_login,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def manage_users(self):
        """Управление пользователями"""
        self.clear_content()
        self.section_header.config(text="👥 Управление пользователями")
        
        # Панель инструментов
        toolbar = tk.Frame(self.content_frame, bg=self.colors['bg'])
        toolbar.pack(fill=tk.X, pady=10)
        
        tk.Button(toolbar, text="➕ Добавить пользователя", command=self.add_user_dialog,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="🔄 Обновить", command=self.manage_users,
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        # Таблица пользователей
        table_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Заголовки таблицы
        columns = ("ID", "Имя", "Роль", "Email", "Телефон")
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Заполняем таблицу
        self.cursor.execute('''
            SELECT id, full_name, role, email, phone 
            FROM users 
            ORDER BY role, full_name
        ''')
        
        for user in self.cursor.fetchall():
            tree.insert('', 'end', values=user)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(tree, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки управления
        btn_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        def edit_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите пользователя!")
                return
            item = tree.item(selection[0])
            user_id = item['values'][0]
            self.edit_user_dialog(user_id)
        
        def change_login_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите пользователя!")
                return
            item = tree.item(selection[0])
            user_id = item['values'][0]
            self.change_login_dialog(user_id)
        
        def reset_password():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите пользователя!")
                return
            item = tree.item(selection[0])
            user_id = item['values'][0]
            self.reset_password_dialog(user_id)
        
        def delete_user():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите пользователя!")
                return
            item = tree.item(selection[0])
            user_id = item['values'][0]
            
            if user_id == 'admin':
                messagebox.showerror("Ошибка", "Нельзя удалить администратора!")
                return
            
            if messagebox.askyesno("Подтверждение", f"Удалить пользователя {user_id}?"):
                self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                # Удаляем связанные данные
                self.cursor.execute("DELETE FROM students WHERE user_id = ?", (user_id,))
                self.cursor.execute("DELETE FROM teachers WHERE user_id = ?", (user_id,))
                self.cursor.execute("DELETE FROM parents WHERE user_id = ?", (user_id,))
                self.cursor.execute("DELETE FROM moscow_cards WHERE user_id = ?", (user_id,))
                self.conn.commit()
                
                self.log_action('user_deleted', f'Удален пользователь {user_id}')
                messagebox.showinfo("Успех", "Пользователь удален!")
                self.manage_users()
        
        tk.Button(btn_frame, text="✏️ Редактировать", command=edit_selected,
                 bg=self.colors['primary'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="🔑 Изменить логин", command=change_login_selected,
                 bg=self.colors['warning'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="🔄 Сбросить пароль", command=reset_password,
                 bg=self.colors['warning'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="🗑️ Удалить", command=delete_user,
                 bg=self.colors['danger'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
    
    def reset_password_dialog(self, user_id):
        """Сброс пароля пользователя"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Сбросить пароль")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        self.cursor.execute("SELECT full_name FROM users WHERE id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        tk.Label(dialog, text=f"СБРОС ПАРОЛЯ: {user[0]}", font=('Arial', 14, 'bold'), pady=10).pack()
        
        tk.Label(dialog, text="Новый пароль:", font=('Arial', 11)).pack(pady=5)
        new_pass_entry = tk.Entry(dialog, font=('Arial', 11))
        new_pass_entry.pack(pady=5)
        
        # Кнопка генерации случайного пароля
        def generate_random():
            random_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            new_pass_entry.delete(0, tk.END)
            new_pass_entry.insert(0, random_pass)
        
        tk.Button(dialog, text="🎲 Сгенерировать", command=generate_random,
                 bg=self.colors['primary'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(pady=5)
        
        def save_password():
            new_pass = new_pass_entry.get()
            
            if not new_pass:
                messagebox.showerror("Ошибка", "Введите новый пароль!")
                return
            
            if len(new_pass) < 6:
                messagebox.showerror("Ошибка", "Пароль должен быть не менее 6 символов!")
                return
            
            new_hash = self.hash_password(new_pass)
            self.cursor.execute("UPDATE users SET password = ? WHERE id = ?", 
                              (new_hash, user_id))
            self.conn.commit()
            
            self.log_action('password_reset', f'Сброшен пароль пользователя {user_id}')
            messagebox.showinfo("Успех", f"Пароль сброшен!\nНовый пароль: {new_pass}")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Сохранить", command=save_password,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def add_user_dialog(self):
        """Диалог добавления пользователя"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить пользователя")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля ввода
        fields = [
            ("ID:", "id"),
            ("Пароль:", "password"),
            ("Роль:", "role"),
            ("Полное имя:", "full_name"),
            ("Email:", "email"),
            ("Телефон:", "phone"),
        ]
        
        entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(dialog, text=label, font=('Arial', 11)).pack(pady=5)
            if key == 'role':
                var = tk.StringVar()
                ttk.Combobox(dialog, textvariable=var, 
                           values=['student', 'teacher', 'parent', 'admin'],
                           state='readonly').pack(pady=5)
                entries[key] = var
            elif key == 'password':
                entry = tk.Entry(dialog, show='•', font=('Arial', 11))
                entry.pack(pady=5)
                entries[key] = entry
            else:
                entry = tk.Entry(dialog, font=('Arial', 11))
                entry.pack(pady=5)
                entries[key] = entry
        
        def save_user():
            user_data = {}
            for k, v in entries.items():
                if isinstance(v, tk.StringVar):
                    user_data[k] = v.get()
                elif isinstance(v, tk.Entry):
                    user_data[k] = v.get()
            
            if not all(user_data.values()):
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return
            
            try:
                hashed_pass = self.hash_password(user_data['password'])
                self.cursor.execute('''
                    INSERT INTO users (id, password, role, full_name, email, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_data['id'], hashed_pass, user_data['role'],
                     user_data['full_name'], user_data['email'], user_data['phone']))
                
                # Если студент - добавляем в таблицу students
                if user_data['role'] == 'student':
                    self.cursor.execute('''
                        INSERT INTO students (user_id, class_name)
                        VALUES (?, ?)
                    ''', (user_data['id'], '1А'))
                
                # Если учитель - добавляем в таблицу teachers
                elif user_data['role'] == 'teacher':
                    self.cursor.execute('''
                        INSERT INTO teachers (user_id, subjects, classes)
                        VALUES (?, ?, ?)
                    ''', (user_data['id'], '[]', '[]'))
                
                # Если родитель - добавляем в таблицу parents
                elif user_data['role'] == 'parent':
                    self.cursor.execute('''
                        INSERT INTO parents (user_id, children)
                        VALUES (?, ?)
                    ''', (user_data['id'], '[]'))
                
                self.conn.commit()
                
                self.log_action('user_added', f'Добавлен пользователь {user_data["id"]}')
                messagebox.showinfo("Успех", "Пользователь добавлен!")
                dialog.destroy()
                self.manage_users()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Пользователь с таким ID уже существует!")
        
        tk.Button(dialog, text="Сохранить", command=save_user,
                 bg=self.colors['secondary'], fg='white',
                 font=('Arial', 11, 'bold'), relief='flat',
                 padx=20, pady=10).pack(pady=20)
    
    def edit_user_dialog(self, user_id):
        """Редактирование пользователя"""
        self.cursor.execute('''
            SELECT full_name, email, phone, role FROM users WHERE id = ?
        ''', (user_id,))
        
        user = self.cursor.fetchone()
        if not user:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Редактировать: {user[0]}")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Редактирование: {user[0]}",
                font=('Arial', 14, 'bold'), pady=10).pack()
        
        fields = [
            ("Имя:", "name", user[0]),
            ("Email:", "email", user[1]),
            ("Телефон:", "phone", user[2]),
        ]
        
        entries = {}
        for label, key, value in fields:
            tk.Label(dialog, text=label, font=('Arial', 11)).pack(pady=5)
            entry = tk.Entry(dialog, font=('Arial', 11))
            entry.insert(0, value)
            entry.pack(pady=5)
            entries[key] = entry
        
        def save_changes():
            new_name = entries['name'].get()
            new_email = entries['email'].get()
            new_phone = entries['phone'].get()
            
            self.cursor.execute('''
                UPDATE users SET full_name = ?, email = ?, phone = ?
                WHERE id = ?
            ''', (new_name, new_email, new_phone, user_id))
            
            self.conn.commit()
            
            self.log_action('user_edited', f'Изменены данные пользователя {user_id}')
            messagebox.showinfo("Успех", "Данные обновлены!")
            dialog.destroy()
            self.manage_users()
        
        tk.Button(dialog, text="💾 Сохранить", command=save_changes,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def manage_cards(self):
        """Управление картами Москвёнок"""
        self.clear_content()
        self.section_header.config(text="💳 Управление картами Москвёнок")
        
        # Панель управления картами
        control_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(control_frame, text="💳 Выдать карту", command=self.issue_card_dialog,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="🔍 Сканировать карту", command=self.scan_card_dialog,
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        # Таблица карт
        table_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ("UID", "Владелец", "Номер карты", "Баланс", "Лимит", "Статус")
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Заполняем таблицу
        self.cursor.execute('''
            SELECT mc.card_uid, u.full_name, mc.card_number, 
                   mc.balance, mc.daily_limit, mc.active
            FROM moscow_cards mc
            JOIN users u ON mc.user_id = u.id
            ORDER BY u.full_name
        ''')
        
        for card in self.cursor.fetchall():
            values = list(card)
            values[-1] = "🟢 Активна" if values[-1] else "🔴 Заблокирована"
            tree.insert('', 'end', values=values)
        
        # Кнопки управления выбранной картой
        btn_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        def toggle_card():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите карту!")
                return
            
            item = tree.item(selection[0])
            card_uid = item['values'][0]
            current_status = item['values'][5]
            
            new_status = 0 if "Активна" in current_status else 1
            self.cursor.execute('UPDATE moscow_cards SET active = ? WHERE card_uid = ?', 
                              (new_status, card_uid))
            self.conn.commit()
            
            action = 'разблокирована' if new_status else 'заблокирована'
            self.log_action('card_toggle', f'Карта {card_uid} {action}')
            messagebox.showinfo("Успех", f"Карта {action}!")
            self.manage_cards()
        
        def set_limit():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите карту!")
                return
            
            item = tree.item(selection[0])
            card_uid = item['values'][0]
            
            new_limit = simpledialog.askfloat("Изменить лимит", "Новый дневной лимит (руб.):", 
                                            minvalue=0, maxvalue=10000)
            if new_limit is not None:
                self.cursor.execute('UPDATE moscow_cards SET daily_limit = ? WHERE card_uid = ?',
                                  (new_limit, card_uid))
                self.conn.commit()
                self.log_action('limit_changed', f'Изменен лимит карты {card_uid} на {new_limit} руб.')
                messagebox.showinfo("Успех", f"Лимит изменен на {new_limit:.2f} руб.!")
                self.manage_cards()
        
        tk.Button(btn_frame, text="🔒 Заблок/Разблок", command=toggle_card,
                 bg=self.colors['warning'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="📊 Изменить лимит", command=set_limit,
                 bg=self.colors['primary'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
    
    def scan_card_dialog(self):
        """Диалог сканирования карты"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Терминал считывателя Ирон Логик")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Статус считывателя
        status_frame = tk.Frame(dialog, bg='#f0f0f0', height=50)
        status_frame.pack(fill=tk.X)
        
        tk.Label(status_frame, text="🟢 Считыватель Ирон Логик активен",
                font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='green').pack(pady=10)
        
        # Поле для UID карты
        tk.Label(dialog, text="Поднесите карту к считывателю\nили введите UID вручную:",
                font=('Arial', 12), pady=10).pack()
        
        uid_entry = tk.Entry(dialog, font=('Arial', 14), width=20, justify='center')
        uid_entry.pack(pady=10)
        uid_entry.focus()
        
        # Информация о карте
        info_frame = tk.Frame(dialog, bg='white', relief='raised', borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        info_text = tk.Label(info_frame, text="Информация о карте появится здесь",
                           font=('Arial', 11), bg='white', wraplength=450)
        info_text.pack(pady=20)
        
        def process_card():
            card_uid = uid_entry.get().strip().upper()
            if not card_uid:
                messagebox.showerror("Ошибка", "Введите UID карты!")
                return
            
            self.cursor.execute('''
                SELECT mc.card_uid, u.full_name, u.id, mc.card_number,
                       mc.balance, mc.daily_limit, mc.active, mc.issued_date
                FROM moscow_cards mc
                JOIN users u ON mc.user_id = u.id
                WHERE mc.card_uid = ?
            ''', (card_uid,))
            
            card = self.cursor.fetchone()
            
            if card:
                info = f"""
                ✅ КАРТА НАЙДЕНА
                
                👤 Владелец: {card[1]}
                🆔 ID пользователя: {card[2]}
                💳 Номер карты: {card[3]}
                💰 Баланс: {card[4]:.2f} руб.
                📊 Дневной лимит: {card[5]:.2f} руб.
                📅 Выдана: {card[7]}
                Статус: {'🟢 Активна' if card[6] else '🔴 Заблокирована'}
                """
            else:
                info = """
                ❌ КАРТА НЕ НАЙДЕНА
                
                Карта с таким UID не зарегистрирована в системе.
                Обратитесь к администратору для регистрации карты.
                """
            
            info_text.config(text=info)
        
        tk.Button(dialog, text="🔍 Обработать карту", command=process_card,
                 bg=self.colors['primary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=10)
        
        def simulate_scan():
            uid_entry.delete(0, tk.END)
            uid_entry.insert(0, f"A{random.randint(1000, 9999)}")
            dialog.after(500, process_card)
        
        tk.Button(dialog, text="🔄 Симуляция сканирования", command=simulate_scan,
                 bg=self.colors['warning'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(pady=5)
    
    def issue_card_dialog(self):
        """Диалог выдачи новой карты"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Выдать карту Москвёнок")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="ВЫДАЧА НОВОЙ КАРТЫ МОСКВЁНОК",
                font=('Arial', 14, 'bold'), pady=10).pack()
        
        # Выбор пользователя
        tk.Label(dialog, text="Выберите ученика:", font=('Arial', 11)).pack(pady=5)
        
        self.cursor.execute('''
            SELECT u.id, u.full_name 
            FROM users u 
            WHERE u.role = 'student' 
            AND u.id NOT IN (SELECT user_id FROM moscow_cards)
            ORDER BY u.full_name
        ''')
        
        students = self.cursor.fetchall()
        
        if not students:
            tk.Label(dialog, text="Все ученики уже имеют карты",
                    font=('Arial', 11), fg='gray').pack(pady=20)
            return
        
        student_var = tk.StringVar()
        student_combo = ttk.Combobox(dialog, textvariable=student_var,
                                    values=[f"{s[0]} - {s[1]}" for s in students],
                                    state='readonly', width=40)
        student_combo.pack(pady=10)
        
        # Поля карты
        fields = [
            ("UID карты:", "card_uid"),
            ("Номер карты:", "card_number"),
            ("Начальный баланс:", "initial_balance"),
        ]
        
        entries = {}
        for label, key in fields:
            tk.Label(dialog, text=label, font=('Arial', 11)).pack(pady=5)
            entry = tk.Entry(dialog, font=('Arial', 11))
            entry.pack(pady=5)
            entries[key] = entry
        
        # Значения по умолчанию
        entries['card_uid'].insert(0, f"A{random.randint(100000, 999999)}")
        entries['card_number'].insert(0, f"9644{random.randint(100000000000, 999999999999)}")
        entries['initial_balance'].insert(0, "0")
        
        def save_card():
            if not student_var.get():
                messagebox.showerror("Ошибка", "Выберите ученика!")
                return
            
            student_id = student_var.get().split(' - ')[0]
            card_uid = entries['card_uid'].get().strip().upper()
            card_number = entries['card_number'].get().strip()
            
            try:
                balance = float(entries['initial_balance'].get() or 0)
            except ValueError:
                messagebox.showerror("Ошибка", "Неверная сумма баланса!")
                return
            
            if not card_uid or not card_number:
                messagebox.showerror("Ошибка", "Заполните все поля карты!")
                return
            
            try:
                self.cursor.execute('''
                    INSERT INTO moscow_cards 
                    (card_uid, user_id, card_number, balance, daily_limit, active, issued_date)
                    VALUES (?, ?, ?, ?, 300, 1, ?)
                ''', (card_uid, student_id, card_number, balance, 
                     datetime.now().strftime('%Y-%m-%d')))
                self.conn.commit()
                
                self.log_action('card_issued', f'Выдана карта {card_uid} ученику {student_id}')
                messagebox.showinfo("Успех", "Карта выдана успешно!")
                dialog.destroy()
                self.manage_cards()
            except sqlite3.IntegrityError as e:
                messagebox.showerror("Ошибка", f"Ошибка базы данных: {e}")
        
        tk.Button(dialog, text="💳 Выдать карту", command=save_card,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 12, 'bold'),
                 relief='flat', padx=30, pady=12).pack(pady=20)
    
    def canteen_terminal(self):
        """Терминал столовой"""
        self.clear_content()
        self.section_header.config(text="🍽️ Терминал столовой")
        
        # Левая панель - сканирование карты
        left_panel = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(left_panel, text="💳 СКАНИРОВАНИЕ КАРТЫ",
                font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
        
        tk.Label(left_panel, text="Введите UID карты:",
                font=('Arial', 11), bg='white').pack(pady=5)
        
        card_entry = tk.Entry(left_panel, font=('Arial', 12), width=20, justify='center')
        card_entry.pack(pady=10)
        card_entry.focus()
        
        student_info_label = tk.Label(left_panel, text="",
                                      font=('Arial', 11), bg='white',
                                      wraplength=300, justify='left')
        student_info_label.pack(pady=10, padx=20)
        
        # Правая панель - меню
        right_panel = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(right_panel, text="📋 МЕНЮ НА СЕГОДНЯ",
                font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
        
        # Генерация меню, если его нет
        today = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute("SELECT COUNT(*) FROM canteen_menu WHERE date = ?", (today,))
        if self.cursor.fetchone()[0] == 0:
            self.generate_daily_menu(today)
        
        # Список блюд
        menu_frame = tk.Frame(right_panel, bg='white')
        menu_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.cursor.execute('''
            SELECT id, name, price, category FROM canteen_menu WHERE date = ?
        ''', (today,))
        
        menu_items = self.cursor.fetchall()
        
        selected_item = tk.IntVar()
        selected_item.set(-1)
        
        for i, (item_id, name, price, category) in enumerate(menu_items):
            item_frame = tk.Frame(menu_frame, bg='white')
            item_frame.pack(fill=tk.X, pady=2)
            
            rb = tk.Radiobutton(item_frame, text=f"{name} - {price:.2f} руб. ({category})",
                              variable=selected_item, value=i,
                              font=('Arial', 11), bg='white',
                              anchor='w')
            rb.pack(fill=tk.X)
        
        def process_purchase():
            card_uid = card_entry.get().strip().upper()
            if not card_uid:
                messagebox.showerror("Ошибка", "Введите UID карты!")
                return
            
            if selected_item.get() == -1:
                messagebox.showerror("Ошибка", "Выберите блюдо!")
                return
            
            # Ищем карту
            self.cursor.execute('''
                SELECT mc.user_id, mc.balance, mc.daily_limit, mc.active, u.full_name
                FROM moscow_cards mc
                JOIN users u ON mc.user_id = u.id
                WHERE mc.card_uid = ?
            ''', (card_uid,))
            
            card = self.cursor.fetchone()
            
            if not card:
                messagebox.showerror("Ошибка", "Карта не найдена!")
                return
            
            if not card[3]:
                messagebox.showerror("Ошибка", "Карта заблокирована!")
                return
            
            user_id, balance, daily_limit, active, full_name = card
            item = menu_items[selected_item.get()]
            item_name, item_price = item[1], item[2]
            
            # Проверка баланса
            if balance < item_price:
                messagebox.showerror("Ошибка", f"Недостаточно средств! Баланс: {balance:.2f} руб.")
                return
            
            # Проверка дневного лимита
            self.cursor.execute('''
                SELECT COALESCE(SUM(amount), 0) FROM canteen_purchases
                WHERE student_id = ? AND date = ?
            ''', (user_id, today))
            
            today_spent = self.cursor.fetchone()[0]
            
            if today_spent + item_price > daily_limit:
                messagebox.showerror("Ошибка", 
                    f"Превышен дневной лимит!\nПотрачено сегодня: {today_spent:.2f} руб.\nЛимит: {daily_limit:.2f} руб.")
                return
            
            # Списание средств
            new_balance = balance - item_price
            self.cursor.execute('''
                UPDATE moscow_cards SET balance = ?, last_used = ? WHERE card_uid = ?
            ''', (new_balance, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), card_uid))
            
            # Сохранение покупки
            self.cursor.execute('''
                INSERT INTO canteen_purchases (student_id, date, time, item, amount, balance_after)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, today, datetime.now().strftime('%H:%M:%S'),
                 item_name, item_price, new_balance))
            
            self.conn.commit()
            
            # Обновление информации
            student_info_label.config(text=f"""
            ✅ ПОКУПКА УСПЕШНА
            
            👤 {full_name}
            🍽️ {item_name}: {item_price:.2f} руб.
            💰 Остаток: {new_balance:.2f} руб.
            📊 Потрачено сегодня: {today_spent + item_price:.2f} руб.
            """)
            
            self.log_action('purchase', f'Покупка {item_name} на сумму {item_price} руб. пользователем {user_id}')
        
        def check_card():
            card_uid = card_entry.get().strip().upper()
            if not card_uid:
                return
            
            self.cursor.execute('''
                SELECT u.full_name, mc.balance, mc.daily_limit, mc.active,
                       COALESCE(SUM(cp.amount), 0) as today_spent
                FROM moscow_cards mc
                JOIN users u ON mc.user_id = u.id
                LEFT JOIN canteen_purchases cp ON mc.user_id = cp.student_id AND cp.date = ?
                WHERE mc.card_uid = ?
                GROUP BY u.full_name, mc.balance, mc.daily_limit, mc.active
            ''', (today, card_uid))
            
            card = self.cursor.fetchone()
            
            if card:
                status = "🟢 Активна" if card[3] else "🔴 Заблокирована"
                student_info_label.config(text=f"""
                ✅ КАРТА НАЙДЕНА
                
                👤 {card[0]}
                💰 Баланс: {card[1]:.2f} руб.
                📊 Лимит: {card[2]:.2f} руб./день
                🍽️ Потрачено сегодня: {card[4]:.2f} руб.
                Статус: {status}
                """)
            else:
                student_info_label.config(text="❌ Карта не найдена")
        
        # Кнопки
        buttons_frame = tk.Frame(left_panel, bg='white')
        buttons_frame.pack(pady=10)
        
        tk.Button(buttons_frame, text="🔍 Проверить", command=check_card,
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(buttons_frame, text="💳 Купить", command=process_purchase,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 10, 'bold'),
                 relief='flat', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
    
    def generate_daily_menu(self, date):
        """Генерация меню на день"""
        menu_items = [
            ("Борщ", 65.00, "супы"),
            ("Куриный суп", 55.00, "супы"),
            ("Гречка с котлетой", 85.00, "горячее"),
            ("Макароны с сыром", 45.00, "горячее"),
            ("Плов", 75.00, "горячее"),
            ("Салат Цезарь", 60.00, "салаты"),
            ("Овощной салат", 40.00, "салаты"),
            ("Компот", 15.00, "напитки"),
            ("Чай", 10.00, "напитки"),
            ("Сок", 25.00, "напитки"),
            ("Булочка", 20.00, "выпечка"),
            ("Пирожок с капустой", 25.00, "выпечка"),
            ("Шоколадка", 30.00, "сладости"),
            ("Яблоко", 15.00, "фрукты"),
        ]
        
        selected = random.sample(menu_items, min(8, len(menu_items)))
        
        for name, price, category in selected:
            self.cursor.execute('''
                INSERT INTO canteen_menu (date, name, price, category)
                VALUES (?, ?, ?, ?)
            ''', (date, name, price, category))
        
        self.conn.commit()
    
    def show_teacher_schedule(self):
        """Показать расписание учителя"""
        self.clear_content()
        self.section_header.config(text="📅 Мое расписание")
        
        # Создаем вкладки для дней недели
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        
        self.cursor.execute("SELECT classes FROM teachers WHERE user_id = ?", 
                          (self.current_user['id'],))
        teacher_data = self.cursor.fetchone()
        teacher_classes = json.loads(teacher_data[0]) if teacher_data and teacher_data[0] else []
        
        for day in days:
            day_frame = tk.Frame(notebook, bg='white')
            notebook.add(day_frame, text=day)
            
            tk.Label(day_frame, text=f"Расписание на {day.lower()}",
                    font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
            
            if not teacher_classes:
                tk.Label(day_frame, text="📭 Нет привязанных классов",
                        font=('Arial', 11), bg='white', fg='gray').pack(pady=20)
                continue
            
            for class_name in teacher_classes:
                self.cursor.execute('''
                    SELECT lesson_number, time_start, time_end, subject, room
                    FROM schedule
                    WHERE class_name = ? AND day_of_week = ? AND teacher_id = ?
                    ORDER BY lesson_number
                ''', (class_name, day, self.current_user['id']))
                
                lessons = self.cursor.fetchall()
                
                if lessons:
                    class_label = tk.Label(day_frame, text=f"\n🏫 {class_name} класс",
                                         font=('Arial', 12, 'bold'), bg='white',
                                         fg=self.colors['primary'])
                    class_label.pack(anchor='w', padx=20)
                    
                    for lesson in lessons:
                        lesson_frame = tk.Frame(day_frame, bg='white', relief='solid', borderwidth=1)
                        lesson_frame.pack(fill=tk.X, padx=30, pady=2)
                        
                        tk.Label(lesson_frame, text=f"Урок {lesson[0]}: {lesson[1]}-{lesson[2]}",
                                font=('Arial', 10, 'bold'), bg='white').pack(side=tk.LEFT, padx=10, pady=5)
                        
                        tk.Label(lesson_frame, text=f"{lesson[3]} ({lesson[4]})",
                                font=('Arial', 10), bg='white').pack(side=tk.LEFT, padx=10)
                else:
                    tk.Label(day_frame, text=f"📭 Нет уроков в {class_name} классе",
                            font=('Arial', 10), bg='white', fg='gray').pack(anchor='w', padx=30, pady=5)
    
    def show_grades_journal(self):
        """Журнал оценок для учителя"""
        self.clear_content()
        self.section_header.config(text="📝 Журнал оценок")
        
        # Выбор класса
        control_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(control_frame, text="Выберите класс:", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.cursor.execute('''
            SELECT classes FROM teachers WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        teacher = self.cursor.fetchone()
        classes = json.loads(teacher[0]) if teacher and teacher[0] else []
        
        class_var = tk.StringVar()
        if classes:
            class_var.set(classes[0])
        
        class_combo = ttk.Combobox(control_frame, textvariable=class_var,
                                  values=classes, state='readonly', width=15)
        class_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="📊 Показать", 
                 command=lambda: self.show_class_journal(class_var.get()),
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=5).pack(side=tk.LEFT, padx=10)
        
        # Кнопка добавить оценку
        tk.Button(control_frame, text="➕ Выставить оценку", 
                 command=self.add_grade_dialog,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=5).pack(side=tk.RIGHT, padx=10)
        
        # Область для отображения журнала
        self.journal_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        self.journal_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        if classes:
            self.show_class_journal(classes[0])
    
    def show_class_journal(self, class_name):
        """Отображение журнала класса"""
        for widget in self.journal_frame.winfo_children():
            widget.destroy()
        
        # Получаем учеников класса
        self.cursor.execute('''
            SELECT u.id, u.full_name FROM users u
            JOIN students s ON u.id = s.user_id
            WHERE s.class_name = ?
            ORDER BY u.full_name
        ''', (class_name,))
        
        students = self.cursor.fetchall()
        
        if not students:
            tk.Label(self.journal_frame, text="Нет учеников в классе",
                    font=('Arial', 12), bg='white', fg='gray').pack(pady=20)
            return
        
        # Создаем таблицу
        columns = ("Ученик",) + tuple(f"Оценка {i+1}" for i in range(5)) + ("Средний",)
        tree = ttk.Treeview(self.journal_frame, columns=columns, show='headings', height=15)
        
        tree.heading("Ученик", text="Ученик")
        tree.column("Ученик", width=200)
        
        for i in range(5):
            tree.heading(f"Оценка {i+1}", text=f"Оценка {i+1}")
            tree.column(f"Оценка {i+1}", width=80)
        
        tree.heading("Средний", text="Средний")
        tree.column("Средний", width=80)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Заполняем данными
        for student_id, student_name in students:
            self.cursor.execute('''
                SELECT grade FROM grades 
                WHERE student_id = ? 
                ORDER BY date DESC LIMIT 5
            ''', (student_id,))
            
            grades = [g[0] for g in self.cursor.fetchall()]
            avg = sum(grades) / len(grades) if grades else 0
            
            values = [student_name] + grades + [0] * (5 - len(grades)) + [f"{avg:.2f}"]
            tree.insert('', 'end', values=values)
    
    def add_grade_dialog(self):
        """Диалог выставления оценки"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Выставить оценку")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="ВЫСТАВИТЬ ОЦЕНКУ", font=('Arial', 14, 'bold'), pady=10).pack()
        
        # Выбор класса
        tk.Label(dialog, text="Класс:", font=('Arial', 11)).pack(pady=5)
        
        self.cursor.execute('''
            SELECT classes FROM teachers WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        teacher = self.cursor.fetchone()
        classes = json.loads(teacher[0]) if teacher and teacher[0] else []
        
        class_var = tk.StringVar()
        if classes:
            class_var.set(classes[0])
        
        class_combo = ttk.Combobox(dialog, textvariable=class_var,
                                  values=classes, state='readonly')
        class_combo.pack(pady=5)
        
        # Выбор ученика
        tk.Label(dialog, text="Ученик:", font=('Arial', 11)).pack(pady=5)
        
        student_var = tk.StringVar()
        student_combo = ttk.Combobox(dialog, textvariable=student_var, state='readonly')
        student_combo.pack(pady=5)
        
        def update_students(*args):
            selected_class = class_var.get()
            if selected_class:
                self.cursor.execute('''
                    SELECT u.full_name FROM users u
                    JOIN students s ON u.id = s.user_id
                    WHERE s.class_name = ?
                ''', (selected_class,))
                students = [s[0] for s in self.cursor.fetchall()]
                student_combo['values'] = students
                if students:
                    student_var.set(students[0])
        
        class_var.trace('w', update_students)
        if classes:
            update_students()
        
        # Выбор предмета
        tk.Label(dialog, text="Предмет:", font=('Arial', 11)).pack(pady=5)
        
        self.cursor.execute('''
            SELECT subjects FROM teachers WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        subjects_data = self.cursor.fetchone()
        subjects = json.loads(subjects_data[0]) if subjects_data and subjects_data[0] else []
        
        subject_var = tk.StringVar()
        if subjects:
            subject_var.set(subjects[0])
        
        subject_combo = ttk.Combobox(dialog, textvariable=subject_var,
                                    values=subjects, state='readonly')
        subject_combo.pack(pady=5)
        
        # Оценка
        tk.Label(dialog, text="Оценка:", font=('Arial', 11)).pack(pady=5)
        
        grade_var = tk.IntVar(value=5)
        grade_frame = tk.Frame(dialog, bg='#f0f0f0')
        grade_frame.pack(pady=10)
        
        for grade in [2, 3, 4, 5]:
            tk.Radiobutton(grade_frame, text=str(grade), variable=grade_var, value=grade,
                          font=('Arial', 12), bg='#f0f0f0', indicatoron=0,
                          width=5, padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Тип работы
        tk.Label(dialog, text="Тип работы:", font=('Arial', 11)).pack(pady=5)
        
        type_var = tk.StringVar(value="ответ у доски")
        type_combo = ttk.Combobox(dialog, textvariable=type_var,
                                 values=["контрольная", "самостоятельная", "домашняя", "ответ у доски"],
                                 state='readonly')
        type_combo.pack(pady=5)
        
        # Комментарий
        tk.Label(dialog, text="Комментарий:", font=('Arial', 11)).pack(pady=5)
        comment_entry = tk.Entry(dialog, font=('Arial', 11), width=30)
        comment_entry.pack(pady=5)
        
        def save_grade():
            student_name = student_var.get()
            if not student_name:
                return
            
            self.cursor.execute('''
                SELECT id FROM users WHERE full_name = ?
            ''', (student_name,))
            
            student = self.cursor.fetchone()
            if not student:
                return
            
            self.cursor.execute('''
                INSERT INTO grades (student_id, subject, grade, date, type, comment, teacher_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (student[0], subject_var.get(), grade_var.get(),
                 datetime.now().strftime('%Y-%m-%d'), type_var.get(),
                 comment_entry.get(), self.current_user['id']))
            
            self.conn.commit()
            
            self.log_action('grade_added', 
                          f'Выставлена оценка {grade_var.get()} по {subject_var.get()} ученику {student[0]}')
            
            messagebox.showinfo("Успех", "Оценка выставлена!")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Сохранить", command=save_grade,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def mark_attendance(self):
        """Отметить посещаемость"""
        self.clear_content()
        self.section_header.config(text="✅ Отметить посещаемость")
        
        # Выбор класса
        control_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(control_frame, text="Класс:", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.cursor.execute("SELECT classes FROM teachers WHERE user_id = ?",
                          (self.current_user['id'],))
        
        teacher = self.cursor.fetchone()
        classes = json.loads(teacher[0]) if teacher and teacher[0] else []
        
        class_var = tk.StringVar()
        if classes:
            class_var.set(classes[0])
        
        class_combo = ttk.Combobox(control_frame, textvariable=class_var,
                                  values=classes, state='readonly')
        class_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="Дата:", font=('Arial', 11)).pack(side=tk.LEFT, padx=20)
        
        date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        date_entry = tk.Entry(control_frame, textvariable=date_var, 
                             font=('Arial', 11), width=12)
        date_entry.pack(side=tk.LEFT, padx=5)
        
        # Область для отметки посещаемости
        self.attendance_frame = tk.Frame(self.content_frame, bg='white', 
                                        relief='raised', borderwidth=1)
        self.attendance_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        def show_students_for_attendance():
            for widget in self.attendance_frame.winfo_children():
                widget.destroy()
            
            class_name = class_var.get()
            date = date_var.get()
            
            self.cursor.execute('''
                SELECT u.id, u.full_name
                FROM users u
                JOIN students s ON u.id = s.user_id
                WHERE s.class_name = ?
                ORDER BY u.full_name
            ''', (class_name,))
            
            students = self.cursor.fetchall()
            
            if not students:
                tk.Label(self.attendance_frame, text="Нет учеников в классе",
                        font=('Arial', 12), bg='white', fg='gray').pack(pady=20)
                return
            
            header_frame = tk.Frame(self.attendance_frame, bg='#f0f0f0')
            header_frame.pack(fill=tk.X)
            
            tk.Label(header_frame, text="Ученик", font=('Arial', 11, 'bold'),
                    bg='#f0f0f0', width=30).pack(side=tk.LEFT, padx=10, pady=5)
            
            tk.Label(header_frame, text="Присутствует", font=('Arial', 11, 'bold'),
                    bg='#f0f0f0', width=15).pack(side=tk.LEFT, padx=10, pady=5)
            
            tk.Label(header_frame, text="Время входа", font=('Arial', 11, 'bold'),
                    bg='#f0f0f0', width=15).pack(side=tk.LEFT, padx=10, pady=5)
            
            attendance_vars = {}
            time_vars = {}
            
            for student_id, student_name in students:
                student_frame = tk.Frame(self.attendance_frame, bg='white')
                student_frame.pack(fill=tk.X, padx=10, pady=2)
                
                tk.Label(student_frame, text=student_name, font=('Arial', 11),
                        bg='white', width=30).pack(side=tk.LEFT, padx=10)
                
                present_var = tk.BooleanVar(value=True)
                attendance_vars[student_id] = present_var
                
                tk.Checkbutton(student_frame, variable=present_var, bg='white').pack(side=tk.LEFT, padx=10)
                
                time_var = tk.StringVar(value=datetime.now().strftime('%H:%M'))
                time_vars[student_id] = time_var
                
                time_entry = tk.Entry(student_frame, textvariable=time_var,
                                     font=('Arial', 11), width=10)
                time_entry.pack(side=tk.LEFT, padx=10)
            
            def save_attendance():
                for student_id in attendance_vars:
                    present = attendance_vars[student_id].get()
                    entry_time = time_vars[student_id].get() if present else None
                    
                    self.cursor.execute('''
                        INSERT INTO attendance (student_id, date, present, entry_time)
                        VALUES (?, ?, ?, ?)
                    ''', (student_id, date, present, entry_time))
                
                self.conn.commit()
                
                self.log_action('attendance_marked', 
                              f'Отмечена посещаемость {class_name} класса на {date}')
                
                messagebox.showinfo("Успех", "Посещаемость отмечена!")
                show_students_for_attendance()
            
            tk.Button(self.attendance_frame, text="💾 Сохранить", command=save_attendance,
                     bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                     relief='flat', padx=20, pady=10).pack(pady=10)
        
        def load_attendance():
            show_students_for_attendance()
        
        tk.Button(control_frame, text="📋 Загрузить список", command=load_attendance,
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=5).pack(side=tk.LEFT, padx=10)
    
    def show_student_schedule(self):
        """Показать расписание ученика"""
        self.clear_content()
        self.section_header.config(text="📅 Мое расписание")
        
        self.cursor.execute("SELECT class_name FROM students WHERE user_id = ?",
                          (self.current_user['id'],))
        
        student = self.cursor.fetchone()
        if not student:
            tk.Label(self.content_frame, text="❌ Класс не найден",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        class_name = student[0]
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        
        for day in days:
            day_frame = tk.Frame(notebook, bg='white')
            notebook.add(day_frame, text=day)
            
            tk.Label(day_frame, text=f"Расписание на {day.lower()}",
                    font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
            
            self.cursor.execute('''
                SELECT lesson_number, time_start, time_end, subject, room
                FROM schedule
                WHERE class_name = ? AND day_of_week = ?
                ORDER BY lesson_number
            ''', (class_name, day))
            
            lessons = self.cursor.fetchall()
            
            if lessons:
                for lesson in lessons:
                    lesson_frame = tk.Frame(day_frame, bg='white', relief='solid', borderwidth=1)
                    lesson_frame.pack(fill=tk.X, padx=20, pady=5)
                    
                    tk.Label(lesson_frame, text=f"{lesson[1]}-{lesson[2]}",
                            font=('Arial', 11, 'bold'), bg='white',
                            fg=self.colors['primary']).pack(side=tk.LEFT, padx=10, pady=5)
                    
                    tk.Label(lesson_frame, text=f"Урок {lesson[0]}: {lesson[3]}",
                            font=('Arial', 12), bg='white').pack(side=tk.LEFT, padx=10)
                    
                    tk.Label(lesson_frame, text=f"{lesson[4]}",
                            font=('Arial', 11), bg='white', fg='gray').pack(side=tk.RIGHT, padx=10)
            else:
                tk.Label(day_frame, text="📭 Нет уроков",
                        font=('Arial', 14), bg='white', fg='gray').pack(pady=50)
    
    def show_student_homework(self):
        """Показать домашние задания"""
        self.clear_content()
        self.section_header.config(text="📚 Домашние задания")
        
        self.cursor.execute("SELECT class_name FROM students WHERE user_id = ?",
                          (self.current_user['id'],))
        
        student = self.cursor.fetchone()
        if not student:
            tk.Label(self.content_frame, text="❌ Класс не найден",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        class_name = student[0]
        today = datetime.now().strftime('%Y-%m-%d')
        
        self.cursor.execute('''
            SELECT subject, description, date
            FROM homework
            WHERE class_name = ? AND date = ?
            ORDER BY subject
        ''', (class_name, today))
        
        homework = self.cursor.fetchall()
        
        if homework:
            for subject, description, date in homework:
                hw_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
                hw_frame.pack(fill=tk.X, padx=20, pady=10)
                
                tk.Label(hw_frame, text=f"📖 {subject}",
                        font=('Arial', 14, 'bold'), bg='white',
                        fg=self.colors['primary'], pady=5).pack(anchor='w', padx=20)
                
                tk.Label(hw_frame, text=description,
                        font=('Arial', 11), bg='white',
                        wraplength=800, justify='left').pack(anchor='w', padx=30, pady=10)
                
                tk.Label(hw_frame, text=f"📅 {date}",
                        font=('Arial', 9), bg='white', fg='gray').pack(anchor='w', padx=20)
        else:
            tk.Label(self.content_frame, text="📭 Домашних заданий на сегодня нет",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
    
    def show_student_grades(self):
        """Показать оценки ученика"""
        self.clear_content()
        self.section_header.config(text="📊 Мои оценки")
        
        self.cursor.execute('''
            SELECT subject, grade, date, type, comment
            FROM grades
            WHERE student_id = ?
            ORDER BY subject, date DESC
        ''', (self.current_user['id'],))
        
        grades = self.cursor.fetchall()
        
        if not grades:
            tk.Label(self.content_frame, text="📭 Оценок пока нет",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        # Группируем по предметам
        grades_by_subject = {}
        for subject, grade, date, type_, comment in grades:
            if subject not in grades_by_subject:
                grades_by_subject[subject] = []
            grades_by_subject[subject].append((grade, date, type_, comment))
        
        # Создаем вкладки для предметов
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for subject, marks in grades_by_subject.items():
            subject_frame = tk.Frame(notebook, bg='white')
            notebook.add(subject_frame, text=subject)
            
            avg = sum(m[0] for m in marks) / len(marks)
            
            tk.Label(subject_frame, text=f"Предмет: {subject}",
                    font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
            
            tk.Label(subject_frame, text=f"Средний балл: {avg:.2f}",
                    font=('Arial', 12), bg='white', fg=self.colors['primary']).pack()
            
            # Таблица оценок
            columns = ("Дата", "Оценка", "Тип", "Комментарий")
            tree = ttk.Treeview(subject_frame, columns=columns, show='headings')
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            
            tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            for grade, date, type_, comment in marks:
                tree.insert('', 'end', values=(date, grade, type_, comment))
    
    def show_student_card(self):
        """Показать карту ученика"""
        self.clear_content()
        self.section_header.config(text="💳 Моя карта Москвёнок")
        
        self.cursor.execute('''
            SELECT card_uid, card_number, balance, daily_limit, active, 
                   issued_date, last_used
            FROM moscow_cards 
            WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        card = self.cursor.fetchone()
        
        if card:
            card_frame = tk.Frame(self.content_frame, bg='white',
                                 relief='raised', borderwidth=3)
            card_frame.pack(padx=50, pady=30, fill=tk.X)
            
            # Имитация пластиковой карты
            card_color = '#2196F3' if card[4] else '#f44336'
            
            card_visual = tk.Frame(card_frame, bg=card_color, height=180)
            card_visual.pack(fill=tk.X, padx=20, pady=20)
            card_visual.pack_propagate(False)
            
            tk.Label(card_visual, text="МОСКВЁНОК",
                    font=('Arial', 18, 'bold'), bg=card_color, fg='white').pack(pady=5)
            
            tk.Label(card_visual, text=card[1],
                    font=('Arial', 14), bg=card_color, fg='white').pack(pady=5)
            
            tk.Label(card_visual, text=f"Баланс: {card[2]:.2f} руб.",
                    font=('Arial', 12, 'bold'), bg=card_color, fg='white').pack(pady=5)
            
            # Детали карты
            details_frame = tk.Frame(card_frame, bg='white')
            details_frame.pack(padx=20, pady=10, fill=tk.X)
            
            details = [
                f"UID: {card[0]}",
                f"Дневной лимит: {card[3]:.2f} руб.",
                f"Статус: {'🟢 Активна' if card[4] else '🔴 Заблокирована'}",
                f"Выдана: {card[5]}",
                f"Последнее использование: {card[6] or 'Н/Д'}"
            ]
            
            for detail in details:
                tk.Label(details_frame, text=detail, font=('Arial', 11),
                        bg='white').pack(anchor='w', pady=3)
            
            # История покупок
            tk.Label(card_frame, text="📋 Последние покупки:",
                    font=('Arial', 12, 'bold'), bg='white').pack(pady=10)
            
            self.cursor.execute('''
                SELECT date, time, item, amount
                FROM canteen_purchases
                WHERE student_id = ?
                ORDER BY date DESC, time DESC
                LIMIT 5
            ''', (self.current_user['id'],))
            
            purchases = self.cursor.fetchall()
            
            if purchases:
                for purchase in purchases:
                    tk.Label(card_frame, 
                            text=f"{purchase[0]} {purchase[1]}: {purchase[2]} - {purchase[3]:.2f} руб.",
                            font=('Arial', 10), bg='white').pack(anchor='w', padx=40)
            else:
                tk.Label(card_frame, text="Покупок пока нет",
                        font=('Arial', 10), bg='white', fg='gray').pack(pady=5)
        else:
            tk.Label(self.content_frame, text="❌ Карта не найдена",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
    
    def show_student_attendance(self):
        """Показать посещаемость ученика"""
        self.clear_content()
        self.section_header.config(text="📋 Моя посещаемость")
        
        self.cursor.execute('''
            SELECT date, present, entry_time, exit_time
            FROM attendance
            WHERE student_id = ?
            ORDER BY date DESC
            LIMIT 30
        ''', (self.current_user['id'],))
        
        attendance = self.cursor.fetchall()
        
        if attendance:
            total = len(attendance)
            present = sum(1 for a in attendance if a[1])
            
            # Статистика
            stats_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
            stats_frame.pack(fill=tk.X, padx=10, pady=10)
            
            stats = [
                f"📊 Всего дней: {total}",
                f"✅ Присутствовал: {present}",
                f"❌ Пропущено: {total - present}",
                f"📈 Процент: {present/total*100:.1f}%"
            ]
            
            for stat in stats:
                tk.Label(stats_frame, text=stat, font=('Arial', 12),
                        bg='white', pady=5).pack()
            
            # Таблица посещаемости
            table_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
            table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            columns = ("Дата", "Статус", "Вход", "Выход")
            tree = ttk.Treeview(table_frame, columns=columns, show='headings')
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            
            tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            for date, present, entry, exit in attendance:
                status = "✅ Был" if present else "❌ Отсутствовал"
                tree.insert('', 'end', values=(date, status, entry or 'Н/Д', exit or 'Н/Д'))
        else:
            tk.Label(self.content_frame, text="📭 Данных о посещаемости нет",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
    
    def show_achievements(self):
        """Показать достижения"""
        self.clear_content()
        self.section_header.config(text="🏆 Мои достижения")
        
        # Получаем средний балл
        self.cursor.execute('''
            SELECT AVG(grade) FROM grades WHERE student_id = ?
        ''', (self.current_user['id'],))
        
        avg = self.cursor.fetchone()[0] or 0
        
        achievements_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        achievements_frame.pack(fill=tk.X, padx=50, pady=30)
        
        tk.Label(achievements_frame, text="🏆 ДОСТИЖЕНИЯ",
                font=('Arial', 18, 'bold'), bg='white', pady=20).pack()
        
        tk.Label(achievements_frame, text=f"Средний балл: {avg:.2f}",
                font=('Arial', 14), bg='white',
                fg=self.colors['primary']).pack(pady=10)
        
        if avg >= 4.5:
            status = "🏅 Отличник"
            color = '#4CAF50'
        elif avg >= 4.0:
            status = "🥈 Хорошист"
            color = '#2196F3'
        elif avg >= 3.0:
            status = "🥉 Успевающий"
            color = '#FF9800'
        else:
            status = "📚 Нужно подтянуть учебу"
            color = '#f44336'
        
        tk.Label(achievements_frame, text=status, font=('Arial', 16, 'bold'),
                bg='white', fg=color, pady=20).pack()
    
    def show_messages(self):
        """Показать сообщения"""
        self.clear_content()
        self.section_header.config(text="📨 Сообщения")
        
        # Кнопка нового сообщения
        tk.Button(self.content_frame, text="✉️ Написать сообщение",
                 command=self.send_message_dialog,
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(pady=10)
        
        # Список сообщений
        messages_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        messages_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.cursor.execute('''
            SELECT m.id, u.full_name, m.subject, m.text, m.date, m.read
            FROM messages m
            JOIN users u ON m.from_user = u.id
            WHERE m.to_user = ?
            ORDER BY m.date DESC
        ''', (self.current_user['id'],))
        
        messages = self.cursor.fetchall()
        
        if not messages:
            tk.Label(messages_frame, text="📭 Сообщений нет",
                    font=('Arial', 14), bg='white', fg='gray').pack(pady=50)
            return
        
        # Отображаем сообщения
        canvas = tk.Canvas(messages_frame, bg='white')
        scrollbar = ttk.Scrollbar(messages_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for msg_id, from_name, subject, text, date, read in messages:
            msg_frame = tk.Frame(scrollable_frame, bg='white', relief='solid', borderwidth=1)
            msg_frame.pack(fill=tk.X, padx=10, pady=5)
            
            read_icon = "📩" if not read else "📨"
            header = f"{read_icon} От: {from_name} | {subject}"
            tk.Label(msg_frame, text=header, font=('Arial', 11, 'bold'),
                    bg='white').pack(anchor='w', padx=10, pady=5)
            
            tk.Label(msg_frame, text=text, font=('Arial', 10),
                    bg='white', wraplength=600, justify='left').pack(anchor='w', padx=20, pady=5)
            
            tk.Label(msg_frame, text=f"Дата: {date}", font=('Arial', 9),
                    bg='white', fg='gray').pack(anchor='w', padx=10, pady=2)
            
            # Отметить как прочитанное
            if not read:
                def mark_read(msg_id=msg_id):
                    self.cursor.execute("UPDATE messages SET read = 1 WHERE id = ?", (msg_id,))
                    self.conn.commit()
                    self.show_messages()
                
                tk.Button(msg_frame, text="Отметить прочитанным", command=mark_read,
                         bg=self.colors['primary'], fg='white', font=('Arial', 9),
                         relief='flat', padx=10, pady=2).pack(anchor='w', padx=20)
    
    def send_message_dialog(self):
        """Диалог отправки сообщения"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Новое сообщение")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="НОВОЕ СООБЩЕНИЕ", font=('Arial', 14, 'bold'), pady=10).pack()
        
        # Получатель
        tk.Label(dialog, text="Получатель:", font=('Arial', 11)).pack(pady=5)
        
        self.cursor.execute('''
            SELECT id, full_name, role FROM users
            WHERE id != ?
            ORDER BY role, full_name
        ''', (self.current_user['id'],))
        
        recipients = [f"{r[0]} - {r[1]} ({self.get_role_display(r[2])})" 
                     for r in self.cursor.fetchall()]
        
        recipient_var = tk.StringVar()
        recipient_combo = ttk.Combobox(dialog, textvariable=recipient_var,
                                      values=recipients, state='readonly', width=40)
        recipient_combo.pack(pady=5)
        
        # Тема
        tk.Label(dialog, text="Тема:", font=('Arial', 11)).pack(pady=5)
        subject_entry = tk.Entry(dialog, font=('Arial', 11), width=40)
        subject_entry.pack(pady=5)
        
        # Текст сообщения
        tk.Label(dialog, text="Сообщение:", font=('Arial', 11)).pack(pady=5)
        text_widget = tk.Text(dialog, font=('Arial', 11), width=40, height=8)
        text_widget.pack(pady=5)
        
        def send_message():
            if not recipient_var.get():
                messagebox.showerror("Ошибка", "Выберите получателя!")
                return
            
            recipient_id = recipient_var.get().split(' - ')[0]
            subject = subject_entry.get()
            text = text_widget.get("1.0", tk.END).strip()
            
            if not text:
                messagebox.showerror("Ошибка", "Введите текст сообщения!")
                return
            
            self.cursor.execute('''
                INSERT INTO messages (from_user, to_user, subject, text, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.current_user['id'], recipient_id, subject, text,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            self.conn.commit()
            
            # Отправляем уведомление
            self.cursor.execute('''
                INSERT INTO notifications (user_id, date, message)
                VALUES (?, ?, ?)
            ''', (recipient_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 f'Новое сообщение от {self.current_user["full_name"]}'))
            
            self.conn.commit()
            
            messagebox.showinfo("Успех", "Сообщение отправлено!")
            dialog.destroy()
            self.show_messages()
        
        tk.Button(dialog, text="📨 Отправить", command=send_message,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def show_my_children(self):
        """Показать моих детей"""
        self.clear_content()
        self.section_header.config(text="👶 Мои дети")
        
        self.cursor.execute('''
            SELECT children FROM parents WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        parent_data = self.cursor.fetchone()
        
        if not parent_data or not parent_data[0]:
            tk.Label(self.content_frame, text="❌ Нет привязанных детей",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        children_ids = json.loads(parent_data[0])
        
        for child_id in children_ids:
            self.cursor.execute('''
                SELECT u.full_name, s.class_name, s.birth_date, s.health_group
                FROM users u
                JOIN students s ON u.id = s.user_id
                WHERE u.id = ?
            ''', (child_id,))
            
            child = self.cursor.fetchone()
            
            if child:
                card_frame = tk.Frame(self.content_frame, bg='white', 
                                     relief='raised', borderwidth=2)
                card_frame.pack(fill=tk.X, padx=20, pady=10)
                
                tk.Label(card_frame, text=f"👶 {child[0]}",
                        font=('Arial', 16, 'bold'), bg='white', pady=10).pack()
                
                info_text = f"""
                🏫 Класс: {child[1]}
                🎂 Дата рождения: {child[2]}
                ❤️ Группа здоровья: {child[3]}
                """
                
                tk.Label(card_frame, text=info_text, font=('Arial', 11),
                        bg='white', justify='left').pack(padx=20, pady=10)
    
    def show_children_grades(self):
        """Показать оценки детей"""
        self.clear_content()
        self.section_header.config(text="📊 Успеваемость детей")
        
        self.cursor.execute('''
            SELECT children FROM parents WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        parent_data = self.cursor.fetchone()
        
        if not parent_data or not parent_data[0]:
            tk.Label(self.content_frame, text="❌ Нет привязанных детей",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        children_ids = json.loads(parent_data[0])
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for child_id in children_ids:
            self.cursor.execute("SELECT full_name FROM users WHERE id = ?", (child_id,))
            child_name = self.cursor.fetchone()[0]
            
            child_frame = tk.Frame(notebook, bg='white')
            notebook.add(child_frame, text=child_name)
            
            self.cursor.execute('''
                SELECT subject, AVG(grade), COUNT(grade)
                FROM grades
                WHERE student_id = ?
                GROUP BY subject
            ''', (child_id,))
            
            subjects_grades = self.cursor.fetchall()
            
            if subjects_grades:
                for subject, avg, count in subjects_grades:
                    frame = tk.Frame(child_frame, bg='white', relief='solid', borderwidth=1)
                    frame.pack(fill=tk.X, padx=20, pady=5)
                    
                    tk.Label(frame, text=subject, font=('Arial', 12, 'bold'),
                            bg='white').pack(side=tk.LEFT, padx=10, pady=5)
                    
                    tk.Label(frame, text=f"Средний: {avg:.2f}",
                            font=('Arial', 12), bg='white',
                            fg=self.colors['primary']).pack(side=tk.LEFT, padx=10)
                    
                    tk.Label(frame, text=f"Оценок: {count}",
                            font=('Arial', 12), bg='white').pack(side=tk.RIGHT, padx=10)
            else:
                tk.Label(child_frame, text="📭 Оценок пока нет",
                        font=('Arial', 14), bg='white', fg='gray').pack(pady=50)
    
    def show_children_schedule(self):
        """Показать расписание детей"""
        self.clear_content()
        self.section_header.config(text="📅 Расписание детей")
        
        self.cursor.execute('''
            SELECT children FROM parents WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        parent_data = self.cursor.fetchone()
        
        if not parent_data or not parent_data[0]:
            tk.Label(self.content_frame, text="❌ Нет привязанных детей",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        children_ids = json.loads(parent_data[0])
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        
        for child_id in children_ids:
            self.cursor.execute('''
                SELECT u.full_name, s.class_name
                FROM users u
                JOIN students s ON u.id = s.user_id
                WHERE u.id = ?
            ''', (child_id,))
            
            child = self.cursor.fetchone()
            if not child:
                continue
            
            child_frame = tk.Frame(notebook, bg='white')
            notebook.add(child_frame, text=child[0])
            
            for day in days:
                self.cursor.execute('''
                    SELECT lesson_number, time_start, time_end, subject, room
                    FROM schedule
                    WHERE class_name = ? AND day_of_week = ?
                    ORDER BY lesson_number
                ''', (child[1], day))
                
                lessons = self.cursor.fetchall()
                
                if lessons:
                    tk.Label(child_frame, text=f"\n📅 {day}:",
                            font=('Arial', 12, 'bold'), bg='white',
                            fg=self.colors['primary']).pack(anchor='w', padx=20)
                    
                    for lesson in lessons:
                        lesson_text = f"  {lesson[1]}-{lesson[2]}: {lesson[3]} ({lesson[4]})"
                        tk.Label(child_frame, text=lesson_text,
                                font=('Arial', 10), bg='white').pack(anchor='w', padx=30)
    
    def manage_children_cards(self):
        """Управление картами детей"""
        self.clear_content()
        self.section_header.config(text="💳 Управление картами детей")
        
        self.cursor.execute('''
            SELECT children FROM parents WHERE user_id = ?
        ''', (self.current_user['id'],))
        
        parent_data = self.cursor.fetchone()
        
        if not parent_data or not parent_data[0]:
            tk.Label(self.content_frame, text="❌ Нет привязанных детей",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
            return
        
        children_ids = json.loads(parent_data[0])
        
        for child_id in children_ids:
            self.cursor.execute('''
                SELECT u.full_name, mc.card_uid, mc.card_number, mc.balance, 
                       mc.daily_limit, mc.active
                FROM users u
                LEFT JOIN moscow_cards mc ON u.id = mc.user_id
                WHERE u.id = ?
            ''', (child_id,))
            
            card = self.cursor.fetchone()
            
            if card:
                card_frame = tk.Frame(self.content_frame, bg='white',
                                     relief='raised', borderwidth=2)
                card_frame.pack(fill=tk.X, padx=20, pady=10)
                
                tk.Label(card_frame, text=f"💳 Карта: {card[0]}",
                        font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
                
                if card[1]:  # Если карта существует
                    info_frame = tk.Frame(card_frame, bg='white')
                    info_frame.pack(padx=20, pady=10)
                    
                    labels = [
                        f"UID: {card[1]}",
                        f"Номер: {card[2]}",
                        f"Баланс: {card[3]:.2f} руб.",
                        f"Дневной лимит: {card[4]:.2f} руб.",
                        f"Статус: {'🟢 Активна' if card[5] else '🔴 Заблокирована'}",
                    ]
                    
                    for label in labels:
                        tk.Label(info_frame, text=label, font=('Arial', 11),
                                bg='white').pack(anchor='w', pady=2)
                    
                    btn_frame = tk.Frame(card_frame, bg='white')
                    btn_frame.pack(pady=10)
                    
                    tk.Button(btn_frame, text="💰 Пополнить",
                             command=lambda cid=child_id: self.top_up_card_dialog(cid),
                             bg=self.colors['primary'], fg='white', font=('Arial', 10),
                             relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=5)
                    
                    # Кнопка блокировки/разблокировки
                    toggle_text = "🔒 Заблокировать" if card[5] else "🔓 Разблокировать"
                    tk.Button(btn_frame, text=toggle_text,
                             command=lambda cid=child_id, status=card[5]: self.toggle_child_card(cid, status),
                             bg=self.colors['warning'], fg='white', font=('Arial', 10),
                             relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=5)
                    
                    # История покупок
                    self.cursor.execute('''
                        SELECT date, time, item, amount
                        FROM canteen_purchases
                        WHERE student_id = ?
                        ORDER BY date DESC, time DESC
                        LIMIT 5
                    ''', (child_id,))
                    
                    purchases = self.cursor.fetchall()
                    
                    if purchases:
                        tk.Label(card_frame, text="📋 Последние покупки:",
                                font=('Arial', 11, 'bold'), bg='white').pack(pady=5)
                        for purchase in purchases:
                            tk.Label(card_frame,
                                    text=f"{purchase[0]} {purchase[1]}: {purchase[2]} - {purchase[3]:.2f} руб.",
                                    font=('Arial', 10), bg='white').pack(anchor='w', padx=40)
                else:
                    tk.Label(card_frame, text="❌ Карта не выдана",
                            font=('Arial', 11), bg='white', fg='gray').pack(pady=10)
    
    def toggle_child_card(self, child_id, current_status):
        """Переключение статуса карты ребенка"""
        new_status = 0 if current_status else 1
        self.cursor.execute('''
            UPDATE moscow_cards SET active = ? WHERE user_id = ?
        ''', (new_status, child_id))
        self.conn.commit()
        
        action = 'разблокирована' if new_status else 'заблокирована'
        self.log_action('card_toggle', f'Карта ребенка {child_id} {action}')
        messagebox.showinfo("Успех", f"Карта {action}!")
        self.manage_children_cards()
    
    def top_up_card_dialog(self, child_id=None):
        """Диалог пополнения карты"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Пополнить карту")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="ПОПОЛНЕНИЕ КАРТЫ", font=('Arial', 14, 'bold'), pady=10).pack()
        
        # Сумма пополнения
        tk.Label(dialog, text="Сумма пополнения (руб.):", font=('Arial', 11)).pack(pady=10)
        amount_entry = tk.Entry(dialog, font=('Arial', 14), width=15, justify='center')
        amount_entry.pack(pady=10)
        amount_entry.focus()
        
        # Быстрые суммы
        quick_frame = tk.Frame(dialog, bg='#f0f0f0')
        quick_frame.pack(pady=10)
        
        for amount in [100, 200, 500, 1000]:
            def set_amount(val=amount):
                amount_entry.delete(0, tk.END)
                amount_entry.insert(0, str(val))
            
            tk.Button(quick_frame, text=f"{amount} руб.", command=set_amount,
                     bg=self.colors['primary'], fg='white', font=('Arial', 10),
                     relief='flat', padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        def process_top_up():
            try:
                amount = float(amount_entry.get())
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректную сумму!")
                return
            
            # Обновляем баланс
            self.cursor.execute('''
                UPDATE moscow_cards SET balance = balance + ? WHERE user_id = ?
            ''', (amount, child_id))
            
            self.conn.commit()
            
            self.cursor.execute('''
                SELECT balance FROM moscow_cards WHERE user_id = ?
            ''', (child_id,))
            
            new_balance = self.cursor.fetchone()[0]
            
            self.log_action('card_topup', 
                          f'Пополнение карты {child_id} на сумму {amount} руб.')
            
            messagebox.showinfo("Успех", 
                f"Карта пополнена!\nСумма: {amount:.2f} руб.\nНовый баланс: {new_balance:.2f} руб.")
            
            dialog.destroy()
            self.manage_children_cards()
        
        tk.Button(dialog, text="💰 Пополнить", command=process_top_up,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 12, 'bold'),
                 relief='flat', padx=30, pady=10).pack(pady=20)
    
    def show_canteen_menu(self):
        """Показать меню столовой"""
        self.clear_content()
        self.section_header.config(text="🍽️ Меню столовой")
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        self.cursor.execute('''
            SELECT name, price, category
            FROM canteen_menu
            WHERE date = ?
            ORDER BY category, name
        ''', (today,))
        
        menu_items = self.cursor.fetchall()
        
        if menu_items:
            # Группируем по категориям
            categories = {}
            for name, price, category in menu_items:
                if category not in categories:
                    categories[category] = []
                categories[category].append((name, price))
            
            for category, items in categories.items():
                cat_frame = tk.Frame(self.content_frame, bg='white',
                                   relief='raised', borderwidth=1)
                cat_frame.pack(fill=tk.X, padx=20, pady=5)
                
                tk.Label(cat_frame, text=f"📋 {category.upper()}",
                        font=('Arial', 12, 'bold'), bg='white',
                        fg=self.colors['primary'], pady=5).pack()
                
                for name, price in items:
                    item_frame = tk.Frame(cat_frame, bg='white')
                    item_frame.pack(fill=tk.X, padx=20)
                    
                    tk.Label(item_frame, text=name, font=('Arial', 11),
                            bg='white').pack(side=tk.LEFT)
                    
                    tk.Label(item_frame, text=f"{price:.2f} руб.",
                            font=('Arial', 11, 'bold'), bg='white').pack(side=tk.RIGHT)
        else:
            # Генерируем меню если его нет
            self.generate_daily_menu(today)
            self.show_canteen_menu()
    
    def request_documents(self):
        """Запросить документы"""
        self.clear_content()
        self.section_header.config(text="📄 Электронные справки")
        
        doc_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        doc_frame.pack(padx=50, pady=30, fill=tk.X)
        
        tk.Label(doc_frame, text="📄 ЭЛЕКТРОННЫЕ СПРАВКИ",
                font=('Arial', 16, 'bold'), bg='white', pady=20).pack()
        
        documents = [
            ("📋 Справка об обучении", "Справка об обучении"),
            ("💰 Справка о доходах", "Справка о доходах"),
            ("🍽️ Справка о питании", "Справка о питании"),
            ("🏫 Справка о посещении школы", "Справка о посещении школы"),
        ]
        
        for doc_text, doc_type in documents:
            btn = tk.Button(doc_frame, text=doc_text, 
                          command=lambda dt=doc_type: self.generate_document(dt),
                          bg=self.colors['primary'], fg='white',
                          font=('Arial', 11), relief='flat',
                          padx=20, pady=10)
            btn.pack(pady=5, padx=50, fill=tk.X)
    
    def generate_document(self, doc_type):
        """Генерация справки"""
        result = f"""
        ╔══════════════════════════════════════╗
        ║     {doc_type.upper()}     ║
        ╚══════════════════════════════════════╝
        
        Дата выдачи: {datetime.now().strftime('%d.%m.%Y')}
        Школа: ГБОУ Школа №1234
        Адрес: г. Москва, ул. Примерная, д. 1
        Директор: Иванова Елена Петровна
        """
        
        if self.current_role == 'parent':
            self.cursor.execute('''
                SELECT children FROM parents WHERE user_id = ?
            ''', (self.current_user['id'],))
            
            parent_data = self.cursor.fetchone()
            if parent_data and parent_data[0]:
                children_ids = json.loads(parent_data[0])
                for child_id in children_ids:
                    self.cursor.execute('''
                        SELECT u.full_name, s.class_name
                        FROM users u
                        JOIN students s ON u.id = s.user_id
                        WHERE u.id = ?
                    ''', (child_id,))
                    
                    child = self.cursor.fetchone()
                    if child:
                        result += f"\nУченик: {child[0]}, {child[1]} класс"
        
        result += f"\n\nДокумент сформирован автоматически {datetime.now().strftime('%d.%m.%Y в %H:%M')}"
        
        messagebox.showinfo("Справка", result)
    
    def manage_homework(self):
        """Управление домашними заданиями"""
        self.clear_content()
        self.section_header.config(text="📚 Домашние задания")
        
        # Кнопка добавить задание
        tk.Button(self.content_frame, text="➕ Задать домашнее задание",
                 command=self.add_homework_dialog,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=8).pack(pady=10)
        
        # Список домашних заданий
        self.cursor.execute('''
            SELECT id, class_name, subject, date, description
            FROM homework
            WHERE teacher_id = ?
            ORDER BY date DESC
            LIMIT 20
        ''', (self.current_user['id'],))
        
        homework_list = self.cursor.fetchall()
        
        if homework_list:
            for hw_id, class_name, subject, date, description in homework_list:
                hw_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
                hw_frame.pack(fill=tk.X, padx=10, pady=5)
                
                tk.Label(hw_frame, text=f"📖 {subject} - {class_name} класс",
                        font=('Arial', 12, 'bold'), bg='white',
                        fg=self.colors['primary']).pack(anchor='w', padx=10, pady=5)
                
                tk.Label(hw_frame, text=description,
                        font=('Arial', 10), bg='white',
                        wraplength=800, justify='left').pack(anchor='w', padx=20, pady=5)
                
                tk.Label(hw_frame, text=f"📅 {date}",
                        font=('Arial', 9), bg='white', fg='gray').pack(anchor='w', padx=10)
        else:
            tk.Label(self.content_frame, text="📭 Домашних заданий пока нет",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
    
    def add_homework_dialog(self):
        """Диалог добавления домашнего задания"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Задать домашнее задание")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="ЗАДАТЬ ДОМАШНЕЕ ЗАДАНИЕ",
                font=('Arial', 14, 'bold'), pady=10).pack()
        
        # Выбор класса
        tk.Label(dialog, text="Класс:", font=('Arial', 11)).pack(pady=5)
        
        self.cursor.execute("SELECT classes FROM teachers WHERE user_id = ?",
                          (self.current_user['id'],))
        
        teacher = self.cursor.fetchone()
        classes = json.loads(teacher[0]) if teacher and teacher[0] else []
        
        class_var = tk.StringVar()
        if classes:
            class_var.set(classes[0])
        
        class_combo = ttk.Combobox(dialog, textvariable=class_var,
                                  values=classes, state='readonly')
        class_combo.pack(pady=5)
        
        # Выбор предмета
        tk.Label(dialog, text="Предмет:", font=('Arial', 11)).pack(pady=5)
        
        self.cursor.execute("SELECT subjects FROM teachers WHERE user_id = ?",
                          (self.current_user['id'],))
        
        subjects_data = self.cursor.fetchone()
        subjects = json.loads(subjects_data[0]) if subjects_data and subjects_data[0] else []
        
        subject_var = tk.StringVar()
        if subjects:
            subject_var.set(subjects[0])
        
        subject_combo = ttk.Combobox(dialog, textvariable=subject_var,
                                    values=subjects, state='readonly')
        subject_combo.pack(pady=5)
        
        # Дата
        tk.Label(dialog, text="Дата:", font=('Arial', 11)).pack(pady=5)
        
        date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        date_entry = tk.Entry(dialog, textvariable=date_var, font=('Arial', 11))
        date_entry.pack(pady=5)
        
        # Описание задания
        tk.Label(dialog, text="Задание:", font=('Arial', 11)).pack(pady=5)
        
        homework_text = tk.Text(dialog, font=('Arial', 11), width=50, height=8)
        homework_text.pack(pady=5)
        
        def save_homework():
            class_name = class_var.get()
            subject = subject_var.get()
            date = date_var.get()
            description = homework_text.get("1.0", tk.END).strip()
            
            if not all([class_name, subject, date, description]):
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return
            
            self.cursor.execute('''
                INSERT INTO homework (class_name, subject, date, description, teacher_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (class_name, subject, date, description, self.current_user['id']))
            
            self.conn.commit()
            
            self.log_action('homework_added', f'Добавлено ДЗ по {subject} для {class_name} класса')
            messagebox.showinfo("Успех", "Домашнее задание задано!")
            dialog.destroy()
            self.manage_homework()
        
        tk.Button(dialog, text="💾 Сохранить", command=save_homework,
                 bg=self.colors['secondary'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def show_my_classes(self):
        """Показать мои классы"""
        self.clear_content()
        self.section_header.config(text="👥 Мои классы")
        
        self.cursor.execute("SELECT classes FROM teachers WHERE user_id = ?",
                          (self.current_user['id'],))
        
        teacher = self.cursor.fetchone()
        classes = json.loads(teacher[0]) if teacher and teacher[0] else []
        
        for class_name in classes:
            class_frame = tk.Frame(self.content_frame, bg='white',
                                  relief='raised', borderwidth=2)
            class_frame.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Label(class_frame, text=f"🏫 {class_name} класс",
                    font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
            
            self.cursor.execute('''
                SELECT u.full_name
                FROM users u
                JOIN students s ON u.id = s.user_id
                WHERE s.class_name = ?
                ORDER BY u.full_name
            ''', (class_name,))
            
            students = self.cursor.fetchall()
            
            if students:
                students_frame = tk.Frame(class_frame, bg='white')
                students_frame.pack(padx=20, pady=10, fill=tk.X)
                
                for i, (student_name,) in enumerate(students, 1):
                    tk.Label(students_frame, text=f"{i}. {student_name}",
                            font=('Arial', 11), bg='white').pack(anchor='w')
            else:
                tk.Label(class_frame, text="Нет учеников",
                        font=('Arial', 11), bg='white', fg='gray').pack(pady=10)
    
    def show_teacher_reports(self):
        """Отчеты учителя"""
        self.clear_content()
        self.section_header.config(text="📈 Отчеты учителя")
        
        self.cursor.execute("SELECT classes FROM teachers WHERE user_id = ?",
                          (self.current_user['id'],))
        
        teacher = self.cursor.fetchone()
        classes = json.loads(teacher[0]) if teacher and teacher[0] else []
        
        for class_name in classes:
            class_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
            class_frame.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Label(class_frame, text=f"📊 {class_name} класс",
                    font=('Arial', 14, 'bold'), bg='white',
                    fg=self.colors['primary'], pady=10).pack()
            
            # Статистика по классу
            self.cursor.execute('''
                SELECT u.full_name, AVG(g.grade) as avg_grade
                FROM users u
                JOIN students s ON u.id = s.user_id
                LEFT JOIN grades g ON u.id = g.student_id
                WHERE s.class_name = ?
                GROUP BY u.id
                ORDER BY avg_grade DESC
            ''', (class_name,))
            
            students_stats = self.cursor.fetchall()
            
            if students_stats:
                for student_name, avg_grade in students_stats:
                    if avg_grade:
                        tk.Label(class_frame, 
                                text=f"• {student_name}: {avg_grade:.2f}",
                                font=('Arial', 11), bg='white').pack(anchor='w', padx=30)
                    else:
                        tk.Label(class_frame,
                                text=f"• {student_name}: нет оценок",
                                font=('Arial', 11), bg='white', fg='gray').pack(anchor='w', padx=30)
            else:
                tk.Label(class_frame, text="Нет данных",
                        font=('Arial', 11), bg='white', fg='gray').pack(pady=10)
    
    def show_reports(self):
        """Показать отчеты"""
        self.clear_content()
        self.section_header.config(text="📈 Отчеты и статистика")
        
        # Общая статистика
        stats_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(stats_frame, text="ОБЩАЯ СТАТИСТИКА",
                font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
        
        # Считаем статистику
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
        students_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'")
        teachers_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM moscow_cards WHERE active = 1")
        active_cards = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT SUM(balance) FROM moscow_cards")
        total_balance = self.cursor.fetchone()[0] or 0
        
        self.cursor.execute("SELECT COUNT(*) FROM moscow_cards")
        total_cards = self.cursor.fetchone()[0]
        
        stats = [
            f"👨‍🎓 Учеников: {students_count}",
            f"👩‍🏫 Учителей: {teachers_count}",
            f"💳 Всего карт: {total_cards}",
            f"💳 Активных карт: {active_cards}",
            f"💰 Общий баланс карт: {total_balance:.2f} руб.",
        ]
        
        for stat in stats:
            tk.Label(stats_frame, text=stat, font=('Arial', 12),
                    bg='white', pady=5).pack()
        
        # Топ учеников
        top_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(top_frame, text="🏆 ТОП-5 УЧЕНИКОВ",
                font=('Arial', 14, 'bold'), bg='white', pady=10).pack()
        
        self.cursor.execute('''
            SELECT u.full_name, s.class_name, AVG(g.grade) as avg_grade
            FROM users u
            JOIN students s ON u.id = s.user_id
            JOIN grades g ON u.id = g.student_id
            GROUP BY u.id
            ORDER BY avg_grade DESC
            LIMIT 5
        ''')
        
        top_students = self.cursor.fetchall()
        
        if top_students:
            for i, (name, class_name, avg) in enumerate(top_students, 1):
                tk.Label(top_frame,
                        text=f"{i}. {name} ({class_name}): {avg:.2f}",
                        font=('Arial', 11), bg='white').pack(anchor='w', padx=30, pady=2)
        else:
            tk.Label(top_frame, text="Нет данных",
                    font=('Arial', 11), bg='white', fg='gray').pack(pady=10)
    
    def show_logs(self):
        """Показать логи системы"""
        self.clear_content()
        self.section_header.config(text="📝 Логи системы")
        
        # Таблица логов
        table_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Дата", "Пользователь", "Действие", "Описание")
        tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Получаем логи
        self.cursor.execute('''
            SELECT timestamp, user_id, action, description
            FROM system_logs
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        for log in self.cursor.fetchall():
            tree.insert('', 'end', values=log)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(tree, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопка очистки логов
        def clear_logs():
            if messagebox.askyesno("Подтверждение", "Очистить все логи?"):
                self.cursor.execute("DELETE FROM system_logs")
                self.conn.commit()
                self.show_logs()
        
        tk.Button(self.content_frame, text="🗑️ Очистить логи", command=clear_logs,
                 bg=self.colors['danger'], fg='white', font=('Arial', 9),
                 relief='flat', padx=10, pady=5).pack(pady=5)
    
    def log_action(self, action, description=''):
        """Логирование действий"""
        try:
            self.cursor.execute('''
                INSERT INTO system_logs (timestamp, user_id, action, description)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 self.current_user['id'] if self.current_user else 'system',
                 action, description))
            self.conn.commit()
        except:
            pass
    
    def system_settings(self):
        """Настройки системы"""
        self.clear_content()
        self.section_header.config(text="⚙️ Настройки системы")
        
        settings_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        settings_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(settings_frame, text="НАСТРОЙКИ СИСТЕМЫ",
                font=('Arial', 14, 'bold'), bg='white', pady=20).pack()
        
        info = """
        Версия: 3.0
        Тип: Московская Электронная Школа
        База данных: SQLite
        Считыватель: Ирон Логик (эмулятор)
        
        Функции:
        ✅ Управление пользователями
        ✅ Изменение логинов и паролей
        ✅ Карты Москвёнок
        ✅ Расписание и журнал
        ✅ Терминал столовой
        ✅ Домашние задания
        ✅ Посещаемость
        ✅ Сообщения и уведомления
        ✅ Отчеты и статистика
        ✅ Логирование действий
        """
        
        tk.Label(settings_frame, text=info, font=('Arial', 11),
                bg='white', justify='left').pack(padx=20, pady=10)
        
        # Кнопка сброса базы данных
        def reset_database():
            if messagebox.askyesno("Подтверждение", 
                                   "Сбросить базу данных?\nВсе данные будут удалены!"):
                self.cursor.execute("DELETE FROM users")
                self.cursor.execute("DELETE FROM students")
                self.cursor.execute("DELETE FROM teachers")
                self.cursor.execute("DELETE FROM parents")
                self.cursor.execute("DELETE FROM moscow_cards")
                self.cursor.execute("DELETE FROM schedule")
                self.cursor.execute("DELETE FROM grades")
                self.cursor.execute("DELETE FROM homework")
                self.cursor.execute("DELETE FROM attendance")
                self.cursor.execute("DELETE FROM canteen_menu")
                self.cursor.execute("DELETE FROM canteen_purchases")
                self.cursor.execute("DELETE FROM messages")
                self.cursor.execute("DELETE FROM notifications")
                self.cursor.execute("DELETE FROM system_logs")
                self.conn.commit()
                
                self.create_admin()
                self.create_demo_data()
                messagebox.showinfo("Успех", "База данных сброшена!")
                self.system_settings()
        
        tk.Button(settings_frame, text="🔄 Сбросить базу данных", command=reset_database,
                 bg=self.colors['danger'], fg='white', font=('Arial', 11, 'bold'),
                 relief='flat', padx=20, pady=10).pack(pady=20)
    
    def manage_schedule(self):
        """Управление расписанием"""
        self.clear_content()
        self.section_header.config(text="📅 Управление расписанием")
        
        # Выбор класса для просмотра
        control_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(control_frame, text="Класс:", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.cursor.execute("SELECT DISTINCT class_name FROM schedule ORDER BY class_name")
        classes = [c[0] for c in self.cursor.fetchall()]
        
        if not classes:
            classes = ["1А", "5Б", "9В", "11А"]
        
        class_var = tk.StringVar(value=classes[0])
        class_combo = ttk.Combobox(control_frame, textvariable=class_var,
                                  values=classes, state='readonly', width=15)
        class_combo.pack(side=tk.LEFT, padx=5)
        
        def show_schedule():
            for widget in schedule_frame.winfo_children():
                widget.destroy()
            
            class_name = class_var.get()
            days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
            
            notebook = ttk.Notebook(schedule_frame)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            for day in days:
                day_frame = tk.Frame(notebook, bg='white')
                notebook.add(day_frame, text=day)
                
                self.cursor.execute('''
                    SELECT lesson_number, time_start, time_end, subject, room, teacher_id, id
                    FROM schedule
                    WHERE class_name = ? AND day_of_week = ?
                    ORDER BY lesson_number
                ''', (class_name, day))
                
                lessons = self.cursor.fetchall()
                
                if lessons:
                    for lesson in lessons:
                        lesson_frame = tk.Frame(day_frame, bg='white', relief='solid', borderwidth=1)
                        lesson_frame.pack(fill=tk.X, padx=10, pady=5)
                        
                        tk.Label(lesson_frame, text=f"Урок {lesson[0]}: {lesson[1]}-{lesson[2]}",
                                font=('Arial', 10, 'bold'), bg='white', width=20).pack(side=tk.LEFT, padx=5)
                        
                        tk.Label(lesson_frame, text=lesson[3],
                                font=('Arial', 10), bg='white', width=20).pack(side=tk.LEFT)
                        
                        tk.Label(lesson_frame, text=lesson[4],
                                font=('Arial', 10), bg='white', width=15).pack(side=tk.LEFT)
                        
                        # Получаем имя учителя
                        self.cursor.execute("SELECT full_name FROM users WHERE id = ?", (lesson[5],))
                        teacher = self.cursor.fetchone()
                        teacher_name = teacher[0] if teacher else "Не назначен"
                        tk.Label(lesson_frame, text=teacher_name,
                                font=('Arial', 9), bg='white', fg='gray').pack(side=tk.LEFT, padx=5)
                else:
                    tk.Label(day_frame, text="📭 Нет уроков",
                            font=('Arial', 11), bg='white', fg='gray').pack(pady=20)
        
        tk.Button(control_frame, text="📅 Показать", command=show_schedule,
                 bg=self.colors['primary'], fg='white', font=('Arial', 10),
                 relief='flat', padx=15, pady=5).pack(side=tk.LEFT, padx=10)
        
        schedule_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=1)
        schedule_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        show_schedule()
    
    def manage_classes(self):
        """Управление классами"""
        self.clear_content()
        self.section_header.config(text="🏫 Управление классами")
        
        # Список классов с информацией
        self.cursor.execute('''
            SELECT DISTINCT s.class_name, 
                   COUNT(s.user_id) as student_count,
                   (SELECT u.full_name FROM users u JOIN teachers t ON u.id = t.user_id 
                    WHERE t.classes LIKE '%' || s.class_name || '%' LIMIT 1) as teacher_name
            FROM students s
            GROUP BY s.class_name
            ORDER BY s.class_name
        ''')
        
        classes = self.cursor.fetchall()
        
        if classes:
            for class_name, student_count, teacher_name in classes:
                class_frame = tk.Frame(self.content_frame, bg='white', relief='raised', borderwidth=2)
                class_frame.pack(fill=tk.X, padx=20, pady=10)
                
                tk.Label(class_frame, text=f"🏫 {class_name} класс",
                        font=('Arial', 16, 'bold'), bg='white', pady=10).pack()
                
                info_frame = tk.Frame(class_frame, bg='white')
                info_frame.pack(padx=20, pady=10, fill=tk.X)
                
                tk.Label(info_frame, text=f"👨‍🎓 Учеников: {student_count}",
                        font=('Arial', 12), bg='white').pack(anchor='w')
                
                tk.Label(info_frame, text=f"👩‍🏫 Классный руководитель: {teacher_name or 'Не назначен'}",
                        font=('Arial', 12), bg='white').pack(anchor='w')
                
                # Список учеников
                self.cursor.execute('''
                    SELECT u.full_name
                    FROM users u
                    JOIN students s ON u.id = s.user_id
                    WHERE s.class_name = ?
                    ORDER BY u.full_name
                ''', (class_name,))
                
                students = self.cursor.fetchall()
                
                if students:
                    students_frame = tk.Frame(class_frame, bg='white')
                    students_frame.pack(padx=30, pady=10, fill=tk.X)
                    
                    tk.Label(students_frame, text="Ученики:",
                            font=('Arial', 11, 'bold'), bg='white').pack(anchor='w')
                    
                    for i, (student_name,) in enumerate(students, 1):
                        tk.Label(students_frame, text=f"  {i}. {student_name}",
                                font=('Arial', 10), bg='white').pack(anchor='w')
        else:
            tk.Label(self.content_frame, text="📭 Классы не найдены",
                    font=('Arial', 14), bg=self.colors['bg'], fg='gray').pack(pady=50)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MoscowElectronicSchool()
    app.run()