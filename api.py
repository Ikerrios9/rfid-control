# Importa lo necesario para trabajar con FastApi
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import uvicorn
import asyncio
import json
import io
import os
# Datos que son necesarios para una Api web completa
# Conexion a la base de datos
# Acceso a los datos
# Sistema de autentificacion JWT
from db import DB
from repositorio import RFIDRepo
from auth import (
    hash_password, verify_password, create_token, decode_token,
    get_current_user, COOKIE_NAME, ensure_default_admin
)

# Crea una instancia de FastApi
app = FastAPI(title="RFID Control — IES D. Antonio Hellín Costa")

db = DB()
repo = RFIDRepo(db)

# Utiliza los archivos staticos
app.mount("/static", StaticFiles(directory="static"), name="static")

from jinja2 import Environment, FileSystemLoader, select_autoescape


jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    cache_size=0,
    auto_reload=True
)

templates = Jinja2Templates(directory="templates")
templates.env = jinja_env

def render_template(filename: str, context: dict = None):
    if context is None:
        context = {}
    try:
        with open(f"templates/{filename}", "r", encoding="utf-8") as f:
            content = f.read()
        for key, value in context.items():
            content = content.replace(f"{{{{ {key} }}}}", str(value))
        return HTMLResponse(content)
    except Exception as e:
        print(f"Error rendering {filename}: {e}")
        return HTMLResponse(f"<h1>Error al cargar {filename}</h1>", status_code=500)


# Esto nos permite que los datos se actualice en tiempo real
# Cuando alguien pase una tarjeta
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# Variable global para tarjetas pendientes de registro
pending_cards: dict[str, datetime] = {}

@app.on_event("startup")
async def startup():
    # Crear admin por defecto si no existe
    ensure_default_admin(db)


# Mantiene la conexion activa con el frontend

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# Rutas web, a los HTML
# Pantalla de bienvenida
@app.get("/display", response_class=HTMLResponse)
async def display_page(request: Request):

    return render_template("display.html", {
        "user": None,
        "title": "Pantalla de Bienvenida"
    })

# Login por defecto
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": None}
    )

# Verifica si el usuario esta logueado y muestra datos. sino lo manda al login
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    accesos = repo.listar_accesos(20)
    stats = repo.contar_eventos_hoy()
    usuarios = repo.listar_usuarios()

    return templates.TemplateResponse(
        request=request, name="index.html", context={
            "user": user,
            "active_page": "dashboard",
            "accesos": accesos,
            "stats": stats,
            "total_usuarios": len(usuarios),
            "ahora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

# Rutas protegidas, solo accesible para usarios admin
@app.post("/api/usuarios")
async def api_create_usuario(request: Request, nombre: str = Form(...), uid: str = Form(...), notas: str = Form(None)):
    user = get_current_user(request)
    if not user or user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    resultado = repo.crear_usuario(uid, nombre, notas)
    return {"status": "ok", "mensaje": "Usuario registrado correctamente"}


@app.get("/usuarios", response_class=HTMLResponse)
async def usuarios_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("rol") != "admin":
        return RedirectResponse("/", status_code=303)

    usuarios = repo.listar_usuarios()
    return templates.TemplateResponse(
        request=request, name="usuarios.html", context={
            "user": user,
            "active_page": "usuarios",
            "usuarios": usuarios
        }
    )


@app.get("/admins", response_class=HTMLResponse)
async def admins_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("rol") != "admin":
        return RedirectResponse("/", status_code=303)

    admins = repo.listar_admins()
    return templates.TemplateResponse(
        request=request, name="admins.html", context={
            "user": user,
            "active_page": "admins",
            "admins": admins
        }
    )


# Verifica el usuario en la base de datos, para generar su token
@app.post("/api/login")
async def api_login(request: Request, username: str = Form(...), password: str = Form(...)):
    admin = repo.get_admin_by_username(username)
    if not admin or not verify_password(password, admin["password_hash"]):
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"error": "Usuario o contraseña incorrectos"},
            status_code=401
        )

    if not admin["activo"]:
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"error": "Cuenta desactivada. Contacta al administrador."},
            status_code=403
        )

    token = create_token({
        "sub": admin["username"],
        "nombre": admin["nombre_completo"],
        "rol": admin["rol"],
        "id": admin["id"]
    })
    #Guarda el token en una cookie
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=43200)
    return response

# Elimina la cookie y muesta el login
@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# Apis
# Listar usuarios
@app.get("/api/usuarios")
def api_listar_usuarios(q: str = ""):
    if q:
        return repo.buscar_usuarios(q)
    return repo.listar_usuarios()

