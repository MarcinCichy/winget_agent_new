# Plik: updater.py (wersja z obsługą backupu i rollbacku)
import sys
import os
import shutil
import time
import subprocess
import json
import logging

# Konfiguracja logowania, aby było spójne z resztą systemu
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
        logging.error(f"Błąd wykonania polecenia: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Krytyczny błąd wykonania polecenia: {e}")
        return False


def do_update(args):
    service_pid_str, new_agent_path, current_agent_path, service_name, hostname, api_endpoint = args
    backup_path = current_agent_path + ".bak"
    flag_path = os.path.join(os.path.dirname(current_agent_path), "health_check.flag")

    logging.info(f"Rozpoczynanie procesu aktualizacji dla usługi '{service_name}'...")
    logging.info(f"Oczekiwanie 10 sekund na zamknięcie starej usługi (PID: {service_pid_str})...")
    time.sleep(10)

    try:
        # 1. Utwórz backup starego agenta
        if os.path.exists(current_agent_path):
            logging.info(f"Tworzenie kopii zapasowej: {current_agent_path} -> {backup_path}")
            shutil.move(current_agent_path, backup_path)

        # 2. Wgraj nowego agenta
        logging.info(f"Instalowanie nowej wersji: {new_agent_path} -> {current_agent_path}")
        shutil.move(new_agent_path, current_agent_path)

        # 3. Utwórz flagę dla health check
        logging.info(f"Tworzenie flagi health check: {flag_path}")
        with open(flag_path, "w") as f:
            f.write("1")

        # 4. Uruchom nową usługę
        if run_command(["sc", "start", service_name]):
            logging.info("Aktualizacja (krok plikowy) zakończona. Agent uruchomiony w trybie weryfikacji.")
            report_status(api_endpoint, hostname, "sukces_oczekuje_na_potwierdzenie")
            return True
        else:
            raise RuntimeError("Nie udało się uruchomić nowej wersji usługi.")

    except Exception as e:
        logging.critical(f"Krytyczny błąd podczas aktualizacji: {e}. Próba wykonania rollbacku...")
        # Automatyczny rollback w razie błędu na tym etapie
        if os.path.exists(backup_path):
            logging.info("Przywracanie agenta z kopii zapasowej...")
            shutil.move(backup_path, current_agent_path)
            run_command(["sc", "start", service_name])
        report_status(api_endpoint, hostname, "błąd", str(e))
        return False


def do_rollback():
    # Argumenty dla rollbacku: sciezka_do_agenta nazwa_uslugi
    if len(sys.argv) < 4:
        logging.error("Niewystarczająca liczba argumentów dla rollbacku.")
        return

    current_agent_path = sys.argv[2]
    service_name = sys.argv[3]
    backup_path = current_agent_path + ".bak"
    flag_path = os.path.join(os.path.dirname(current_agent_path), "health_check.flag")

    logging.warning("Inicjowanie procedury ROLLBACK!")
    run_command(["sc", "stop", service_name])
    time.sleep(5)

    if not os.path.exists(backup_path):
        logging.error("Brak pliku kopii zapasowej! Nie można wykonać rollbacku.")
        return

    if os.path.exists(current_agent_path):
        os.remove(current_agent_path)

    shutil.move(backup_path, current_agent_path)
    logging.info("Stara wersja agenta została przywrócona.")

    if os.path.exists(flag_path):
        os.remove(flag_path)

    run_command(["sc", "start", service_name])
    logging.info("Usługa została uruchomiona na przywróconej wersji.")


def do_cleanup():
    current_agent_path = sys.argv[2]
    backup_path = current_agent_path + ".bak"
    logging.info(f"Rozpoczynanie czyszczenia po aktualizacji. Usuwanie pliku: {backup_path}")
    if os.path.exists(backup_path):
        try:
            os.remove(backup_path)
            logging.info("Plik kopii zapasowej został pomyślnie usunięty.")
        except Exception as e:
            logging.error(f"Nie udało się usunąć pliku kopii zapasowej: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        do_rollback()
    elif len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
        do_cleanup()
    elif len(sys.argv) == 7:
        do_update(sys.argv[1:])
    else:
        logging.error(f"Nieprawidłowa liczba argumentów: {len(sys.argv) - 1}. Oczekiwano 2, 3 lub 6.")
        sys.exit(1)