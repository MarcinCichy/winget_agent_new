import os
import shutil
import subprocess
import tempfile
import logging
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import current_app
import zipfile


class AgentVersionService:
    """Klasa do zarządzania wersją agenta na serwerze w oparciu o plik version.txt."""

    def __init__(self):
        self.builds_dir = os.path.join(current_app.root_path, '..', 'agent_builds')
        self.agent_path = os.path.join(self.builds_dir, 'agent.exe')
        self.version_path = os.path.join(self.builds_dir, 'version.txt')
        os.makedirs(self.builds_dir, exist_ok=True)

    def get_server_agent_version(self) -> str:
        """Odczytuje wersję z pliku version.txt."""
        try:
            if os.path.exists(self.version_path):
                with open(self.version_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logging.error(f"Błąd odczytu pliku wersji: {e}")
        return "1.0.0"

    def get_suggested_next_version(self) -> str:
        """Sugeruje następny numer wersji przez inkrementację ostatniej cyfry."""
        current_version = self.get_server_agent_version()
        parts = current_version.split('.')
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except (ValueError, IndexError):
            return "1.0.1"

    def set_server_agent_version(self, new_version: str):
        """Zapisuje nową wersję do pliku version.txt."""
        try:
            with open(self.version_path, 'w') as f:
                f.write(new_version)
            logging.info(f"Ustawiono nową wersję agenta na serwerze: {new_version}")
        except Exception as e:
            logging.error(f"Błąd zapisu pliku wersji: {e}")

    def get_server_agent_info(self):
        """Zbiera kompletne informacje o agencie na serwerze."""
        version = self.get_server_agent_version()
        agent_info = {
            'version': version,
            'file_exists': False
        }
        if os.path.exists(self.agent_path):
            try:
                stat = os.stat(self.agent_path)
                agent_info.update({
                    'file_exists': True,
                    'name': 'agent.exe',
                    'size_kb': round(stat.st_size / 1024, 2),
                    'modified_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logging.error(f"Nie udało się odczytać metadanych pliku agenta: {e}")

        return agent_info


class AgentGenerator:
    """Klasa odpowiedzialna za generowanie PEŁNEGO PAKIETU agenta."""

    def __init__(self, template_content):
        self.template = template_content

    def generate_agent_bundle(self, config: dict):
        """Generuje agent.exe, ui_helper.exe, updater.exe i pakuje je do ZIP."""
        if not shutil.which("pyinstaller"):
            raise FileNotFoundError("PyInstaller nie jest dostępny na serwerze.")

        build_dir = tempfile.mkdtemp(prefix="winget-agent-build-")

        try:
            # --- Przygotowanie plików źródłowych ---
            agent_version = config.get('agent_version', '0.0.0')

            source_dir = os.path.join(current_app.root_path, '..')
            shutil.copy(os.path.join(source_dir, 'ui_helper.py'), build_dir)
            shutil.copy(os.path.join(source_dir, 'updater.py'), build_dir)

            try:
                error_definitions_path = os.path.join(source_dir, 'error_definitions.json')
                with open(error_definitions_path, 'r', encoding='utf-8') as f:
                    errors_obj = json.load(f)
                    errors_code_string = str(errors_obj)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logging.error(f"Nie udało się załadować pliku error_definitions.json: {e}")
                errors_code_string = "[]"

            final_agent_code = self.template \
                .replace('__API_ENDPOINT_1__', config.get('api_endpoint_1', '')) \
                .replace('__API_ENDPOINT_2__', config.get('api_endpoint_2', '')) \
                .replace('__API_KEY__', config.get('api_key', '')) \
                .replace('__AGENT_VERSION__', agent_version) \
                .replace('__LOOP_INTERVAL__', str(config.get('loop_interval', 60))) \
                .replace('__REPORT_INTERVAL__', str(config.get('report_interval', 3600))) \
                .replace('__WINGET_PATH__', config.get('winget_path', '').replace('\\', '\\\\')) \
                .replace('__ERROR_DEFINITIONS_JSON__', errors_code_string)

            script_path = os.path.join(build_dir, "agent_service.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(final_agent_code)

            # --- Uruchomienie PyInstaller dla wszystkich komponentów ---
            logging.info("Rozpoczynanie budowania pakietu agenta...")
            common_args = ["--onefile", "--hidden-import=win32timezone"]

            # Agent i updater jako aplikacje konsolowe (bez okna)
            subprocess.run(["pyinstaller", *common_args, "--name", "agent", "agent_service.py"], check=True,
                           capture_output=True, text=True, cwd=build_dir)
            logging.info("agent.exe zbudowany pomyślnie.")
            subprocess.run(["pyinstaller", *common_args, "--name", "updater", "updater.py"], check=True,
                           capture_output=True, text=True, cwd=build_dir)
            logging.info("updater.exe zbudowany pomyślnie.")

            # UI Helper jako aplikacja bez konsoli (windowed)
            subprocess.run(["pyinstaller", *common_args, "--windowed", "--name", "ui_helper", "ui_helper.py"],
                           check=True, capture_output=True, text=True, cwd=build_dir)
            logging.info("ui_helper.exe zbudowany pomyślnie.")

            # --- Pakowanie do pliku ZIP ---
            dist_dir = os.path.join(build_dir, 'dist')
            zip_path = os.path.join(build_dir, f"WingetAgent_v{agent_version}.zip")

            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(os.path.join(dist_dir, 'agent.exe'), arcname='agent.exe')
                zf.write(os.path.join(dist_dir, 'ui_helper.exe'), arcname='ui_helper.exe')
                zf.write(os.path.join(dist_dir, 'updater.exe'), arcname='updater.exe')

            logging.info(f"Stworzono pakiet wdrożeniowy: {zip_path}")
            return zip_path

        except subprocess.CalledProcessError as e:
            logging.error(f"Błąd kompilacji PyInstaller: {e.stderr}")
            raise


class ReportGenerator:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def _to_local_time(self, utc_dt):
        if not utc_dt: return "N/A"
        try:
            if isinstance(utc_dt, str): utc_dt = datetime.fromisoformat(str(utc_dt).split('.')[0])
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"));
            return utc_dt.astimezone(ZoneInfo("Europe/Warsaw")).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return str(utc_dt)

    def generate_report_content(self, computer_ids):
        content = []
        for cid in computer_ids:
            details = self.db_manager.get_computer_details_by_id(cid)
            if details: content.append(self.generate_single_report_content(
                {'report': details['computer'], 'apps': details['apps'], 'updates': details['updates']}))
        return "\n\n".join(content)

    def generate_single_report_content(self, details):
        report_info, apps, updates = details['report'], details['apps'], details['updates']
        hostname, ip_address = report_info['hostname'], report_info['ip_address']
        content = [f"# RAPORT DLA KOMPUTERA: {hostname} ({ip_address})"]
        report_time = report_info['report_timestamp'] if 'report_timestamp' in report_info.keys() else report_info[
            'last_report']
        content.append(f"Data raportu: {self._to_local_time(report_time)}")
        content.append(
            f"Data wygenerowania pliku: {datetime.now(ZoneInfo('Europe/Warsaw')).strftime('%Y-%m-%d %H:%M:%S')}\n")
        if updates:
            content.append("## Oczekujące aktualizacje w raporcie:")
            for item in updates: content.append(f"* [SYSTEM] {item['name']} ({item['app_id']})" if item[
                                                                                                       'update_type'] == 'OS' else f"* [APLIKACJA] {item['name']}: {item['current_version']} -> {item['available_version']}")
        else:
            content.append("## Brak oczekujących aktualizacji w raporcie.")
        content.append("\n" + "=" * 30 + "\n")
        if apps:
            content.append("## Zainstalowane aplikacje w raporcie:")
            for app in apps: content.append(f"* {app['name']} (Wersja: {app['version']})")
        else:
            content.append("## Brak zainstalowanych aplikacji w raporcie.")
        content.append("\n" + "=" * 80)
        return "\n".join(content)