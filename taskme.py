import sqlite3
from datetime import datetime
from nicegui import ui
from User import User
from Tasks import TaskManager

# SQLite Datenbank initialisieren (nur beim ersten Start)
def init_db():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (name TEXT PRIMARY KEY, profile_picture TEXT, race TEXT, user_class TEXT, experience INTEGER, level INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (name TEXT, difficulty TEXT, due_date TEXT, completed BOOLEAN, user_name TEXT, 
                  FOREIGN KEY(user_name) REFERENCES users(name))''')
    conn.commit()
    conn.close()

# Hauptanwendung
class TaskApp:
    def __init__(self):
        self.user = None
        self.task_manager = TaskManager()

    def load_user(self, name):
        self.user = User.load_user(name)
        if self.user is None:
            self.create_user(name)

    def create_user(self, name):
        profile_picture = ui.input("Gib das Profilbild des Nutzers ein (Pfad oder URL):").value
        race = ui.input("Gib die Rasse des Nutzers ein:").value
        user_class = ui.input("Gib die Klasse des Nutzers ein:").value
        self.user = User(name, profile_picture, race, user_class, experience=0, level=1)
        self.user.save_to_db()

    def add_experience(self, points):
        if self.user:
            self.user.experience += points
            self.check_level_up()
            self.user.save_to_db()

    def check_level_up(self):
        while self.user.experience >= self.user.level * 5:
            self.user.level += 1
            ui.notify(f"Gut gemacht! Du hast Level {self.user.level} erreicht.")

    def add_task(self, name, difficulty, due_date):
        try:
            due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            self.task_manager.add_task(name, difficulty, str(due_date), self.user)
        except ValueError:
            ui.notify("Ungültiges Datum. Bitte verwende das Format YYYY-MM-DD.")

    def complete_task(self, task_name):
        task = self.task_manager.complete_task(task_name, self.user)
        if task:
            points = 0
            if task.difficulty == 'leicht':
                points = 1
            elif task.difficulty == 'mittel':
                points = 2
            elif task.difficulty == 'schwer':
                points = 3
            self.add_experience(points)

#GUI aufbauen
def main():
    init_db()
    app = TaskApp()

    ui.label("Willkommen im Task Manager")
    user_name_input = ui.input("Gib deinen Namen ein:")

    def on_submit():
        user_name = user_name_input.value
        app.load_user(user_name)
        ui.notify(f"Willkommen, {user_name}!")

    ui.button("Bestätigen", on_click=on_submit)

#Aufgaben hinzufügen
    ui.label("Neue Aufgabe hinzufügen")
    task_name_input = ui.input("Aufgabenname:")
    difficulty_input = ui.input("Schwierigkeit (leicht/mittel/schwer):")
    due_date_input = ui.input("Fälligkeitsdatum (Format: YYYY-MM-DD):")

    def add_task():
        app.add_task(task_name_input.value, difficulty_input.value, due_date_input.value)
        ui.notify("Aufgabe hinzugefügt!")

    ui.button("Aufgabe hinzufügen", on_click=add_task)

    # Aufgabe als erledigt markieren
    ui.label("Aufgabe als erledigt markieren")
    complete_task_input = ui.input("Aufgabenname:")

    def complete_task():
        app.complete_task(complete_task_input.value)
        ui.notify("Aufgabe als erledigt markiert!")

    ui.button("Aufgabe erledigen", on_click=complete_task)

    # Aufgaben anzeigen
    ui.label("Aufgaben anzeigen")

    def show_tasks():
        tasks = app.task_manager.tasks
        ui.notify("Aufgaben:\\n" + "\\n".join([str(task) for task in tasks]))

    ui.button("Aufgaben anzeigen", on_click=show_tasks)

if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run()