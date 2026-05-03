# 🚀 TaskView

**TaskView** is a lightweight, fast, and minimal desktop task manager built using Python, Flask, and PyWebView.
It is designed for **simplicity and speed**, focusing only on what matters: managing your tasks efficiently.

---

## ✨ Features

### 🧩 Core Features

* ➕ Add tasks quickly
* ✅ Mark tasks as complete
* 🔄 Drag & drop to reorder tasks
* 💾 Persistent storage using SQLite
* ⚡ Instant updates (no reload required)

---

### 🖥️ Desktop Mode (Special Feature)

* Separate **task-only window**
* Shows only tasks (no input UI clutter)
* Designed for:

  * Focus mode
  * Always-on screen usage
* Supports:

  * ✔ Mark complete
  * 🔄 Reorder tasks

---

### 🎨 UI & Experience

* Modern glass-style UI
* Smooth animations
* Responsive layout (resizable window)
* Clean and distraction-free

---

## 🛠️ Tech Stack

* Python
* Flask (Backend)
* SQLite (Database)
* PyWebView (Desktop App)
* HTML, CSS, JavaScript (Frontend)

---

## ⚙️ Installation

### 1. Clone or download the project

```bash
git clone <your-repo-url>
cd TaskView
```

---

### 2. Install dependencies

```bash
pip install flask pywebview werkzeug
```

---

## ▶️ Running the App

### Normal Mode (Main + Desktop window)

```bash
python taskview.py
```

---

### Desktop-Only Mode

```bash
python taskview.py --desktop
```

---

## 📦 Build EXE (Windows)

Using PyInstaller

### Basic Build

```bash
pyinstaller --clean --noconfirm --onefile --windowed taskview.py
```

---

### Optimized Build (Recommended)

```bash
pyinstaller --clean --noconfirm --onefile --windowed --strip --noupx taskview.py
```

---

### Desktop-Only EXE

```bash
pyinstaller --clean --noconfirm --onefile --windowed --name TaskViewDesktop taskview.py
```

Run:

```bash
dist\\TaskViewDesktop.exe --desktop
```

---

## 🚀 Auto Start on Boot (Windows)

1. Press `Win + R`
2. Type:

```text
shell:startup
```

3. Add shortcut of your `.exe` file

---

## 📂 Project Structure

```
TaskView/
│── taskview.py
│── tasks.db
│── dist/
│── build/
```

---

## 🧠 Design Philosophy

TaskView is intentionally:

* Minimal
* Fast
* No unnecessary features

It avoids complexity and focuses on:

> “Add → View → Complete → Done”

---

## 🔮 Future Improvements (Optional)

* Desktop widget mode (always-on-top)
* Cloud sync
* Notifications
* Keyboard shortcuts
* Mobile companion app

---

## 📜 License

This project is open-source and free to use.

---

## 🙌 Acknowledgment

Built with simplicity in mind to create a **distraction-free productivity experience**.

---
