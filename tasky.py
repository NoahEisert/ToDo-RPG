import sqlite3
from datetime import datetime, timedelta
from nicegui import ui
from PIL import Image

# SQLite-Datenbank initialisieren (nur beim ersten Start)
def init_db():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (name TEXT PRIMARY KEY, profile_picture TEXT, user_class TEXT, user_race TEXT, experience INTEGER, level INTEGER, gold INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, difficulty TEXT, due_date TEXT, status TEXT DEFAULT 'offen', user_name TEXT,
                  FOREIGN KEY(user_name) REFERENCES users(name))''')
    conn.commit()
    conn.close()

class User:
    def __init__(self, name, profile_picture='', user_class=None, user_race=None, experience=0, level=1, gold=0):
        self.name = name
        self.profile_picture = profile_picture or 'default-profile.jpg'
        self.user_class = user_class
        self.user_race = user_race
        self.experience = experience
        self.level = level
        self.gold = gold

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
        c.execute('''INSERT OR REPLACE INTO users (name, profile_picture, user_class, user_race, experience, level, gold) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                  (self.name, self.profile_picture, self.user_class, self.user_race, self.experience, self.level, self.gold))
        conn.commit()
        conn.close()

class TaskManager:
    def __init__(self):
        self.load_tasks()

    def load_tasks(self):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tasks")
        self.tasks = c.fetchall()
        conn.close()

    def get_tasks(self, user_name, status):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE status = ? AND user_name = ?", (status, user_name))
        tasks = c.fetchall()
        conn.close()
        return tasks

    def add_task(self, name, difficulty, due_date, user_name):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('''INSERT INTO tasks (name, difficulty, due_date, status, user_name) VALUES (?, ?, ?, 'offen', ?)''',
                  (name, difficulty, due_date, user_name))
        conn.commit()
        conn.close()
        self.load_tasks()

    def complete_task(self, task_id):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = 'erledigt' WHERE id = ?", (task_id,))
        c.execute("SELECT difficulty FROM tasks WHERE id = ?", (task_id,))
        difficulty = c.fetchone()[0]
        conn.commit()
        conn.close()
        self.load_tasks()
        return difficulty

    def delete_task(self, task_id):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_tasks()

class TaskApp:
    def __init__(self):
        self.user = None
        self.task_manager = TaskManager()
        self.buttons_disabled = {
            "login": False,
            "save_profile": False
        }
        self.text_elements = []  # Liste, um UI-Elemente zu speichern, die gelöscht werden sollen
        self.tasks_elements = []  # Liste, um die Aufgabenanzeigen zu speichern, die gelöscht werden sollen

    def load_user(self, name):
        if self.buttons_disabled["login"]:
            ui.notify("Login wurde bereits abgeschlossen.")
            return
        self.user = User.load_user(name)
        if not self.user:
            self.user = User(name)
            self.user.save_to_db()
        self.buttons_disabled["login"] = True
        self.update_user_info()
        ui.notify(f"Willkommen, {self.user.name}!")

    def update_user_class_race(self, user_class, user_race):
        if self.buttons_disabled["save_profile"]:
            ui.notify("Profil wurde bereits gespeichert.")
            return
        if self.user:
            self.user.user_class = user_class
            self.user.user_race = user_race
            self.user.save_to_db()
            self.buttons_disabled["save_profile"] = True
            self.update_user_info()
            ui.notify("Klasse und Rasse erfolgreich aktualisiert.")

    def update_user_info(self):
        # Nur aktualisieren, wenn der Benutzer existiert
        if self.user:
            with ui.row():
                ui.image(f"{self.user.profile_picture}")  # Profilbild anzeigen
                with ui.column() as column:
                    ui.label(f"Name: {self.user.name}")
                    ui.label(f"Profilbild: {self.user.profile_picture}")  # Pfad des Profilbildes
                    ui.label(f"Klasse: {self.user.user_class}")
                    ui.label(f"Rasse: {self.user.user_race}")
                    ui.label(f"Level: {self.user.level}")
                    ui.label(f"Gold: {self.user.gold}")  # Gold anzeigen
                self.text_elements.append(column)  # Speichere die textbasierte UI-Komponente

    def add_experience(self, points):
        if self.user:
            self.user.experience += points
            while self.user.experience >= self.user.level * 5:
                self.user.level += 1
                self.user.experience -= self.user.level * 5
                self.user.gold += 20  # 20 Gold pro Level-Up
                ui.notify(f"Level {self.user.level} erreicht! Glückwunsch! Du hast 20 Gold erhalten!",type="info")
            self.user.save_to_db()

    def add_task(self, name, difficulty, due_date):
        if self.user:
            self.task_manager.add_task(name, difficulty, due_date, self.user.name)
            ui.notify(f"Aufgabe '{name}' hinzugefügt!")  # Nur Benachrichtigung über die hinzugefügte Aufgabe

    def complete_task(self, task_name):
        if self.user:
            tasks = self.task_manager.get_tasks(self.user.name, 'offen')
            task_id = next((task[0] for task in tasks if task[1] == task_name), None)
            if task_id:
                difficulty = self.task_manager.complete_task(task_id)
                points = {"leicht": 1, "mittel": 2, "schwer": 3}.get(difficulty, 0)
                self.add_experience(points)
                ui.notify("Aufgabe abgeschlossen!")
            else:
                ui.notify("Aufgabe nicht gefunden!")

    def delete_task(self, task_name):
        if self.user:
            tasks = self.task_manager.get_tasks(self.user.name, 'offen')
            task_id = next((task[0] for task in tasks if task[1] == task_name), None)
            if task_id:
                self.task_manager.delete_task(task_id)
                ui.notify("Aufgabe gelöscht!")
            else:
                ui.notify("Aufgabe nicht gefunden!")

    def clear_ui(self):
        # Lösche nur die Text-Labels und Text-Inhalte
        for element in self.text_elements:
            element.clear()  # Lösche die textbasierte UI-Komponente
        self.text_elements.clear()  # Lösche die Liste der Text-UI-Elemente

        # Lösche auch die Aufgabenanzeigen
        for tasks in self.tasks_elements:
            tasks.clear()  # Lösche die Anzeige der Aufgaben
        self.tasks_elements.clear()  # Lösche die Liste der Aufgabenanzeigen

    def display_open_tasks(self):
        open_tasks = self.task_manager.get_tasks(self.user.name, 'offen')

        with ui.column() as tasks_column:
            ui.label("Offene Aufgaben:")
            for task in open_tasks:
                ui.label(f"{task[1]} - {task[2]} (Fällig: {task[3]})")
            self.tasks_elements.append(tasks_column)  # Speichere die Aufgabenanzeige

    def display_completed_tasks(self):
        completed_tasks = self.task_manager.get_tasks(self.user.name, 'erledigt')

        with ui.column() as tasks_column:
            ui.label("Abgeschlossene Aufgaben:")
            for task in completed_tasks:
                ui.label(f"{task[1]} - {task[2]} (Erledigt)")
            self.tasks_elements.append(tasks_column)  # Speichere die Aufgabenanzeige

