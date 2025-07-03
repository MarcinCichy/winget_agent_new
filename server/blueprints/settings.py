from flask import Blueprint, render_template, request, flash, redirect, url_for
from server.forms import SettingsForm

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    if form.validate_on_submit():
        # Logika generowania EXE z parametrem (czy ma być jako usługa)
        flash("Agent został wygenerowany!", "success")
        return redirect(url_for('settings.settings'))
    return render_template('settings/settings.html', form=form)
