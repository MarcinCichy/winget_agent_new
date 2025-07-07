import sqlite3
import logging
import click
from flask import current_app, g
from flask.cli import with_appcontext


# --- Funkcje do zarządzania połączeniem ---

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Tworzy tabele w bazie danych na podstawie schematu."""
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Komenda CLI do czyszczenia i tworzenia nowej bazy danych."""
    init_db()
    click.echo('Zainicjowano bazę danych.')


def init_app(app):
    """Rejestruje funkcje zarządzania bazą danych w aplikacji."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


# --- Klasa Managera Bazy Danych ---

class DatabaseManager:
    """Klasa hermetyzująca wszystkie operacje na bazie danych."""

    def __init__(self):
        self.db = get_db()

    def _execute(self, query, params=(), commit=False):
        cursor = self.db.execute(query, params)
        if commit:
            self.db.commit()
        return cursor

    def get_all_computers(self):
        return self._execute(
            "SELECT id, hostname, ip_address, last_report, reboot_required FROM computers ORDER BY hostname COLLATE NOCASE").fetchall()

    def get_computer_details(self, hostname):
        computer = self._execute("SELECT * FROM computers WHERE hostname = ?", (hostname,)).fetchone()
        if not computer: return None

        latest_report = self._execute(
            "SELECT id FROM reports WHERE computer_id = ? ORDER BY report_timestamp DESC LIMIT 1",
            (computer['id'],)).fetchone()

        apps, updates = [], []
        if latest_report:
            report_id = latest_report['id']
            apps = self._execute(
                "SELECT name, version, app_id FROM applications WHERE report_id = ? ORDER BY name COLLATE NOCASE",
                (report_id,)).fetchall()
            updates = self._execute(
                "SELECT id, name, app_id, status, current_version, available_version, update_type FROM updates WHERE report_id = ? ORDER BY update_type, name COLLATE NOCASE",
                (report_id,)).fetchall()

        return {"computer": computer, "apps": apps, "updates": updates}

    def get_computer_history(self, hostname):
        computer = self._execute("SELECT * FROM computers WHERE hostname = ?", (hostname,)).fetchone()
        if not computer: return None
        reports = self._execute(
            "SELECT id, report_timestamp FROM reports WHERE computer_id = ? ORDER BY report_timestamp DESC",
            (computer['id'],)).fetchall()
        return {"computer": computer, "reports": reports}

    def save_report(self, data):
        hostname = data.get('hostname')
        logging.info(f"Przetwarzanie raportu od: {hostname}")

        try:
            # --- Zapis komputera i raportu (bez zmian) ---
            computer = self._execute("SELECT id FROM computers WHERE hostname = ?", (hostname,)).fetchone()
            if computer:
                computer_id = computer['id']
                self._execute(
                    "UPDATE computers SET ip_address = ?, reboot_required = ?, last_report = CURRENT_TIMESTAMP WHERE id = ?",
                    (data.get('ip_address'), data.get('reboot_required', False), computer_id))
            else:
                cursor = self._execute("INSERT INTO computers (hostname, ip_address, reboot_required) VALUES (?, ?, ?)",
                                       (hostname, data.get('ip_address'), data.get('reboot_required', False)))
                computer_id = cursor.lastrowid
            cursor = self._execute("INSERT INTO reports (computer_id) VALUES (?)", (computer_id,))
            report_id = cursor.lastrowid

            # --- Zapis aplikacji (bez zmian) ---
            apps_to_insert = [(report_id, app.get('name'), app.get('version'), app.get('id', 'N/A')) for app in
                              data.get('installed_apps', [])]
            if apps_to_insert:
                self.db.executemany("INSERT INTO applications (report_id, name, version, app_id) VALUES (?, ?, ?, ?)",
                                    apps_to_insert)

            # ### KLUCZOWA POPRAWKA - Zapis aktualizacji ###

            # 1. Przetwarzanie aktualizacji aplikacji z klucza 'available_app_updates'
            app_updates_to_insert = [
                (report_id, u.get('name'), u.get('id', 'N/A'), u.get('version'), u.get('available_version'), 'APP')
                for u in data.get('available_app_updates', [])
            ]
            if app_updates_to_insert:
                self.db.executemany(
                    "INSERT INTO updates (report_id, name, app_id, current_version, available_version, update_type) VALUES (?, ?, ?, ?, ?, ?)",
                    app_updates_to_insert)

            # 2. Przetwarzanie aktualizacji systemu z klucza 'pending_os_updates'
            os_updates_to_insert = [
                (report_id, u.get('Title'), u.get('KB', 'N/A'), 'N/A', 'N/A', 'OS')
                for u in data.get('pending_os_updates', []) if isinstance(u, dict)
            ]
            if os_updates_to_insert:
                self.db.executemany(
                    "INSERT INTO updates (report_id, name, app_id, current_version, available_version, update_type) VALUES (?, ?, ?, ?, ?, ?)",
                    os_updates_to_insert)

            self.db.commit()
            return True
        except sqlite3.Error as e:
            self.db.rollback()
            logging.error(f"Błąd transakcji podczas zapisu raportu od {hostname}: {e}", exc_info=True)
            return False

    def create_task(self, computer_id, command, payload, update_id=None):
        # Poprawka: payload powinien być zapisany jako JSON string
        json_payload = json.dumps(payload) if isinstance(payload, dict) else payload
        self._execute("INSERT INTO tasks (computer_id, command, payload) VALUES (?, ?, ?)",
                      (computer_id, command, json_payload), commit=True)
        if update_id:
            self._execute("UPDATE updates SET status = 'Oczekuje' WHERE id = ?", (update_id,), commit=True)

    def get_pending_tasks(self, hostname):
        computer = self._execute("SELECT id FROM computers WHERE hostname = ?", (hostname,)).fetchone()
        if not computer: return []

        tasks = self._execute("SELECT id, command, payload FROM tasks WHERE computer_id = ? AND status = 'oczekuje'",
                              (computer['id'],)).fetchall()
        if tasks:
            task_ids = [(t['id'],) for t in tasks]
            self.db.executemany("UPDATE tasks SET status = 'w toku', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                task_ids)
            self.db.commit()

        return [dict(row) for row in tasks]

    def update_task_status(self, task_id, status):
        self._execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, task_id),
                      commit=True)

    def get_computer_details_by_id(self, computer_id):
        computer = self._execute("SELECT * FROM computers WHERE id = ?", (computer_id,)).fetchone()
        if not computer: return None
        return self.get_computer_details(computer['hostname'])

    def get_report_details(self, report_id):
        report = self._execute(
            "SELECT r.id, r.report_timestamp, c.hostname, c.ip_address FROM reports r JOIN computers c ON r.computer_id = c.id WHERE r.id = ?",
            (report_id,)).fetchone()
        if not report: return None
        apps = self._execute(
            "SELECT name, version, app_id FROM applications WHERE report_id = ? ORDER BY name COLLATE NOCASE",
            (report_id,)).fetchall()
        updates = self._execute(
            "SELECT name, app_id, current_version, available_version, update_type FROM updates WHERE report_id = ? ORDER BY update_type, name COLLATE NOCASE",
            (report_id,)).fetchall()
        return {"report": report, "apps": apps, "updates": updates}