def main():
    init_db()
    app = TaskApp()

    ui.label("DONERIGHT-Ihre Management Software")

    with ui.row():
        user_name_input = ui.input("Name eingeben:")
        ui.button("Bestätigen", on_click=lambda: app.load_user(user_name_input.value))

    with ui.row():
        user_class = ui.select(["Kämpfer", "Sprinter", "Arzt", "CEO"], label="Klasse")
        user_race = ui.select(["Mensch", "Elf", "Zwerg", "Ork"], label="Rasse")

        def select_profile_picture():
            def on_file_selected(e):
                if e.files:
                    file = e.files[0]
                    # Konvertiere das Bild zu JPG
                    img = Image.open(file)
                    file_path = f"images/{app.user.name}_profile.jpg"
                    img.convert('RGB').save(file_path, "JPEG")
                    app.user.profile_picture = file_path
                    app.user.save_to_db()  # Speichere das Profilbild in der Datenbank
                    app.update_user_info()  # Aktualisiere die Benutzerinfo
                    ui.notify("Profilbild aktualisiert!")

            ui.upload(on_upload=on_file_selected).open()

        ui.button("Profilbild auswählen", on_click=select_profile_picture)
        ui.button("Speichern", on_click=lambda: app.update_user_class_race(user_class.value, user_race.value))

    with ui.column():
        task_name_input = ui.input("Aufgabenname:")
        task_due_date = ui.input("Fälligkeitsdatum (DD-MM-YYYY):", value=(datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y"))

        with ui.row():
            ui.button("Leicht", on_click=lambda: app.add_task(task_name_input.value, "leicht", task_due_date.value), color="green")
            ui.button("Mittel", on_click=lambda: app.add_task(task_name_input.value, "mittel", task_due_date.value), color="yellow")
            ui.button("Schwer", on_click=lambda: app.add_task(task_name_input.value, "schwer", task_due_date.value), color="red")

        # Eingabefeld für das Erledigen oder Löschen von Aufgaben
        task_action_input = ui.input("Aufgabenname eingeben:")

        with ui.row():
            ui.button("Aufgabe erledigen", on_click=lambda: app.complete_task(task_action_input.value), color="green")
            ui.button("Aufgabe löschen", on_click=lambda: app.delete_task(task_action_input.value), color="red")
            ui.button("Clear", on_click=lambda: app.clear_ui(), color="blue")  # Clear-Knopf zum Löschen der UI

        # Knöpfe zum Anzeigen von offenen und erledigten Aufgaben nebeneinander
        with ui.row():
            ui.button("Offene Aufgaben anzeigen", on_click=app.display_open_tasks)
            ui.button("Abgeschlossene Aufgaben anzeigen", on_click=app.display_completed_tasks)

if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run()
