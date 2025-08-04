# run.py
from winget_dashboard import create_app
from waitress import serve

app = create_app()

if __name__ == "__main__":
    # Używamy stabilnego serwera Waitress zamiast deweloperskiego Flask
    print("Starting server with Waitress on http://0.0.0.0:5000")
    serve(app, host='0.0.0.0', port=5000)