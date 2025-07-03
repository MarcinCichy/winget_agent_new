from flask import Blueprint, render_template, redirect, url_for, flash
from server.models import db, BlacklistKeyword
from server.forms import BlacklistForm

blacklist_bp = Blueprint('blacklist', __name__, url_prefix='/blacklist')

@blacklist_bp.route('/', methods=['GET', 'POST'])
def blacklist():
    form = BlacklistForm()
    if form.validate_on_submit():
        keyword = form.keyword.data
        if not BlacklistKeyword.query.filter_by(keyword=keyword).first():
            db.session.add(BlacklistKeyword(keyword=keyword))
            db.session.commit()
            flash("Dodano słowo do blacklisty!", "success")
        else:
            flash("To słowo już istnieje!", "warning")
        return redirect(url_for('blacklist.blacklist'))
    blacklist = BlacklistKeyword.query.all()
    return render_template('blacklist/list.html', form=form, blacklist=blacklist)
