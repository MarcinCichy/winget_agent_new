# Plik: ui_helper.py (finalna wersja z schtasks.exe dla maksymalnej kompatybilności)
import socket
import json
import threading
from tkinter import messagebox, Tk
import logging
import os
import subprocess
import struct
import tempfile  # <-- NOWY IMPORT

# Konfiguracja logowania
LOG_DIR = os.path.join(os.environ.get('ProgramData'), "WingetAgent")
LOG_FILE = os.path.join(LOG_DIR, "ui_helper.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '127.0.0.1'
PORT = 61900


def show_dialog(data):
    try:
        root = Tk()
        root.withdraw()
        dialog_type = data.get('type', 'info')
        title = data.get('title', 'Winget Dashboard')
        message = data.get('message', '')
        response_str = "error"
        if dialog_type == 'request':
            detail_text = data.get('detail',
                                   "Wybierz 'Tak', aby uruchomić teraz, lub 'Nie', aby zaplanować na zamknięcie systemu.")
            user_response = messagebox.askyesno(title, message, icon='question', detail=detail_text)
            response_str = "now" if user_response else "shutdown"
        else:
            messagebox.showinfo(title, message, icon='info')
            response_str = "ok"
        root.destroy()
        return json.dumps({"status": "dialog_ok", "response": response_str})
    except Exception as e:
        logging.error(f"Błąd w show_dialog: {e}", exc_info=True)
        return json.dumps({"status": "error", "details": str(e)})


def run_command_as_user(command_str):
    logging.info(f"Otrzymano prośbę o wykonanie polecenia: {command_str}")
    try:
        full_command = f"$ProgressPreference = 'SilentlyContinue'; [System.Threading.Thread]::CurrentThread.CurrentUICulture = 'en-US'; {command_str}"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_command],
            capture_output=True, text=True, encoding='utf-8', errors='ignore',
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=1800
        )

        clean_stdout = result.stdout.replace('\\', '/')
        clean_stderr = result.stderr.replace('\\', '/')

        if result.returncode == 0 or "Successfully installed" in clean_stdout or "successfully installed" in clean_stderr:
            logging.info(f"Polecenie zakończone sukcesem. Kod wyjścia: {result.returncode}")
            return json.dumps({"status": "success", "details": clean_stdout})
        else:
            logging.error(
                f"Polecenie nie powiodło się. Kod: {result.returncode}\nSTDOUT: {clean_stdout}\nSTDERR: {clean_stderr}")
            error_details = f"Kod wyjścia: {result.returncode}\n\nSTDOUT:\n{clean_stdout}\n\nSTDERR:\n{clean_stderr}"
            return json.dumps({"status": "failure", "details": error_details})

    except Exception as e:
        logging.error(f"Krytyczny błąd wykonania polecenia przez UI Helpera: {e}", exc_info=True)
        return json.dumps({"status": "failure", "details": str(e)})


# --- NOWA, OSTATECZNA WERSJA FUNKCJI ---
def schedule_task_as_user(task_name, command_to_run):
    """Planuje zadanie przy użyciu schtasks.exe dla maksymalnej kompatybilności."""
    logging.info(f"Otrzymano prośbę o zaplanowanie zadania '{task_name}' przy użyciu schtasks.exe")

    # Tworzenie ścieżki do tymczasowego pliku skryptu
    temp_dir = tempfile.gettempdir()
    script_path = os.path.join(temp_dir, f"{task_name}.ps1")

    # Kompletne polecenie, które znajdzie się w pliku .ps1 (wraz z usunięciem tego pliku)
    script_content = f"""
{command_to_run}
Remove-Item -Path "{script_path}" -Force -ErrorAction SilentlyContinue
"""
    try:
        # Zapisz polecenie do pliku tymczasowego
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Polecenie, które zostanie wykonane przez schtasks
        task_command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{script_path}"'

        # Stworzenie zadania za pomocą schtasks.exe
        # /SC ONEVENT - wyzwalacz na zdarzenie
        # /EC Security - w dzienniku Zabezpieczeń
        # /MO "*[System[EventID=4647]]" - dla zdarzenia wylogowania
        # /F - wymuś utworzenie (nadpisz, jeśli istnieje)
        schtasks_command = [
            'schtasks', '/Create',
            '/TN', task_name,
            '/TR', task_command,
            '/SC', 'ONEVENT',
            '/EC', 'Security',
            '/MO', "*[System[EventID=4647]]",
            '/F'
        ]

        result = subprocess.run(
            schtasks_command,
            capture_output=True, text=True, encoding='cp852', errors='ignore',
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if result.returncode == 0:
            logging.info(f"Pomyślnie zaplanowano zadanie '{task_name}' za pomocą schtasks.exe.")
            return json.dumps({"status": "success", "details": f"Zadanie '{task_name}' zostało poprawnie zaplanowane."})
        else:
            logging.error(
                f"Nie udało się zaplanować zadania '{task_name}'. Kod: {result.returncode}\nBłąd: {result.stdout or result.stderr}")
            return json.dumps({"status": "failure", "details": result.stdout or result.stderr})

    except Exception as e:
        logging.error(f"Krytyczny błąd podczas planowania zadania: {e}", exc_info=True)
        return json.dumps({"status": "failure", "details": str(e)})


# --- KONIEC NOWEJ WERSJI FUNKCJI ---

def handle_client(conn, addr):
    logging.info(f"Połączono z {addr} - obsługa w wątku {threading.get_ident()}")
    response_json = ""
    try:
        header_bytes = conn.recv(4)
        if not header_bytes: return
        msg_len = struct.unpack('>I', header_bytes)[0]

        chunks = []
        bytes_recd = 0
        while bytes_recd < msg_len:
            chunk = conn.recv(min(msg_len - bytes_recd, 4096))
            if not chunk: raise RuntimeError("Połączenie przerwane")
            chunks.append(chunk)
            bytes_recd += len(chunk)

        data = json.loads(b''.join(chunks).decode('utf-8'))
        logging.info(f"Otrzymano polecenie: {data}")
        dialog_type = data.get('type')

        if dialog_type in ['request', 'info']:
            response_json = show_dialog(data)
        elif dialog_type == 'execute_command':
            response_json = run_command_as_user(data.get('command'))
        elif dialog_type == 'schedule_task':
            response_json = schedule_task_as_user(data.get('task_name'), data.get('command'))
        else:
            response_json = json.dumps({"status": "error", "details": f"Nieznany typ polecenia: {dialog_type}"})

        response_bytes = response_json.encode('utf-8')
        conn.sendall(struct.pack('>I', len(response_bytes)))
        conn.sendall(response_bytes)
        logging.info(f"Wysłano odpowiedź do agenta o długości {len(response_bytes)} bajtów.")

    except Exception as e:
        logging.error(f"Krytyczny błąd podczas obsługi klienta: {e}", exc_info=True)
    finally:
        conn.close()
        logging.info(f"Zakończono obsługę klienta dla {addr}, wątek {threading.get_ident()} zakończony.")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
        except OSError as e:
            logging.critical(f"Nie można powiązać portu {PORT}. Czy inna instancja Pomocnika UI już działa? Błąd: {e}")
            return
        s.listen(5)
        logging.info(f"Pomocnik UI nasłuchuje na {HOST}:{PORT}")
        while True:
            try:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                logging.error(f"Błąd w głównej pętli serwera UI: {e}", exc_info=True)


if __name__ == "__main__":
    main()