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

import webbrowser
from idlelib.tooltip import Hovertip

APP_VERSION = "1.2.0"


class WordleApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"Wordle Auto-Solver v{APP_VERSION}")
        self.geometry("310x400")
        self.icon = PhotoImage(file=self.resource_path(os.path.join("assets", "icon.png")))
        self.withdraw()
        self.iconphoto(False, self.icon)
        self.center_window()
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
        self.translate_button = ttk.Button(
            self, text="Translate to Persian", command=self.translate_word, state=tk.DISABLED
        )
        self.translate_button.pack(pady=5, fill=tk.X, padx=10)

        # Donate button with image
        heart_path = self.resource_path(os.path.join("assets", "heart.png"))
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
        self.deiconify()

    def on_close(self):
        """Stops the solver, closes the Chrome window, and exits the app."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

        self.running = False
        self.destroy()

    def check_driver(self):
        """Periodically checks if the Chrome window is still open. If it was closed,
        stops the solver and resets the UI."""

        if self.driver:
            try:
                self.driver.title
            except Exception:
                self.add_log("Chrome window was closed unexpectedly.")
                self.running = False
                self.start_button.config(text="Start")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

    def start_driver_watcher(self):
        """Periodically checks if the Chrome window is still open. If it was closed,
        stops the solver and resets the UI."""

        def loop():
            self.check_driver()
            if self.running:
                self.after(2000, loop)

        loop()

    def resource_path(self, relative_path):
        """Returns the absolute path to a file in the same directory as the script.
        This is used to find resources like images when the script is run from a
        different directory (e.g. as an executable)."""
        temp_dir = os.path.dirname(__file__)
        return os.path.join(temp_dir, relative_path)

    def center_window(self):
        """Centers the window on the screen."""
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
        """Adds a new log message to the log box with a timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def toggle_solver(self):
        """Toggle the solver on or off. If it was off, start the solver and
        disable the translate button. If it was on, stop the solver and
        re-enable the translate button."""
        if not self.running:
            self.running = True
            self.start_button.config(text="Stop")
            self.translate_button.configure(state=tk.DISABLED)
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
        """
        Starts the Chrome driver, loads the Wordle game page, and begins the solving loop.

        This function is called when the Start button is clicked. The solving loop will attempt to
        solve the game by guessing words and analyzing the results. The loop will continue until the
        game is solved or the maximum number of attempts is reached.

        The function is also responsible for displaying the game page and handling any errors that
        occur during the solving loop.
        """
        chrome_path = self.resource_path(os.path.join("assets", "chromedriver.exe"))

        if not os.path.exists(chrome_path):
            self.add_log(f"Chromedriver not found at: {chrome_path}")
            self.running = False
            self.start_button.config(text="Start")
            return

        try:
            service = Service(chrome_path)
            options = webdriver.ChromeOptions()
            # keep browser visible (do not use headless)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # set window size
            target_width = int(screen_width / 3)
            target_height = int(screen_height)

            # options.add_argument("--headless=new") # run headless
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--window-size={target_width},{target_height}")
            options.add_argument("--window-position=0,0")

            self.driver = webdriver.Chrome(service=service, options=options)
            self.start_driver_watcher()

            self.driver.set_page_load_timeout(10)  # 10 ثانیه زمان برای get
            try:
                self.driver.get("https://www.nytimes.com/games/wordle/index.html")
                self.add_log("Chrome started and page requested.")
            except Exception as e:
                self.add_log(f"Page load took too long or failed: {e}")
                try:
                    self.driver.execute_script("window.stop();")
                    self.add_log("Forced stop sent to browser.")
                except Exception as e2:
                    self.add_log(f"Failed to force stop: {e2}")

            # if user pressed Stop meanwhile, stop
            if not self.running:
                self.add_log("Stopped by user before clicking buttons.")
                return

            # 1) Click "Accept all" (cookie consent) if present
            try:
                accept_btn = WebDriverWait(self.driver, 5).until(
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
                words_file = self.resource_path(os.path.join("assets", "words_sorted.txt"))
                with open(words_file, "r", encoding="utf-8") as f:
                    words = [w.strip() for w in f if w.strip()]

                analyzer = LetterFrequencyAnalyzer(words_file)
                analyzer.analyze()

                # --- start of replacement loop ---
                solver = WordleSolver(words)
                known_pattern = [None] * 5
                present_letters = set()
                excluded_letters = set()
                unknowns = []  # list of (index, letter) accumulated across attempts
                current_candidates = words[:]  # start with all words
                max_attempts = 6
                solved = False
                time.sleep(0.2)

                for attempt in range(1, max_attempts + 1):
                    # choose best guess from current candidates using analyzer
                    top = analyzer.suggest_best_words(word_list=current_candidates, top_n=1)
                    if not top:
                        self.add_log("No candidate for guessing. Stopping.")
                        break
                    guess = top[0][0]
                    self.add_log(f"Attempt {attempt}: guessing '{guess}'")

                    # send guess
                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        for ch in guess:
                            body.send_keys(ch)
                            time.sleep(0.12)
                        body.send_keys(Keys.ENTER)
                        self.add_log(f"Sent '{guess}' to page (typed into body).")
                    except Exception as e_send:
                        self.add_log(f"Failed to send guess '{guess}': {e_send}")
                        break

                    # wait for row element to appear
                    row_selector = f"div[aria-label='Row {attempt}']"
                    try:
                        row_elem = WebDriverWait(self.driver, 12).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, row_selector))
                        )
                    except Exception as e:
                        self.add_log(f"Row {attempt} element not found: {e}")
                        break

                    # wait until all tiles in this row have a final state (not 'tbd' or empty)
                    wait_start = time.time()
                    tiles = []
                    while time.time() - wait_start < 12:
                        tiles = row_elem.find_elements(By.CSS_SELECTOR, "div.Tile-module_tile__UWEHN")
                        if len(tiles) >= 5:
                            states = [t.get_attribute("data-state") or "" for t in tiles[:5]]
                            if all(s and ("tbd" not in s.lower()) for s in states):
                                break
                        time.sleep(0.18)
                    else:
                        self.add_log(f"Row {attempt} not ready (timeout).")
                        break

                    # read results
                    results = []
                    for t in tiles[:5]:
                        letter = (t.text or "").strip().lower()
                        state = t.get_attribute("data-state")
                        if not state:
                            aria = (t.get_attribute("aria-label") or "").lower()
                            if "correct" in aria:
                                state = "correct"
                            elif "present" in aria:
                                state = "present"
                            elif "absent" in aria:
                                state = "absent"
                        results.append({"letter": letter, "state": state})

                    self.add_log(f"Row {attempt} states: {results}")

                    # check win
                    if all(item["state"] == "correct" for item in results):
                        self.add_log(f"🎉 Solved! The word is '{guess}'.")
                        solved = True
                        self.translate_button.configure(state=tk.NORMAL)
                        self.last_solution = guess
                        break

                    # update knowledge: known_pattern, present_letters, excluded_letters, unknowns (accumulate)
                    # row_present = {item["letter"] for item in results if item["state"] == "present"}  # check this late TODO

                    for idx, item in enumerate(results):
                        l = item["letter"]
                        s = item["state"]
                        if not l:
                            continue
                        if s == "correct":
                            known_pattern[idx] = l
                            present_letters.add(l)
                            if l in excluded_letters:
                                excluded_letters.discard(l)
                        elif s == "present":
                            present_letters.add(l)
                            if l in excluded_letters:
                                excluded_letters.discard(l)
                            if (idx, l) not in unknowns:
                                unknowns.append((idx, l))
                        elif s == "absent":
                            # only add to excluded if we have no evidence that letter exists elsewhere
                            # (not present in any discovered present/correct and not in unknowns)
                            if (
                                (l not in present_letters)
                                and (l not in known_pattern)
                                and (not any(u[1] == l for u in unknowns))
                            ):
                                excluded_letters.add(l)

                    self.add_log(f"known_pattern: {known_pattern}")
                    self.add_log(f"present_letters: {sorted(list(present_letters))}")
                    self.add_log(f"excluded_letters: {sorted(list(excluded_letters))}")
                    self.add_log(f"unknowns (accumulated): {unknowns}")

                    # filter candidates using accumulated constraints
                    current_candidates = solver.filter_candidates(known_pattern, unknowns, list(excluded_letters))
                    self.add_log(f"Candidates left: {len(current_candidates)}")

                    if not current_candidates:
                        self.add_log("No candidates left. Stopping.")
                        break

                    # small delay before next attempt
                    time.sleep(0.4)

                # end of attempts
                if not solved:
                    try:
                        # تلاش برای گرفتن متن کلمه روز از toast
                        toast_elem = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.Toast-module_toast__iiVsN"))
                        )
                        solution_word = (toast_elem.text or "").strip()
                        if solution_word:
                            self.last_solution = solution_word.lower()
                            self.add_log(f"❌ Solver failed. The correct word was: '{solution_word}'")
                            self.translate_button.configure(state=tk.NORMAL)
                        else:
                            self.add_log("Solver finished but no solution word was found in toast.")
                    except Exception as ex:
                        self.add_log(f"Solver finished (failed to find solution word). Error: {ex}")

                # --- remove ads and overlays ---
                try:
                    # wait for #loginPrompt-dialog to appear
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "loginPrompt-dialog")))
                    self.driver.execute_script(
                        """
                        let el = document.querySelector("#loginPrompt-dialog");
                        if (el) { el.remove(); }
                    """
                    )
                    self.add_log("Removed #loginPrompt-dialog from DOM.")
                except Exception as ex:
                    self.add_log(f"#loginPrompt-dialog not found or could not be removed: {ex}")

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[id^='lire-ui-']"))
                    )
                    self.driver.execute_script(
                        """
                        document.querySelectorAll("[id^='lire-ui-']").forEach(el => el.remove());
                    """
                    )
                    self.add_log("Removed all elements with id starting with 'lire-ui-'.")
                except Exception as ex:
                    self.add_log(f"No elements with id starting with 'lire-ui-' found or could not be removed: {ex}")
                # --- end of replacement loop ---

            except Exception as ex_first:
                self.add_log(f"Error during solving loop: {ex_first}")

                # time.sleep(3)
                # page_html = self.driver.page_source
                # with open("debug_page.html", "w", encoding="utf-8") as f:
                #     f.write(page_html)
                # self.add_log("Saved debug_page.html for inspection.")

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
        finally:
            self.check_driver()

        # do NOT quit the driver here on success — leave it open so Stop button can close it later

    def translate_word(self):
        """Shows a translation of the last solved word from English to Farsi (Persian).
        If no solution is available yet, shows a message box with an appropriate message.
        Uses the free MyMemory Translation API (https://mymemory.translated.net/doc/).
        The translation is attempted in a separate request and will be None if the request
        fails or times out (6 seconds).
        """
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
        """
        Opens a donation window with options to support the project.
        """

        top = tk.Toplevel(self)
        top.title("Donate ❤")
        top.resizable(False, False)

        # Center the window
        top.withdraw()
        top.iconphoto(False, self.icon)
        top.update_idletasks()
        width, height = 550, 300
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

        top.grab_set()
        top.transient(self)

        # ==== Layout starts ====

        # Donate image (clickable)
        donate_img = tk.PhotoImage(file=self.resource_path(os.path.join("assets", "donate.png")))
        donate_button = ttk.Label(top, image=donate_img, cursor="hand2")
        donate_button.grid(row=0, column=0, columnspan=2, pady=(30, 20))
        donate_button.image = donate_img
        top.deiconify()

        def open_link(event):
            """
            Opens the donation link in a web browser when the donate button is clicked.
            The link is: http://www.coffeete.ir/Titan
            """
            webbrowser.open_new("http://www.coffeete.ir/Titan")

        donate_button.bind("<Button-1>", open_link)

        # USDT Label
        usdt_label = ttk.Label(top, text="USDT (Tether) – TRC20 Wallet Address :", font=("Segoe UI", 10, "bold"))
        usdt_label.grid(row=1, column=0, columnspan=2, pady=(30, 5), sticky="w", padx=20)

        # Entry field (readonly)
        wallet_address = "TGoKk5zD3BMSGbmzHnD19m9YLpH5ZP8nQe"
        wallet_entry = ttk.Entry(top, width=40)
        wallet_entry.insert(0, wallet_address)
        wallet_entry.configure(state="readonly")
        wallet_entry.grid(row=2, column=0, padx=(20, 10), pady=5, sticky="ew")

        # Copy button
        copy_btn = ttk.Button(top, text="Copy")
        copy_btn.grid(row=2, column=1, padx=(0, 20), pady=5, sticky="w")

        tooltip = None

        def copy_wallet():
            """
            Copies the wallet address to the clipboard and shows a tooltip notification.
            The notification is automatically hidden after 2 seconds using the `after` method.
            """

            nonlocal tooltip
            self.clipboard_clear()
            self.clipboard_append(wallet_address)
            self.update()

            if tooltip:
                tooltip.hidetip()
                tooltip = None

            tooltip = Hovertip(copy_btn, "Copied to clipboard!")
            tooltip.showtip()

            def hide_tip():
                """
                Hides the tooltip notification created by `copy_wallet`.
                """

                if tooltip:
                    tooltip.hidetip()

            top.after(2000, hide_tip)

        copy_btn.configure(command=copy_wallet)

        # Make the first column expand
        top.grid_columnconfigure(0, weight=1)


if __name__ == "__main__":
    app = WordleApp()
    app.mainloop()
