-- Schemat dla bazy danych SQLite

DROP TABLE IF EXISTS computers;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS updates;
DROP TABLE IF EXISTS tasks;

CREATE TABLE computers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT UNIQUE NOT NULL COLLATE NOCASE,
    ip_address TEXT,
    last_report TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reboot_required BOOLEAN DEFAULT FALSE,
    blacklist_keywords TEXT
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    computer_id INTEGER NOT NULL,
    report_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (computer_id) REFERENCES computers (id) ON DELETE CASCADE
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    version TEXT,
    app_id TEXT,
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE
);

CREATE TABLE updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    app_id TEXT,
    current_version TEXT,
    available_version TEXT,
    update_type TEXT NOT NULL, -- 'OS' or 'APP'
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    computer_id INTEGER NOT NULL,
    command TEXT NOT NULL,
    payload TEXT,
    status TEXT DEFAULT 'oczekuje',
    result_details TEXT, -- NOWA KOLUMNA NA SZCZEGÓŁY BŁĘDU
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (computer_id) REFERENCES computers (id) ON DELETE CASCADE
);