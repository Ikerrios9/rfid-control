-- Esquema PostgreSQL para RFID Control
-- Compatible con Render Postgres y postgres:16-alpine en local

-- Tipos ENUM
DO $$ BEGIN
    CREATE TYPE evento_tipo AS ENUM ('ENTRADA', 'SALIDA');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE rol_tipo AS ENUM ('admin', 'profesor');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Tablas principales
CREATE TABLE IF NOT EXISTS usuarios (
    uid_limpio VARCHAR(32) PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL,
    notas VARCHAR(255) NULL,
    ultimo_evento evento_tipo NULL
);

CREATE TABLE IF NOT EXISTS accesos (
    id BIGSERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP NOT NULL,
    uid_limpio VARCHAR(32) NOT NULL,
    nombre VARCHAR(80) NOT NULL,
    evento evento_tipo NOT NULL,
    CONSTRAINT fk_accesos_usuarios FOREIGN KEY (uid_limpio)
        REFERENCES usuarios (uid_limpio) ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_uid_fecha ON accesos (uid_limpio, fecha_hora);

CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    rol rol_tipo DEFAULT 'profesor',
    activo SMALLINT DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usuario admin por defecto (contraseña: admin123)
INSERT INTO admin_users (username, password_hash, nombre_completo, rol, activo)
VALUES (
    'admin',
    '$2b$12$BflUDKvtfPpUeFCkFkIPo.ZNIzex5JfGNpSRMgfLrkQwJKUdoBA6u',
    'Administrador',
    'admin',
    1
)
ON CONFLICT (username) DO NOTHING;
