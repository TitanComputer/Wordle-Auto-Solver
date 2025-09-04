import os
import threading
import time
import requests
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
from PIL import Image, ImageTk
from solver import WordleSolver, LetterFrequencyAnalyzer

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, JavascriptException

APP_VERSION = "1.0.0"


class WordleApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"Wordle Auto-Solver v{APP_VERSION}")
        self.geometry("310x400")
        self.icon = PhotoImage(file=self.resource_path(os.path.join("assets", "icon.png")))
        self.withdraw()
        self.iconphoto(False, self.icon)
        self.center_window()
        self.deiconify()
        self.resizable(False, False)

        # # ttk Style manager
        # self.style = ttk.Style()
        # self.themes = self.style.theme_names()

        # # Theme selector
        # self.theme_var = tk.StringVar(value=self.style.theme_use())
        # theme_label = ttk.Label(self, text="Theme:")
        # theme_label.pack(pady=(8, 0))
        # self.theme_combo = ttk.Combobox(self, textvariable=self.theme_var, values=self.themes, state="readonly")
        # self.theme_combo.pack(pady=4, fill=tk.X, padx=10)
        # self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        self.driver = None
        self.running = False
        self.thread = None
        self.last_solution = None

        # Start / Stop button
        self.start_button = ttk.Button(self, text="Start", command=self.toggle_solver)
        self.start_button.pack(pady=5, fill=tk.X, padx=10)

        # Log box
        self.log_box = tk.Text(self, height=10, width=40, state=tk.DISABLED)
        self.log_box.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # Translate button
        self.translate_button = ttk.Button(self, text="Translate to Persian", command=self.translate_word)
        self.translate_button.pack(pady=5, fill=tk.X, padx=10)

        # Donate button with image
        heart_path = os.path.join("assets", "heart.png")
        if os.path.exists(heart_path):
            heart_img = Image.open(heart_path).resize((20, 20))
            self.heart_photo = ImageTk.PhotoImage(heart_img)
        else:
            self.heart_photo = None

        donate_frame = ttk.Frame(self)
        donate_frame.pack(pady=5)
        self.donate_button = ttk.Button(
            donate_frame, text="Donate", command=self.open_donate_page, image=self.heart_photo, compound="right"
        )
        self.donate_button.pack(fill=tk.X, padx=10)

    def resource_path(self, relative_path):
        temp_dir = os.path.dirname(__file__)
        return os.path.join(temp_dir, relative_path)

    def center_window(self):
        self.update_idletasks()  # make sure geometry info is updated
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # def change_theme(self, event=None):
    #     selected = self.theme_var.get()
    #     try:
    #         self.style.theme_use(selected)
    #         self.add_log(f"Theme changed to {selected}")
    #     except tk.TclError:
    #         self.add_log(f"Failed to apply theme: {selected}")

    def add_log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def toggle_solver(self):
        if not self.running:
            self.running = True
            self.start_button.config(text="Stop")
            self.log_box.config(state=tk.NORMAL)
            self.log_box.delete("1.0", tk.END)
            self.log_box.config(state=tk.DISABLED)
            self.thread = threading.Thread(target=self.run_solver, daemon=True)
            self.thread.start()
        else:
            self.add_log("Stop requested by user.")
            self.running = False
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.start_button.config(text="Start")

    def run_solver(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        chrome_path = os.path.join(base_dir, "assets", "chromedriver.exe")
        words_file = os.path.join(base_dir, "assets", "words_sorted.txt")

        if not os.path.exists(chrome_path):
            self.add_log(f"Chromedriver not found at: {chrome_path}")
            self.running = False
            self.start_button.config(text="Start")
            return

        try:
            service = Service(chrome_path)
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-gpu")
            self.driver = webdriver.Chrome(service=service, options=options)
            self.add_log("Chrome started.")
            self.driver.get("https://www.nytimes.com/games/wordle/index.html")
            time.sleep(1.2)
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
            except Exception:
                pass

            if os.path.exists(words_file):
                with open(words_file, "r", encoding="utf-8") as f:
                    words = [w.strip() for w in f if w.strip()]
            else:
                self.add_log(f"Words file not found: {words_file}")
                words = []

            if not words:
                self.add_log("No words loaded. Aborting solver.")
                return

            analyzer = LetterFrequencyAnalyzer(input_path=words_file)
            analyzer.analyze()
            solver = WordleSolver(words)

            known_pattern = [None] * 5
            excluded_letters = set()
            present_letters = set()
            candidates = words.copy()
            solved = False

            for attempt in range(6):
                if not self.running:
                    self.add_log("Stopped by user.")
                    break

                top = analyzer.suggest_best_words(word_list=candidates, top_n=1)
                guess = top[0][0] if top else (candidates[0] if candidates else None)

                if not guess:
                    self.add_log("No candidate available. Stopping.")
                    break

                self.add_log(f"Trying word: {guess} (attempt {attempt+1})")

                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    for ch in guess:
                        body.send_keys(ch)
                        time.sleep(0.06)
                    body.send_keys(Keys.ENTER)
                except Exception as ex:
                    self.add_log(f"Error sending keys: {ex}")
                    break

                evals = None
                wait_until = time.time() + 12
                while time.time() < wait_until:
                    if not self.running:
                        break
                    try:
                        script = f"""
const app = document.querySelector('game-app');
if(!app) return null;
const shadow = app.shadowRoot;
const rows = shadow.querySelectorAll('game-row');
if(rows.length <= {attempt}) return null;
const row = rows[{attempt}];
const tiles = row.shadowRoot.querySelectorAll('game-tile');
if(!tiles) return null;
let arr = [];
tiles.forEach(t => {{
  arr.push({{letter: t.getAttribute('letter'), evaluation: t.getAttribute('evaluation')}})
}});
return arr;
"""
                        res = self.driver.execute_script(script)
                    except (WebDriverException, JavascriptException):
                        res = None
                    if res and isinstance(res, list) and all(tile.get("evaluation") for tile in res):
                        evals = res
                        break
                    time.sleep(0.18)

                if not evals:
                    self.add_log("No evaluation received (timeout).")
                    continue

                row_letters = [tile.get("letter") for tile in evals]
                row_states = [tile.get("evaluation") for tile in evals]
                self.add_log("Result: " + ", ".join(f"{l}:{s}" for l, s in zip(row_letters, row_states)))

                if all(s == "correct" for s in row_states):
                    solution = "".join(row_letters)
                    self.add_log(f"Solved! Word is: {solution}")
                    self.last_solution = solution
                    messagebox.showinfo("Solved", f"Solution: {solution}")
                    solved = True
                    break

                row_present_letters = {letter for letter, state in zip(row_letters, row_states) if state == "present"}
                for idx, (letter, state) in enumerate(zip(row_letters, row_states)):
                    if state == "correct":
                        known_pattern[idx] = letter
                        present_letters.add(letter)
                    elif state == "present":
                        present_letters.add(letter)
                    elif (
                        state == "absent"
                        and letter not in row_present_letters
                        and letter not in present_letters
                        and letter not in known_pattern
                    ):
                        excluded_letters.add(letter)

                unknowns = [
                    (idx, letter)
                    for idx, (letter, state) in enumerate(zip(row_letters, row_states))
                    if state == "present"
                ]
                candidates = solver.filter_candidates(known_pattern, unknowns, list(excluded_letters))
                self.add_log(f"Candidates remaining: {len(candidates)}")
                time.sleep(0.4)

            if not solved and self.running:
                self.add_log("Solver finished without solution.")

        except Exception as ex:
            self.add_log(f"Error: {ex}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.driver = None
            self.running = False
            self.start_button.config(text="Start")

    def translate_word(self):
        if not self.last_solution:
            messagebox.showinfo("Translation", "No solution available yet.")
            return
        try:
            r = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": self.last_solution, "langpair": "en|fa"},
                timeout=6,
            )
            translation = r.json().get("responseData", {}).get("translatedText")
        except Exception:
            translation = None
        messagebox.showinfo("Translation", f"{self.last_solution} → {translation or 'not available'}")

    def open_donate_page(self):
        messagebox.showinfo("Donate", "Donate page (to be implemented)")


if __name__ == "__main__":
    app = WordleApp()
    app.mainloop()
