from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Computer(db.Model):
    __tablename__ = "computers"
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String, unique=True, nullable=False)
    ip_address = db.Column(db.String, nullable=False)
    reboot_required = db.Column(db.Boolean, default=False)
    last_report = db.Column(db.DateTime)

    reports = db.relationship("Report", backref="computer", lazy=True)
    tasks = db.relationship("Task", backref="computer", lazy=True)  # Dodane: relacja do Task

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    report_timestamp = db.Column(db.DateTime)
    applications = db.relationship("Application", backref="report", lazy=True)
    updates = db.relationship("Update", backref="report", lazy=True)

class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    name = db.Column(db.String, nullable=False)
    version = db.Column(db.String)
    app_id = db.Column(db.String)

class Update(db.Model):
    __tablename__ = "updates"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    name = db.Column(db.String, nullable=False)
    app_id = db.Column(db.String)
    current_version = db.Column(db.String)
    available_version = db.Column(db.String)
    update_type = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default="Do uaktualnienia")

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    command = db.Column(db.String, nullable=False)
    payload = db.Column(db.String)
    status = db.Column(db.String, default="oczekuje")
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

class BlacklistKeyword(db.Model):
    __tablename__ = "blacklist_keywords"
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String, unique=True, nullable=False)
