from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Inventario, Compra, CompraDetalle
from datetime import datetime

compras_bp = Blueprint('compras', __name__, url_prefix='/compras')

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@compras_bp.route('/')
@login_required
def lista_compras():
    compras = Compra.query.order_by(Compra.fecha.desc()).all()
    return render_template('compras.html', compras=compras)

@compras_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva_compra():
    if request.method == 'POST':
        proveedor = request.form.get('proveedor', '').strip()
        factura = request.form.get('factura', '').strip()
        observaciones = request.form.get('observaciones', '').strip()

        compra = Compra(
            proveedor=proveedor if proveedor else None,
            factura=factura if factura else None,
            observaciones=observaciones if observaciones else None
        )
        db.session.add(compra)
        db.session.flush()  # para obtener id

        # Obtener datos de los productos
        codigos_barras = request.form.getlist('codigo_barras[]')
        nombres = request.form.getlist('nombre_producto[]')
        cantidades = request.form.getlist('cantidad[]')
        precios_unitarios = request.form.getlist('precio_unitario[]')
        precios_venta = request.form.getlist('precio_venta[]')

        for i in range(len(nombres)):
            if not nombres[i] or not cantidades[i] or not precios_unitarios[i]:
                continue  # omitir filas incompletas

            nombre = nombres[i].strip()
            codigo = codigos_barras[i].strip() if i < len(codigos_barras) and codigos_barras[i] else None
            cantidad = float(cantidades[i])
            costo = float(precios_unitarios[i])
            precio_venta_val = float(precios_venta[i]) if i < len(precios_venta) and precios_venta[i] else 0.0

            # Buscar producto existente
            producto = None
            if codigo:
                producto = Inventario.query.filter_by(codigo_barras=codigo).first()
            if not producto and nombre:
                producto = Inventario.query.filter_by(nombre=nombre).first()

            if not producto:
                # Crear nuevo producto
                producto = Inventario(
                    nombre=nombre,
                    codigo_barras=codigo,
                    precio=precio_venta_val,   # precio de venta (puede ser 0 si no se proporcionó)
                    costo=costo,               # costo de compra
                    cantidad=0,
                    estatus=True
                )
                db.session.add(producto)
                db.session.flush()  # para obtener el id

            # Crear detalle de compra
            detalle = CompraDetalle(
                compra_id=compra.id,
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=costo
            )
            db.session.add(detalle)

            # Actualizar stock y costo (último costo)
            producto.cantidad += cantidad
            producto.costo = costo  # o implementar promedio si se desea

        db.session.commit()
        flash(f'Compra #{compra.id} registrada con éxito', 'success')
        return redirect(url_for('compras.lista_compras'))

    # GET: mostrar formulario
    productos = Inventario.query.where(Inventario.estatus == True).order_by(Inventario.nombre).all()
    return render_template('nueva_compra.html', productos=productos)

@compras_bp.route('/<int:compra_id>')
@login_required
def ver_compra(compra_id):
    compra = Compra.query.get_or_404(compra_id)
    return render_template('ver_compra.html', compra=compra)

# Opcional: eliminar compra (con cuidado)
@compras_bp.route('/<int:compra_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_compra(compra_id):
    compra = Compra.query.get_or_404(compra_id)
    # Primero revertir el stock (opcional, podría ser peligroso)
    for detalle in compra.detalles:
        inventario = detalle.inventario
        inventario.cantidad -= detalle.cantidad
    db.session.delete(compra)
    db.session.commit()
    flash(f'Compra #{compra_id} eliminada y stock revertido', 'success')
    return redirect(url_for('compras.lista_compras'))