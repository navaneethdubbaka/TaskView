import sys
import threading
import sqlite3
from flask import Flask, request, jsonify, render_template_string
from werkzeug.serving import make_server
import webview

app = Flask(__name__)
DB_PATH = "tasks.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_positions():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id
            FROM tasks
            ORDER BY COALESCE(position, 2147483647) ASC, id ASC
        """).fetchall()

        for idx, row in enumerate(rows):
            conn.execute("UPDATE tasks SET position=? WHERE id=?", (idx, row["id"]))


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL DEFAULT 0
            )
        """)

        cols = [row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        if "completed" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN completed INTEGER NOT NULL DEFAULT 0")
        if "position" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN position INTEGER NOT NULL DEFAULT 0")

    normalize_positions()


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": bool(row["completed"]),
        "position": row["position"],
    }


MAIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskView</title>
    <style>
        :root{
            --bg1:#08111f;
            --bg2:#111d33;
            --card:rgba(15, 23, 42, 0.82);
            --line:rgba(148, 163, 184, 0.16);
            --text:#e5eefc;
            --muted:#94a3b8;
            --accent:#22d3ee;
            --accent2:#38bdf8;
            --shadow: 0 24px 70px rgba(0,0,0,0.36);
        }

        * { box-sizing: border-box; }

        html, body {
            margin: 0;
            min-height: 100%;
            font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at top, rgba(56,189,248,0.16), transparent 35%),
                linear-gradient(135deg, var(--bg1), var(--bg2));
        }

        body {
            min-height: 100vh;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 18px;
            overflow: auto;
        }

        .app {
            width: min(100%, 900px);
        }

        .hero {
            text-align: center;
            margin: 10px 0 22px;
        }

        .title {
            font-size: clamp(30px, 4vw, 42px);
            font-weight: 800;
            letter-spacing: -0.05em;
            margin: 0;
        }

        .subtitle {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 14px;
        }

        .panel {
            width: 100%;
            background: var(--card);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 26px;
            backdrop-filter: blur(20px);
            box-shadow: var(--shadow);
            padding: 20px;
        }

        .section-title {
            margin: 0 0 14px;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .form {
            display: flex;
            gap: 12px;
            align-items: center;
            background: rgba(15,23,42,0.92);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            padding: 12px;
        }

        .input {
            flex: 1;
            border: 0;
            outline: none;
            background: transparent;
            color: var(--text);
            font-size: 15px;
            padding: 8px 6px;
            min-width: 0;
        }

        .input::placeholder {
            color: #64748b;
        }

        .primary {
            border: 0;
            border-radius: 13px;
            padding: 11px 18px;
            color: #03111a;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            font-weight: 800;
            cursor: pointer;
            transition: transform 140ms ease, filter 140ms ease;
            flex: 0 0 auto;
        }

        .primary:hover {
            filter: brightness(1.04);
            transform: translateY(-1px);
        }

        .note {
            margin-top: 12px;
            color: var(--muted);
            font-size: 12px;
            text-align: center;
            line-height: 1.5;
        }

        .badge {
            display: inline-block;
            margin-top: 12px;
            padding: 7px 11px;
            border-radius: 999px;
            border: 1px solid rgba(56,189,248,0.25);
            background: rgba(15,23,42,0.58);
            color: #bae6fd;
            font-size: 12px;
        }

        @media (max-width: 700px) {
            body { padding: 12px; }
            .panel { padding: 16px; border-radius: 22px; }
            .form { flex-direction: column; align-items: stretch; }
            .primary { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="app">
        <div class="hero">
            <h1 class="title">TaskView</h1>
            <p class="subtitle">Add tasks here. Open the desktop window for task-only view.</p>
        </div>

        <div class="panel">
            <h2 class="section-title">Add a task</h2>
            <form id="taskForm" class="form">
                <input id="taskInput" class="input" name="title" type="text" placeholder="Type a task and press Enter..." autocomplete="off" />
                <button class="primary" type="submit">Add</button>
            </form>

            <div class="note">
                The desktop window shows only tasks. There you can mark them complete and reorder them.
            </div>

            <div class="badge">TaskView Desktop Mode is separate</div>
        </div>
    </div>

<script>
    const taskForm = document.getElementById("taskForm");
    const taskInput = document.getElementById("taskInput");

    taskForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const title = taskInput.value.trim();
        if (!title) {
            taskInput.focus();
            return;
        }

        const formData = new FormData();
        formData.append("title", title);

        const res = await fetch("/api/tasks", {
            method: "POST",
            body: formData
        });

        if (!res.ok) return;

        taskForm.reset();
        taskInput.focus();
    });

    taskInput.focus();
</script>
</body>
</html>
"""


DESKTOP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskView Desktop</title>
    <style>
        :root{
            --bg1:#08111f;
            --bg2:#111d33;
            --card:rgba(15, 23, 42, 0.82);
            --line:rgba(148, 163, 184, 0.16);
            --text:#e5eefc;
            --muted:#94a3b8;
            --accent:#22d3ee;
            --accent2:#38bdf8;
            --danger:#f87171;
            --shadow: 0 24px 70px rgba(0,0,0,0.36);
        }

        * { box-sizing: border-box; }

        html, body {
            margin: 0;
            min-height: 100%;
            font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at top, rgba(56,189,248,0.16), transparent 35%),
                linear-gradient(135deg, var(--bg1), var(--bg2));
        }

        body {
            min-height: 100vh;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 14px;
            overflow: auto;
        }

        .app {
            width: min(100%, 700px);
        }

        .hero {
            text-align: center;
            margin: 8px 0 16px;
        }

        .title {
            font-size: clamp(26px, 4vw, 38px);
            font-weight: 800;
            letter-spacing: -0.05em;
            margin: 0;
        }

        .subtitle {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 13px;
        }

        .panel {
            width: 100%;
            background: var(--card);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 26px;
            backdrop-filter: blur(20px);
            box-shadow: var(--shadow);
            padding: 18px;
        }

        .list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 120px;
            max-height: calc(100vh - 170px);
            overflow-y: auto;
            padding-right: 2px;
        }

        .empty {
            border: 1px dashed rgba(148,163,184,0.25);
            border-radius: 18px;
            padding: 26px;
            text-align: center;
            color: var(--muted);
            background: rgba(15,23,42,0.35);
        }

        .task {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 14px;
            border-radius: 18px;
            background: rgba(15,23,42,0.78);
            border: 1px solid rgba(148, 163, 184, 0.16);
            transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
            user-select: none;
        }

        .task:hover {
            background: rgba(15,23,42,0.92);
            border-color: rgba(56,189,248,0.22);
            transform: translateY(-1px);
        }

        .task.dragging {
            opacity: 0.45;
            transform: scale(0.99);
        }

        .handle {
            width: 22px;
            min-width: 22px;
            text-align: center;
            color: #7dd3fc;
            cursor: grab;
            user-select: none;
            font-size: 18px;
            line-height: 1;
            touch-action: none;
            flex: 0 0 auto;
        }

        .handle:active { cursor: grabbing; }

        .check {
            width: 18px;
            height: 18px;
            accent-color: var(--accent);
            cursor: pointer;
            flex: 0 0 auto;
        }

        .task-title {
            flex: 1;
            font-size: 15px;
            line-height: 1.4;
            word-break: break-word;
            min-width: 0;
        }

        .task.completed .task-title {
            text-decoration: line-through;
            color: #94a3b8;
            opacity: 0.75;
        }

        .hint {
            margin-top: 12px;
            color: var(--muted);
            font-size: 12px;
            text-align: center;
        }

        .ctx-menu {
            position: fixed;
            z-index: 9999;
            background: rgba(10, 18, 36, 0.98);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 12px;
            padding: 5px;
            min-width: 172px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.55);
            backdrop-filter: blur(20px);
            display: none;
        }

        .ctx-menu.visible {
            display: block;
        }

        .ctx-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 9px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            color: var(--text);
            transition: background 100ms ease, color 100ms ease;
            user-select: none;
            white-space: nowrap;
        }

        .ctx-item:hover {
            background: rgba(56, 189, 248, 0.13);
            color: var(--accent);
        }

        .ctx-item.danger { color: var(--danger); }

        .ctx-item.danger:hover {
            background: rgba(248, 113, 113, 0.12);
            color: var(--danger);
        }

        .ctx-sep {
            height: 1px;
            background: rgba(148, 163, 184, 0.14);
            margin: 4px 0;
        }

        .task-title[contenteditable="true"] {
            outline: none;
            background: rgba(56, 189, 248, 0.08);
            border-radius: 6px;
            padding: 2px 6px;
            border: 1px solid rgba(56, 189, 248, 0.32);
        }

        @media (max-width: 700px) {
            body { padding: 10px; }
            .panel { padding: 14px; border-radius: 22px; }
            .list { max-height: calc(100vh - 190px); }
        }
    </style>
</head>
<body>
    <div class="app">
        <div class="hero">
            <h1 class="title">TaskView</h1>
            <p class="subtitle">Desktop view: tasks only. Mark complete and reorder.</p>
        </div>

        <div class="panel">
            <div id="tasksList" class="list"></div>
            <div class="hint">Drag to reorder &middot; Tick to complete &middot; Right-click for more options</div>
        </div>
    </div>

    <div id="ctxMenu" class="ctx-menu" role="menu">
        <div class="ctx-item" id="ctxEdit">Edit title</div>
        <div class="ctx-item" id="ctxToggle">Mark complete</div>
        <div class="ctx-sep"></div>
        <div class="ctx-item danger" id="ctxDelete">Delete</div>
    </div>

<script>
    const tasksList = document.getElementById("tasksList");
    let draggedTaskEl = null;

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    async function loadTasks() {
        const res = await fetch("/api/tasks");
        const tasks = await res.json();

        if (!tasks.length) {
            tasksList.innerHTML = `
                <div class="empty">
                    No tasks yet. Add your first task from the main window.
                </div>
            `;
            return;
        }

        tasksList.innerHTML = tasks.map(task => `
            <div class="task ${task.completed ? 'completed' : ''}" data-id="${task.id}">
                <div class="handle" draggable="true" title="Drag to reorder">⋮⋮</div>

                <input
                    class="check"
                    type="checkbox"
                    ${task.completed ? 'checked' : ''}
                    onchange="toggleTask(${task.id})"
                    aria-label="Toggle task"
                >

                <div class="task-title">${escapeHtml(task.title)}</div>
            </div>
        `).join("");

        bindDragAndDrop();
    }

    function bindDragAndDrop() {
        const items = Array.from(tasksList.querySelectorAll(".task"));

        items.forEach(item => {
            const handle = item.querySelector(".handle");

            handle.addEventListener("dragstart", (e) => {
                draggedTaskEl = item;
                item.classList.add("dragging");
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", item.dataset.id);
            });

            handle.addEventListener("dragend", () => {
                item.classList.remove("dragging");
                draggedTaskEl = null;
            });

            item.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
            });

            item.addEventListener("drop", async (e) => {
                e.preventDefault();
                if (!draggedTaskEl || draggedTaskEl === item) return;

                const rect = item.getBoundingClientRect();
                const after = e.clientY > rect.top + rect.height / 2;

                if (after) {
                    item.after(draggedTaskEl);
                } else {
                    item.before(draggedTaskEl);
                }

                await saveOrder();
            });
        });
    }

    tasksList.addEventListener("dragover", (e) => {
        e.preventDefault();
    });

    tasksList.addEventListener("drop", async (e) => {
        if (!draggedTaskEl) return;
        const target = e.target.closest(".task");
        if (!target) {
            tasksList.appendChild(draggedTaskEl);
            await saveOrder();
        }
    });

    async function saveOrder() {
        const orderedIds = Array.from(tasksList.querySelectorAll(".task")).map(el => Number(el.dataset.id));
        await fetch("/api/tasks/reorder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ordered_ids: orderedIds })
        });
        await loadTasks();
    }

    async function toggleTask(id) {
        await fetch(`/api/tasks/${id}/toggle`, { method: "POST" });
        await loadTasks();
    }

    // ---- context menu ----
    const ctxMenu = document.getElementById("ctxMenu");
    let ctxTaskId = null;

    function showCtxMenu(x, y, taskId, completed) {
        ctxTaskId = taskId;
        document.getElementById("ctxToggle").textContent = completed ? "Mark incomplete" : "Mark complete";
        ctxMenu.style.left = x + "px";
        ctxMenu.style.top = y + "px";
        ctxMenu.classList.add("visible");
        const rect = ctxMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) ctxMenu.style.left = (x - rect.width) + "px";
        if (rect.bottom > window.innerHeight) ctxMenu.style.top = (y - rect.height) + "px";
    }

    function hideCtxMenu() {
        ctxMenu.classList.remove("visible");
        ctxTaskId = null;
    }

    tasksList.addEventListener("contextmenu", (e) => {
        const taskEl = e.target.closest(".task");
        if (!taskEl) return;
        e.preventDefault();
        showCtxMenu(e.clientX, e.clientY, Number(taskEl.dataset.id), taskEl.classList.contains("completed"));
    });

    document.addEventListener("click", (e) => { if (!ctxMenu.contains(e.target)) hideCtxMenu(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideCtxMenu(); });

    document.getElementById("ctxEdit").addEventListener("click", () => {
        const id = ctxTaskId;
        hideCtxMenu();
        const taskEl = tasksList.querySelector(`.task[data-id="${id}"]`);
        if (!taskEl) return;
        const titleEl = taskEl.querySelector(".task-title");
        const oldTitle = titleEl.textContent;
        titleEl.contentEditable = "true";
        titleEl.focus();
        const range = document.createRange();
        range.selectNodeContents(titleEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        async function commitEdit() {
            const newTitle = titleEl.textContent.trim();
            titleEl.contentEditable = "false";
            if (!newTitle || newTitle === oldTitle) { titleEl.textContent = oldTitle; return; }
            const fd = new FormData();
            fd.append("title", newTitle);
            await fetch(`/api/tasks/${id}/rename`, { method: "POST", body: fd });
            await loadTasks();
        }

        titleEl.addEventListener("blur", commitEdit, { once: true });
        titleEl.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); titleEl.blur(); }
            if (e.key === "Escape") { titleEl.textContent = oldTitle; titleEl.contentEditable = "false"; }
        });
    });

    document.getElementById("ctxToggle").addEventListener("click", async () => {
        const id = ctxTaskId;
        hideCtxMenu();
        await toggleTask(id);
    });

    document.getElementById("ctxDelete").addEventListener("click", async () => {
        const id = ctxTaskId;
        hideCtxMenu();
        await fetch(`/api/tasks/${id}/delete`, { method: "POST" });
        await loadTasks();
    });

    loadTasks();
    setInterval(loadTasks, 2000);
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(MAIN_HTML)


@app.route("/desktop")
def desktop():
    return render_template_string(DESKTOP_HTML)


@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title, completed, position
            FROM tasks
            ORDER BY COALESCE(position, 2147483647) ASC, id ASC
        """).fetchall()

    return jsonify([task_to_dict(row) for row in rows])


