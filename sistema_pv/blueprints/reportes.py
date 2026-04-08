from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from functools import wraps

from sqlalchemy import func
from extensions import db
from models import Ventas, DetalleVenta, Inventario, Pago, mexico_tz
import pdfkit
from flask import render_template, make_response

# Configura la ruta al ejecutable dentro de tu empaquetado
import sys
import os
if getattr(sys, 'frozen', False):
    wkhtmltopdf_path = os.path.join(sys._MEIPASS, 'bin', 'wkhtmltopdf.exe')
else:
    wkhtmltopdf_path = 'bin/wkhtmltopdf.exe'  # ruta en desarrollo

config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/reporte/diario')
@login_required
def reporte_diario():
    hoy = datetime.now(mexico_tz).date()
    inicio = datetime.combine(hoy, datetime.min.time(), tzinfo=mexico_tz)
    fin = datetime.combine(hoy, datetime.max.time(), tzinfo=mexico_tz)
    ventas = Ventas.query.filter(Ventas.estado == True, Ventas.fecha >= inicio, Ventas.fecha <= fin).all()
    total_ventas = sum(v.total for v in ventas)
    total_pagos_efectivo = sum(p.monto for v in ventas for p in v.pagos if p.metodo_pago == 'efectivo')
    total_pagos_tarjeta = sum(p.monto for v in ventas for p in v.pagos if p.metodo_pago == 'tarjeta')
    ahora = datetime.now(mexico_tz)
    rendered = render_template('reporte_diario_pdf.html',
                            ventas=ventas,
                            total=total_ventas,
                            efectivo=total_pagos_efectivo,
                            tarjeta=total_pagos_tarjeta,
                            fecha=hoy,
                            ahora=ahora)

    pdf = pdfkit.from_string(rendered, False, configuration=config)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=reporte_{hoy}.pdf'
    return response

from datetime import datetime, timedelta
from flask import request, redirect, url_for, flash, make_response
import pdfkit

@reportes_bp.route('/ventas-periodo')
@login_required
def reporte_ventas_periodo():
    fecha_inicio_str = request.args.get('fecha_inicio')
    fecha_fin_str = request.args.get('fecha_fin')

    if not fecha_inicio_str or not fecha_fin_str:
        hoy = datetime.now(mexico_tz).date()
        fecha_fin = hoy
        fecha_inicio = hoy - timedelta(days=30)
    else:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('reportes.formulario_periodo'))

    inicio = datetime.combine(fecha_inicio, datetime.min.time(), tzinfo=mexico_tz)
    fin = datetime.combine(fecha_fin, datetime.max.time(), tzinfo=mexico_tz)

    ventas = Ventas.query.filter(
        Ventas.estado == True,
        Ventas.fecha >= inicio,
        Ventas.fecha <= fin
    ).order_by(Ventas.fecha.asc()).all()

    total_general = sum(v.total for v in ventas)
    total_efectivo = sum(p.monto for v in ventas for p in v.pagos if p.metodo_pago == 'efectivo')
    total_tarjeta = sum(p.monto for v in ventas for p in v.pagos if p.metodo_pago == 'tarjeta')
    total_otro = sum(p.monto for v in ventas for p in v.pagos if p.metodo_pago == 'otro')

    productos_vendidos = db.session.query(
        Inventario.nombre,
        func.sum(DetalleVenta.cantidad).label('cantidad_total'),
        func.sum(DetalleVenta.cantidad * DetalleVenta.precio_unitario).label('ingreso_total')
    ).join(DetalleVenta, Inventario.id == DetalleVenta.producto_id)\
     .join(Ventas, Ventas.id == DetalleVenta.venta_id)\
     .filter(Ventas.estado == True, Ventas.fecha >= inicio, Ventas.fecha <= fin)\
     .group_by(Inventario.id)\
     .order_by(func.sum(DetalleVenta.cantidad).desc())\
     .limit(10).all()

    ventas_por_dia = db.session.query(
        func.date(Ventas.fecha).label('fecha_dia'),
        func.sum(DetalleVenta.cantidad * DetalleVenta.precio_unitario).label('total_dia')
    ).join(DetalleVenta).filter(
        Ventas.estado == True,
        Ventas.fecha >= inicio,
        Ventas.fecha <= fin
    ).group_by(func.date(Ventas.fecha)).order_by(func.date(Ventas.fecha).asc()).all()

    # CORRECCIÓN AQUÍ:
    dias = [datetime.strptime(dia.fecha_dia, '%Y-%m-%d').strftime('%d/%m') for dia in ventas_por_dia]
    totales_dia = [float(dia.total_dia) for dia in ventas_por_dia]
    max_total = max(totales_dia) if totales_dia else 1

    ahora = datetime.now(mexico_tz)
    rendered = render_template('reporte_periodo_pdf.html',
                               ventas=ventas,
                               total_general=total_general,
                               total_efectivo=total_efectivo,
                               total_tarjeta=total_tarjeta,
                               total_otro=total_otro,
                               fecha_inicio=fecha_inicio,
                               fecha_fin=fecha_fin,
                               ahora=ahora,
                               productos_mas_vendidos=productos_vendidos,
                               dias=dias,
                               totales_dia=totales_dia,
                               max_total=max_total)

    pdf = pdfkit.from_string(rendered, False, configuration=config)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=ventas_{fecha_inicio}_a_{fecha_fin}.pdf'
    return response

@reportes_bp.route('/formulario-periodo')
@login_required
def formulario_periodo():
    return render_template('seleccionar_fechas.html')
