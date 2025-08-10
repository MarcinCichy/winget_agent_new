# Plik: updater.py

import sys
import os
import shutil
import time
import subprocess
import json
import logging
import zipfile
import tempfile

LOG_DIR = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), "WingetAgent")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - UPDATER - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "updater.log")),
        logging.StreamHandler()
    ]
)

try:
    import requests

    USE_REQUESTS = True
except ImportError:
    import urllib.request

    USE_REQUESTS = False


def report_status(endpoint, hostname, status, details=""):
    url = f"{endpoint.strip('/')}/api/agent/update_status"
    payload = {'hostname': hostname, 'status': status, 'details': details}
    logging.info(f"Raportowanie statusu do {url} z danymi: {payload}")
    try:
        if USE_REQUESTS:
            requests.post(url, json=payload, timeout=15)
        else:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=15)
        logging.info("Status zaraportowany pomyślnie.")
    except Exception as e:
        logging.error(f"BŁĄD podczas raportowania statusu: {e}")


def run_command(command):
    logging.info(f"Wykonywanie polecenia: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        logging.info(f"Polecenie zakończone sukcesem. Wynik: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Błąd wykonania polecenia: {e.stderr if e.stderr else e.stdout}")
        return False
    except Exception as e:
        logging.error(f"Krytyczny błąd wykonania polecenia: {e}")
        return False


def do_update(zip_path, service_name, hostname, api_endpoint):
    agent_dir = os.path.dirname(os.path.abspath(sys.executable))
    files_to_update = ["agent.exe", "ui_helper.exe"]  # updater.exe na razie nie aktualizujemy
    flag_path = os.path.join(agent_dir, "health_check.flag")

    logging.info(f"Rozpoczynanie procesu aktualizacji z pliku {zip_path}...")

    logging.info("Oczekiwanie 5 sekund na całkowite zamknięcie starej usługi...")
    time.sleep(5)

    try:
        # Krok 1: Utwórz backupy
        for filename in files_to_update:
            current_path = os.path.join(agent_dir, filename)
            backup_path = current_path + ".bak"
            if os.path.exists(current_path):
                logging.info(f"Tworzenie kopii zapasowej: {current_path} -> {backup_path}")
                shutil.copy(current_path, backup_path)

        # Krok 2: Rozpakuj i wgraj nowe pliki
        with tempfile.TemporaryDirectory() as temp_dir:
            logging.info(f"Rozpakowywanie archiwum do: {temp_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)

            for filename in files_to_update:
                source_path = os.path.join(temp_dir, filename)
                dest_path = os.path.join(agent_dir, filename)
                if os.path.exists(source_path):
                    logging.info(f"Instalowanie nowej wersji: {source_path} -> {dest_path}")
                    shutil.move(source_path, dest_path)
                else:
                    logging.warning(f"Pliku {filename} nie znaleziono w archiwum ZIP. Pomijanie.")

        # Krok 3: Utwórz flagę dla health check
        logging.info(f"Tworzenie flagi health check: {flag_path}")
        with open(flag_path, "w") as f:
            f.write("1")

        # Krok 4: Usuń pobrany plik ZIP
        os.remove(zip_path)

        # Krok 5: Uruchom nową usługę
        if run_command(["sc", "start", service_name]):
            logging.info("Aktualizacja (krok plikowy) zakończona. Agent uruchomiony w trybie weryfikacji.")
            report_status(api_endpoint, hostname, "sukces_oczekuje_na_potwierdzenie")
        else:
            raise RuntimeError("Nie udało się uruchomić nowej wersji usługi.")

    except Exception as e:
        logging.critical(f"Krytyczny błąd podczas aktualizacji: {e}. Próba wykonania rollbacku...")
        do_rollback(service_name, from_update_failure=True)
        report_status(api_endpoint, hostname, "błąd", f"Krytyczny błąd aktualizatora: {e}")


def do_rollback(service_name, from_update_failure=False):
    agent_dir = os.path.dirname(os.path.abspath(sys.executable))
    files_to_update = ["agent.exe", "ui_helper.exe"]
    flag_path = os.path.join(agent_dir, "health_check.flag")

    logging.warning("Inicjowanie procedury ROLLBACK!")
    if not from_update_failure:
        run_command(["sc", "stop", service_name])
        time.sleep(5)

    rollback_success = True
    for filename in files_to_update:
        current_path = os.path.join(agent_dir, filename)
        backup_path = current_path + ".bak"
        if not os.path.exists(backup_path):
            logging.error(f"Brak pliku kopii zapasowej dla {filename}! Nie można w pełni przywrócić stanu.")
            rollback_success = False
            continue

        if os.path.exists(current_path):
            os.remove(current_path)

        shutil.move(backup_path, current_path)
        logging.info(f"Plik {filename} został przywrócony z kopii zapasowej.")

    if os.path.exists(flag_path):
        os.remove(flag_path)

    if rollback_success:
        run_command(["sc", "start", service_name])
        logging.info("Usługa została uruchomiona na przywróconej wersji.")
    else:
        logging.critical("Rollback nie powiódł się w pełni. System może być w stanie niestabilnym!")


def do_cleanup():
    agent_dir = os.path.dirname(os.path.abspath(sys.executable))
    files_to_update = ["agent.exe", "ui_helper.exe"]
    logging.info("Rozpoczynanie czyszczenia po pomyślnej aktualizacji.")

    for filename in files_to_update:
        backup_path = os.path.join(agent_dir, filename + ".bak")
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
                logging.info(f"Plik kopii zapasowej {backup_path} został usunięty.")
            except Exception as e:
                logging.error(f"Nie udało się usunąć pliku kopii zapasowej {backup_path}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        service_name = sys.argv[2] if len(sys.argv) > 2 else "WingetDashboardAgent"
        do_rollback(service_name)
    elif len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
        do_cleanup()
    elif len(sys.argv) > 1 and sys.argv[1] == '--update-from-zip':
        if len(sys.argv) < 6:
            logging.error("Niewystarczająca liczba argumentów dla aktualizacji z ZIP.")
            sys.exit(1)
        zip_path, service_name, hostname, api_endpoint = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        do_update(zip_path, service_name, hostname, api_endpoint)
    else:
        logging.error(f"Nieprawidłowe polecenie lub liczba argumentów: {sys.argv}")
        sys.exit(1)