@app.route("/api/tasks", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    with get_db() as conn:
        last_pos = conn.execute("SELECT COALESCE(MAX(position), -1) FROM tasks").fetchone()[0]
        next_pos = int(last_pos) + 1
        conn.execute(
            "INSERT INTO tasks (title, completed, position) VALUES (?, 0, ?)",
            (title, next_pos)
        )

    return "", 204


@app.route("/api/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    with get_db() as conn:
        conn.execute("""
            UPDATE tasks
            SET completed = CASE WHEN completed = 1 THEN 0 ELSE 1 END
            WHERE id = ?
        """, (task_id,))
    return "", 204


@app.route("/api/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    normalize_positions()
    return "", 204


@app.route("/api/tasks/<int:task_id>/rename", methods=["POST"])
def rename_task(task_id):
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400
    with get_db() as conn:
        conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
    return "", 204


@app.route("/api/tasks/reorder", methods=["POST"])
def reorder_tasks():
    payload = request.get_json(silent=True) or {}
    ordered_ids = payload.get("ordered_ids", [])

    if not isinstance(ordered_ids, list):
        return jsonify({"error": "ordered_ids must be a list"}), 400

    with get_db() as conn:
        for pos, task_id in enumerate(ordered_ids):
            conn.execute(
                "UPDATE tasks SET position = ? WHERE id = ?",
                (pos, int(task_id))
            )

    return "", 204


class ServerThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


if __name__ == "__main__":
    init_db()
    server = ServerThread(app)
    server.start()

    desktop_only = "--desktop" in sys.argv

    if desktop_only:
        webview.create_window(
            "TaskView Desktop",
            "http://127.0.0.1:5000/desktop",
            width=520,
            height=760,
            min_size=(320, 240),
            resizable=True
        )
        webview.start()
    else:
        webview.create_window(
            "TaskView",
            "http://127.0.0.1:5000",
            width=900,
            height=620,
            min_size=(360, 260),
            resizable=True
        )
        webview.create_window(
            "TaskView Desktop",
            "http://127.0.0.1:5000/desktop",
            width=520,
            height=760,
            min_size=(320, 240),
            resizable=True
        )
        webview.start()

    server.shutdown()