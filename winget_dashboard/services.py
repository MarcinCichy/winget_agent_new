# winget_dashboard/services.py
import os
import shutil
import subprocess
import tempfile
import logging
import json
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

        final_agent_code = self.template \
            .replace('__API_ENDPOINT_1__', config.get('api_endpoint_1', '')) \
            .replace('__API_ENDPOINT_2__', config.get('api_endpoint_2', '')) \
            .replace('__API_KEY__', config.get('api_key', '')) \
            .replace('__LOOP_INTERVAL__', str(config.get('loop_interval', 60))) \
            .replace('__REPORT_INTERVAL__', str(config.get('report_interval', 60))) \
            .replace('__WINGET_PATH__', config.get('winget_path', ''))

        build_dir = tempfile.mkdtemp(prefix="winget-agent-build-")
        script_path = os.path.join(build_dir, "agent_service.py")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(final_agent_code)

        command = [
            "pyinstaller", "--onefile", "--noconsole",
            "--hidden-import=win32timezone",
            "--name", "WingetAgentService",
            script_path
        ]

        logging.info(f"Uruchamianie PyInstaller w katalogu: {build_dir}")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8',
                                    cwd=build_dir)
            logging.info(f"PyInstaller output: {result.stdout}")

            output_exe_path = os.path.join(build_dir, 'dist', 'WingetAgentService.exe')
            if not os.path.exists(output_exe_path):
                raise FileNotFoundError(f"PyInstaller nie stworzył pliku .exe. Log: {result.stderr}")

            final_path = os.path.join(tempfile.gettempdir(), f"agent_{os.urandom(4).hex()}.exe")
            shutil.move(output_exe_path, final_path)

            return final_path

        except subprocess.CalledProcessError as e:
            logging.error(f"Błąd kompilacji PyInstaller: {e.stderr}")
            raise
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)


class ReportGenerator:
    """Klasa do generowania treści raportów tekstowych."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def _to_local_time(self, utc_str):
        if not utc_str: return "N/A"
        try:
            utc_dt = datetime.fromisoformat(str(utc_str).split('.')[0]).replace(tzinfo=ZoneInfo("UTC"))
            local_dt = utc_dt.astimezone(ZoneInfo("Europe/Warsaw"))
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return utc_str

    def generate_report_content(self, computer_ids):
        content = []
        for cid in computer_ids:
            details = self.db_manager.get_computer_details_by_id(cid)
            if not details: continue

            computer = details['computer']
            content.append(f"# RAPORT DLA KOMPUTERA: {computer['hostname']} ({computer['ip_address']})")
            content.append(
                f"Data wygenerowania: {datetime.now(ZoneInfo('Europe/Warsaw')).strftime('%Y-%m-%d %H:%M:%S')}")
            content.append("")

            updates = details['updates']
            if updates:
                content.append("## Oczekujące aktualizacje:")
                for item in updates:
                    content.append(f"* {item['name']}: {item['current_version']} -> {item['available_version']}")
            else:
                content.append("## Brak oczekujących aktualizacji.")

            content.append("\n" + "=" * 80 + "\n")
        return "\n".join(content)