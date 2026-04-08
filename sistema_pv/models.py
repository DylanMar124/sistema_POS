from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

mexico_tz = pytz.timezone('America/Mexico_City')

def local_now():
    """Retorna la fecha y hora actual en la zona horaria de México"""
    return datetime.now(mexico_tz)

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='cajero')
    password_hash = db.Column(db.String(128), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_active(self):
        return self.activo
    
class Inventario(db.Model):
    __tablename__ = "inventario"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo = db.Column(db.Float, nullable=False)
    codigo_barras = db.Column(db.String(50))
    estatus = db.Column(db.Boolean, default=True)

class Ventas(db.Model):
    __tablename__ = "ventas"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=local_now, index=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.Boolean, default=True)

    detalles = db.relationship('DetalleVenta', backref='ventas', lazy=True, cascade='all, delete-orphan')
    pagos = db.relationship('Pago', backref='ventas', lazy=True, cascade='all, delete-orphan')
    usuario = db.relationship('Usuario', backref='ventas')

    @property
    def total(self):
        return sum(d.subtotal for d in self.detalles)

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(20), nullable=False)  # 'efectivo', 'tarjeta', 'otro'
    fecha_hora = db.Column(db.DateTime, default=local_now)

class DetalleVenta(db.Model):
    __tablename__ = "detalle_venta"
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('inventario.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float)

    inventario = db.relationship('Inventario', backref='ventas')

    @property
    def subtotal(self):
        return self.cantidad * (self.precio_unitario or 0)
    
class Compra(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=local_now, index=True)
    proveedor = db.Column(db.String(100))
    factura = db.Column(db.String(50))
    observaciones = db.Column(db.Text)

    detalles = db.relationship('CompraDetalle', backref='compra', lazy=True, cascade='all, delete-orphan')

    @property
    def total(self):
        return sum(d.subtotal for d in self.detalles)


class CompraDetalle(db.Model):
    __tablename__ = 'compra_detalles'
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compras.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('inventario.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=True)  # opcional

    inventario = db.relationship('Inventario', backref='compras')

    @property
    def subtotal(self):
        return self.cantidad * (self.precio_unitario or 0)