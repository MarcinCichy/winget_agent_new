from flask import Blueprint, render_template, redirect, url_for, flash
from server.models import db, Task, Computer
from server.forms import TaskForm

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

@tasks_bp.route('/', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    return render_template('tasks/list.html', tasks=tasks)

@tasks_bp.route('/create', methods=['GET', 'POST'])
def create_task():
    form = TaskForm()
    form.computer_id.choices = [(c.id, c.hostname) for c in Computer.query.all()]
    if form.validate_on_submit():
        task = Task(
            computer_id=form.computer_id.data,
            command=form.command.data,
            payload=form.payload.data
        )
        db.session.add(task)
        db.session.commit()
        flash("Dodano nowe zadanie!", "success")
        return redirect(url_for('tasks.list_tasks'))
    return render_template('tasks/create.html', form=form)
