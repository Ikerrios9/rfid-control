from datetime import datetime

class RFIDRepo:
    def __init__(self, db):
        self.db = db

    # ══════════════════════════════════════════════════════════
    #  USUARIOS DE TARJETAS RFID
    # ══════════════════════════════════════════════════════════

    def get_usuario(self, uid):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM usuarios WHERE uid_limpio=%s", (uid,))
            return cur.fetchone()
        finally:
            conn.close()

    def listar_usuarios(self):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM usuarios ORDER BY nombre")
            return cur.fetchall()
        finally:
            conn.close()

    def buscar_usuarios(self, filtro):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            like = f"%{filtro}%"
            cur.execute(
                "SELECT * FROM usuarios WHERE nombre LIKE %s OR uid_limpio LIKE %s ORDER BY nombre",
                (like, like)
            )
            return cur.fetchall()
        finally:
            conn.close()

    def crear_usuario(self, uid, nombre, notas=""):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO usuarios (uid_limpio, nombre, fecha_registro, notas, ultimo_evento) "
                "VALUES (%s, %s, %s, %s, NULL)",
                (uid, nombre, datetime.now(), notas)
            )
            conn.commit()
        finally:
            conn.close()

    def actualizar_usuario(self, uid, nombre, notas=""):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE usuarios SET nombre=%s, notas=%s WHERE uid_limpio=%s",
                (nombre, notas, uid)
            )
            conn.commit()
        finally:
            conn.close()

    def eliminar_usuario(self, uid):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            # Primero eliminar accesos relacionados
            cur.execute("DELETE FROM accesos WHERE uid_limpio=%s", (uid,))
            cur.execute("DELETE FROM usuarios WHERE uid_limpio=%s", (uid,))
            conn.commit()
        finally:
            conn.close()

    def actualizar_ultimo_evento(self, uid, evento):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE usuarios SET ultimo_evento=%s WHERE uid_limpio=%s",
                (evento, uid)
            )
            conn.commit()
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════
    #  ACCESOS
    # ══════════════════════════════════════════════════════════

    def insertar_acceso(self, uid, nombre, evento, fecha_hora=None):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            fecha_hora = fecha_hora or datetime.now()
            cur.execute(
                "INSERT INTO accesos (fecha_hora, uid_limpio, nombre, evento) VALUES (%s, %s, %s, %s)",
                (fecha_hora, uid, nombre, evento)
            )
            conn.commit()
        finally:
            conn.close()

    def listar_accesos(self, limit=50):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT a.*, u.nombre as nombre_usuario 
                FROM accesos a 
                JOIN usuarios u ON a.uid_limpio = u.uid_limpio 
                ORDER BY a.fecha_hora DESC LIMIT %s
            """, (limit,))
            return cur.fetchall()
        finally:
            conn.close()

    def contar_eventos_hoy(self):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN evento = 'ENTRADA' THEN 1 ELSE 0 END), 0) AS entradas,
                    COALESCE(SUM(CASE WHEN evento = 'SALIDA'  THEN 1 ELSE 0 END), 0) AS salidas
                FROM accesos
                WHERE fecha_hora::date = CURRENT_DATE
            """)
            return cur.fetchone()
        finally:
            conn.close()

    def filtrar_accesos(self, uid=None, fecha_desde=None, fecha_hasta=None,
                        hora_desde=None, hora_hasta=None, evento=None):
        """Consulta de accesos con filtros múltiples para informes."""
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            query = """
                SELECT a.*, u.nombre as nombre_usuario 
                FROM accesos a 
                JOIN usuarios u ON a.uid_limpio = u.uid_limpio 
                WHERE 1=1
            """
            params = []

            if uid:
                query += " AND a.uid_limpio = %s"
                params.append(uid)
            if fecha_desde:
                query += " AND a.fecha_hora::date >= %s"
                params.append(fecha_desde)
            if fecha_hasta:
                query += " AND a.fecha_hora::date <= %s"
                params.append(fecha_hasta)
            if hora_desde:
                query += " AND a.fecha_hora::time >= %s"
                params.append(hora_desde)
            if hora_hasta:
                query += " AND a.fecha_hora::time <= %s"
                params.append(hora_hasta)
            if evento and evento in ("ENTRADA", "SALIDA"):
                query += " AND a.evento = %s"
                params.append(evento)

            query += " ORDER BY a.fecha_hora DESC"
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════
    #  ADMIN USERS (cuentas del sistema)
    # ══════════════════════════════════════════════════════════

    def get_admin_by_username(self, username):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM admin_users WHERE username=%s", (username,))
            return cur.fetchone()
        finally:
            conn.close()

    def get_admin_by_id(self, admin_id):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM admin_users WHERE id=%s", (admin_id,))
            return cur.fetchone()
        finally:
            conn.close()

    def listar_admins(self):
        conn = self.db.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, username, nombre_completo, rol, activo, fecha_creacion FROM admin_users ORDER BY nombre_completo")
            return cur.fetchall()
        finally:
            conn.close()

    def crear_admin(self, username, password_hash, nombre_completo, rol="profesor"):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO admin_users (username, password_hash, nombre_completo, rol) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (username, password_hash, nombre_completo, rol)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return new_id
        finally:
            conn.close()

    def actualizar_admin(self, admin_id, nombre_completo, rol, activo):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE admin_users SET nombre_completo=%s, rol=%s, activo=%s WHERE id=%s",
                (nombre_completo, rol, activo, admin_id)
            )
            conn.commit()
        finally:
            conn.close()

    def actualizar_password_admin(self, admin_id, password_hash):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE admin_users SET password_hash=%s WHERE id=%s",
                (password_hash, admin_id)
            )
            conn.commit()
        finally:
            conn.close()

    def eliminar_admin(self, admin_id):
        conn = self.db.connect()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM admin_users WHERE id=%s", (admin_id,))
            conn.commit()
        finally:
            conn.close()
