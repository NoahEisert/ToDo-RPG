from datetime import datetime, timedelta
from nicegui import ui
import os
import sqlite3
import atexit

# Initialize database connection and create tables if they don't exist
conn = sqlite3.connect('selected_images.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        points INTEGER DEFAULT 0
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS selected_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title_top TEXT,
        title_bottom TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        difficulty TEXT,
        points INTEGER,
        due_date DATE,
        due_time TIME,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
conn.commit()

# Global variables
logged_in_user_id = None
logged_in = False
selected_task_id = None  # Track the currently selected task for editing
container = ui.column().classes('items-center justify-center')

def login(username):
    global logged_in_user_id, logged_in
    cursor.execute('SELECT id, points FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    if user:
        logged_in_user_id = user[0]
        ui.notify(f'Welcome back, {username}!')
    else:
        cursor.execute('INSERT INTO users (username, points) VALUES (?, ?)', (username, 0))
        conn.commit()
        logged_in_user_id = cursor.lastrowid
        ui.notify(f'New user created: {username}')
    logged_in = True
    rebuild_ui()

def show_task_creation():
    container.clear()  # Clear previous content

    task_name_input = ui.input(label="Aufgabenname").style('width: 300px')
    date_input = ui.input(label="Datum", value=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")).style('width: 150px')
    time_input = ui.input(label="Uhrzeit", value="09:00").style('width: 100px')

    # Points selection buttons with an update for edit
    def add_or_update_task(difficulty=None, points=None):
        global selected_task_id
        task_name = task_name_input.value
        due_date = date_input.value
        due_time = time_input.value

        if selected_task_id:
            # Update task
            cursor.execute('''
                UPDATE tasks 
                SET name = ?, difficulty = ?, points = ?, due_date = ?, due_time = ? 
                WHERE id = ? AND user_id = ?
            ''', (task_name, difficulty, points, due_date, due_time, selected_task_id, logged_in_user_id))
            selected_task_id = None
            ui.notify(f"Task '{task_name}' updated.")
        else:
            # Insert new task
            cursor.execute('''
                INSERT INTO tasks (user_id, name, difficulty, points, due_date, due_time) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (logged_in_user_id, task_name, difficulty, points, due_date, due_time))
            conn.commit()
            
            # Update user points manually by retrieving, incrementing, and updating
            cursor.execute('SELECT points FROM users WHERE id = ?', (logged_in_user_id,))
            current_points = cursor.fetchone()[0]
            new_points = current_points + points
            cursor.execute('UPDATE users SET points = ? WHERE id = ?', (new_points, logged_in_user_id))
            conn.commit()
            
            # Check for level up
            if new_points >= 5:
                ui.notify(f"Du hast den nächsten Level erreicht!")
                new_points -= 5  # Reset points after leveling up
                cursor.execute('UPDATE users SET points = ? WHERE id = ?', (new_points, logged_in_user_id))
                conn.commit()

            ui.notify(f"Task '{task_name}' added with difficulty '{difficulty}' for {points} points.")

        update_task_list()  # Refresh task list
        rebuild_ui()  # Refresh UI in case of level up

    with container:
        with ui.row():
            ui.label("Aufgabe hinzufügen").style('font-weight: bold; font-size: 20px')
        task_name_input
        ui.label("Schwierigkeit:")
        with ui.row().classes('justify-center'):
            ui.button("Easy", on_click=lambda: add_or_update_task("Easy", 1)).style('margin-right: 10px')
            ui.button("Mittel", on_click=lambda: add_or_update_task("Mittel", 2)).style('margin-right: 10px')
            ui.button("Hard", on_click=lambda: add_or_update_task("Hard", 3))
        ui.label("Datum und Uhrzeit:")
        date_input
        time_input

    # Task list section
    task_list_column = ui.column().classes('items-center')
    with container:
        with ui.row().classes('justify-between'):
            ui.label("Tasks:").style('font-weight: bold; font-size: 20px')
        task_list_column

    def update_task_list():
        task_list_column.clear()
        cursor.execute('SELECT id, name, difficulty, due_date, due_time FROM tasks WHERE user_id = ?', (logged_in_user_id,))
        tasks = cursor.fetchall()
        for task in tasks:
            task_id, name, difficulty, due_date, due_time = task
            with task_list_column:
                with ui.row().classes('items-center'):
                    ui.label(f"{name} ({difficulty}): Due {due_date} at {due_time}")
                    ui.button("Edit", on_click=lambda t=task: load_task_for_edit(t)).style('margin-left: 10px')
                    ui.button("Delete", on_click=lambda t_id=task_id: delete_task(t_id)).style('margin-left: 5px')

    def load_task_for_edit(task):
        global selected_task_id
        selected_task_id, name, difficulty, due_date, due_time = task
        task_name_input.value = name
        date_input.value = due_date
        time_input.value = due_time
        ui.notify(f"Editing task '{name}'")

    def delete_task(task_id):
        cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, logged_in_user_id))
        conn.commit()
        ui.notify("Task deleted.")
        update_task_list()  # Refresh task list

    update_task_list()  # Load tasks on initial screen

def rebuild_ui():
    container.clear()
    if not logged_in:
        with container:
            username_input = ui.input(label='Username').style('width: 300px')
            ui.button('Login', on_click=lambda: login(username_input.value))
    else:
        show_task_creation()

def close_connection():
    conn.close()

atexit.register(close_connection)

rebuild_ui()
ui.run()

