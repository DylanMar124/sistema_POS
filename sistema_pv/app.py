from flask import Flask, render_template
import webbrowser
import threading
import time
from extensions import app, db, login_manager
from models import Usuario, Inventario, Ventas, DetalleVenta
from auth import auth_bp
from werkzeug.security import generate_password_hash
from flask_login import login_required
from datetime import datetime, date, timedelta
from sqlalchemy import func
from flask import request, render_template_string, redirect, url_for, session
from blueprints.usuarios import  usuarios_bp
from blueprints.compras import compras_bp
from blueprints.inventario import inventario_bp
from blueprints.ventas import ventas_bp
from blueprints.reportes import reportes_bp
import pytz
from licencia import validar_licencia_guardada, verificar_codigo_licencia, guardar_licencia

# Template simple para activación (puedes personalizarlo)
ACTIVACION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Activación del Sistema</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        input { padding: 10px; width: 400px; margin: 10px; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; cursor: pointer; }
        .error { color: red; }
    </style>
</head>
<body>
    <h2>Activación del Sistema</h2>
    <p>Ingrese el código de licencia proporcionado:</p>
    <form method="POST">
        <input type="text" name="codigo" placeholder="Código de licencia" required><br>
        <button type="submit">Activar</button>
    </form>
    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}
    <hr>
    <p>Fingerprint de este equipo: <strong>{{ fingerprint }}</strong></p>
    <p>Envíe este código a su proveedor para obtener la licencia.</p>
</body>
</html>
"""

@app.before_request
def verificar_activacion():
    # Excluir rutas que no requieren activación (como la propia página de activación)
    if request.endpoint in ('activar', 'static'):
        return
    # Verificar si ya está activado
    valida, _ = validar_licencia_guardada()
    if not valida:
        return redirect(url_for('activar'))
    
@app.route('/activar', methods=['GET', 'POST'])
def activar():
    from licencia import get_fingerprint
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip()
        ok, resultado = verificar_codigo_licencia(codigo)
        if ok:
            guardar_licencia(codigo)
            return redirect(url_for('auth.login'))  # redirige al inicio
        else:
            return render_template_string(ACTIVACION_TEMPLATE,
                                          error=resultado,
                                          fingerprint=get_fingerprint())
    return render_template_string(ACTIVACION_TEMPLATE,
                                  error=None,
                                  fingerprint=get_fingerprint())

app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(reportes_bp)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

with app.app_context():
    db.create_all()

    if not Usuario.query.first():
        admin = Usuario(
            nombre='superadmin',
            rol='admin',
            activo=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("Usuario administrador creado con contraseña 'admin'")

@app.route('/')
@login_required
def index():

    mexico_tz = pytz.timezone('America/Mexico_City')
    hoy = datetime.now(mexico_tz).date()
    inicio_hoy = datetime.combine(hoy, datetime.min.time(), tzinfo=mexico_tz)
    fin_hoy = datetime.combine(hoy, datetime.max.time(), tzinfo=mexico_tz)

    # Total vendido hoy (suma de subtotales de detalles de ventas activas de hoy)
    total_vendido_hoy = db.session.query(
    func.sum(DetalleVenta.cantidad * DetalleVenta.precio_unitario)
        ).join(Ventas).filter(
            Ventas.estado == True,
            Ventas.fecha >= inicio_hoy,
            Ventas.fecha <= fin_hoy
        ).scalar() or 0.0

    # Cantidad de ventas de hoy
    total_ventas_hoy = Ventas.query.filter(Ventas.estado == True, Ventas.fecha >= inicio_hoy, Ventas.fecha <= fin_hoy).count()

    # Ventas de la semana (últimos 7 días, agrupadas por día para la tabla)
    semana_inicio = hoy - timedelta(days=6)
    inicio_semana = datetime.combine(semana_inicio, datetime.min.time(), tzinfo=mexico_tz)
    fin_semana = fin_hoy
    ventas_por_dia = db.session.query(
    func.date(Ventas.fecha).label('fecha_dia'),
    func.count(Ventas.id).label('cantidad'),
    func.sum(DetalleVenta.cantidad * DetalleVenta.precio_unitario).label('total')
    ).join(DetalleVenta).filter(
        Ventas.estado == True,
        Ventas.fecha >= inicio_semana,
        Ventas.fecha <= fin_semana
    ).group_by(func.date(Ventas.fecha)).order_by(func.date(Ventas.fecha).asc()).all()

    dias_semana = []
    totales_dias = []
    for dia in ventas_por_dia:
        fecha_obj = datetime.strptime(dia.fecha_dia, '%Y-%m-%d').date()
        dias_semana.append(fecha_obj.strftime('%a %d/%m'))
        totales_dias.append(float(dia.total or 0))

    # Últimas 10 ventas (para la tabla de actividad reciente)
    ultimas_ventas = Ventas.query.filter_by(estado=True).\
        order_by(Ventas.fecha.desc()).\
        limit(10).all()

    inventario = Inventario.query.filter(Inventario.estatus == True).order_by(Inventario.nombre)
    totalInventario = inventario.count()
    stockBajoInventario = inventario.filter(Inventario.cantidad <= 5).count()
    productosStockBajo = Inventario.query.filter(Inventario.estatus == True, Inventario.cantidad <= 5).order_by(Inventario.nombre).limit(5).all()

    return render_template('index.html',
                           totalInventario=totalInventario,
                           stockBajoInventario=stockBajoInventario,
                           productosStockBajo=productosStockBajo,
                           total_vendido_hoy=total_vendido_hoy,
                           total_ventas_hoy=total_ventas_hoy,
                           ventas_por_dia=ventas_por_dia,
                           ultimas_ventas=ultimas_ventas,
                           dias_semana=dias_semana,
                           totales_dias=totales_dias)
def abrir_navegador():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    threading.Thread(target=abrir_navegador).start()
    app.run(debug=False, host='127.0.0.1', port=5000)