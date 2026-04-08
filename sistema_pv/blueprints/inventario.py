from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
from extensions import db
from models import Inventario

inventario_bp = Blueprint('inventario', __name__, url_prefix='/inventario')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@inventario_bp.route('/')
@login_required
def lista_inventario():
    inventario = Inventario.query.where(Inventario.estatus == True).order_by(Inventario.nombre)

    totalInventario = inventario.count()
    stockBajoInventario = inventario.filter(Inventario.cantidad <= 5).count()
    totalCosto = inventario.with_entities(func.sum(Inventario.costo* Inventario.cantidad)).scalar() or 0

    return render_template('inventario.html', inventario=inventario,
                           totalInventario=totalInventario,
                           stockBajoInventario=stockBajoInventario
                           ,totalCosto=totalCosto)


@inventario_bp.route('/editar', methods=['POST'])
@login_required
def editar_inventario():
    inventario_id = request.form['id']
    nombre = request.form['nombre']
    precio = request.form['precio']
    cantidad = request.form['cantidad']
    codigo_de_barras = request.form.get('codigo', '').strip() or None
    
    inventario = Inventario.query.get_or_404(inventario_id)
    
    # Verificar si hay otro producto con el mismo nombre
    nombre_duplicado = Inventario.query.filter(
        Inventario.nombre == nombre,
        Inventario.id != inventario_id,
        Inventario.estatus == True   # solo activos
    ).first()
    if nombre_duplicado:
        flash('Ya existe otro producto activo con ese nombre', 'info')
        return redirect(url_for('inventario.lista_inventario'))

    if codigo_de_barras:
        codigo_duplicado = Inventario.query.filter(
            Inventario.codigo_barras == codigo_de_barras,
            Inventario.id != inventario_id,
            Inventario.estatus == True
        ).first()
        if codigo_duplicado:
            flash('Ya existe otro producto activo con ese código de barras', 'info')
            return redirect(url_for('inventario.lista_inventario'))
    
    inventario.nombre = nombre
    inventario.precio = precio
    inventario.cantidad = cantidad
    inventario.codigo_barras = codigo_de_barras

    db.session.commit()
    flash('Producto actualizado', 'success')
    return redirect(url_for('inventario.lista_inventario'))

@inventario_bp.route('/eliminar/<int:inventario_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_producto(inventario_id):
    inventario = Inventario.query.get_or_404(inventario_id)

    inventario.estatus = False
    db.session.commit()
    flash('Producto eliminado', 'success')
    return redirect(url_for('inventario.lista_inventario'))