from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Usuario

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@usuarios_bp.route('/')
@login_required
@admin_required
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@usuarios_bp.route('/crear', methods=['POST'])
@login_required
@admin_required
def crear_usuario():
    nombre = request.form['nombre']
    password = request.form['password']
    rol = request.form['rol']
    
    # Verificar si ya existe
    if Usuario.query.filter_by(nombre=nombre).first():
        flash('El nombre de usuario ya existe', 'info')
        return redirect(url_for('usuarios.lista_usuarios'))
    
    nuevo = Usuario(
        nombre=nombre,
        rol=rol,
        activo=True
    )
    nuevo.set_password(password)
    db.session.add(nuevo)
    db.session.commit()
    flash('Usuario creado correctamente', 'success')
    return redirect(url_for('usuarios.lista_usuarios'))

@usuarios_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_usuario(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    
    # No permitir desactivarse a sí mismo
    if usuario.id == current_user.id:
        flash('No puedes desactivar tu propio usuario', 'info')
        return redirect(url_for('usuarios.lista_usuarios'))
    
    usuario.activo = not usuario.activo
    db.session.commit()
    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f'Usuario {usuario.nombre} {estado}', 'success')
    return redirect(url_for('usuarios.lista_usuarios'))