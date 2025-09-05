import os
import threading
import time
import requests
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
from PIL import Image, ImageTk
from solver import WordleSolver, LetterFrequencyAnalyzer

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        self.protocol("WM_DELETE_WINDOW", self.on_close)

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

    def on_close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

        self.running = False
        self.destroy()

    def check_driver(self):
        if self.driver:
            try:
                self.driver.title
            except Exception:
                self.add_log("Chrome window was closed unexpectedly.")
                self.running = False
                self.start_button.config(text="Start")
                self.driver = None

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

        if not os.path.exists(chrome_path):
            self.add_log(f"Chromedriver not found at: {chrome_path}")
            self.running = False
            self.start_button.config(text="Start")
            return

        try:
            service = Service(chrome_path)
            options = webdriver.ChromeOptions()
            # keep browser visible (do not use headless)
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            self.driver = webdriver.Chrome(service=service, options=options)
            self.add_log("Chrome started.")
            self.driver.get("https://www.nytimes.com/games/wordle/index.html")

            wait = WebDriverWait(self.driver, 25)

            # wait until document.readyState == 'complete'
            try:
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                self.add_log("Page load complete.")
            except Exception as e:
                self.add_log(f"Timeout waiting for full page load: {e}")

            # if user pressed Stop meanwhile, stop
            if not self.running:
                self.add_log("Stopped by user before clicking buttons.")
                return

            # 1) Click "Accept all" (cookie consent) if present
            try:
                accept_btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "#fides-button-group > div.fides-banner-button-group.fides-banner-primary-actions > button.fides-banner-button.fides-banner-button-primary.fides-accept-all-button",
                        )
                    )
                )
                accept_btn.click()
                self.add_log("Clicked 'Accept all' button.")
            except Exception as ex:
                self.add_log(f"'Accept all' button not found or not clickable: {ex}")

            # 2) Click "Play" button (start the game) if present
            play_xpath = "//button[contains(text(),'Play')]"
            try:
                btn_play = WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.XPATH, play_xpath)))
                # remove overlay via JS
                self.driver.execute_script(
                    """
                    let overlay = document.querySelector('.fides-modal-overlay');
                    if(overlay) overlay.remove();
                """
                )
                # now click via JS
                self.driver.execute_script("arguments[0].click();", btn_play)
                self.add_log("Clicked 'Play' button via JS.")
            except Exception as ex:
                self.add_log(f"'Play' button not found or not clickable: {ex}")
                return

            # Close modal
            try:
                close_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#help-dialog > div > div > button"))
                )
                close_btn.click()
                self.add_log("Clicked 'Close' button.")
            except Exception as ex:
                self.add_log(f"'Close' button not found or not clickable: {ex}")
                return

            try:
                self.driver.execute_script(
                    """
                    let ad = document.querySelector("div[class^='Ad-module_adContainer__']");
                    if(ad) { ad.style.display = 'none'; }
                """
                )
                self.add_log("Ad element hidden (dynamic class handled).")
            except Exception as ex:
                self.add_log(f"Error hiding ad: {ex}")

            # === prepare analyzer and words ===
            try:
                words_file = os.path.join(base_dir, "assets", "words_sorted.txt")
                with open(words_file, "r", encoding="utf-8") as f:
                    words = [w.strip() for w in f if w.strip()]

                # analyzer را با مسیر فایل مقداردهی کن (تو خودت قبلاً اشاره کردی)
                analyzer = LetterFrequencyAnalyzer(words_file)
                analyzer.analyze()

                # بهترین کلمهٔ اول را بگیر
                top = analyzer.suggest_best_words(word_list=words, top_n=1)
                if not top:
                    self.add_log("No candidate words found in words_sorted.txt")
                    # می‌تونی return یا ادامه بدی
                first_guess = top[0][0]
                self.add_log(f"First guess selected: {first_guess}")
                time.sleep(0.12)

                # === send the word to the page ===
                # روش ساده و معمول: ارسال روی body سپس ENTER
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    # تایپ آهسته با تاخیر کوچک تا کلیدها از دست نروند
                    for ch in first_guess:
                        body.send_keys(ch)
                        time.sleep(0.12)  # اگر miss دیدی این مقدار رو 0.1 یا 0.12 کن
                    body.send_keys(Keys.ENTER)
                    self.add_log(f"Sent '{first_guess}' to page (typed into body).")
                except Exception as e_send:
                    # fallback: ارسال با JS (اگر send_keys به هر دلیلی کار نکرد)
                    try:
                        for ch in first_guess:
                            self.driver.execute_script(
                                "document.body.dispatchEvent(new KeyboardEvent('keydown', {key: arguments[0]}));", ch
                            )
                            time.sleep(0.08)
                        self.driver.execute_script(
                            "document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));"
                        )
                        self.add_log(f"Sent '{first_guess}' via JS fallback.")
                    except Exception as e_js:
                        self.add_log(f"Failed to send first guess: {e_send} / {e_js}")
                        raise

                # === wait & read Row 1 results ===
                try:
                    row1 = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Row 1']"))
                    )

                    # صبر تا همه data-state ها از "tbd" خارج بشن
                    def row_ready(driver):
                        tiles = row1.find_elements(By.CSS_SELECTOR, "div.Tile-module_tile__UWEHN")
                        states = [t.get_attribute("data-state") for t in tiles]
                        return all(s and s != "tbd" for s in states)

                    WebDriverWait(self.driver, 10).until(row_ready)

                    # حالا نتایج نهایی رو بخون
                    tiles = row1.find_elements(By.CSS_SELECTOR, "div.Tile-module_tile__UWEHN")
                    results = []
                    for tile in tiles:
                        letter = tile.text.strip().lower()
                        state = tile.get_attribute("data-state")
                        results.append({"letter": letter, "state": state})

                    self.add_log(f"Row 1 states: {results}")

                    # === ادامهٔ پردازش مثل قبل ===
                    known_pattern = [None] * 5
                    present_letters = set()
                    excluded_letters = set()

                    row_present = {item["letter"] for item in results if item["state"] == "present"}

                    for idx, item in enumerate(results):
                        l = item["letter"]
                        s = item["state"]
                        if s == "correct":
                            known_pattern[idx] = l
                            present_letters.add(l)
                        elif s == "present":
                            present_letters.add(l)
                        elif s == "absent":
                            if (l not in row_present) and (l not in present_letters) and (l not in known_pattern):
                                excluded_letters.add(l)

                    self.add_log(f"known_pattern: {known_pattern}")
                    self.add_log(f"present_letters: {sorted(list(present_letters))}")
                    self.add_log(f"excluded_letters: {sorted(list(excluded_letters))}")

                    solver = WordleSolver(words)
                    unknowns = [(i, item["letter"]) for i, item in enumerate(results) if item["state"] == "present"]
                    candidates = solver.filter_candidates(known_pattern, unknowns, list(excluded_letters))
                    self.add_log(f"Candidates after Row 1: {len(candidates)}")

                    if candidates:
                        next_best = analyzer.suggest_best_words(word_list=candidates, top_n=1)[0][0]
                        self.add_log(f"Next best guess (for Row 2): {next_best}")

                except Exception as e:
                    self.add_log(f"Error reading Row 1: {e}")

                # time.sleep(3)  # صبر برای تغییر وضعیت
                # page_html = self.driver.page_source
                # with open("debug_page.html", "w", encoding="utf-8") as f:
                #     f.write(page_html)
                # self.add_log("Saved debug_page.html for inspection.")

            except Exception as ex_first:
                self.add_log(f"Error during first-guess sequence: {ex_first}")

        except Exception as ex:
            self.add_log(f"Error in run_solver: {ex}")
            # cleanup on error
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass
            self.driver = None
            self.running = False
            self.start_button.config(text="Start")
        # do NOT quit the driver here on success — leave it open so Stop button can close it later

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
