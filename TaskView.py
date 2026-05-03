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


def normalize_positions():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id
            FROM tasks
            ORDER BY COALESCE(position, 2147483647) ASC, id ASC
        """).fetchall()

        for idx, row in enumerate(rows):
            conn.execute("UPDATE tasks SET position=? WHERE id=?", (idx, row["id"]))


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
            border: 1px solid var(--line);
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
            border: 1px solid var(--line);
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
            border: 1px solid var(--line);
            border-radius: 26px;
            backdrop-filter: blur(20px);
            box-shadow: var(--shadow);
            padding: 18px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 14px;
        }

        .stat {
            background: rgba(15,23,42,0.65);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 12px 14px;
            min-width: 0;
        }

        .stat .label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 6px;
        }

        .stat .value {
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.03em;
        }

        .list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 120px;
            max-height: calc(100vh - 220px);
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
            border: 1px solid var(--line);
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

        @media (max-width: 700px) {
            body { padding: 10px; }
            .panel { padding: 14px; border-radius: 22px; }
            .stats { grid-template-columns: 1fr; }
            .list { max-height: calc(100vh - 300px); }
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
            <div class="stats">
                <div class="stat">
                    <div class="label">Total</div>
                    <div id="statTotal" class="value">0</div>
                </div>
                <div class="stat">
                    <div class="label">Done</div>
                    <div id="statDone" class="value">0</div>
                </div>
                <div class="stat">
                    <div class="label">Pending</div>
                    <div id="statPending" class="value">0</div>
                </div>
            </div>

            <div id="tasksList" class="list"></div>

            <div class="hint">Drag the handle to reorder. Tick the box to complete.</div>
        </div>
    </div>

<script>
    const tasksList = document.getElementById("tasksList");
    const statTotal = document.getElementById("statTotal");
    const statDone = document.getElementById("statDone");
    const statPending = document.getElementById("statPending");

    let draggedTaskEl = null;

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    async function loadTasks() {
        const res = await fetch("/api/tasks");
        const tasks = await res.json();

        statTotal.textContent = tasks.length;
        statDone.textContent = tasks.filter(t => t.completed).length;
        statPending.textContent = tasks.filter(t => !t.completed).length;

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