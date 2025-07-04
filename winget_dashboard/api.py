# winget_dashboard/api.py
from flask import Blueprint, request, jsonify, abort, current_app
from functools import wraps
from .db import DatabaseManager

bp = Blueprint('api', __name__, url_prefix='/api')


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-Key') and request.headers.get('X-API-Key') == current_app.config['API_KEY']:
            return f(*args, **kwargs)
        abort(401)

    return decorated_function


@bp.route('/report', methods=['POST'])
@require_api_key
def receive_report():
    data = request.get_json()
    if not data or 'hostname' not in data:
        return "Bad Request", 400

    db_manager = DatabaseManager()
    if db_manager.save_report(data):
        return "Report received successfully", 200
    else:
        return "Internal Server Error", 500


@bp.route('/tasks/<hostname>', methods=['GET'])
@require_api_key
def get_tasks(hostname):
    db_manager = DatabaseManager()
    tasks = db_manager.get_pending_tasks(hostname)
    return jsonify(tasks)


@bp.route('/tasks/result', methods=['POST'])
@require_api_key
def task_result():
    data = request.get_json()
    task_id, status = data.get('task_id'), data.get('status')
    if not task_id or not status:
        return "Bad Request", 400

    db_manager = DatabaseManager()
    db_manager.update_task_status(task_id, status)
    return "Result received", 200


@bp.route('/settings/blacklist', methods=['GET'])
@require_api_key
def get_blacklist():
    keywords_str = current_app.config['DEFAULT_BLACKLIST_KEYWORDS']
    keywords = [line.strip() for line in keywords_str.strip().split('\n') if line.strip()]
    return jsonify(keywords)

# --- NOWE TRASY DLA PRZYCISKÓW W PANELU ---

@bp.route('/computer/<int:computer_id>/refresh', methods=['POST'])
def request_refresh(computer_id):
    db_manager = DatabaseManager()
    db_manager.create_task(computer_id, 'force_report', '{}')
    return jsonify({"status": "success", "message": "Zadanie odświeżenia zlecone"})

@bp.route('/computer/<int:computer_id>/update', methods=['POST'])
def request_update(computer_id):
    data = request.get_json()
    db_manager = DatabaseManager()
    db_manager.create_task(
        computer_id=computer_id,
        command='update_package',
        payload=data.get('package_id'),
        update_id=data.get('update_id') # Przekazujemy ID aktualizacji do oznaczenia
    )
    return jsonify({"status": "success", "message": "Zadanie aktualizacji zlecone"})

@bp.route('/computer/<int:computer_id>/uninstall', methods=['POST'])
def request_uninstall(computer_id):
    data = request.get_json()
    db_manager = DatabaseManager()
    db_manager.create_task(
        computer_id=computer_id,
        command='uninstall_package',
        payload=data.get('package_id')
    )
    return jsonify({"status": "success", "message": "Zadanie deinstalacji zlecone"})