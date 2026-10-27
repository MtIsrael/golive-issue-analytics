-- Go-Live Issue Analytics: schema (SQLite; standard SQL, ports to SQL Server / PostgreSQL)
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS tdr_results;
DROP TABLE IF EXISTS workstations;
DROP TABLE IF EXISTS sla_targets;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    department_id  INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL,
    unit_type      TEXT    NOT NULL,
    staff_count    INTEGER NOT NULL
);

CREATE TABLE workstations (
    workstation_id INTEGER PRIMARY KEY,
    device_name    TEXT    NOT NULL UNIQUE,   -- e.g. NRMC-02-LBL0051
    department_id  INTEGER NOT NULL REFERENCES departments(department_id),
    device_type    TEXT    NOT NULL,          -- WOW, Desktop, Label Printer, Laser Printer, Badge Tap Reader, Barcode Scanner
    location       TEXT
);

-- Technical Device Readiness: every device is tested before go-live
CREATE TABLE tdr_results (
    tdr_id          INTEGER PRIMARY KEY,
    workstation_id  INTEGER NOT NULL UNIQUE REFERENCES workstations(workstation_id),
    tested_dt       TEXT    NOT NULL,
    initial_result  TEXT    NOT NULL CHECK (initial_result IN ('Pass', 'Fail')),
    fail_reason     TEXT,
    final_status    TEXT    NOT NULL CHECK (final_status IN ('Pass', 'Pass on retest', 'Failed retest', 'Not retested')),
    retest_dt       TEXT
);

CREATE TABLE sla_targets (
    priority      TEXT PRIMARY KEY CHECK (priority IN ('P1', 'P2', 'P3', 'P4')),
    target_hours  REAL NOT NULL
);

-- ServiceNow-style incident tickets logged during the go-live
CREATE TABLE tickets (
    ticket_id           TEXT    PRIMARY KEY,           -- INC#######
    created_dt          TEXT    NOT NULL,
    resolved_dt         TEXT,                          -- NULL while open
    status              TEXT    NOT NULL CHECK (status IN ('Open', 'Resolved')),
    go_live_day         INTEGER NOT NULL,              -- 1 = go-live day; negative = days before go-live
    department_id       INTEGER NOT NULL REFERENCES departments(department_id),
    workstation_id      INTEGER REFERENCES workstations(workstation_id),  -- device-related tickets only
    category            TEXT    NOT NULL,
    subcategory         TEXT    NOT NULL,
    priority            TEXT    NOT NULL REFERENCES sla_targets(priority),
    reported_by_role    TEXT,
    resolver_group      TEXT    NOT NULL,
    resolution          TEXT,
    resolved_at_elbow   INTEGER NOT NULL CHECK (resolved_at_elbow IN (0, 1)),
    first_response_min  REAL,
    shift               TEXT    NOT NULL CHECK (shift IN ('Day', 'Night'))
);

CREATE INDEX ix_tix_day      ON tickets (go_live_day, category);
CREATE INDEX ix_tix_dept     ON tickets (department_id);
CREATE INDEX ix_tix_ws       ON tickets (workstation_id);
CREATE INDEX ix_ws_dept      ON workstations (department_id);
