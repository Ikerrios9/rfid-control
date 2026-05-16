"""
Módulo de autenticación — JWT + bcrypt (doble hash)
"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Request
import hashlib
import bcrypt as _bcrypt
import os

# ── Configuración ──────────────────────────────────────────
SECRET_KEY = "rfid-control-ies-antonio-hellin-costa-2026-secret-key"
ALGORITHM = "HS256"
COOKIE_NAME = "rfid_token"

# ── Contraseñas (doble hash) ───────────────────────────────
def hash_password(password: str) -> str:
    # Pre-hash with sha256 to avoid bcrypt 72-byte limit
    pw = hashlib.sha256(password.encode()).hexdigest().encode()
    return _bcrypt.hashpw(pw, _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pw = hashlib.sha256(plain.encode()).hexdigest().encode()
        return _bcrypt.checkpw(pw, hashed.encode())
    except:
        return False

# ── JWT ────────────────────────────────────────────────────
def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=12)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_token(token)


# ── Crear admin por defecto ────────────────────────────────
def ensure_default_admin(db):
    """Crea/actualiza el usuario admin con hash correcto"""
    try:
        conn = db.connect()
        cur = conn.cursor(dictionary=True)

        # Generar hash correcto con tu método
        hashed = hash_password("admin123")

        cur.execute("""
            INSERT INTO admin_users
            (username, password_hash, nombre_completo, rol, activo)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                nombre_completo = EXCLUDED.nombre_completo,
                rol = EXCLUDED.rol,
                activo = EXCLUDED.activo
        """, ("admin", hashed, "Administrador", "admin", 1))

        conn.commit()
        print("✅ Usuario admin verificado/actualizado correctamente (admin / admin123)")

    except Exception as e:
        print(f"⚠️ Error en ensure_default_admin: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()