# Crear usuarios
@app.post("/api/usuarios")
def api_crear_usuario(uid: str = Form(...), nombre: str = Form(...), notas: str = Form("")):
    try:
        # verifica que no exista
        if repo.get_usuario(uid):
            return JSONResponse({"status": "error", "mensaje": "Ya existe un usuario con ese UID"}, status_code=400)
        repo.crear_usuario(uid, nombre, notas)
        # elimina si habia una tarjeta pendiente
        pending_cards.pop(uid, None)
        return JSONResponse({"status": "ok", "mensaje": "Usuario registrado correctamente"})
    except Exception as e:
        return JSONResponse({"status": "error", "mensaje": str(e)}, status_code=500)

# Actualizar usuarios, datos
@app.put("/api/usuarios/{uid}")
async def api_actualizar_usuario(uid: str, request: Request):
    try:
        body = await request.json()
        nombre = body.get("nombre", "")
        notas = body.get("notas", "")
        if not nombre:
            return JSONResponse({"status": "error", "mensaje": "El nombre es obligatorio"}, status_code=400)
        repo.actualizar_usuario(uid, nombre, notas)
        return JSONResponse({"status": "ok", "mensaje": "Usuario actualizado"})
    except Exception as e:
        return JSONResponse({"status": "error", "mensaje": str(e)}, status_code=500)

# Eliminar usuarios con todos sus registros
@app.delete("/api/usuarios/{uid}")
def api_eliminar_usuario(uid: str):
    try:
        repo.eliminar_usuario(uid)
        return JSONResponse({"status": "ok", "mensaje": "Usuario eliminado"})
    except Exception as e:
        return JSONResponse({"status": "error", "mensaje": str(e)}, status_code=500)


# Api accesos
# El limite que tenemos son 50 accesos que muestra, se puede modificar
@app.get("/api/accesos")
def api_listar_accesos():
    accesos = repo.listar_accesos(50)

    for a in accesos:
        if isinstance(a.get("fecha_hora"), datetime):
            a["fecha_hora"] = a["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S")
    return accesos

# Entradas y salidas de un dia
@app.get("/api/stats")
def api_stats():
    stats = repo.contar_eventos_hoy()
    total = len(repo.listar_usuarios())
    return {"entradas_hoy": stats["entradas"], "salidas_hoy": stats["salidas"], "total_usuarios": total}


# Api solo para administradores

@app.get("/api/admins")
def api_listar_admins():
    admins = repo.listar_admins()
    for a in admins:
        if isinstance(a.get("fecha_creacion"), datetime):
            a["fecha_creacion"] = a["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S")
    return admins


@app.post("/api/admins")
async def api_crear_admin(request: Request):
    try:
        body = await request.json()
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()
        nombre = body.get("nombre_completo", "").strip()
        rol = body.get("rol", "profesor")

        if not username or not password or not nombre:
            return JSONResponse({"status": "error", "mensaje": "Todos los campos son obligatorios"}, status_code=400)

        if repo.get_admin_by_username(username):
            return JSONResponse({"status": "error", "mensaje": "El nombre de usuario ya existe"}, status_code=400)

        hashed = hash_password(password)
        new_id = repo.crear_admin(username, hashed, nombre, rol)
        return JSONResponse({"status": "ok", "mensaje": "Cuenta creada", "id": new_id})
    except Exception as e:
        return JSONResponse({"status": "error", "mensaje": str(e)}, status_code=500)


@app.put("/api/admins/{admin_id}")
async def api_actualizar_admin(admin_id: int, request: Request):
    try:
        body = await request.json()
        nombre = body.get("nombre_completo", "").strip()
        rol = body.get("rol", "profesor")
        activo = body.get("activo", True)

        if not nombre:
            return JSONResponse({"status": "error", "mensaje": "El nombre es obligatorio"}, status_code=400)

        repo.actualizar_admin(admin_id, nombre, rol, 1 if activo else 0)

        # Si cambian contraseña
        new_pass = body.get("password", "").strip()
        if new_pass:
            repo.actualizar_password_admin(admin_id, hash_password(new_pass))

        return JSONResponse({"status": "ok", "mensaje": "Cuenta actualizada"})
    except Exception as e:
        return JSONResponse({"status": "error", "mensaje": str(e)}, status_code=500)


@app.delete("/api/admins/{admin_id}")
def api_eliminar_admin(admin_id: int):
    try:
        repo.eliminar_admin(admin_id)
        return JSONResponse({"status": "ok", "mensaje": "Cuenta eliminada"})
    except Exception as e:
        return JSONResponse({"status": "error", "mensaje": str(e)}, status_code=500)


# Si detecta una tarjeta nueva sin registrar.

