# Plik: updater.py
import sys
import os
import shutil
import time
import subprocess


def log(message):
    """Proste logowanie do pliku w folderze TEMP."""
    log_file = os.path.join(os.environ.get("TEMP", "C:\\Windows\\Temp"), "agent_updater_log.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


if __name__ == "__main__":
    log("Updater uruchomiony.")
    if len(sys.argv) < 5:
        log(f"Błąd: Niewystarczająca liczba argumentów. Otrzymano: {len(sys.argv) - 1}")
        sys.exit(1)

    # Argumenty przekazywane z agent.exe
    service_pid_str = sys.argv[1]
    new_agent_path = sys.argv[2]
    current_agent_path = sys.argv[3]
    service_name = sys.argv[4]

    log(f"PID usługi do zatrzymania: {service_pid_str}")
    log(f"Ścieżka nowego agenta: {new_agent_path}")
    log(f"Ścieżka obecnego agenta: {current_agent_path}")
    log(f"Nazwa usługi: {service_name}")

    # Krok 1: Poczekaj chwilę, aż główna usługa sama się zatrzyma.
    # Agent sam wywołuje SvcStop(), ten sleep daje pewność, że proces się zamknie.
    log("Oczekiwanie 10 sekund na całkowite zamknięcie starej usługi...")
    time.sleep(10)

    # Krok 2: Podmiana pliku agent.exe w pętli na wypadek blokady pliku.
    log("Próba podmiany pliku wykonywalnego agenta...")
    for i in range(5):  # Próbuj przez 25 sekund (5 * 5s)
        try:
            shutil.move(new_agent_path, current_agent_path)
            log("Podmiana pliku agenta zakończona sukcesem.")
            break  # Wyjdź z pętli jeśli się udało
        except Exception as e:
            log(f"Próba {i + 1}/5 nie powiodła się: {e}. Ponawiam za 5 sekund...")
            time.sleep(5)
    else:  # Ten blok wykona się, jeśli pętla for zakończy się bez 'break'
        log("KRYTYCZNY BŁĄD: Nie udało się podmienić pliku agenta po wielu próbach.")
        sys.exit(2)

    # Krok 3: Uruchomienie nowej wersji usługi
    log("Próba uruchomienia nowej wersji usługi...")
    try:
        subprocess.run(["sc", "start", service_name], check=True, capture_output=True)
        log("Polecenie uruchomienia usługi wysłane pomyślnie.")
    except Exception as e:
        log(f"KRYTYCZNY BŁĄD: Nie udało się uruchomić usługi: {e}")
        sys.exit(3)

    log("Proces aktualizacji zakończony.")
    sys.exit(0)