import os
import logging
import shutil
import io
from flask import (
    Blueprint, render_template, current_app, send_file, request,
    flash, redirect, url_for, abort, send_from_directory, Response, after_this_request
)
from datetime import datetime
from .db import DatabaseManager
from .services import AgentGenerator, ReportGenerator

bp = Blueprint('views', __name__)


@bp.route('/')
def index():
    db_manager = DatabaseManager()
    computers = db_manager.get_all_computers()
    return render_template('index.html', computers=computers)


@bp.route('/computer/<hostname>')
def computer_details(hostname):
    db_manager = DatabaseManager()

    # 1. Pobieramy wszystkie szczegóły (tak jak wcześniej)
    details = db_manager.get_computer_details(hostname)
    if not details: abort(404)

    # 2. OMIJAMY PROBLEM: Ignorujemy potencjalnie błędną czarną listę z powyższego zapytania
    #    i zamiast tego wywołujemy funkcję, o której udowodniliśmy, że działa poprawnie.
    editable_blacklist = db_manager.get_computer_blacklist(hostname)

    # 3. Wstawiamy poprawną wartość do słownika, który trafi do szablonu.
    details['editable_blacklist'] = editable_blacklist

    return render_template('computer.html', **details)


@bp.route('/computer/<hostname>/history')
def computer_history(hostname):
    db_manager = DatabaseManager()
    history = db_manager.get_computer_history(hostname)
    if not history: abort(404)
    return render_template('history.html', **history)


@bp.route('/report/<int:report_id>')
def view_report(report_id):
    db_manager = DatabaseManager()
    report_data = db_manager.get_report_details(report_id)
    if not report_data: abort(404)
    return render_template('report_view.html', **report_data)


@bp.route('/settings')
def settings():
    return render_template('settings.html',
                           server_api_key=current_app.config['API_KEY'],
                           default_blacklist_keywords=current_app.config['DEFAULT_BLACKLIST_KEYWORDS'])


@bp.route('/settings/generate_exe', methods=['POST'])
def generate_exe():
    build_dir = None
    try:
        with open(current_app.config['AGENT_TEMPLATE_PATH'], "r", encoding="utf-8") as f:
            template = f.read()

        agent_generator = AgentGenerator(template)
        config = {k: v for k, v in request.form.items()}

        exe_path = agent_generator.generate_exe(config)
        build_dir = os.path.dirname(os.path.dirname(exe_path))

        buffer = io.BytesIO()
        with open(exe_path, 'rb') as f:
            buffer.write(f.read())
        buffer.seek(0)

        @after_this_request
        def cleanup(response):
            try:
                if build_dir and os.path.exists(build_dir):
                    shutil.rmtree(build_dir)
                    logging.info(f"Usunięto katalog tymczasowy: {build_dir}")
            except Exception as e:
                logging.error(f"Nie udało się usunąć katalogu tymczasowego {build_dir}: {e}")
            return response

        return send_file(
            buffer,
            as_attachment=True,
            download_name='agent.exe',
            mimetype='application/vnd.microsoft.portable-executable'
        )

    except Exception as e:
        if build_dir and os.path.exists(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
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
    computer_data = db_manager.get_computer_details_by_id(computer_id)
    if not computer_data:
        abort(404)
    computer = computer_data['computer']

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