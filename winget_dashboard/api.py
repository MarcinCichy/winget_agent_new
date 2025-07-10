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
    computer_id = db_manager.save_report(data)

    if computer_id:
        # --- NOWA LOGIKA CZYSZCZENIA ---
        # Pobierz ID pakietów, które wciąż są na liście do aktualizacji
        apps_still_needing_update = {
            update['id'] for update in data.get('available_app_updates', [])
        }

        # Pobierz wszystkie aktywne zadania aktualizacji dla tego komputera
        active_update_tasks = db_manager.get_active_tasks_for_computer(computer_id, command_filter='update_package')

        tasks_to_remove = []
        for task in active_update_tasks:
            # Jeśli zadanie dotyczy pakietu, którego nie ma już na liście "do aktualizacji",
            # oznacza to, że aktualizacja się powiodła (przez agenta lub ręcznie).
            if task['payload'] not in apps_still_needing_update:
                tasks_to_remove.append(task['id'])

        if tasks_to_remove:
            db_manager.delete_tasks(tasks_to_remove)
            current_app.logger.info(
                f"Wyczyszczono {len(tasks_to_remove)} nieaktualnych zadań aktualizacji dla komputera ID {computer_id}.")

        return "Report received and tasks cleaned successfully", 200
        # --- KONIEC NOWEJ LOGIKI ---
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
    db_manager = DatabaseManager()
    task_id = db_manager.create_task(
        computer_id=computer_id,
        command='update_package',
        payload=data.get('package_id')
    )
    return jsonify({"status": "success", "message": "Zadanie aktualizacji zlecone", "task_id": task_id})


@bp.route('/computer/<int:computer_id>/uninstall', methods=['POST'])
def request_uninstall(computer_id):
    data = request.get_json()
    db_manager = DatabaseManager()
    task_id = db_manager.create_task(
        computer_id=computer_id,
        command='uninstall_package',
        payload=data.get('package_id')
    )
    return jsonify({"status": "success", "message": "Zadanie deinstalacji zlecone", "task_id": task_id})


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
    status = db_manager.get_task_status(task_id)
    if status:
        return jsonify({"status": status})
    else:
        return jsonify({"status": "not_found"}), 404


@bp.route('/computers/refresh_all', methods=['POST'])
def request_refresh_all():
    db_manager = DatabaseManager()
    computers = db_manager.get_all_computers()
    task_ids = []
    for computer in computers:
        task_id = db_manager.create_task(computer['id'], 'force_report', '{}')
        task_ids.append(task_id)

    return jsonify({
        "status": "success",
        "message": f"Zlecono odświeżenie dla {len(task_ids)} komputerów.",
        "task_count": len(task_ids)
    })