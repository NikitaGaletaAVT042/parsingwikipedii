import sqlite3
import tkinter as tk
from tkinter import Toplevel, ttk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class NeuralSearch:

    def __init__(self, dbFileName):
        self.conn = sqlite3.connect(dbFileName)
        self.vectorizer = TfidfVectorizer()

    def __del__(self):
        self.conn.close()

    def load_data(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT content, url FROM pages')
        rows = cursor.fetchall()
        texts = [row[0] for row in rows]
        urls = [row[1] for row in rows]
        return texts, urls

    def train_model(self):
        texts, urls = self.load_data()
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        self.texts = texts
        self.urls = urls
        self.tfidf_matrix = tfidf_matrix

    def find_answer(self, query):
        query_tfidf = self.vectorizer.transform([query])
        cosine_sim = cosine_similarity(query_tfidf, self.tfidf_matrix)
        best_match_idx = cosine_sim.argmax()
        best_match_text = self.texts[best_match_idx]
        best_match_url = self.urls[best_match_idx]
        return best_match_text, best_match_url


class NeuralSearchGUI:

    def __init__(self, dbFileName):
        self.search_model = NeuralSearch(dbFileName)
        self.search_model.train_model()

    def show_interface(self):
        self.root = Toplevel()
        self.root.title("Поиск по нейронной сети")

        self.answer_label = tk.Label(self.root, text="Ответ:")
        self.answer_label.pack()

        self.answer_text = tk.Text(self.root, height=15, width=70)
        self.answer_text.pack()

        self.query_label = tk.Label(self.root, text="Введите ваш вопрос:")
        self.query_label.pack()

        self.query_entry = tk.Entry(self.root, width=70)
        self.query_entry.pack()

        self.search_button = tk.Button(self.root, text="Поиск", command=self.perform_search)
        self.search_button.pack()

    def perform_search(self):
        query = self.query_entry.get()
        if query:
            answer, url = self.search_model.find_answer(query)
            self.answer_text.delete(1.0, tk.END)
            self.answer_text.insert(tk.END, f"Ответ: {answer}\n\nИсточник: {url}")
        else:
            self.answer_text.delete(1.0, tk.END)
            self.answer_text.insert(tk.END, "Пожалуйста, введите вопрос для поиска.")


if __name__ == "__main__":
    search_app = NeuralSearchGUI("wikipedia.db")
    search_app.show_interface()
