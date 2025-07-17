import os
import logging
import shutil
import io
from flask import (Blueprint, render_template, current_app, send_file, request, flash, redirect, url_for, abort,
                   Response, after_this_request)
from datetime import datetime
from .db import DatabaseManager
from .services import AgentGenerator, ReportGenerator, AgentVersionService

bp = Blueprint('views', __name__)


@bp.route('/')
def index():
    db_manager = DatabaseManager()
    computers = db_manager.get_all_computers()
    version_service = AgentVersionService()
    server_agent_info = version_service.get_server_agent_info()
    return render_template('index.html', computers=computers, server_agent_info=server_agent_info)


@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    version_service = AgentVersionService()

    if request.method == 'POST':
        if 'new_version' in request.form:
            new_version = request.form.get('new_version')
            if 'agent_file' not in request.files or not request.files['agent_file'].filename:
                flash('Nie wybrano pliku agent.exe do wgrania.', 'error')
                return redirect(url_for('views.settings'))

            if not new_version:
                flash('Musisz podać numer nowej wersji.', 'error')
                return redirect(url_for('views.settings'))

            file = request.files['agent_file']
            if file and file.filename.endswith('.exe'):
                try:
                    agent_builds_dir = os.path.join(current_app.root_path, '..', 'agent_builds')
                    file.save(os.path.join(agent_builds_dir, 'agent.exe'))
                    version_service.set_server_agent_version(new_version)
                    flash(f'Pomyślnie wgrano agenta i ustawiono wersję serwera na: {new_version}', 'success')
                except Exception as e:
                    flash(f'Wystąpił błąd podczas zapisu pliku lub wersji: {e}', 'error')
            else:
                flash('Dozwolone są tylko pliki .exe', 'error')
            return redirect(url_for('views.settings'))

    server_agent_info = version_service.get_server_agent_info()
    suggested_next_version = version_service.get_suggested_next_version()

    return render_template('settings.html',
                           server_api_key=current_app.config['API_KEY'],
                           server_agent_info=server_agent_info,
                           suggested_next_version=suggested_next_version,
                           default_blacklist_keywords=current_app.config['DEFAULT_BLACKLIST_KEYWORDS'])


@bp.route('/settings/generate_exe', methods=['POST'])
def generate_exe():
    build_dir = None
    try:
        with open(current_app.config['AGENT_TEMPLATE_PATH'], "r", encoding="utf-8") as f:
            template = f.read()

        agent_generator = AgentGenerator(template)
        config = {k: v for k, v in request.form.items()}

        # Wersja jest teraz brana bezpośrednio z formularza generatora
        agent_version_to_generate = config.get('agent_version', '0.0.0')

        exe_path = agent_generator.generate_exe(config)
        build_dir = os.path.dirname(os.path.dirname(exe_path))
        buffer = io.BytesIO()
        with open(exe_path, 'rb') as f:
            buffer.write(f.read())
        buffer.seek(0)

        @after_this_request
        def cleanup(response):
            if build_dir and os.path.exists(build_dir): shutil.rmtree(build_dir, ignore_errors=True)
            return response

        return send_file(buffer, as_attachment=True, download_name=f'agent.exe',
                         mimetype='application/vnd.microsoft.portable-executable')
    except Exception as e:
        if build_dir and os.path.exists(build_dir): shutil.rmtree(build_dir, ignore_errors=True)
        logging.error(f"Błąd podczas generowania EXE: {e}", exc_info=True)
        flash(f"Wystąpił nieoczekiwany błąd serwera: {e}", "error")
        return redirect(url_for('views.settings'))


# ... (reszta tras bez zmian) ...
@bp.route('/computer/<hostname>')
def computer_details(hostname):
    db_manager = DatabaseManager()
    details = db_manager.get_computer_details(hostname)
    if not details: abort(404)
    details['editable_blacklist'] = db_manager.get_computer_blacklist(hostname)
    details['task_statuses'] = db_manager.get_computer_tasks(details['computer']['id'])
    return render_template('computer.html', **details)


@bp.route('/computer/<hostname>/history')
def computer_history(hostname):
    db_manager = DatabaseManager()
    search_params = {'start_date': request.args.get('start_date', ''), 'end_date': request.args.get('end_date', ''),
                     'keyword': request.args.get('keyword', '')}
    clean_search_params = {k: v for k, v in search_params.items() if v}
    history = db_manager.get_computer_history(hostname, search_params=clean_search_params)
    if not history: abort(404)
    history['search_params'] = search_params
    return render_template('history.html', **history)


@bp.route('/report/<int:report_id>')
def view_report(report_id):
    db_manager = DatabaseManager()
    report_data = db_manager.get_report_details(report_id)
    if not report_data: abort(404)
    return render_template('report_view.html', **report_data)


@bp.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


@bp.route('/report/computer/<int:computer_id>')
def report_single(computer_id):
    db_manager = DatabaseManager()
    details = db_manager.get_computer_details_by_id(computer_id)
    if not details: abort(404)
    report_generator = ReportGenerator(db_manager)
    content = report_generator.generate_single_report_content(
        {'report': details['computer'], 'apps': details['apps'], 'updates': details['updates']})
    computer = details['computer']
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


@bp.route('/report/history/<int:report_id>')
def report_from_history(report_id):
    db_manager = DatabaseManager()
    report_data = db_manager.get_report_details(report_id)
    if not report_data: abort(404)
    report_generator = ReportGenerator(db_manager)
    content = report_generator.generate_single_report_content(report_data)
    report_info = report_data['report']
    hostname, report_dt = report_info['hostname'], report_info['report_timestamp']
    timestamp_str = report_dt.strftime('%Y%m%d_%H%M%S')
    filename = f"report_{hostname}_{timestamp_str}.txt"
    return Response(content, mimetype='text/plain', headers={"Content-disposition": f"attachment; filename={filename}"})