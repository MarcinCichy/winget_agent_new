import os
from dotenv import load_dotenv

class AgentConfig:
    """
    Klasa do zarządzania konfiguracją agenta.
    """

    def __init__(self, dotenv_path=".env"):
        # Ładujemy zmienne środowiskowe (jeśli .env jest w innym miejscu, możesz przekazać ścieżkę)
        load_dotenv(dotenv_path)
        self.api_endpoints = [
            os.environ.get("AGENT_API_ENDPOINT", "").strip()
        ]
        # Jeśli planujesz więcej endpointów — np. oddzielasz przecinkiem:
        other = os.environ.get("AGENT_API_ENDPOINTS", "")
        if other:
            self.api_endpoints += [ep.strip() for ep in other.split(",") if ep.strip()]

        self.api_key = os.environ.get("API_KEY", "")
        self.loop_interval = int(os.environ.get("AGENT_LOOP_INTERVAL", "60"))
        self.full_report_interval = int(os.environ.get("AGENT_FULL_REPORT_INTERVAL", "60"))
        self.winget_path_conf = os.environ.get("WINGET_PATH_CONF", "")
        self.blacklist_keywords = [
            kw.strip().lower()
            for kw in os.environ.get("BLACKLIST_KEYWORDS", "").splitlines()
            if kw.strip()
        ]

    def as_dict(self):
        """
        Przydatne, jeśli chcesz przekazywać całą konfigurację jako słownik.
        """
        return {
            "api_endpoints": self.api_endpoints,
            "api_key": self.api_key,
            "loop_interval": self.loop_interval,
            "full_report_interval": self.full_report_interval,
            "winget_path_conf": self.winget_path_conf,
            "blacklist_keywords": self.blacklist_keywords,
        }
