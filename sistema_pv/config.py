import os
import sys

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-temporal-cambiar'
    
    # --- LÓGICA PARA GUARDAR LA BD JUNTO AL EJECUTABLE ---
    if getattr(sys, 'frozen', False):
        # Estamos en un .exe: obtener la carpeta donde está el ejecutable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Modo desarrollo: usar la carpeta del proyecto
        base_dir = os.path.abspath(os.path.dirname(__file__))

    # Crear la carpeta si no existe (por si acaso)
    os.makedirs(base_dir, exist_ok=True)

    db_path = os.path.join(base_dir, 'database.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False