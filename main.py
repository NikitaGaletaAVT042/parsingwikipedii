import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import tkinter as tk
from tkinter import messagebox, Toplevel, ttk
import webbrowser
from neural_search import NeuralSearchGUI

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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT,
                url TEXT,
                frequency INTEGER,
                positions TEXT
            )
        ''')
        self.conn.commit()

    def addIndex(self, soup, url, word1, word2):
        text = self.getTextOnly(soup)
        words = re.findall(r'\b\w+\b', text.lower())
        word1 = word1.lower()
        word2 = word2.lower()

        # Сохраняем карту слов
        self.buildWordMap(url, words)

        if word1 in words and word2 in words:
            if not any(name.lower() in url.lower() for name in self.names):
                if not self.hasNameInSources(soup):
                    print(f"Найдена статья с обоими словами: {url}")
                    title = soup.find('h1').get_text()
                    self.found_articles.append((url, title))
                    return True
        return False

    def buildWordMap(self, url, words):
        cursor = self.conn.cursor()
        word_positions = {}

        for index, word in enumerate(words):
            if word not in word_positions:
                word_positions[word] = []
            word_positions[word].append(index)

        for word, positions in word_positions.items():
            frequency = len(positions)
            positions_str = ','.join(map(str, positions))
            cursor.execute('''
                INSERT OR IGNORE INTO word_map (word, url, frequency, positions)
                VALUES (?, ?, ?, ?)
            ''', (word, url, frequency, positions_str))

        self.conn.commit()

    def hasNameInSources(self, soup):
        references_section = soup.find(id='Источники')
        if references_section:
            for link in references_section.find_all('a', href=True):
                ref_url = link['href']
                if any(name.lower() in ref_url.lower() for name in self.names):
                    print(f"Пропускаем статью с источником, содержащим имя: {ref_url}")
                    return True
        return False

    def getTextOnly(self, soup):
        paragraphs = soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'span', 'li'])
        return ' '.join([p.get_text() for p in paragraphs])

    def crawl(self, startUrl, word1, word2, maxDepth=3):
        to_crawl = [startUrl]
        crawled = set()

        for depth in range(maxDepth):
            next_crawl = []
            for url in to_crawl:
                if url in crawled:
                    continue

                print(f"Парсим: {url}")
                try:
                    html_doc = requests.get(url).text
                    soup = BeautifulSoup(html_doc, "html.parser")

                    if any(name.lower() in url.lower() for name in self.names):
                        print(f"Пропускаем ссылку с именем: {url}")
                        continue

                    self.addIndex(soup, url, word1, word2)

                    for link in soup.find_all('a', href=True):
                        link_url = link['href']
                        full_url = requests.compat.urljoin(startUrl, link_url)

                        if link_url.startswith("/wiki/") and not link_url.startswith("/wiki/Служебная:") and \
                                not any(name.lower() in full_url.lower() for name in self.names):
                            if full_url not in crawled:
                                next_crawl.append(full_url)

                except requests.exceptions.RequestException as e:
                    print(f"Ошибка при загрузке страницы: {url}, {e}")

                crawled.add(url)
            to_crawl = next_crawl

    def checkWordMap(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM word_map')
        count = cursor.fetchone()[0]
        print(f"В карте слов {count} записей.")

    def offline_search(self, word1, word2):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT url, SUM(frequency) as total_frequency
            FROM word_map
            WHERE word = ? OR word = ?
            GROUP BY url
            ORDER BY total_frequency DESC
        ''', (word1.lower(), word2.lower()))

        results = cursor.fetchall()
        return [(row[0], row[1]) for row in results]


def check_words(word1, word2, names):
    if word1 and word2:
        for name in names:
            if word1.lower() == name.lower() or word2.lower() == name.lower():
                return False
    return True


def start_crawl():
    word1 = entry_word1.get()
    word2 = entry_word2.get()
    names = ["Мария", "Александр", "Ольга", "Иван", "Анна", "Наталья"]

    if word1 and word2:
        if not check_words(word1, word2, names):
            messagebox.showerror("Ошибка", "Одно из введённых слов является именем. Попробуйте другие слова.")
            return

    crawler = Crawler("wikipedia.db")
    crawler.crawl("https://ru.wikipedia.org/wiki/", word1, word2, maxDepth=5)

    crawler.checkWordMap()

    if crawler.found_articles:
        show_results(crawler.found_articles)
    else:
        messagebox.showinfo("Информация", "Статьи с этими словами не найдены.")


def offline_search():
    word1 = entry_word1.get()
    word2 = entry_word2.get()

    if not word1 or not word2:
        messagebox.showwarning("Предупреждение", "Введите оба слова для оффлайн поиска")
        return

    crawler = Crawler("wikipedia.db")
    results = crawler.offline_search(word1, word2)

    if results:
        show_results(results)
    else:
        messagebox.showinfo("Информация", "Статьи с этими словами не найдены в оффлайн режиме.")


def open_link(event, url):
    webbrowser.open_new(url)


def show_results(articles):
    result_window = Toplevel(root)
    result_window.title("Найденные статьи")

    tree = ttk.Treeview(result_window, columns=("URL", "Frequency"), show="headings", height=15)
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("URL", text="Ссылка")
    tree.heading("Frequency", text="Частота")

    tree.column("URL", width=300)
    tree.column("Frequency", width=100)

    for article in articles:
        tree.insert("", "end", values=article)

    scrollbar = ttk.Scrollbar(result_window, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.config(yscrollcommand=scrollbar.set)

    def on_double_click(event):
        item = tree.selection()[0]
        url = tree.item(item, "values")[0]
        webbrowser.open_new(url)

    tree.bind("<Double-1>", on_double_click)

def start_neural_search():
    neural_search_gui = NeuralSearchGUI("wikipedia.db")
    neural_search_gui.show_interface()
root = tk.Tk()
root.title("Парсер Википедии")

label_word1 = tk.Label(root, text="Введите первое слово:")
label_word1.pack()

entry_word1 = tk.Entry(root)
entry_word1.pack()

label_word2 = tk.Label(root, text="Введите второе слово:")
label_word2.pack()

entry_word2 = tk.Entry(root)
entry_word2.pack()

button_crawl = tk.Button(root, text="Начать парсинг", command=start_crawl)
button_crawl.pack()

button_offline = tk.Button(root, text="Оффлайн поиск", command=offline_search)
button_offline.pack()

button_neural_search = tk.Button(root, text="Поиск по нейронной сети", command=start_neural_search)
button_neural_search.pack()

root.mainloop()
