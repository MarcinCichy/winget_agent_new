DROP TABLE IF EXISTS computers;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS updates;
DROP TABLE IF EXISTS tasks;

CREATE TABLE computers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    reboot_required BOOLEAN DEFAULT FALSE,
    last_report TIMESTAMP,
    blacklist_keywords TEXT,
    agent_version TEXT,
    last_agent_update_status TEXT,
    last_agent_update_ts TIMESTAMP
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
    app_id TEXT NOT NULL,
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
    result_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (computer_id) REFERENCES computers (id) ON DELETE CASCADE
);