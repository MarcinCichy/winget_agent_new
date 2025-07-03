import os
from flask import Flask
from dotenv import load_dotenv
from models import db  # <-- TO DODAŁEM!

# Ładuj zmienne środowiskowe z .env w katalogu server/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///winget.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # <-- TO DODAŁEM!

# Przykład: ładowanie blacklisty z .env (możesz użyć, jeśli chcesz zarządzać nią też po stronie serwera)
BLACKLIST_KEYWORDS = [
    kw.strip().lower()
    for kw in os.environ.get("BLACKLIST_KEYWORDS", "").splitlines()
    if kw.strip()
]
