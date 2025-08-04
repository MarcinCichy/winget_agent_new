# winget_dashboard/__init__.py
import os
from flask import Flask, render_template
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import sqlite3


def create_app(test_config=None):
    """Tworzy i konfiguruje instancję aplikacji Flask."""
    app = Flask(__name__, instance_relative_config=True)

    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Załaduj konfigurację
    from . import config
    app.config.from_object(config.Config)

    # Upewnij się, że folder 'instance' istnieje
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Inicjalizacja bazy danych
    from . import db
    db.init_app(app)

    # Rejestracja Blueprintów (modułów z trasami)
    from . import views
    app.register_blueprint(views.bp)

    from . import api
    app.register_blueprint(api.bp)

    # Filtry Jinja2 i procesory kontekstu
    @app.template_filter('to_local_time')
    def to_local_time_filter(utc_str):
        if not utc_str: return "N/A"
        try:
            # Upewnij się, że mamy do czynienia z poprawnym stringiem ISO
            utc_dt = datetime.fromisoformat(str(utc_str).split('.')[0]).replace(tzinfo=ZoneInfo("UTC"))
            # Strefa czasowa dla Polski
            local_dt = utc_dt.astimezone(ZoneInfo("Europe/Warsaw"))
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return utc_str

    @app.context_processor
    def inject_year():
        return {'current_year': datetime.now(ZoneInfo("UTC")).year}

    # Zapobieganie cache'owaniu stron w przeglądarce
    @app.after_request
    def add_header(response):
        if 'text/html' in response.content_type:
            response.headers[
                'Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
        return response

    # <-- POCZĄTEK DODANEGO FRAGMENTU -->
    # Dedykowana obsługa błędów bazy danych (np. brakująca kolumna)
    @app.errorhandler(sqlite3.OperationalError)
    def handle_db_operational_error(error):
        """Wyświetla przyjazną stronę błędu, gdy schemat DB jest nieaktualny."""
        app.logger.critical(
            f"Wystąpił błąd operacji na bazie danych. Prawdopodobnie schemat jest nieaktualny. Błąd: {error}",
            exc_info=True
        )
        # Zwracamy naszą nową stronę błędu i kod HTTP 500
        return render_template('db_error.html', error=error), 500
    # <-- KONIEC DODANEGO FRAGMENTU -->

    return app