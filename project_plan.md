# 📋 WingetAgent – Plan Projektu i Checklist

## 1. OGÓLNA STRUKTURA PROJEKTU

- [x] Utwórz repozytorium o strukturze (patrz README/ustalenia).
- [x] Ustal plik `.env` z konfiguracją (API_KEY, baza danych itp.).
- [x] Przygotuj README.md z krótkim opisem projektu i strukturą folderów.

---

## 2. KOD AGENTA (folder `agent/`)

### 2.1. Konfiguracja i podstawy
- [x] Stwórz `config.py` (klasa `AgentConfig` – ładowanie z pliku, zmienne środowiskowe).
- [x] Stwórz `utils.py` (funkcje pomocnicze – logowanie, parsowanie).

### 2.2. Logika agenta
- [x] Stwórz `winget_agent.py` (klasa `WingetAgent`: pobieranie listy aplikacji, filtracja przez blacklistę, zbieranie statusu).
- [x] Stwórz `task_runner.py` (klasa `TaskRunner`: obsługa tasków typu upgrade, uninstall, refresh).
- [x] Stwórz `main.py` (punkt wejścia; ładuje konfig, uruchamia pętlę agenta).

### 2.3. Dodatki i testy
- [x] Stwórz plik `requirements.txt` z zależnościami (`requests`, `python-dotenv` itd.).
- [ ] Dodać przykładowy test (`test_config.py` itp.).

### 2.4. Tryb usługi Windows
- [x] Dodaj obsługę uruchamiania jako usługa systemowa Windows (np. przez [`pywin32`](https://pypi.org/project/pywin32/), [`nssm`](https://nssm.cc/), lub skrypt instalujący usługę).
- [x] Przetestuj generowanie `agent.exe` przez PyInstaller, który działa jako usługa.

---

## 3. KOD SERWERA (folder `server/`)

### 3.1. Podstawy
- [x] Skonfiguruj Flask, utwórz `server/app.py` (główne uruchamianie).
- [x] Zintegruj SQLAlchemy (`models.py` – klasy: Computer, Report, Task, itp.).
- [x] Wydziel `blueprints/` – podziel API na logiczne moduły (komputery, raporty, zadania, ustawienia/generator agenta).

### 3.2. Endpointy i funkcjonalności
- [x] API przyjmowania raportów od agentów.
- [x] API zadań (task queue, odbieranie wyników).
- [x] Generator agenta (endpoint + template).

### 3.3. Panel webowy
- [x] Szablony Jinja (`templates/`): lista komputerów, szczegóły, historia, raporty, ustawienia.
- [x] Static (`static/`): style, JavaScript, motyw ciemny/jasny.
- [x] Dodaj UX: wyszukiwanie, filtry, feedback o błędach.

### 3.4. Bezpieczeństwo i testy
- [ ] CSRF na formularzach.
- [ ] Testy integracyjne API.
- [ ] Logowanie zdarzeń admina, rate limiting.

### 3.5. Migracja bazy
- [x] SQLAlchemy: przetestuj z SQLite i (opcjonalnie) z PostgreSQL — konfiguracja przez `.env`.

---

## 4. OGÓLNE USPRAWNIENIA I MODULARNOŚĆ

- [x] Każdy kluczowy moduł/test ma swój plik.
- [x] Kod czytelny, DRY, podzielony na klasy/metody.
- [x] Wszystkie pliki z dependencjami: `requirements.txt` (osobno dla agenta i serwera).
- [x] Dokumentacja i opis uruchamiania w README.md.
- [ ] Lista TODO – na bieżąco uzupełniaj o własne potrzeby i pomysły!

---

## 5. NICE-TO-HAVE/ROZWÓJ

- [x] Edytowalna blacklist w panelu webowym.
- [ ] Dynamiczna aktualizacja blacklisty w agentach.
- [ ] Mikroserwisy lub dockerizacja.
- [x] Responsywność mobilna panelu.
- [ ] Automatyzacja testów (np. CI/CD).
- [ ] Notyfikacje mail/SMS (opcjonalnie).

