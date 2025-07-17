# winget_dashboard/config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))


class Config:
    """Klasa konfiguracyjna dla aplikacji Flask."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    API_KEY = os.environ.get('API_KEY')

    # WRACAMY DO TEJ METODY: Ustaw tutaj wersję agenta, która jest obecnie na serwerze.
    # Zmieniaj ją ręcznie po wgraniu nowego pliku agent.exe
    AGENT_VERSION = "1.1.0"

    DATABASE = os.path.join(os.path.dirname(basedir), 'instance', 'winget_dashboard.db')

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
    AGENT_TEMPLATE_PATH = os.path.join(basedir, "..", "agent_template.py.txt")