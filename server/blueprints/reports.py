from flask import Blueprint, render_template
from server.models import Report

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/', methods=['GET'])
def list_reports():
    reports = Report.query.order_by(Report.report_timestamp.desc()).all()
    return render_template('reports/list.html', reports=reports)

@reports_bp.route('/<int:report_id>', methods=['GET'])
def report_details(report_id):
    report = Report.query.get_or_404(report_id)
    return render_template('reports/details.html', report=report)
