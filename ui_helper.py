# Plik: ui_helper.py (wersja z wątkami)
import socket
import json
import threading
from tkinter import messagebox, Tk
import logging
import os

# Konfiguracja logowania
LOG_DIR = os.path.join(os.environ.get('ProgramData'), "WingetAgent")
LOG_FILE = os.path.join(LOG_DIR, "ui_helper.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '127.0.0.1'
PORT = 61900

def show_dialog(data):
    """Funkcja do wyświetlania okna dialogowego."""
    try:
        root = Tk()
        root.withdraw()
        dialog_type = data.get('type', 'info')
        title = data.get('title', 'Winget Dashboard')
        message = data.get('message', '')
        response_str = "error"
        if dialog_type == 'request':
            detail_text = data.get('detail', "Wybierz 'Tak', aby uruchomić teraz, lub 'Nie', aby zaplanować na zamknięcie systemu.")
            user_response = messagebox.askyesno(title, message, icon='question', detail=detail_text)
            response_str = "now" if user_response else "shutdown"
        else:
            messagebox.showinfo(title, message, icon='info')
            response_str = "ok"
        root.destroy()
        return response_str
    except Exception as e:
        logging.error(f"Błąd w show_dialog: {e}", exc_info=True)
        return "error"

def handle_client(conn, addr):
    """
    Obsługuje pojedyncze połączenie klienta w osobnym wątku.
    """
    logging.info(f"Połączono z {addr} - obsługa w wątku {threading.get_ident()}")
    try:
        data_bytes = conn.recv(2048)
        if not data_bytes:
            logging.warning("Otrzymano puste dane, zamykanie połączenia.")
            return

        data = json.loads(data_bytes.decode('utf-8'))
        logging.info(f"Otrzymano polecenie: {data}")

        # To wywołanie blokuje TEN WĄTEK, a nie główną pętlę
        user_choice = show_dialog(data)

        logging.info(f"Odpowiedź użytkownika: {user_choice}")
        conn.sendall(user_choice.encode('utf-8'))

    except ConnectionAbortedError as e:
        logging.error(f"Połączenie przerwane przez hosta (agent prawdopodobnie się rozłączył): {e}")
    except Exception as e:
        logging.error(f"Błąd podczas obsługi klienta: {e}", exc_info=True)
    finally:
        conn.close()
        logging.info(f"Zakończono obsługę klienta dla {addr}, wątek {threading.get_ident()} zakończony.")

def main():
    """Główna funkcja serwera nasłuchującego."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
        except OSError as e:
            logging.critical(f"Nie można powiązać portu {PORT}. Czy inna instancja Pomocnika UI już działa? Błąd: {e}")
            return

        s.listen(5)
        logging.info(f"Pomocnik UI nasłuchuje na {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            # Uruchom nowy wątek, aby obsłużyć klienta i natychmiast wróć do nasłuchiwania
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()

if __name__ == "__main__":
    main()