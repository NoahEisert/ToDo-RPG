import sqlite3
from datetime import datetime, timedelta
from nicegui import ui

# SQLite Datenbank initialisieren (nur beim ersten Start)
def init_db():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (name TEXT PRIMARY KEY, profile_picture TEXT, user_class TEXT, race TEXT, experience INTEGER, level INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, difficulty TEXT, due_date TEXT, status TEXT, user_name TEXT,
                  FOREIGN KEY(user_name) REFERENCES users(name))''')
    conn.commit()
    conn.close()

class User:
    def __init__(self, name, profile_picture, user_class, race, experience=0, level=1):
        self.name = name
        self.profile_picture = profile_picture
        self.user_class = user_class
        self.race = race
        self.experience = experience
        self.level = level

    @staticmethod
    def load_user(name):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE name = ?", (name,))
        row = c.fetchone()
        conn.close()
        if row:
            return User(*row)
        return None

    def save_to_db(self):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users (name, profile_picture, user_class, race, experience, level) 
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                  (self.name, self.profile_picture, self.user_class, self.race, self.experience, self.level))
        conn.commit()
        conn.close()

class TaskManager:
    def __init__(self):
        self.tasks = []
        self.load_tasks()

    def load_tasks(self):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tasks")
        self.tasks = c.fetchall()
        conn.close()

    def get_pending_tasks(self, user_name):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE status = 'offen' AND user_name = ?", (user_name,))
        pending_tasks = c.fetchall()
        conn.close()
        return pending_tasks

    def add_task(self, name, difficulty, due_date, user):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('''INSERT INTO tasks (name, difficulty, due_date, status, user_name) VALUES (?, ?, ?, ?, ?)''',
                  (name, difficulty, due_date, "offen", user.name))
        conn.commit()
        conn.close()
        self.load_tasks()

    def edit_task(self, task_id, new_name, new_difficulty, new_due_date):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('''UPDATE tasks SET name = ?, difficulty = ?, due_date = ? WHERE id = ?''',
                  (new_name, new_difficulty, new_due_date, task_id))
        conn.commit()
        conn.close()
        self.load_tasks()

    def delete_task(self, task_id):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_tasks()

    def complete_task(self, task_id):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = ? WHERE id = ?", ("erledigt", task_id))
        c.execute("SELECT difficulty FROM tasks WHERE id = ?", (task_id,))
        difficulty = c.fetchone()[0]
        conn.commit()
        conn.close()
        self.load_tasks()
        return difficulty

class TaskApp:
    def __init__(self):
        self.user = None
        self.task_manager = TaskManager()

    def load_user(self, name):
        self.user = User.load_user(name)
        if self.user is None:
            self.create_user(name)

    def create_user(self, name):
        profile_picture = ui.input("Profilbild (Pfad/URL):").value
        user_class = ui.input("Klasse:").value
        race = ui.select(["Zauberer", "Rapper", "Soldat", "Bettler"], label="Wähle deine Rasse").value
        self.user = User(name, profile_picture, user_class, race)
        self.user.save_to_db()

    def add_experience(self, points):
        if self.user:
            self.user.experience += points
            self.check_level_up()
            self.user.save_to_db()

    def check_level_up(self):
        while self.user.experience >= self.user.level * 5:
            self.user.level += 1
            ui.notify(f"Level {self.user.level} erreicht! Belohnung erhalten.")

    def add_task(self, name, difficulty, due_date):
        try:
            due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            self.task_manager.add_task(name, difficulty, str(due_date), self.user)
            ui.notify("Aufgabe hinzugefügt.")
        except ValueError:
            ui.notify("Ungültiges Datum. Format: YYYY-MM-DD.")

    def edit_task(self, task_id, new_name, new_difficulty, new_due_date):
        self.task_manager.edit_task(task_id, new_name, new_difficulty, new_due_date)
        ui.notify("Aufgabe bearbeitet.")

    def delete_task(self, task_id):
        self.task_manager.delete_task(task_id)
        ui.notify("Aufgabe gelöscht.")

    def complete_task(self, task_id):
        difficulty = self.task_manager.complete_task(task_id)
        points = {"leicht": 1, "mittel": 2, "schwer": 3}.get(difficulty, 0)
        self.add_experience(points)
        ui.notify("Aufgabe erledigt!")

    def show_pending_tasks(self):
        if self.user:
            pending_tasks = self.task_manager.get_pending_tasks(self.user.name)
            if pending_tasks:
                task_list = "\n".join([f"{task[0]}: {task[1]} ({task[2]} - bis {task[3]})" for task in pending_tasks])
                ui.notify(f"Offene Aufgaben:\n{task_list}")
            else:
                ui.notify("Keine offenen Aufgaben.")

def main():
    init_db()
    app = TaskApp()

    ui.label("Willkommen beim ToDoRPG")
    user_name_input = ui.input("Name eingeben:")

    def on_submit():
        user_name = user_name_input.value
        app.load_user(user_name)
        ui.notify(f"Willkommen, {user_name}!")

    ui.button("Bestätigen", on_click=on_submit)

    task_name_input = ui.input("Aufgabenname:")
    difficulty_input = ui.select(["leicht", "mittel", "schwer"], value="leicht", label="Schwierigkeit auswählen")
    due_date_input = ui.input("Fälligkeitsdatum (YYYY-MM-DD):", value=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

    def add_task():
        app.add_task(task_name_input.value, difficulty_input.value, due_date_input.value)

    ui.button("Aufgabe hinzufügen", on_click=add_task)

    task_id_input = ui.input("Aufgaben-ID:")

    def complete_task():
        app.complete_task(int(task_id_input.value))

    ui.button("Aufgabe erledigen", on_click=complete_task)

    def delete_task():
        app.delete_task(int(task_id_input.value))

    ui.button("Aufgabe löschen", on_click=delete_task)

    ui.button("Offene Aufgaben anzeigen", on_click=app.show_pending_tasks)

if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run()
