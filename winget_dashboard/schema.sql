-- Usuwa istniejące tabele, jeśli istnieją, aby zapewnić czysty start.
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS updates;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS computers;

-- Tworzy tabelę do przechowywania informacji o komputerach.
CREATE TABLE computers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hostname TEXT UNIQUE NOT NULL,
  ip_address TEXT,
  last_report TIMESTAMP,
  reboot_required BOOLEAN NOT NULL DEFAULT 0,
  -- POPRAWKA: Dodano brakującą kolumnę na czarną listę.
  blacklist_keywords TEXT
);

-- Tworzy tabelę do przechowywania poszczególnych raportów.
CREATE TABLE reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  computer_id INTEGER NOT NULL,
  report_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (computer_id) REFERENCES computers (id)
);

-- Przechowuje listę zainstalowanych aplikacji dla każdego raportu.
CREATE TABLE applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  version TEXT,
  app_id TEXT,
  FOREIGN KEY (report_id) REFERENCES reports (id)
);

-- Przechowuje listę dostępnych aktualizacji (zarówno aplikacji, jak i systemu).
CREATE TABLE updates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  app_id TEXT,
  current_version TEXT,
  available_version TEXT,
  update_type TEXT, -- 'APP' lub 'OS'
  status TEXT NOT NULL DEFAULT 'Dostępna', -- np. Dostępna, Oczekuje, Błąd
  FOREIGN KEY (report_id) REFERENCES reports (id)
);

-- Przechowuje zadania do wykonania przez agentów.
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  computer_id INTEGER NOT NULL,
  command TEXT NOT NULL,
  payload TEXT,
  status TEXT NOT NULL DEFAULT 'oczekuje', -- oczekuje, w toku, zakończone, błąd
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (computer_id) REFERENCES computers (id)
);
