import sqlite3
import logging
import click
from flask import current_app, g
from flask.cli import with_appcontext
import json


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None: db.close()


def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    db.commit()


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Zainicjowano bazę danych.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


class DatabaseManager:
    def __init__(self):
        self.db = get_db()

    def _execute(self, query, params=(), commit=False):
        cursor = self.db.execute(query, params)
        if commit: self.db.commit()
        return cursor

    def save_report(self, data):
        hostname = data.get('hostname')
        if not hostname:
            logging.error("Otrzymano raport bez nazwy hosta.")
            return None

        try:
            computer_cursor = self._execute("SELECT id FROM computers WHERE hostname = ? COLLATE NOCASE", (hostname,))
            computer = computer_cursor.fetchone()

            if not computer:
                default_keywords_raw = current_app.config['DEFAULT_BLACKLIST_KEYWORDS']
                default_keywords_list = [line.strip() for line in default_keywords_raw.strip().split('\n') if
                                         line.strip()]
                default_blacklist_str = ", ".join(default_keywords_list)

                self._execute(
                    "INSERT INTO computers (hostname, blacklist_keywords, ip_address, reboot_required) VALUES (?, ?, ?, ?)",
                    (hostname, default_blacklist_str, data.get('ip_address'), data.get('reboot_required', False)),
                    commit=True)

                computer_cursor = self._execute("SELECT id FROM computers WHERE hostname = ? COLLATE NOCASE",
                                                (hostname,))
                computer = computer_cursor.fetchone()

            computer_id = computer['id']

            self._execute(
                "UPDATE computers SET ip_address = ?, reboot_required = ?, last_report = CURRENT_TIMESTAMP WHERE id = ?",
                (data.get('ip_address'), data.get('reboot_required', False), computer_id)
            )

            report_cursor = self._execute("INSERT INTO reports (computer_id) VALUES (?)", (computer_id,))
            report_id = report_cursor.lastrowid

            apps_to_insert = [(report_id, app.get('name'), app.get('version'), app.get('id', 'N/A')) for app in
                              data.get('installed_apps', [])]
            if apps_to_insert:
                self.db.executemany("INSERT INTO applications (report_id, name, version, app_id) VALUES (?, ?, ?, ?)",
                                    apps_to_insert)

            app_updates_to_insert = [
                (report_id, u.get('name'), u.get('id', 'N/A'), u.get('version'), u.get('available_version'), 'APP') for
                u in data.get('available_app_updates', [])]
            if app_updates_to_insert:
                self.db.executemany(
                    "INSERT INTO updates (report_id, name, app_id, current_version, available_version, update_type) VALUES (?, ?, ?, ?, ?, ?)",
                    app_updates_to_insert)

            os_updates_to_insert = [
                (report_id, u.get('Title'), u.get('KB', 'N/A'), 'N/A', 'N/A', 'OS')
                for u in data.get('pending_os_updates', []) if isinstance(u, dict)]
            if os_updates_to_insert:
                self.db.executemany(
                    "INSERT INTO updates (report_id, name, app_id, current_version, available_version, update_type) VALUES (?, ?, ?, ?, ?, ?)",
                    os_updates_to_insert)

            self.db.commit()
            return computer_id
        except sqlite3.Error as e:
            self.db.rollback()
            logging.error(f"Błąd transakcji podczas zapisu raportu od {hostname}: {e}", exc_info=True)
            return None

    def update_computer_blacklist(self, hostname, new_blacklist):
        self._execute("UPDATE computers SET blacklist_keywords = ? WHERE hostname = ? COLLATE NOCASE",
                      (new_blacklist, hostname),
                      commit=True)
        logging.info(f"Zaktualizowano czarną listę dla komputera: {hostname}")

    def get_computer_blacklist(self, hostname):
        result = self._execute("SELECT blacklist_keywords FROM computers WHERE hostname = ? COLLATE NOCASE",
                               (hostname,)).fetchone()
        return result['blacklist_keywords'] if result else ""

    def get_all_computers(self):
        return self._execute(
            "SELECT id, hostname, ip_address, last_report, reboot_required FROM computers ORDER BY hostname COLLATE NOCASE").fetchall()

    def get_computer_details(self, hostname):
        computer = self._execute("SELECT * FROM computers WHERE hostname = ? COLLATE NOCASE", (hostname,)).fetchone()
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
                "SELECT id, name, app_id, current_version, available_version, update_type FROM updates WHERE report_id = ? ORDER BY update_type, name COLLATE NOCASE",
                (report_id,)).fetchall()
        return {"computer": computer, "apps": apps, "updates": updates}

    def get_computer_history(self, hostname):
        computer = self._execute("SELECT * FROM computers WHERE hostname = ? COLLATE NOCASE", (hostname,)).fetchone()
        if not computer: return None
        reports = self._execute(
            "SELECT id, report_timestamp FROM reports WHERE computer_id = ? ORDER BY report_timestamp DESC",
            (computer['id'],)).fetchall()
        return {"computer": computer, "reports": reports}

    def create_task(self, computer_id, command, payload):
        json_payload = json.dumps(payload) if isinstance(payload, dict) else payload
        cursor = self._execute("INSERT INTO tasks (computer_id, command, payload) VALUES (?, ?, ?)",
                               (computer_id, command, json_payload), commit=True)
        return cursor.lastrowid

    def get_pending_tasks(self, hostname):
        computer = self._execute("SELECT id FROM computers WHERE hostname = ? COLLATE NOCASE", (hostname,)).fetchone()
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
        if status in ['zakończone', 'błąd']:
            self._execute("DELETE FROM tasks WHERE id = ?", (task_id,), commit=True)
            logging.info(f"Usunięto zakończone/błędne zadanie o ID: {task_id}")
        else:
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

    def get_active_tasks_for_computer(self, computer_id, command_filter=None):
        query = "SELECT id, payload, status FROM tasks WHERE computer_id = ? AND status NOT IN ('zakończone', 'błąd')"
        params = [computer_id]
        if command_filter:
            query += " AND command = ?"
            params.append(command_filter)
        return self._execute(query, tuple(params)).fetchall()

    def delete_tasks(self, task_ids):
        if not task_ids:
            return
        placeholders = ','.join('?' for _ in task_ids)
        self._execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", task_ids, commit=True)
        logging.info(f"Usunięto zadania o ID: {task_ids}")

    # TA FUNKCJA BYŁA BRAKUJĄCA w jednej z poprzednich wersji
    def get_computer_tasks(self, computer_id):
        tasks = self._execute(
            "SELECT payload, status FROM tasks WHERE computer_id = ? AND status NOT IN ('zakończone', 'błąd')",
            (computer_id,)
        ).fetchall()
        return {row['payload']: row['status'] for row in tasks}

    # TA FUNKCJA BYŁA BRAKUJĄCA w Twoim pliku
    def get_task_status(self, task_id):
        result = self._execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        # Jeśli zadanie zostało usunięte (bo się zakończyło), zwróć 'zakończone'
        return result['status'] if result else "zakończone"