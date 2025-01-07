import sqlite3

class User:
    def __init__(self, name, profile_picture, race, user_class, experience=0, level=1):
        """
        Initialisiert einen Nutzer mit einem Namen, Rasse, Klasse, Erfahrungspunkten und Level.
        """
        self.name = name
        self.race = race
        self.user_class = user_class
        self.experience = experience  #Startet mit 0 Erfahrungspunkten
        self.level = level             #Startet auf Level 1

    def add_experience(self, points):
        """
        Fügt dem Nutzer Erfahrungspunkte hinzu und überprüft, ob ein Levelaufstieg erfolgt.
        """
        self.experience += points
        print(f"{points} Erfahrungspunkte hinzugefügt. Gesamt: {self.experience} Punkte.")

        # Überprüfen, ob der Nutzer ein Level aufsteigt (pro 30 Erfahrungspunkte ein Level)
        while self.experience >= 30:
            self.level_up()

    def level_up(self):
        """
        Steigt ein Level auf und zieht 30 Erfahrungspunkte ab.
        """
        self.level += 1
        self.experience -= 30
        print(f"Herzlichen Glückwunsch! {self.name} ist nun Level {self.level}.")

    def save_to_db(self):
        """
        Speichert den Nutzer in die SQLite-Datenbank.
        """
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('''INSERT INTO users (name, profile_picture, race, user_class, experience, level)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (self.name, self.profile_picture, self.race, self.user_class, self.experience, self.level))
        conn.commit()
        conn.close()

    @staticmethod
    def load_user(name):
        """
        Lädt einen Nutzer aus der SQLite-Datenbank.
        """
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE name = ?', (name,))
        result = c.fetchone()
        conn.close()
        if result:
            return User(*result)
        else:
            return None
