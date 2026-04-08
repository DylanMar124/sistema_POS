
from flask import Blueprint, render_template, request, redirect, jsonify, url_for, flash, json
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Ventas, DetalleVenta, Inventario, Pago

ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@ventas_bp.route('/')
@login_required
def lista_ventas():
    ventas = Ventas.query.order_by(Ventas.fecha.desc()).all()
    return render_template('ventas.html', ventas=ventas)

@ventas_bp.route('/nueva', methods=['GET'])
@login_required
def nueva_venta():
    productos = Inventario.query.filter_by(estatus=True).order_by(Inventario.nombre).all()
    return render_template('nueva_venta.html', productos=productos)

@ventas_bp.route('/buscar_producto', methods=['GET'])
@login_required
def buscar_producto():
    codigo = request.args.get('codigo', '').strip()
    if not codigo:
        return jsonify({'error': 'Código vacío'}), 400
    
    # Buscar por código de barras primero, luego por nombre (coincidencia parcial)
    producto = Inventario.query.filter(
        Inventario.estatus == True,
        Inventario.codigo_barras == codigo
    ).first()
    
    if not producto:
        # Si no, buscar por nombre que contenga el texto (útil para escritura manual)
        producto = Inventario.query.filter(
            Inventario.estatus == True,
            Inventario.nombre.ilike(f'%{codigo}%')
        ).first()
    
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404
    
    return jsonify({
        'id': producto.id,
        'nombre': producto.nombre,
        'precio': producto.precio,
        'stock': producto.cantidad,
        'codigo_barras': producto.codigo_barras
    })

@ventas_bp.route('/nueva', methods=['POST'])
@login_required
def guardar_venta():
    
    carrito = request.json.get('carrito', [])
    pagos = request.json.get('pagos', [])
    observaciones = request.json.get('observaciones', '')
    
    if not carrito or not pagos:
        return jsonify({'error': 'Carrito o pagos vacíos'}), 400
    
    # Crear cabecera de venta
    venta = Ventas(
        vendedor_id=current_user.id,
        observaciones=observaciones
    )
    db.session.add(venta)
    db.session.flush()  # obtener id
    
    total_venta = 0
    # Procesar detalles y actualizar stock
    for item in carrito:
        producto = Inventario.query.get(item['id'])
        if not producto or producto.cantidad < item['cantidad']:
            db.session.rollback()
            return jsonify({'error': f'Stock insuficiente para {producto.nombre if producto else "producto"}'}), 400
        
        detalle = DetalleVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            cantidad=item['cantidad'],
            precio_unitario=item['precio_unitario']
        )
        db.session.add(detalle)
        producto.cantidad -= item['cantidad']
        total_venta += detalle.subtotal
    
    # Verificar que la suma de pagos sea al menos el total (puede ser mayor? normalmente igual)
    total_pagado = sum(p['monto'] for p in pagos)
    if abs(total_pagado - total_venta) > 0.01:  # tolerancia centavos
        db.session.rollback()
        return jsonify({'error': f'El total pagado ({total_pagado}) no coincide con el total de la venta ({total_venta})'}), 400
    
    # Registrar pagos
    for pago in pagos:
        pago_obj = Pago(
            venta_id=venta.id,
            monto=pago['monto'],
            metodo_pago=pago['metodo']
        )
        db.session.add(pago_obj)
    
    db.session.commit()
    flash(f'Venta #{venta.id} registrada con éxito', 'success')
    return jsonify({'success': True, 'redirect': url_for('ventas.lista_ventas')})

@ventas_bp.route('/<int:venta_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_venta(venta_id):
    venta = Ventas.query.get_or_404(venta_id)
    
    if not venta.estado:
        flash('La venta ya está cancelada', 'warning')
        return redirect(url_for('ventas.lista_ventas'))
    # Primero revertir el stock (opcional, podría ser peligroso)
    for detalle in venta.detalles:
        inventario = detalle.inventario
        inventario.cantidad += detalle.cantidad
    
    venta.estado = False

    db.session.commit()
    flash(f'La venta #{venta_id} a sido eliminada y el stock revertido', 'success')
    return redirect(url_for('ventas.lista_ventas'))

@ventas_bp.route('/<int:venta_id>')
@login_required
def ver_detalles_venta(venta_id):
    venta = Ventas.query.get_or_404(venta_id)
    return render_template('ver_venta.html', venta=venta)

@ventas_bp.route('/ticket/<int:venta_id>')
@login_required
def ticket_venta(venta_id):
    venta = Ventas.query.get_or_404(venta_id)
    return render_template('ticket.html', venta=venta)