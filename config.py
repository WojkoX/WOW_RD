import os

# To pobiera ścieżkę do folderu I:\TEST
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'twoje-tajne-haslo'
    
    # Budujemy pełną ścieżkę: 
    db_path = os.path.join(basedir, 'instance', 'wow_rd.sqlite')
    
    # SQLite wymaga 4 ukośników dla ścieżek bezwzględnych w Windows: sqlite:///C:\...
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    APP_NAME = "WOW_RD Zabrze"
    VERSION = "0.1"
    OKW_COUNT = 39