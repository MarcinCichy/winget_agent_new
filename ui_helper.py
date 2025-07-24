# Plik: ui_helper.py (WERSJA FINAŁOWA z ostateczną poprawką uprawnień)

import socket
import json
import threading
import logging
import os
import subprocess
import struct
import tempfile
import ctypes
import base64

# Konfiguracja logowania
LOG_DIR = os.path.join(os.environ.get('ProgramData'), "WingetAgent")
LOG_FILE = os.path.join(LOG_DIR, "ui_helper.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '127.0.0.1'
PORT = 61900


def show_dialog_native(data):
    """Wyświetla natywne okno dialogowe Windows, które jest bezpieczne wątkowo."""
    try:
        dialog_type = data.get('type', 'info')
        title = data.get('title', 'Winget Dashboard')
        message = data.get('message', '')
        response_str = "error"

        MB_OK = 0x00000000
        MB_YESNO = 0x00000004
        MB_ICONINFORMATION = 0x00000040
        MB_ICONQUESTION = 0x00000020
        IDYES = 6

        if dialog_type == 'request':
            style = MB_YESNO | MB_ICONQUESTION
            full_message = f"{message}\n\n{data.get('detail', '')}"
            result = ctypes.windll.user32.MessageBoxW(0, full_message, title, style)
            response_str = "now" if result == IDYES else "shutdown"
        else: # Obejmuje 'info' i każdy inny typ
            style = MB_OK | MB_ICONINFORMATION
            ctypes.windll.user32.MessageBoxW(0, message, title, style)
            response_str = "ok"

        return json.dumps({"status": "dialog_ok", "response": response_str})
    except Exception as e:
        logging.error(f"Błąd w show_dialog_native: {e}", exc_info=True)
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

        if result.returncode == 0 or "Successfully installed" in result.stdout or "successfully installed" in result.stderr:
            logging.info(f"Polecenie zakończone sukcesem. Kod wyjścia: {result.returncode}")
            return json.dumps({"status": "success", "details": result.stdout})
        else:
            logging.error(
                f"Polecenie nie powiodło się. Kod: {result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            error_details = f"Kod wyjścia: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            return json.dumps({"status": "failure", "details": error_details})
    except Exception as e:
        logging.error(f"Krytyczny błąd wykonania polecenia przez UI Helpera: {e}", exc_info=True)
        return json.dumps({"status": "failure", "details": str(e)})


def schedule_task_as_user(task_name, command_to_run, trigger_type='onlogon'):
    logging.info(f"Otrzymano prośbę o zaplanowanie zadania '{task_name}' z wyzwalaczem '{trigger_type}'")
    temp_dir = tempfile.gettempdir()
    starter_script_path = os.path.join(temp_dir, f"{task_name}.ps1")
    log_file_path = os.path.join(temp_dir, f"{task_name}.log")

    main_script_content = f"""
Start-Transcript -Path "{log_file_path}" -Force
{command_to_run}
Stop-Transcript
Remove-Item -Path "{starter_script_path}" -Force -ErrorAction SilentlyContinue
"""
    try:
        encoded_command = base64.b64encode(main_script_content.encode('utf-16-le')).decode('ascii')
        starter_script_content = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_command}"

        with open(starter_script_path, "w", encoding="utf-8") as f:
            f.write(starter_script_content)

        task_command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{starter_script_path}"'

        # ===============================================================
        # OSTATECZNA POPRAWKA: Dodajemy /RU SYSTEM, aby zadanie było globalne
        # ===============================================================
        base_schtasks_command = ['schtasks', '/Create', '/TN', task_name, '/TR', task_command, '/F', '/RU', 'SYSTEM']

        if trigger_type == 'onlogon':
            final_schtasks_command = base_schtasks_command + ['/SC', 'ONLOGON', '/DELAY', '0001:00']
        else:
            final_schtasks_command = base_schtasks_command + ['/SC', 'ONLOGON', '/DELAY', '0001:00']

        result = subprocess.run(
            final_schtasks_command,
            capture_output=True, text=True, encoding='cp852', errors='ignore',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            logging.info(f"Pomyślnie zaplanowano zadanie '{task_name}'.")
            return json.dumps({"status": "success", "details": f"Zadanie '{task_name}' zostało poprawnie zaplanowane."})
        else:
            error_msg = result.stdout or result.stderr
            logging.error(f"Nie udało się zaplanować zadania '{task_name}'. Kod: {result.returncode}\nBłąd: {error_msg}")
            return json.dumps({"status": "failure", "details": error_msg})
    except Exception as e:
        logging.error(f"Krytyczny błąd podczas planowania zadania: {e}", exc_info=True)
        return json.dumps({"status": "failure", "details": str(e)})


def handle_client(conn, addr):
    logging.info(f"Połączono z {addr} - obsługa w wątku {threading.get_ident()}")
    try:
        header_bytes = conn.recv(4)
        if not header_bytes: return
        msg_len = struct.unpack('>I', header_bytes)[0]
        chunks, bytes_recd = [], 0
        while bytes_recd < msg_len:
            chunk = conn.recv(min(msg_len - bytes_recd, 4096))
            if not chunk: raise RuntimeError("Połączenie przerwane")
            chunks.append(chunk)
            bytes_recd += len(chunk)
        data = json.loads(b''.join(chunks).decode('utf-8'))
        logging.info(f"Otrzymano polecenie: {data}")
        dialog_type = data.get('type')

        if dialog_type == 'ping': # Obsługa nowego polecenia ping
            response_json = json.dumps({"status": "pong"})
        elif dialog_type in ['request', 'info']:
            response_json = show_dialog_native(data)
        elif dialog_type == 'execute_command':
            response_json = run_command_as_user(data.get('command'))
        elif dialog_type == 'schedule_task':
            response_json = schedule_task_as_user(
                data.get('task_name'),
                data.get('command'),
                data.get('trigger_type', 'onlogon')
            )
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