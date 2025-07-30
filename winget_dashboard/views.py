import os
import shutil
import io
import socket
import logging
from flask import (Blueprint, render_template, current_app, send_file, request, flash, redirect, url_for, abort,
                   Response, after_this_request)
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .db import DatabaseManager
from .services import AgentGenerator, ReportGenerator, AgentVersionService

bp = Blueprint('views', __name__)


def _get_suggested_server_address():
    """Sugeruje adres serwera, dając priorytet zmiennej środowiskowej."""
    # Metoda 1: Użyj zmiennej środowiskowej (najlepsza dla Dockera)
    env_url = os.environ.get('SERVER_PUBLIC_URL')
    if env_url:
        return env_url.strip('/')

    # Metoda 2: Spróbuj automatycznie wykryć IP (dla testów lokalnych)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            return f"http://{ip}:5000"
    except Exception:
        # Metoda 3: Fallback, jeśli wszystko inne zawiedzie
        return "http://TWOJ_ADRES_IP:5000"


@bp.route('/')
def index():
    db_manager = DatabaseManager()
    computers_raw = db_manager.get_all_computers()
    version_service = AgentVersionService()
    server_agent_info = version_service.get_server_agent_info()

    offline_threshold = current_app.config['AGENT_OFFLINE_THRESHOLD']
    now_utc = datetime.now(timezone.utc)

    computers = []
    for computer_row in computers_raw:
        computer = dict(computer_row)
        computer['is_offline'] = False  # Domyślnie ustawiamy jako online

        last_report = computer.get('last_report')

        if last_report:
            try:
                last_report_dt = None
                # Sprawdzamy, czy data jest tekstem, czy już obiektem datetime
                if isinstance(last_report, str):
                    last_report_dt = datetime.fromisoformat(last_report).replace(tzinfo=timezone.utc)
                elif isinstance(last_report, datetime):
                    last_report_dt = last_report.replace(tzinfo=timezone.utc)

                # Jeśli udało się przetworzyć datę, sprawdzamy próg
                if last_report_dt:
                    seconds_since_report = (now_utc - last_report_dt).total_seconds()
                    if seconds_since_report > offline_threshold:
                        computer['is_offline'] = True
            except (ValueError, TypeError) as e:
                # Jeśli wystąpi błąd, logujemy go zamiast ignorować
                current_app.logger.warning(
                    f"Nie można przetworzyć znacznika czasu '{last_report}' dla komputera {computer.get('hostname')}: {e}")
                pass
        else:
            # Jeśli nigdy nie było raportu, uznajemy za offline
            computer['is_offline'] = True

        computers.append(computer)

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
    suggested_server_address = _get_suggested_server_address()

    return render_template('settings.html',
                           server_api_key=current_app.config['API_KEY'],
                           server_agent_info=server_agent_info,
                           suggested_next_version=suggested_next_version,
                           suggested_server_address=suggested_server_address,
                           default_blacklist_keywords=current_app.config['DEFAULT_BLACKLIST_KEYWORDS'])


@bp.route('/settings/generate_exe', methods=['POST'])
def generate_exe():
    build_dir = None
    try:
        with open(current_app.config['AGENT_TEMPLATE_PATH'], "r", encoding="utf-8") as f:
            template = f.read()

        agent_generator = AgentGenerator(template)
        config = {k: v for k, v in request.form.items()}

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
        {'report': dict(details['computer']), 'apps': details['apps'], 'updates': details['updates']})
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