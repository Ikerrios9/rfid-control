# Despliegue RFID Control — Render + Raspberry Pi

Arquitectura:

- **Raspberry Pi (instituto)**: corre `docker-compose up` con la app + PostgreSQL local. Es la única que habla con el lector RFID.
- **Render**: hospeda una copia de la web + PostgreSQL para acceso desde casa / tribunal.
- **Sincronización**: cada 1 minuto la Pi sube los registros nuevos a Render con `sync_to_cloud.py`.

---

## 1. Despliegue en Render

### Opción A — Blueprint (un click)

1. Sube el repo a GitHub.
2. En Render: **New → Blueprint** y selecciona el repo. Detectará `render.yaml` y creará:
   - `rfid-db` (PostgreSQL free, expira en 30 días).
   - `rfid-control` (Web Service con `Dockerfile.cloud`).
3. La variable `DATABASE_URL` se inyecta automáticamente.
4. Al primer despliegue, el esquema todavía no existe. Ve a **rfid-db → Shell** (o usa la URL externa con psql) y ejecuta el contenido de `database.sql`. Alternativa: shell del web service y `python setup_db.py`.

### Opción B — Manual

1. **New → PostgreSQL** (plan Free). Anota la *External Database URL*.
2. Conéctate con psql o pgAdmin y ejecuta `database.sql`.
3. **New → Web Service**, conecta el repo:
   - Runtime: **Docker**
   - Dockerfile path: `./Dockerfile.cloud`
   - Plan: Free
   - Env vars:
     - `DATABASE_URL` = *Internal Database URL* de la DB de Render
     - `PYTHONUNBUFFERED` = `1`

Tras el deploy: `https://rfid-control.onrender.com/login` (admin / admin123).

> Render free duerme tras 15 min sin tráfico. El primer acceso tras dormir tarda ~30s.

---

## 2. Raspberry Pi (local)

Mismos archivos, levantar con Docker como antes:

```bash
docker compose up -d --build
```

- Web local: http://<ip-pi>:8000
- DB local: postgres en el contenedor `rfid-postgres` (puerto 5432 interno).
- El lector RFID (pyscard) sigue funcionando porque `docker-compose.yml` expone `/dev/bus/usb`.

### Configurar la sincronización cada 1 min

En la Pi, añade la URL pública de la DB de Render como variable de entorno (no la del servicio web — la de la **DB**, *External Database URL*).

Edita el `docker-compose.yml` y descomenta / pon:

```yaml
    environment:
      ...
      CLOUD_DATABASE_URL: postgresql://USER:PASS@HOST/DB
```

Reinicia: `docker compose up -d`.

Luego añade un cron dentro del contenedor o en la propia Pi (más sencillo este último):

```bash
crontab -e
```

Añade:

```
*/20 * * * * docker exec rfid-app python sync_to_cloud.py >> /var/log/rfid-sync.log 2>&1
```

Prueba inmediatamente:

```bash
docker exec rfid-app python sync_to_cloud.py
```

Salida esperada:

```
[sync] arrancando (2026-05-16 18:00:00)
[sync] OK usuarios=4 admins=1 accesos_nuevos=12 en 0.8s
```

---

## 3. Variables de entorno (resumen)

| Variable             | Dónde                | Para qué |
|----------------------|----------------------|----------|
| `DATABASE_URL`       | Render web service   | Conexión a la DB de Render |
| `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` | Pi (docker-compose) | DB local en la Pi |
| `CLOUD_DATABASE_URL` | Pi (docker-compose)  | DB de Render, usada por `sync_to_cloud.py` |
| `PORT`               | Render (automático)  | Puerto que asigna Render al servicio web |

---

## 4. Comprobaciones rápidas

- **Pi**: `docker compose ps` → ambos contenedores `healthy`.
- **Render**: pestaña *Logs* del web service → `Uvicorn running on http://0.0.0.0:...`.
- **Sync**: tras lanzar `sync_to_cloud.py`, entra a la web de Render y deberías ver los mismos usuarios/accesos que tienes en la Pi.

---

## 5. Notas para el TFG

- La DB free de Render se elimina automáticamente a los 30 días. Si la creas el 2026-05-16, te dura hasta ~2026-06-15 — suficiente para la presentación del 2026-06-03.
- El lector RFID **no** funciona en Render: requiere un periférico USB físico. Por eso solo se despliega la web/API.
- La copia en la nube es **solo de lectura efectiva**: los registros de acceso reales se generan siempre en la Pi cuando alguien pasa la tarjeta.
