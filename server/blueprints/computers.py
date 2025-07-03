from flask import Blueprint, render_template
from server.models import Computer

computers_bp = Blueprint('computers', __name__, url_prefix='/computers')

@computers_bp.route('/', methods=['GET'])
def list_computers():
    computers = Computer.query.all()
    return render_template('computers/list.html', computers=computers)

@computers_bp.route('/<int:computer_id>', methods=['GET'])
def computer_details(computer_id):
    computer = Computer.query.get_or_404(computer_id)
    return render_template('computers/details.html', computer=computer)
