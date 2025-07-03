from flask import Blueprint, render_template
from server.models import Computer, Report, Task

bp = Blueprint('dashboard', __name__, url_prefix='/')

@bp.route('/')
def index():
    computers_count = Computer.query.count()
    last_reports = (
        Report.query.order_by(Report.report_timestamp.desc()).limit(10).all()
    )
    pending_tasks = Task.query.filter(Task.status == "pending").count()
    return render_template(
        'dashboard.html',
        computers_count=computers_count,
        last_reports=last_reports,
        pending_tasks=pending_tasks
    )