@app.get("/api/pending-cards")
def api_pending_cards():
    return [{"uid": uid, "detectada": ts.strftime("%Y-%m-%d %H:%M:%S")} for uid, ts in pending_cards.items()]


# Generar PDF
# Genera usando filtros
@app.get("/informes", response_class=HTMLResponse)
async def informes_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    usuarios = repo.listar_usuarios()
    return templates.TemplateResponse(
        request=request, name="informes.html", context={
            "user": user,
            "active_page": "informes",
            "usuarios": usuarios
        }
    )

# Descargar el PDF
@app.get("/api/informe-pdf")
async def api_informe_pdf(request: Request,
                          uid: str = "",
                          fecha_desde: str = "",
                          fecha_hasta: str = "",
                          hora_desde: str = "",
                          hora_hasta: str = "",
                          evento: str = ""):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    # Registros filtrados
    accesos = repo.filtrar_accesos(
        uid=uid or None,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
        hora_desde=hora_desde or None,
        hora_hasta=hora_hasta or None,
        evento=evento or None
    )


    filtros = {}
    if uid:
        u = repo.get_usuario(uid)
        filtros["usuario"] = f"{u['nombre']} ({uid})" if u else uid
    if fecha_desde:
        filtros["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros["fecha_hasta"] = fecha_hasta
    if hora_desde:
        filtros["hora_desde"] = hora_desde
    if hora_hasta:
        filtros["hora_hasta"] = hora_hasta
    if evento:
        filtros["evento"] = evento


    logo_path = os.path.join("static", "img", "logo.png")
    if not os.path.exists(logo_path):
        logo_path = None

    from pdf_generator import generar_informe_pdf
    pdf_bytes = generar_informe_pdf(
        accesos=accesos,
        generado_por=user.get("nombre", "Sistema"),
        filtros=filtros,
        logo_path=logo_path
    )


    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"informe_accesos_{ts}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# vista previa del PDF
@app.get("/api/preview-accesos")
async def api_preview_accesos(request: Request,
                               uid: str = "",
                               fecha_desde: str = "",
                               fecha_hasta: str = "",
                               hora_desde: str = "",
                               hora_hasta: str = "",
                               evento: str = ""):
    """Preview de los registros filtrados sin generar PDF."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    accesos = repo.filtrar_accesos(
        uid=uid or None,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
        hora_desde=hora_desde or None,
        hora_hasta=hora_hasta or None,
        evento=evento or None
    )


    for a in accesos:
        if isinstance(a.get("fecha_hora"), datetime):
            a["fecha_hora"] = a["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S")

    total = len(accesos)
    entradas = sum(1 for a in accesos if a.get("evento") == "ENTRADA")
    salidas = sum(1 for a in accesos if a.get("evento") == "SALIDA")

    return {
        "total": total,
        "entradas": entradas,
        "salidas": salidas,
        "accesos": accesos[:100]  # Limitar registros sino muestras todos
    }

# Nos permite evitar registrar la misma tarjeta varias veces
last_processed = {}

@app.post("/api/tarjeta")
async def recibir_tarjeta(data: dict):
    uid = data.get("uid")
    if not uid:
        return {"status": "error"}

    import time
    now = time.time()


    if uid in last_processed and now - last_processed[uid] < 6:
        print(f"⏭️ Tarjeta {uid} ignorada (anti-rebote)")
        return {"status": "ignored"}

    last_processed[uid] = now

    try:
        usuario = repo.get_usuario(uid)
        ahora = datetime.now().replace(microsecond=0)

        if not usuario:
            pending_cards[uid] = ahora
            await manager.broadcast({
                "tipo": "tarjeta_nueva",
                "datos": {"uid": uid, "fecha_deteccion": ahora.strftime("%Y-%m-%d %H:%M:%S")}
            })
            print(f"🆕 Tarjeta nueva: {uid}")
            return {"status": "nueva"}

        else:
            nombre = usuario["nombre"]
            ultimo = usuario.get("ultimo_evento")
            evento = "SALIDA" if ultimo == "ENTRADA" else "ENTRADA"

            repo.insertar_acceso(uid, nombre, evento, ahora)
            repo.actualizar_ultimo_evento(uid, evento)

            await manager.broadcast({
                "tipo": "nuevo_acceso",
                "datos": {
                    "nombre": nombre,
                    "uid_limpio": uid,
                    "evento": evento,
                    "fecha_hora": ahora.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
            print(f"✅ {evento} registrado: {nombre}")
            return {"status": "ok", "evento": evento}

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error"}

# Iniciar el sistema
if __name__ == "__main__":
    print("🚀 Sistema RFID — IES D. Antonio Hellín Costa")
    print("   Panel web: http://127.0.0.1:8000")
    print("   Login por defecto: admin / admin123\n")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)