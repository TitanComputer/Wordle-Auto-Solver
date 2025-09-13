# Wordle Auto-Solver

An automatic solver for the Wordle game, built with **TTK** and **Selenium**.  
This project demonstrates how a bot can interact with the Wordle web interface,  
analyze feedback, and automatically guess words until the puzzle is solved.

---

## ❓ What is Wordle?

[Wordle](https://www.nytimes.com/games/wordle/index.html) is a word-guessing game where the player has 6 attempts to guess a hidden 5-letter word.

After each guess, the game gives feedback about the correctness and position of each letter using color codes.

This tool helps users find possible answers based on the feedback from their previous guesses.

## ✨ Features
- 🚀 Fully automated Wordle gameplay inside Chrome
- 📖 Uses a curated dictionary (`words_sorted.txt`) for valid guesses
- 🧠 Smart filtering of candidates based on feedback:
  - **correct** → letter is correct and in the right position  
  - **present** → letter is correct but in the wrong position  
  - **absent** → letter is not in the word
- 📊 Letter frequency analysis to select the most probable guess
- 🔄 Iterates guesses until the solution is found or all six attempts are used
- 🤖 Auto-handles popups, ads, and dialogs during the game
- 📥 Downloadable `.exe` version (Windows only)

## 🖼️ Screenshots

<img width="1135" height="855" alt="Untitled2" src="https://github.com/user-attachments/assets/5d61c3dc-8530-49e5-b44a-8cf9b92cbdb6" />

### 🎬 Usage Guide (Video)

https://github.com/user-attachments/assets/a1b57cae-47f2-4a23-b7a0-f9c27a4b7ebe

## 📥 Download

You can download the latest compiled `.exe` version from the [Releases](https://github.com/TitanComputer/Wordle-Auto-Solver/releases/latest) section.  
No need to install Python — just download and run.

## ⚙️ Usage

If you're using the Python script:
```bash
python main.py
```
Or, run the Wordle-Auto-Solver.exe file directly if you downloaded the compiled version.

### 🖥️ How to Use the GUI

1. Launch the app (`python main.py` or `Wordle-Auto-Solver.exe`) then click "Start".  
2. Chrome opens on the left side and loads [Wordle](https://www.nytimes.com/games/wordle/index.html).  
3. The solver automatically:  
   - Closes popups/ads  
   - Enters the best first guess  
   - Reads feedback and refines candidates  
   - Repeats until solved or 6 tries are used  
4. The log shows progress, the solution 🎉, or failure after 6 attempts.  
5. Press **Stop** anytime to end the solver.  

---

## 📦 Dependencies

- Python 3.10 or newer
- `Selenium`
- Google Chrome (latest)
- ChromeDriver (matching your Chrome version)
- Recommended: Create a virtual environment

Standard libraries only (os, re, etc.)

If you're modifying and running the script directly and use additional packages (like requests or tkinter), install them via:
```bash
pip install -r requirements.txt
```

## 📁 Project Structure

```bash
wordle_auto_solver/
│
├── main.py                     # Main application entry point
├── solver.py                   # Application core logic
├── README.md                   # Project documentation
├── assets/
│   ├── icon.png                # Project icon
│   ├── words_sorted.txt        # Dictionary of sorted english words
│   ├── heart.png               # Heart Logo
│   ├── chromedriver.exe        # Chrome WebDriver for Selenium
│   └── donate.png              # Donate Picture
└── requirements.txt            # Python dependencies
```
## 🎨 Icon Credit
The application icon used in this project is sourced from [Flaticon](https://www.flaticon.com/free-icons/puzzle).

**Puzzle icon** created by [manshagraphics](https://www.flaticon.com/authors/manshagraphics) – [Flaticon](https://www.flaticon.com/)

## 🛠 Compiled with Nuitka and UPX
The executable was built using [`Nuitka`](https://nuitka.net/) and [`UPX`](https://github.com/upx/upx) for better performance and compactness, built automatically via GitHub Actions.

You can build the standalone executable using the following command:

```bash
.\venv\Scripts\python.exe -m nuitka --jobs=4 --enable-plugin=upx --upx-binary="YOUR PATH\upx.exe" --enable-plugin=multiprocessing --lto=yes --enable-plugin=tk-inter --windows-console-mode=disable --follow-imports --windows-icon-from-ico="assets/icon.png" --include-data-dir=assets=assets --include-data-files=assets/chromedriver.exe=assets/chromedriver.exe --python-flag=no_site,no_asserts,no_docstrings --onefile --standalone --msvc=latest --output-filename=Wordle-Auto-Solver main.py
```

## 🚀 CI/CD

The GitHub Actions workflow builds the binary on every release and attaches it as an artifact.

## 🤝 Contributing
Pull requests are welcome.
If you have suggestions for improvements or new features, feel free to open an issue.

## ☕ Support
If you find this project useful and would like to support its development, consider donating:

<a href="http://www.coffeete.ir/Titan"><img width="500" height="140" alt="buymeacoffee" src="https://github.com/user-attachments/assets/8ddccb3e-2afc-4fd9-a782-89464ec7dead" /></a>

## 💰 USDT (Tether) – TRC20 Wallet Address:

```bash
TGoKk5zD3BMSGbmzHnD19m9YLpH5ZP8nQe
```
Thanks a lot for your support! 🙏
