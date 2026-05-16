"""
Generador de informes PDF — Sistema RFID
IES D. Antonio Hellín Costa
"""
from fpdf import FPDF
from datetime import datetime
import os


class InformePDF(FPDF):
    """PDF personalizado con cabecera y pie de página del centro."""

    def __init__(self, generado_por="Sistema", filtros_texto="", logo_path=None):
        super().__init__()
        self.generado_por = generado_por
        self.filtros_texto = filtros_texto
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        # ── Fondo de cabecera ──
        self.set_fill_color(26, 58, 108)  # Azul oscuro del IES
        self.rect(0, 0, 210, 38, 'F')

        # ── Logo si existe ──
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, 10, 4, 30)
            except:
                pass

        # ── Título ──
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(45, 6)
        self.cell(0, 8, 'Sistema de Control de Acceso RFID', ln=True)

        # ── Subtítulo ──
        self.set_font('Helvetica', '', 9)
        self.set_text_color(180, 200, 230)
        self.set_xy(45, 14)
        self.cell(0, 5, 'IES D. Antonio Hellin Costa - Puerto de Mazarron', ln=True)

        # ── Generado por ──
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 180, 220)
        self.set_xy(45, 20)
        fecha_gen = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")
        self.cell(0, 5, f'Informe generado por: {self.generado_por}  |  Fecha: {fecha_gen}', ln=True)

        # ── Filtros aplicados ──
        if self.filtros_texto:
            self.set_xy(45, 26)
            self.set_font('Helvetica', '', 7)
            self.set_text_color(130, 160, 200)
            self.cell(0, 5, f'Filtros: {self.filtros_texto}', ln=True)

        self.ln(8)

    def footer(self):
        self.set_y(-20)

        # Línea separadora
        self.set_draw_color(26, 58, 108)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())

        self.ln(3)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(130, 130, 130)
        self.cell(0, 5, f'IES D. Antonio Hellin Costa  |  Sistema RFID Control  |  Pagina {self.page_no()}/{{nb}}', align='C')


def generar_informe_pdf(accesos, generado_por="Sistema", filtros=None, logo_path=None):
    """
    Genera un PDF con la tabla de accesos filtrados.

    Args:
        accesos: Lista de dicts con los registros de accesos
        generado_por: Nombre del usuario que genera el informe
        filtros: Dict con los filtros aplicados (para mostrar en cabecera)
        logo_path: Ruta al logo del centro

    Returns:
        bytes del PDF generado
    """
    filtros = filtros or {}

    # ── Construir texto de filtros ──
    partes_filtro = []
    if filtros.get("usuario"):
        partes_filtro.append(f"Usuario: {filtros['usuario']}")
    if filtros.get("fecha_desde"):
        partes_filtro.append(f"Desde: {filtros['fecha_desde']}")
    if filtros.get("fecha_hasta"):
        partes_filtro.append(f"Hasta: {filtros['fecha_hasta']}")
    if filtros.get("evento"):
        partes_filtro.append(f"Evento: {filtros['evento']}")
    if filtros.get("uid"):
        partes_filtro.append(f"UID: {filtros['uid']}")
    if not partes_filtro:
        partes_filtro.append("Todos los registros")

    filtros_texto = "  |  ".join(partes_filtro)

    # ── Crear PDF ──
    pdf = InformePDF(
        generado_por=generado_por,
        filtros_texto=filtros_texto,
        logo_path=logo_path
    )
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── Resumen estadístico ──
    total = len(accesos)
    entradas = sum(1 for a in accesos if a.get("evento") == "ENTRADA")
    salidas = sum(1 for a in accesos if a.get("evento") == "SALIDA")

    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(26, 58, 108)
    pdf.cell(0, 8, 'Resumen', ln=True)

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(60, 60, 60)

    # Cajas de resumen
    box_y = pdf.get_y()
    box_w = 58
    box_h = 18

    # Total registros
    pdf.set_fill_color(235, 245, 255)
    pdf.set_draw_color(26, 58, 108)
    pdf.rect(10, box_y, box_w, box_h, 'DF')
    pdf.set_xy(10, box_y + 2)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(box_w, 5, 'Total Registros', align='C', ln=True)
    pdf.set_xy(10, box_y + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(26, 58, 108)
    pdf.cell(box_w, 8, str(total), align='C')

    # Entradas
    pdf.set_fill_color(230, 255, 240)
    pdf.set_draw_color(16, 185, 129)
    pdf.rect(72, box_y, box_w, box_h, 'DF')
    pdf.set_xy(72, box_y + 2)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(box_w, 5, 'Entradas', align='C', ln=True)
    pdf.set_xy(72, box_y + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(16, 140, 100)
    pdf.cell(box_w, 8, str(entradas), align='C')

    # Salidas
    pdf.set_fill_color(230, 245, 255)
    pdf.set_draw_color(6, 182, 212)
    pdf.rect(134, box_y, box_w, box_h, 'DF')
    pdf.set_xy(134, box_y + 2)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(box_w, 5, 'Salidas', align='C', ln=True)
    pdf.set_xy(134, box_y + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(6, 140, 180)
    pdf.cell(box_w, 8, str(salidas), align='C')

    pdf.set_y(box_y + box_h + 8)

    # ── Tabla de datos ──
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(26, 58, 108)
    pdf.cell(0, 8, 'Detalle de Accesos', ln=True)

    if not accesos:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, 'No se encontraron registros con los filtros seleccionados.', ln=True, align='C')
        return pdf.output()

    # Cabecera de tabla
    col_widths = [18, 45, 40, 45, 40]  # #, Fecha/Hora, Nombre, UID, Evento
    headers = ['#', 'Fecha y Hora', 'Nombre', 'UID Tarjeta', 'Evento']

    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(26, 58, 108)
    pdf.set_text_color(255, 255, 255)

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, fill=True, align='C')
    pdf.ln()

    # Filas de datos
    pdf.set_font('Helvetica', '', 8)
    for idx, acceso in enumerate(accesos, 1):
        # Alternar color de fondo
        if idx % 2 == 0:
            pdf.set_fill_color(245, 248, 255)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.set_text_color(60, 60, 60)

        # Formatear fecha
        fecha = acceso.get("fecha_hora", "")
        if isinstance(fecha, datetime):
            fecha = fecha.strftime("%d/%m/%Y %H:%M:%S")
        else:
            fecha = str(fecha)

        nombre = acceso.get("nombre_usuario") or acceso.get("nombre", "")
        uid = acceso.get("uid_limpio", "")
        evento = acceso.get("evento", "")

        # Número
        pdf.cell(col_widths[0], 7, str(idx), border=1, fill=True, align='C')
        # Fecha
        pdf.cell(col_widths[1], 7, fecha, border=1, fill=True, align='C')
        # Nombre
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(col_widths[2], 7, nombre[:25], border=1, fill=True)
        pdf.set_font('Helvetica', '', 8)
        # UID
        pdf.set_text_color(100, 80, 160)
        pdf.cell(col_widths[3], 7, uid, border=1, fill=True, align='C')
        pdf.set_text_color(60, 60, 60)
        # Evento con color
        if evento == "ENTRADA":
            pdf.set_text_color(16, 140, 100)
        else:
            pdf.set_text_color(6, 140, 180)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(col_widths[4], 7, evento, border=1, fill=True, align='C')
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(60, 60, 60)

        pdf.ln()

    return pdf.output()
