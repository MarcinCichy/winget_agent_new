import os
import shutil
import subprocess
import tempfile
import logging
from datetime import datetime
from zoneinfo import ZoneInfo


class AgentGenerator:
    """Klasa odpowiedzialna za generowanie pliku agent.exe."""

    def __init__(self, template_content):
        self.template = template_content

    def generate_exe(self, config: dict):
        if not shutil.which("pyinstaller"):
            logging.error("Program 'pyinstaller' nie jest zainstalowany lub nie ma go w ścieżce PATH.")
            raise FileNotFoundError("PyInstaller nie jest dostępny na serwerze.")

        winget_path = config.get('winget_path', '').replace('\\', '\\\\')

        final_agent_code = self.template \
            .replace('__API_ENDPOINT_1__', config.get('api_endpoint_1', '')) \
            .replace('__API_ENDPOINT_2__', config.get('api_endpoint_2', '')) \
            .replace('__API_KEY__', config.get('api_key', '')) \
            .replace('__LOOP_INTERVAL__', str(config.get('loop_interval', 60))) \
            .replace('__REPORT_INTERVAL__', str(config.get('report_interval', 3600))) \
            .replace('__WINGET_PATH__', winget_path)

        build_dir = tempfile.mkdtemp(prefix="winget-agent-build-")
        script_path = os.path.join(build_dir, "agent_service.py")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(final_agent_code)

        command = [
            "pyinstaller", "--onefile",
            "--hidden-import=win32timezone",
            "--name", "agent",
            script_path
        ]

        logging.info(f"Uruchamianie PyInstaller w katalogu: {build_dir}")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8',
                                    cwd=build_dir)
            logging.info(f"PyInstaller output: {result.stdout}")

            output_exe_path = os.path.join(build_dir, 'dist', 'agent.exe')
            if not os.path.exists(output_exe_path):
                raise FileNotFoundError(f"PyInstaller nie stworzył pliku agent.exe. Log: {result.stderr}")

            return output_exe_path

        except subprocess.CalledProcessError as e:
            logging.error(f"Błąd kompilacji PyInstaller: {e.stderr}")
            shutil.rmtree(build_dir, ignore_errors=True)
            raise


class ReportGenerator:
    """Klasa do generowania treści raportów tekstowych."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def _to_local_time(self, utc_dt):
        if not utc_dt: return "N/A"
        try:
            if isinstance(utc_dt, str):
                utc_dt = datetime.fromisoformat(str(utc_dt).split('.')[0])

            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
            local_dt = utc_dt.astimezone(ZoneInfo("Europe/Warsaw"))
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return str(utc_dt)

    def generate_report_content(self, computer_ids):
        content = []
        for cid in computer_ids:
            details = self.db_manager.get_computer_details_by_id(cid)
            if not details: continue

            # Ujednolicamy strukturę danych, aby pasowała do `get_report_details`
            unified_data = {
                'report': details['computer'],
                'apps': details['apps'],
                'updates': details['updates']
            }
            content.append(self.generate_single_report_content(unified_data))
        return "\n\n".join(content)

    def generate_single_report_content(self, details):
        report_info = details['report']
        apps = details['apps']
        updates = details['updates']

        hostname = report_info['hostname']
        ip_address = report_info['ip_address']

        content = []
        content.append(f"# RAPORT DLA KOMPUTERA: {hostname} ({ip_address})")

        # Czas raportu będzie w kluczu 'report_timestamp' (z historii) lub 'last_report' (dla bieżącego)
        report_time = report_info['report_timestamp'] if 'report_timestamp' in report_info.keys() else report_info[
            'last_report']
        content.append(f"Data raportu: {self._to_local_time(report_time)}")
        content.append(
            f"Data wygenerowania pliku: {datetime.now(ZoneInfo('Europe/Warsaw')).strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("")

        if updates:
            content.append("## Oczekujące aktualizacje w raporcie:")
            for item in updates:
                if item['update_type'] == 'OS':
                    content.append(f"* [SYSTEM] {item['name']} ({item['app_id']})")
                else:
                    content.append(
                        f"* [APLIKACJA] {item['name']}: {item['current_version']} -> {item['available_version']}")
        else:
            content.append("## Brak oczekujących aktualizacji w raporcie.")

        content.append("\n" + "=" * 30 + "\n")

        if apps:
            content.append("## Zainstalowane aplikacje w raporcie:")
            for app in apps:
                content.append(f"* {app['name']} (Wersja: {app['version']})")
        else:
            content.append("## Brak zainstalowanych aplikacji w raporcie.")

        content.append("\n" + "=" * 80)
        return "\n".join(content)