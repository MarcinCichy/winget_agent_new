# Plik: updater.py (wersja z raportowaniem i flagą)
import sys
import os
import shutil
import time
import subprocess
import json

# Spróbuj zaimportować requests, jeśli nie ma, użyj urllib
try:
    import requests

    USE_REQUESTS = True
except ImportError:
    import urllib.request

    USE_REQUESTS = False


def log(message):
    """Proste logowanie do pliku w folderze TEMP."""
    log_file = os.path.join(os.environ.get("TEMP", "C:\\Windows\\Temp"), "agent_updater_log.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def report_status(endpoint, hostname, status):
    """Wysyła status aktualizacji do serwera."""
    url = f"{endpoint.strip('/')}/api/agent/update_status"
    payload = {'hostname': hostname, 'status': status}
    log(f"Raportowanie statusu do {url} z danymi: {payload}")
    try:
        if USE_REQUESTS:
            requests.post(url, json=payload, timeout=15)
        else:  # Fallback do biblioteki standardowej
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data,
                                         headers={'Content-Type': 'application/json', 'User-Agent': 'AgentUpdater'})
            urllib.request.urlopen(req, timeout=15)
        log("Status zaraportowany pomyślnie.")
    except Exception as e:
        log(f"BŁĄD podczas raportowania statusu: {e}")


if __name__ == "__main__":
    log("Updater (v2) uruchomiony.")
    if len(sys.argv) < 7:
        log(f"Błąd: Niewystarczająca liczba argumentów. Otrzymano: {len(sys.argv) - 1}, oczekiwano 6.")
        sys.exit(1)

    service_pid_str = sys.argv[1]
    new_agent_path = sys.argv[2]
    current_agent_path = sys.argv[3]
    service_name = sys.argv[4]
    hostname = sys.argv[5]
    api_endpoint = sys.argv[6]

    update_successful = False
    try:
        log(f"Oczekiwanie 10 sekund na zamknięcie starej usługi (PID: {service_pid_str})...")
        time.sleep(10)

        log("Próba podmiany pliku wykonywalnego agenta...")
        for i in range(5):
            try:
                shutil.move(new_agent_path, current_agent_path)
                log("Podmiana pliku agenta zakończona sukcesem.")
                update_successful = True
                break
            except Exception as e:
                log(f"Próba {i + 1}/5 nie powiodła się: {e}. Ponawiam za 5 sekund...")
                time.sleep(5)
        else:
            log("KRYTYCZNY BŁĄD: Nie udało się podmienić pliku agenta po wielu próbach.")
            update_successful = False

        # Uruchom usługę tylko jeśli podmiana się powiodła
        if update_successful:
            # Tworzymy plik flagi przed uruchomieniem usługi
            log("Tworzenie flagi 'skip_update_check.flag' dla nowego agenta...")
            flag_path = os.path.join(os.path.dirname(current_agent_path), "skip_update_check.flag")
            with open(flag_path, "w") as f:
                f.write("1")

            log("Próba uruchomienia nowej wersji usługi...")
            subprocess.run(["sc", "start", service_name], check=True, capture_output=True)
            log("Polecenie uruchomienia usługi wysłane pomyślnie.")

    except Exception as e:
        log(f"KRYTYCZNY BŁĄD w procesie aktualizacji: {e}")
        update_successful = False
    finally:
        # Zawsze raportuj status, nawet po błędzie
        status_to_report = "sukces" if update_successful else "błąd"
        report_status(api_endpoint, hostname, status_to_report)

    log(f"Proces aktualizacji zakończony ze statusem: {status_to_report}.")
    sys.exit(0 if update_successful else 1)