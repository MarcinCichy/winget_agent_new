from flask import Blueprint, request, jsonify, abort, current_app, url_for, send_from_directory, flash
from functools import wraps
from .db import DatabaseManager
import os

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
    computer_id = db_manager.save_report(data)
    if computer_id:
        apps_still_needing_update = {
            update['id'] for update in data.get('available_app_updates', [])
        }
        active_update_tasks = db_manager.get_active_tasks_for_computer(computer_id, command_filter='update_package')
        tasks_to_remove = []
        for task in active_update_tasks:
            if task['payload'] not in apps_still_needing_update:
                tasks_to_remove.append(task['id'])
        if tasks_to_remove:
            db_manager.delete_tasks(tasks_to_remove)
            current_app.logger.info(
                f"Wyczyszczono {len(tasks_to_remove)} nieaktualnych zadań aktualizacji dla komputera ID {computer_id}.")
        return "Report received and tasks cleaned successfully", 200
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
    details = data.get('details')
    if not task_id or not status:
        return "Bad Request", 400
    db_manager = DatabaseManager()
    db_manager.update_task_status(task_id, status, details)
    return "Result received", 200


@bp.route('/settings/blacklist/<hostname>', methods=['GET'])
@require_api_key
def get_blacklist(hostname):
    db_manager = DatabaseManager()
    keywords_str = db_manager.get_computer_blacklist(hostname)
    if not keywords_str:
        default_keywords_raw = current_app.config['DEFAULT_BLACKLIST_KEYWORDS']
        keywords_list = [line.strip() for line in default_keywords_raw.strip().split('\n') if line.strip()]
    else:
        keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
    return jsonify(keywords_list)


@bp.route('/computer/<int:computer_id>/refresh', methods=['POST'])
def request_refresh(computer_id):
    db_manager = DatabaseManager()
    task_id = db_manager.create_task(computer_id, 'force_report', '{}')
    return jsonify({"status": "success", "message": "Zadanie odświeżenia zlecone", "task_id": task_id})


@bp.route('/computer/<int:computer_id>/update', methods=['POST'])
def request_update(computer_id):
    data = request.get_json()
    package_id = data.get('package_id')
    force = data.get('force', False)
    command = 'update_package' if force else 'request_update'
    db_manager = DatabaseManager()
    task_id = db_manager.create_task(
        computer_id=computer_id,
        command=command,
        payload=package_id
    )
    return jsonify({"status": "success", "message": f"Zadanie ({command}) zlecone", "task_id": task_id})


@bp.route('/computer/<int:computer_id>/uninstall', methods=['POST'])
def request_uninstall(computer_id):
    data = request.get_json()
    package_id = data.get('package_id')
    force = data.get('force', False)
    command = 'uninstall_package' if force else 'request_uninstall'
    db_manager = DatabaseManager()
    task_id = db_manager.create_task(
        computer_id=computer_id,
        command=command,
        payload=package_id
    )
    return jsonify({"status": "success", "message": f"Zadanie ({command}) zlecone", "task_id": task_id})


@bp.route('/computer/<int:computer_id>/blacklist', methods=['POST'])
def update_blacklist(computer_id):
    data = request.get_json()
    new_blacklist_raw = data.get('blacklist_keywords', '')
    keywords = [k.strip() for k in new_blacklist_raw.split(',') if k.strip()]
    clean_blacklist_str = ", ".join(keywords)
    db_manager = DatabaseManager()
    computer_details = db_manager.get_computer_details_by_id(computer_id)
    if not computer_details:
        return jsonify({"status": "error", "message": "Nie znaleziono komputera"}), 404
    hostname = computer_details['computer']['hostname']
    db_manager.update_computer_blacklist(hostname, clean_blacklist_str)
    return jsonify({"status": "success", "message": "Czarna lista zaktualizowana."})


@bp.route('/task_status/<int:task_id>', methods=['GET'])
def task_status(task_id):
    db_manager = DatabaseManager()
    task = db_manager.get_task_details(task_id)
    if task:
        return jsonify(dict(task))
    else:
        active_task = db_manager.get_task_status(task_id)
        if active_task:
            return jsonify({"status": active_task})
        return jsonify({"status": "zakończone"}), 200


@bp.route('/agent/download/latest', methods=['GET'])
def download_latest_agent():
    builds_dir = os.path.join(current_app.root_path, '..', 'agent_builds')
    current_app.logger.info(f"Próba serwowania pliku agent.exe z katalogu: {builds_dir}")
    return send_from_directory(builds_dir, 'agent.exe', as_attachment=True)


@bp.route('/computer/<int:computer_id>/agent_update', methods=['POST'])
def request_agent_update(computer_id):
    base_url = request.host_url.strip('/')
    download_url = f"{base_url}{url_for('api.download_latest_agent')}"
    payload = {'download_url': download_url}

    db_manager = DatabaseManager()
    task_id = db_manager.create_task(
        computer_id=computer_id,
        command='self_update',
        payload=payload
    )
    current_app.logger.info(f"Zlecono zadanie aktualizacji dla komputera ID {computer_id} z URL: {download_url}")
    return jsonify({"status": "success", "message": "Zlecono zadanie aktualizacji agenta", "task_id": task_id})


@bp.route('/agent/update_status', methods=['POST'])
def agent_update_status():
    """Endpoint wywoływany przez updater.py po próbie aktualizacji."""
    data = request.get_json()
    hostname, status = data.get('hostname'), data.get('status')
    if not hostname or not status:
        return "Bad Request", 400

    db_manager = DatabaseManager()
    db_manager.update_agent_update_status(hostname, status)

    computer_details = db_manager.get_computer_details(hostname)
    if computer_details:
        active_tasks = db_manager.get_active_tasks_for_computer(computer_details['computer']['id'],
                                                                command_filter='self_update')
        if active_tasks:
            task_ids_to_remove = [task['id'] for task in active_tasks]
            db_manager.delete_tasks(task_ids_to_remove)
            current_app.logger.info(f"Wyczyszczono {len(task_ids_to_remove)} zadań self-update dla {hostname}.")

    return "Status received", 200


@bp.route('/agent/deploy_update', methods=['POST'])
def deploy_update_to_all():
    db_manager = DatabaseManager()
    computers = db_manager.get_all_computers()

    if not computers:
        # Zmieniamy odpowiedź na bardziej czytelną dla JS
        return jsonify({"status": "warning", "message": "Brak komputerów w bazie danych do aktualizacji."}), 200

    base_url = request.host_url.strip('/')
    download_url = f"{base_url}{url_for('api.download_latest_agent')}"
    payload = {'download_url': download_url}

    tasks_created_count = 0
    for computer in computers:
        db_manager.create_task(
            computer_id=computer['id'],
            command='self_update',
            payload=payload
        )
        tasks_created_count += 1

    message = f"Pomyślnie zlecono zadanie aktualizacji dla {tasks_created_count} komputerów."
    current_app.logger.info(message)
    # Zwracamy sukces i liczbę zleconych zadań
    return jsonify({"status": "success", "message": message, "count": tasks_created_count})
