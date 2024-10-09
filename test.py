import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import tkinter as tk
from tkinter import messagebox, Toplevel, ttk
import webbrowser

class Crawler:

    def __init__(self, dbFileName):
        self.conn = sqlite3.connect(dbFileName)
        self.initDB()
        self.found_articles = []  # Список для хранения найденных статей
        self.names = ["Александр", "Алексей", "Андрей", "Антон", "Артём", "Борис", "Владимир", "Вячеслав", "Георгий", "Дмитрий", "Евгений", "Иван", "Константин", "Максим", "Михаил",
                      "Николай", "Павел", "Сергей", "Юрий", "Ярослав", "Анастасия", "Анна", "Валентина", "Вероника", "Виктория", "Дарья", "Елена", "Екатерина", "Ирина", "Ксения", "Людмила",
                      "Маргарита", "Марина", "Мария", "Наталья", "Оксана", "Ольга", "Полина", "Светлана", "Юлия"]


    def __del__(self):
        self.conn.close()

    def addIndex(self, soup, url, word1, word2):
        # Получаем текст страницы
        text = self.getTextOnly(soup)

        # Разбиваем текст на отдельные слова
        words = re.findall(r'\b\w+\b', text.lower())  # Извлекаем все слова
        word1 = word1.lower()
        word2 = word2.lower()

        # Проверяем наличие обоих слов на странице
        if word1 in words and word2 in words:
            # Проверяем наличие имени в URL
            if not any(name.lower() in url.lower() for name in self.names):
                # Проверяем раздел источников на наличие ссылок с именами
                if not self.hasNameInSources(soup):
                    print(f"Найдена статья с обоими словами: {url}")
                    title = soup.find('h1').get_text()  # Получаем название статьи
                    self.found_articles.append((url, title))  # Сохраняем URL и название статьи
                    return True
        return False

    def hasNameInSources(self, soup):
        # Находим раздел источников
        references_section = soup.find(id='Источники')
        if references_section:
            # Проверяем ссылки в разделе источников
            for link in references_section.find_all('a', href=True):
                ref_url = link['href']
                if any(name.lower() in ref_url.lower() for name in self.names):
                    print(f"Пропускаем статью с источником, содержащим имя: {ref_url}")
                    return True
        return False

    def getTextOnly(self, soup):
        # Извлекаем текст из всех абзацев, заголовков и других важных элементов
        paragraphs = soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'span', 'li'])
        return ' '.join([p.get_text() for p in paragraphs])

    def crawl(self, startUrl, word1, word2, maxDepth=2):
        # Начинаем парсинг с указанного URL (главной страницы Википедии)
        to_crawl = [startUrl]
        crawled = set()

        for depth in range(maxDepth):
            next_crawl = []
            for url in to_crawl:
                if url in crawled:
                    continue

                print(f"Парсим: {url}")
                try:
                    # Загружаем страницу
                    html_doc = requests.get(url).text
                    soup = BeautifulSoup(html_doc, "html.parser")

                    # Проверяем, есть ли в URL одно из имён
                    if any(name.lower() in url.lower() for name in self.names):
                        print(f"Пропускаем ссылку с именем: {url}")
                        continue  # Пропускаем URL, если там есть имя

                    # Проверяем, есть ли на странице оба слова
                    self.addIndex(soup, url, word1, word2)

                    # Ищем ссылки на статьи внутри текущей страницы
                    for link in soup.find_all('a', href=True):
                        link_url = link['href']
                        full_url = requests.compat.urljoin(startUrl, link_url)

                        # Проверка имени в ссылке
                        if link_url.startswith("/wiki/") and not link_url.startswith("/wiki/Служебная:") and \
                                not any(name.lower() in full_url.lower() for name in self.names):
                            if full_url not in crawled:
                                next_crawl.append(full_url)

                except requests.exceptions.RequestException as e:
                    print(f"Ошибка при загрузке страницы: {url}, {e}")

                crawled.add(url)
            to_crawl = next_crawl

    def initDB(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                content TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_url TEXT,
                to_url TEXT,
                link_text TEXT
            )
        ''')
        self.conn.commit()


# Функция для проверки введённых слов
def check_words(word1, word2, names):
    for name in names:
        if word1.lower() == name.lower() or word2.lower() == name.lower():
            return False
    return True


# Функция для запуска парсинга из графического интерфейса
def start_crawl():
    word1 = entry_word1.get()
    word2 = entry_word2.get()
    names = ["Мария", "Александр", "Ольга", "Иван", "Анна", "Наталья"]  # Список имён для проверки

    # Проверка, что оба слова введены
    if not word1 or not word2:
        messagebox.showwarning("Предупреждение", "Введите оба слова")
        return

    # Проверка, что слова не являются именами
    if not check_words(word1, word2, names):
        messagebox.showerror("Ошибка", "Одно из введённых слов является именем. Попробуйте другие слова.")
        return

    # Создаем объект паука и запускаем поиск статей
    crawler = Crawler("wikipedia.db")
    # Парсим сначала первый сайт
    crawler.crawl("https://ru.wikipedia.org/", word1, word2)
    # Парсим второй сайт
    crawler.crawl("https://exponenta.ru/", word1, word2)
    # Если статьи найдены, выводим их результатом
    if crawler.found_articles:
        show_results(crawler.found_articles)
    else:
        messagebox.showinfo("Информация", "Статьи с этими словами не найдены.")

# Функция для открытия ссылки в браузере
def open_link(event, url):
    webbrowser.open_new(url)


# Функция для отображения найденных статей в виде таблицы
def show_results(articles):
    result_window = Toplevel(root)
    result_window.title("Найденные статьи")

    # Создаем таблицу (Treeview)
    tree = ttk.Treeview(result_window, columns=("URL", "Title"), show="headings", height=15)
    tree.pack(side="left", fill="both", expand=True)

    # Определяем заголовки столбцов
    tree.heading("URL", text="Ссылка")
    tree.heading("Title", text="Название статьи")

    # Определяем ширину столбцов
    tree.column("URL", width=300)
    tree.column("Title", width=300)

    # Добавляем статьи в таблицу
    for article in articles:
        tree.insert("", "end", values=article)

    # Добавляем прокрутку
    scrollbar = ttk.Scrollbar(result_window, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.config(yscrollcommand=scrollbar.set)

    # Связываем событие клика по ссылке с открытием браузера
    def on_double_click(event):
        item = tree.selection()[0]
        url = tree.item(item, "values")[0]
        webbrowser.open_new(url)

    tree.bind("<Double-1>", on_double_click)


# Создаем графический интерфейс с использованием Tkinter
root = tk.Tk()
root.title("Парсер Википедии")

# Поля для ввода двух слов
label_word1 = tk.Label(root, text="Введите первое слово:")
label_word1.pack()

entry_word1 = tk.Entry(root)
entry_word1.pack()

label_word2 = tk.Label(root, text="Введите второе слово:")
label_word2.pack()

entry_word2 = tk.Entry(root)
entry_word2.pack()

# Кнопка для запуска парсинга
button_crawl = tk.Button(root, text="Начать парсинг", command=start_crawl)
button_crawl.pack()

# Запуск графического интерфейса
root.mainloop()
