# Winget Dashboard - Centralne Zarządzanie Oprogramowaniem

![Główny interfejs aplikacji](![Main application interface](screenshots/main.png "Main interface")

### Spis Treści
* [Opis](#opis)
* [Główne Funkcje](#główne-funkcje)
* [Architektura](#architektura)
* [Instalacja i Konfiguracja](#instalacja-i-konfiguracja)
* [Stos Technologiczny](#stos-technologiczny)
* [English Version](#english-version)

---

## Opis

**Winget Dashboard** to aplikacja webowa oparta na frameworku Flask, przeznaczona do zdalnego monitorowania i zarządzania oprogramowaniem na komputerach z systemem Windows przy użyciu menedżera pakietów `winget`. Projekt został stworzony z myślą o małych i średnich zespołach IT, które potrzebują prostego, scentralizowanego narzędzia do automatyzacji aktualizacji, deinstalacji i raportowania stanu stacji roboczych.

## Główne Funkcje

### 🛡️ Niezawodność i Bezpieczeństwo
* **Health Check & Automatic Rollback:** Agent po każdej własnej aktualizacji przeprowadza autotest ("health check"). Jeśli nowa wersja z jakiegokolwiek powodu jest wadliwa (np. błąd w kodzie, problem z komunikacją), system **automatycznie przywróci poprzednią, stabilną wersję agenta**, minimalizując ryzyko nieudanego wdrożenia.
* **Inteligentne Zarządzanie Zadaniami:** Serwer automatycznie wykrywa i zamyka przestarzałe lub "zawieszone" zadania aktualizacji, aby zapobiec niechcianym, powtarzającym się akcjom na klientach.
* **Solidna Usługa Windows:** Główny agent działa jako stabilna usługa systemowa, odporna na wylogowanie użytkownika.

### ⚙️ Zdalne Zarządzanie i Automatyzacja
* **Centralny Panel:** Przegląd wszystkich podłączonych komputerów wraz z ich kluczowymi statusami (online/offline, wymagany restart, wersja agenta, liczba dostępnych aktualizacji).
* **Zdalne Akcje:** Możliwość zdalnego zlecania zadań:
    * **Aktualizacja:** pojedynczych aplikacji lub całego systemu operacyjnego.
    * **Deinstalacja:** dowolnej aplikacji wykrytej przez `winget`.
* **Tryb "Poproś" vs "Wymuś":** Zadania mogą być wykonywane w trybie interaktywnym (z prośbą o zgodę użytkownika na pulpicie) lub w pełni cichym (wymuszonym).
* **Generator Agenta:** Wbudowane w panel webowy narzędzie do kompilacji spersonalizowanego pliku `agent.exe` z wpisaną konfiguracją serwera i kluczem API.
* **Automatyczna Aktualizacja Agenta:** Możliwość zdalnego wdrożenia nowej wersji agenta na wszystkich podłączonych komputerach za pomocą jednego kliknięcia.

### 📊 Raportowanie i Konfiguracja
* **Szczegółowy Widok Komputera:** Dostęp do listy zainstalowanych aplikacji, dostępnych aktualizacji oraz oczekujących aktualizacji systemu Windows.
* **Czarna Lista (Blacklist):** Możliwość zdefiniowania globalnej lub indywidualnej dla komputera listy słów kluczowych (np. "redistributable", "visual c++"), aby ignorować określone aplikacje podczas skanowania.
* **Historia Raportów:** Dostęp do historycznych raportów dla każdej maszyny z możliwością filtrowania.
* **Interaktywność z Użytkownikiem:** Agent potrafi wyświetlać natywne okna dialogowe w sesji zalogowanego użytkownika, prosząc go o podjęcie decyzji lub informując o przeprowadzanych akcjach.

## Architektura

System składa się z centralnego serwera oraz trzech komponentów klienckich, które zapewniają jego niezawodne działanie.

* **Serwer (Flask):** Sercem aplikacji jest serwer napisany w Pythonie (Flask + Waitress). Odpowiada za udostępnianie panelu webowego, API do komunikacji z agentami, zarządzanie bazą danych (SQLite) oraz generowanie plików wykonywalnych agenta.
* **Agent (agent.exe):** Główny program działający jako usługa systemowa Windows (`Windows Service`) na komputerach klienckich. Jego zadania to cykliczne raportowanie, pobieranie i koordynowanie zadań oraz komunikacja z Pomocnikiem UI.
* **Pomocnik UI (ui_helper.exe):** Lekki program pośredniczący, uruchamiany automatycznie w kontekście zalogowanego użytkownika. Jest niezbędny, aby ominąć tzw. "Session 0 Isolation", co pozwala agentowi (działającemu jako SYSTEM) na uruchamianie poleceń `winget` i wyświetlanie okien dialogowych na pulpicie użytkownika.
* **Updater (updater.exe):** Specjalistyczne narzędzie odpowiedzialne za proces autoaktualizacji agenta. Implementuje logikę tworzenia kopii zapasowych, podmiany plików oraz automatycznego rollbacku w razie awarii.

## Instalacja i Konfiguracja

### Wymagania
* Python 3.8+
* Git
* `pyinstaller` do budowania komponentów klienckich (`pip install pyinstaller`).

### 1. Konfiguracja Serwera

```bash
# Sklonuj repozytorium
git clone <adres-twojego-repozytorium>
cd winget-dashboard

# Utwórz i aktywuj wirtualne środowisko
python -m venv venv
# Windows
.\venv\Scripts\activate

# Zainstaluj zależności
pip install -r requirements.txt


Utworzenie pliku .env

W głównym folderze projektu utwórz plik .env i uzupełnij go:
Fragment kodu

# Wygeneruj silny, losowy klucz. Możesz użyć: python -c "import secrets; print(secrets.token_hex(16))"
SECRET_KEY=twoj_super_tajny_klucz_sesji

# Wygeneruj losowy klucz API, który będzie używany do autoryzacji agentów
API_KEY=twoj_super_tajny_klucz_api_dla_agentow

Inicjalizacja i uruchomienie

Bash

# Zainicjuj bazę danych (ten krok wykonaj tylko raz)
flask --app run init-db

# Uruchom serwer deweloperski
flask --app run --host=0.0.0.0

# Uruchom serwer produkcyjny (zalecane)
waitress-serve --host=0.0.0.0 --port=5000 winget_dashboard:create_app()

2. Budowanie Komponentów Klienckich

Zanim wdrożysz agentów, musisz jednorazowo zbudować pliki ui_helper.exe i updater.exe.
Bash

# Będąc w głównym folderze projektu, wykonaj:
pyinstaller --onefile --windowed --name ui_helper ui_helper.py
pyinstaller --onefile --name updater updater.py

Gotowe pliki .exe znajdziesz w nowo utworzonym folderze dist/.

3. Generowanie Głównego Agenta (agent.exe)

    Otwórz panel webowy w przeglądarce (np. http://adres-ip-serwera:5000).

    Przejdź do zakładki Ustawienia.

    W formularzu Generator Agenta podaj publiczny adres serwera oraz klucz API (ten sam co w pliku .env).

    Kliknij "Generuj agent.exe", aby pobrać spersonalizowany plik.

4. Wdrożenie na Komputerze Klienckim

    Utwórz folder na maszynie klienckiej, np. C:\Program Files\WingetAgent.

    Umieść w nim trzy pliki wykonywalne:

        agent.exe (pobrany z panelu w kroku 3).

        ui_helper.exe (zbudowany w kroku 2, z folderu dist/).

        updater.exe (zbudowany w kroku 2, z folderu dist/).

    Otwórz Wiersz polecenia (CMD) jako administrator, przejdź do folderu z agentem i wykonaj polecenia:

DOS

# Instalacja usługi
agent.exe install

# Uruchomienie usługi
agent.exe start

Agent jest teraz zainstalowany i po chwili powinien pojawić się w panelu.

Stos Technologiczny

    Backend: Python 3, Flask, Waitress, SQLite

    Frontend: HTML5, CSS3, JavaScript (bez frameworków)

    Agent: Python 3, pywin32

    Narzędzia: PyInstaller

Winget Dashboard - Centralized Software Management (English Version)

Table of Contents

    Description

    Key Features

    Architecture

    Installation and Setup

    Technology Stack

Description

Winget Dashboard is a Flask-based web application for remotely monitoring and managing software on Windows computers using the winget package manager. The project is designed for small to medium-sized IT teams who need a simple, centralized tool to automate updates, uninstalls, and reporting for their workstations.

Key Features

🛡️ Reliability and Security

    Health Check & Automatic Rollback: After every self-update, the agent performs a health check. If the new version is faulty for any reason (e.g., a bug, communication issue), the system will automatically roll back to the previous, stable version, minimizing the risk of failed deployments.

    Intelligent Task Management: The server automatically detects and closes obsolete or "stuck" update tasks to prevent unwanted, repetitive actions on clients.

    Robust Windows Service: The main agent runs as a stable Windows service, resilient to user logouts.

⚙️ Remote Management and Automation

    Central Dashboard: An overview of all connected computers with their key statuses (online/offline, reboot required, agent version, number of available updates).

    Remote Actions: Ability to remotely trigger tasks:

        Update: for single applications or the entire operating system.

        Uninstall: for any application detected by winget.

    "Request" vs. "Force" Mode: Tasks can be executed interactively (with a user consent dialog on their desktop) or completely silently (forced).

    Agent Generator: A built-in tool in the web panel to compile a personalized agent.exe file with a pre-filled server configuration and API key.

    Agent Self-Update: Ability to remotely deploy a new version of the agent to all connected machines with a single click.

📊 Reporting and Configuration

    Detailed Computer View: Access to the list of installed applications, available software updates, and pending Windows Updates.

    Blacklist: Define a global or per-computer list of keywords (e.g., "redistributable", "visual c++") to ignore specific applications during scans.

    Report History: Access historical reports for each machine with filtering capabilities.

    User Interactivity: The agent can display native dialog boxes in the logged-in user's session to request decisions or provide information about ongoing actions.

Architecture

The system consists of a central server and three client components that ensure its reliable operation.

    Server (Flask): The core of the application is a Python server (Flask + Waitress). It is responsible for serving the web panel, providing an API for agents, managing the database (SQLite), and generating the agent executables.

    Agent (agent.exe): The main program running as a Windows Service on client computers. Its tasks include periodically reporting to the server, fetching and coordinating tasks, and communicating with the UI Helper.

    UI Helper (ui_helper.exe): A lightweight intermediary program that runs automatically in the logged-in user's context. It is essential to bypass "Session 0 Isolation," allowing the agent (running as SYSTEM) to execute winget commands and display dialog boxes on the user's desktop.

    Updater (updater.exe): A specialized tool responsible for the agent's self-update process. It implements the logic for creating backups, replacing files, and performing an automatic rollback in case of failure.

Installation and Setup

Prerequisites

    Python 3.8+

    Git

    pyinstaller for building the client components (pip install pyinstaller).

1. Server Setup

Bash

# Clone the repository
git clone <your-repository-address>
cd winget-dashboard

# Create and activate a virtual environment
python -m venv venv
# On Windows
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

Create the .env file

In the project's root directory, create a .env file and fill it with:
Fragment kodu

# Generate a strong, random key. You can use: python -c "import secrets; print(secrets.token_hex(16))"
SECRET_KEY=your_super_secret_session_key

# Generate a random API key that will be used to authorize agents
API_KEY=your_super_secret_api_key_for_agents

Initialize and Run

Bash

# Initialize the database (run this step only once)
flask --app run init-db

# Run the development server
flask --app run --host=0.0.0.0

# Run the production server (recommended)
waitress-serve --host=0.0.0.0 --port=5000 winget_dashboard:create_app()

2. Building Client Components

Before deploying agents, you need to build the ui_helper.exe and updater.exe files once.
Bash

# From the project's root directory, run:
pyinstaller --onefile --windowed --name ui_helper ui_helper.py
pyinstaller --onefile --name updater updater.py

The compiled .exe files will be in the newly created dist/ directory.

3. Generating the Main Agent (agent.exe)

    Open the web panel in your browser (e.g., http://your-server-ip:5000).

    Navigate to the Settings page.

    In the Agent Generator form, provide the public server address and the API Key (the same one as in your .env file).

    Click "Generate agent.exe" to download the personalized file.

4. Deploying on the Client Machine

    Create a folder on the client machine, e.g., C:\Program Files\WingetAgent.

    Place the following three executable files inside it:

        agent.exe (downloaded from the panel in step 3).

        ui_helper.exe (built in step 2, from the dist/ folder).

        updater.exe (built in step 2, from the dist/ folder).

    Open a Command Prompt (CMD) as an administrator, navigate to the agent's folder, and run the following commands:

DOS

# Install the service
agent.exe install

# Start the service
agent.exe start

The agent is now installed and should appear in the dashboard shortly.

Technology Stack

    Backend: Python 3, Flask, Waitress, SQLite

    Frontend: HTML5, CSS3, JavaScript (vanilla)

    Agent: Python 3, pywin32

    Tooling: PyInstaller