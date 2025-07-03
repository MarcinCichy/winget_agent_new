from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired

class BlacklistForm(FlaskForm):
    keyword = StringField('Słowo kluczowe', validators=[DataRequired()])
    submit = SubmitField('Dodaj')

class TaskForm(FlaskForm):
    computer_id = SelectField('Komputer', coerce=int, validators=[DataRequired()])
    command = SelectField('Komenda', choices=[('upgrade', 'Upgrade'), ('uninstall', 'Uninstall')], validators=[DataRequired()])
    payload = StringField('Payload')
    submit = SubmitField('Utwórz zadanie')

class SettingsForm(FlaskForm):
    service_mode = BooleanField('Uruchamiaj jako usługę systemową Windows')
    submit = SubmitField('Generuj agenta')
