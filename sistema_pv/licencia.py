import json
import base64
import datetime
import hashlib
import platform
import subprocess
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

# --- CLAVE PÚBLICA INCRUSTADA (copia la que generaste) ---
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqslle9YvFqSVTXictsz0
iq35KkLTRbLtLRw2lb1ATI2lAwj3FTPTabHvnU7N2EG68IjK9YLXKiNX89nzWML/
h1pXMSk0nef12Nkct7lmw8eKXSg2OFVw1VkyHH+NTvBCb200Bxd4bR3rXpmOiDSY
MZH5BD4Z7jZFKNpmjA6gYndch1xu+Q62vzmTuVdX2WydZcQQyLRrHH94ScYuF1ur
jCV5sKIzUkAXFmQtQD1bfNXoQ9WDwQEz8svh5meUGtPKXOLdiFtJv6k2C5PasrJu
0b9TLU06QKnHyEeASq1wRAaofDoaCH5k3ZyG7yGqGhQkkVg91uQBJWdt4BtFjSoY
RQIDAQAB
-----END PUBLIC KEY-----"""

# --- Obtener fingerprint del equipo ---
def get_fingerprint():
    system = platform.system()
    serial = ""
    creationflags = 0

    if system == "Windows":
        try:
            creationflags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(['wmic', 'path', 'win32_physicalmedia', 'get', 'serialnumber'],
                                    capture_output=True, text=True, check=True,
                                    creationflags=creationflags)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                serial = lines[1].strip()
        except:
            pass
    elif system == "Linux":
        try:
            with open('/sys/class/dmi/id/product_serial', 'r') as f:
                serial = f.read().strip()
        except:
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(['system_profiler', 'SPHardwareDataType'],
                                    capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n'):
                if 'Serial Number (system)' in line:
                    serial = line.split(':')[1].strip()
                    break
        except:
            pass

    if not serial or serial in ('0', 'To be filled by O.E.M.'):
        import uuid
        serial = str(uuid.getnode())

    return hashlib.sha256(serial.encode()).hexdigest()


# --- Verificar código de licencia ingresado por el usuario ---
def verificar_codigo_licencia(codigo):
    """
    Recibe un código de licencia (string) y devuelve (True, datos) si es válido,
    o (False, mensaje_error) si no.
    El código tiene formato: "datos_json.firma_base64"
    """
    try:
        # El código es: "json_data|firma_base64"
        if '|' not in codigo:
            return False, "Formato de código inválido"
        json_data, firma_b64 = codigo.split('|', 1)
        firma = base64.b64decode(firma_b64)

        # Cargar clave pública
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())

        # Verificar firma
        public_key.verify(
            firma,
            json_data.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # Si la firma es correcta, cargar datos
        datos = json.loads(json_data)

        # Verificar que el fingerprint coincida
        fingerprint_actual = get_fingerprint()
        if datos['fingerprint'] != fingerprint_actual:
            return False, "Este código no corresponde a este equipo"

        # Verificar expiración
        fecha_exp = datetime.datetime.strptime(datos['expira'], '%Y-%m-%d').date()
        if fecha_exp < datetime.date.today():
            return False, "La licencia ha expirado"

        return True, datos

    except Exception as e:
        return False, f"Error al verificar licencia: {str(e)}"


# --- Validar si ya existe licencia guardada ---
def validar_licencia_guardada():
    archivo = "licencia.dat"
    if not os.path.exists(archivo):
        return False, "No hay licencia guardada"
    try:
        with open(archivo, 'r') as f:
            codigo = f.read().strip()
        return verificar_codigo_licencia(codigo)
    except Exception as e:
        return False, f"Error al leer licencia: {str(e)}"


# --- Guardar licencia válida ---
def guardar_licencia(codigo):
    with open("licencia.dat", 'w') as f:
        f.write(codigo)