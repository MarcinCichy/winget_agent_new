# winget_dashboard/config.py
import os
from dotenv import load_dotenv

# Wczytaj zmienne z pliku .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))


class Config:
    """Klasa konfiguracyjna dla aplikacji Flask."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    API_KEY = os.environ.get('API_KEY')

    # Ścieżka do bazy danych w folderze 'instance', który jest poza głównym kodem aplikacji
    DATABASE = os.path.join(os.path.dirname(basedir), 'instance', 'winget_dashboard.db')

    # Domyślna czarna lista używana w ustawieniach
    DEFAULT_BLACKLIST_KEYWORDS = """
redistributable
visual c++
.net framework
microsoft
windows
bing
edge
onedrive
office
teams
outlook
store
vcredist
"""
    # Ścieżka do szablonu agenta
    AGENT_TEMPLATE_PATH = os.path.join(basedir, "..", "agent_template.py.txt")