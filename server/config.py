import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///winget_dashboard.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Dalsze opcje wg potrzeby