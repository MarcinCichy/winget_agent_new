# winget_dashboard/views.py
import os
import logging
from flask import (
    Blueprint, render_template, current_app, send_file, request,
    flash, redirect, url_for, abort, send_from_directory, Response
)
from datetime import datetime
from .db import DatabaseManager
from .services import AgentGenerator, ReportGenerator

bp = Blueprint('views', __name__)

@bp.route('/')
def index():
    db_manager = DatabaseManager()
    computers = db_manager.get_all_computers()
    return render_template('index.html', computers=computers, style_url=url_for('static', filename='style.css'))

@bp.route('/computer/<hostname>')
def computer_details(hostname):
    db_manager = DatabaseManager()
    details = db_manager.get_computer_details(hostname)
    if not details: abort(404)
    return render_template('computer.html', **details, style_url=url_for('static', filename='style.css'))

@bp.route('/computer/<hostname>/history')
def computer_history(hostname):
    db_manager = DatabaseManager()
    history = db_manager.get_computer_history(hostname)
    if not history: abort(404)
    return render_template('history.html', **history, style_url=url_for('static', filename='style.css'))

@bp.route('/report/<int:report_id>')
def view_report(report_id):
    db_manager = DatabaseManager()
    report_data = db_manager.get_report_details(report_id)
    if not report_data: abort(404)
    return render_template('report_view.html', **report_data, style_url=url_for('static', filename='style.css'))

@bp.route('/settings')
def settings():
    return render_template('settings.html',
                           server_api_key=current_app.config['API_KEY'],
                           default_blacklist_keywords=current_app.config['DEFAULT_BLACKLIST_KEYWORDS'],
                           style_url=url_for('static', filename='style.css'))


@bp.route('/settings/generate_exe', methods=['POST'])
def generate_exe():
    try:
        with open(current_app.config['AGENT_TEMPLATE_PATH'], "r", encoding="utf-8") as f:
            template = f.read()
        agent_generator = AgentGenerator(template)
        config = {k: v for k, v in request.form.items()}
        exe_path = agent_generator.generate_exe(config)
        return send_file(exe_path, as_attachment=True, download_name='WingetAgentInstaller.exe',
                         mimetype='application/vnd.microsoft.portable-executable')
    except Exception as e:
        logging.error(f"Błąd podczas generowania EXE: {e}", exc_info=True)
        flash(f"Wystąpił nieoczekiwany błąd serwera: {e}", "error")
        return redirect(url_for('views.settings'))


@bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


# --- Trasy do generowania raportów ---
@bp.route('/report/computer/<int:computer_id>')
def report_single(computer_id):
    db_manager = DatabaseManager()
    computer = db_manager.get_computer_details_by_id(computer_id)['computer']
    if not computer: abort(404)

    report_generator = ReportGenerator(db_manager)
    content = report_generator.generate_report_content([computer_id])
    filename = f"report_{computer['hostname']}_{datetime.now().strftime('%Y%m%d')}.txt"
    return Response(content, mimetype='text/plain', headers={"Content-disposition": f"attachment; filename={filename}"})


@bp.route('/report/all')
def report_all():
    db_manager = DatabaseManager()
    computers = db_manager.get_all_computers()
    computer_ids = [c['id'] for c in computers]

    report_generator = ReportGenerator(db_manager)
    content = report_generator.generate_report_content(computer_ids)
    filename = f"report_zbiorczy_{datetime.now().strftime('%Y%m%d')}.txt"
    return Response(content, mimetype='text/plain', headers={"Content-disposition": f"attachment; filename={filename}"})