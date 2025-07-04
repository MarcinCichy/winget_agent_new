# run.py
from winget_dashboard import create_app

app = create_app()

if __name__ == "__main__":
    # W środowisku produkcyjnym użyj serwera WSGI, np. Gunicorn lub Waitress
    # Przykład z Waitress: waitress-serve --host=0.0.0.0 --port=5000 run:app
    app.run(host='0.0.0.0', port=5000, debug=False)