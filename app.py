"""Punto de venta académico. Flask + SQLite, apto para ejecución local."""
import os
import sqlite3
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS productos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 nombre TEXT NOT NULL,
 descripcion TEXT NOT NULL DEFAULT '',
 marca TEXT NOT NULL DEFAULT '',
 precio_centavos INTEGER NOT NULL CHECK(precio_centavos > 0),
 stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
 imagen TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ventas (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
 total_centavos INTEGER NOT NULL CHECK(total_centavos > 0),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS detalle_ventas (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 venta_id INTEGER NOT NULL REFERENCES ventas(id),
 producto_id INTEGER NOT NULL REFERENCES productos(id),
 cantidad INTEGER NOT NULL CHECK(cantidad > 0),
 precio_unitario_centavos INTEGER NOT NULL,
 subtotal_centavos INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_detalle_venta ON detalle_ventas(venta_id);
"""


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=str(BASE_DIR / 'instance' / 'pos.sqlite3'),
        UPLOAD_FOLDER=str(BASE_DIR / 'uploads'),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    secret_path = Path(app.config['DATABASE']).parent / '.secret_key'
    if 'SECRET_KEY' not in app.config or app.config['SECRET_KEY'] is None:
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32), encoding='ascii')
        app.config['SECRET_KEY'] = secret_path.read_text(encoding='ascii')

    def db():
        if 'db' not in g:
            connection = sqlite3.connect(app.config['DATABASE'], timeout=15)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=15000')
            g.db = connection
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        conn = g.pop('db', None)
        if conn is not None:
            conn.close()

    with app.app_context():
        connection = db()
        connection.executescript(SCHEMA)
        count = connection.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
        if count == 0:
            connection.execute('INSERT INTO usuarios(username,password_hash,created_at) VALUES(?,?,?)',
                               ('admin', generate_password_hash('Admin123!'), now()))
        connection.commit()

    def logged_in(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify(error='Inicia sesión para continuar.'), 401
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapper

    def csrf_check():
        token = session.get('csrf_token', '')
        provided = request.headers.get('X-CSRF-Token', '') or request.form.get('csrf_token', '')
        if not token or not secrets.compare_digest(token, provided):
            if request.path.startswith('/api/'):
                return jsonify(error='Sesión de formulario inválida. Recarga la página.'), 403
            abort(403)

    @app.context_processor
    def template_ctx():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(24)
        return {'csrf_token': session['csrf_token']}

    @app.get('/')
    def index():
        return redirect(url_for('panel') if 'user_id' in session else url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            csrf_check()
            username = (request.form.get('username') or '').strip()
            password = request.form.get('password') or ''
            user = db().execute('SELECT * FROM usuarios WHERE username=?', (username,)).fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['csrf_token'] = secrets.token_urlsafe(24)
                return redirect(url_for('panel'))
            flash('Usuario o contraseña incorrectos.', 'error')
        return render_template('login.html')

    @app.post('/logout')
    @logged_in
    def logout():
        csrf_check()
        session.clear()
        return redirect(url_for('login'))

    @app.route('/contrasena', methods=['GET', 'POST'])
    @logged_in
    def change_password():
        if request.method == 'POST':
            csrf_check()
            previous = request.form.get('actual', '')
            new_pass = request.form.get('nueva', '')
            user = db().execute('SELECT * FROM usuarios WHERE id=?', (session['user_id'],)).fetchone()
            if not check_password_hash(user['password_hash'], previous):
                flash('La contraseña actual es incorrecta.', 'error')
            elif len(new_pass) < 8:
                flash('La nueva contraseña debe tener al menos 8 caracteres.', 'error')
            else:
                db().execute('UPDATE usuarios SET password_hash=? WHERE id=?',
                             (generate_password_hash(new_pass), session['user_id']))
                db().commit()
                flash('Contraseña actualizada correctamente.', 'success')
                return redirect(url_for('panel'))
        return render_template('password.html')

    @app.get('/panel')
    @logged_in
    def panel():
        return render_template('panel.html')

    @app.get('/ventas')
    @logged_in
    def ventas():
        data = db().execute('''SELECT v.id,v.total_centavos,v.created_at,u.username,
            (SELECT GROUP_CONCAT(p.nombre || ' x' || dv.cantidad, ', ')
               FROM detalle_ventas dv JOIN productos p ON p.id=dv.producto_id
               WHERE dv.venta_id=v.id) AS detalle
            FROM ventas v JOIN usuarios u ON u.id=v.usuario_id
            ORDER BY v.id DESC LIMIT 300''').fetchall()
        return render_template('ventas.html', ventas=data)

    def serialize_product(row):
        return dict(id=row['id'], nombre=row['nombre'], descripcion=row['descripcion'],
                    marca=row['marca'], precio=f"{row['precio_centavos'] / 100:.2f}",
                    stock=row['stock'], imagen=url_for('uploaded_file', filename=row['imagen']) if row['imagen'] else None)

    @app.get('/api/productos')
    @logged_in
    def products():
        query = (request.args.get('q') or '').strip()[:120]
        if query:
            rows = db().execute('''SELECT * FROM productos
                WHERE nombre LIKE ? OR marca LIKE ? OR descripcion LIKE ? ORDER BY id DESC''',
                tuple([f'%{query}%'] * 3)).fetchall()
        else:
            rows = db().execute('SELECT * FROM productos ORDER BY id DESC').fetchall()
        return jsonify(productos=[serialize_product(x) for x in rows])

    @app.post('/api/productos')
    @logged_in
    def add_product():
        csrf_check()
        nombre = (request.form.get('nombre') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        marca = (request.form.get('marca') or '').strip()
        if not nombre or len(nombre) > 120 or len(marca) > 100 or len(descripcion) > 1000:
            return jsonify(error='Verifica el nombre (1-120), marca (máx. 100) y descripción (máx. 1000).'), 400
        try:
            precio = Decimal(request.form.get('precio', '')).quantize(Decimal('0.01'))
            if not precio.is_finite() or precio <= 0 or precio > Decimal('99999999.99'):
                raise ValueError()
            precio_centavos = int(precio * 100)
            stock_text = request.form.get('stock', '')
            if not stock_text.isdigit():
                raise ValueError()
            stock = int(stock_text)
            if stock > 1000000:
                raise ValueError()
        except (InvalidOperation, ValueError, OverflowError):
            return jsonify(error='El precio debe ser mayor que cero y el stock un entero no negativo.'), 400
        image_file = request.files.get('imagen')
        stored_name = None
        if image_file and image_file.filename:
            ext = Path(image_file.filename).suffix.lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
                return jsonify(error='Imagen no admitida. Usa JPG, PNG o WEBP.'), 400
            try:
                image_file.stream.seek(0)
                with Image.open(image_file.stream) as im:
                    im.verify()
                image_file.stream.seek(0)
                with Image.open(image_file.stream) as im:
                    image_format = im.format
                if image_format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValueError('Invalid format')
                stored_name = uuid.uuid4().hex + {'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}[image_format]
                image_file.stream.seek(0)
                image_file.save(Path(app.config['UPLOAD_FOLDER']) / stored_name)
            except (UnidentifiedImageError, OSError, ValueError):
                return jsonify(error='El archivo no es una imagen válida.'), 400
        connection = db()
        try:
            cur = connection.execute('''INSERT INTO productos
               (nombre,descripcion,marca,precio_centavos,stock,imagen,created_at)
               VALUES(?,?,?,?,?,?,?)''',
               (nombre, descripcion, marca, precio_centavos, stock, stored_name, now()))
            connection.commit()
        except Exception:
            if stored_name:
                (Path(app.config['UPLOAD_FOLDER']) / stored_name).unlink(missing_ok=True)
            raise
        row = connection.execute('SELECT * FROM productos WHERE id=?', (cur.lastrowid,)).fetchone()
        return jsonify(mensaje='Producto registrado correctamente.', producto=serialize_product(row)), 201

    @app.post('/api/vender')
    @logged_in
    def sell():
        csrf_check()
        data = request.get_json(silent=True) or {}
        try:
            producto_id = int(data.get('producto_id'))
            cantidad = int(data.get('cantidad'))
            if isinstance(data.get('cantidad'), bool) or str(data.get('cantidad')) != str(cantidad):
                raise ValueError()
            if producto_id < 1 or cantidad < 1 or cantidad > 1000000:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify(error='Selecciona un producto y una cantidad entera positiva.'), 400
        con = db()
        try:
            con.execute('BEGIN IMMEDIATE')
            product = con.execute('SELECT * FROM productos WHERE id=?', (producto_id,)).fetchone()
            if product is None:
                con.rollback()
                return jsonify(error='El producto no existe.'), 404
            if product['stock'] < cantidad:
                con.rollback()
                return jsonify(error=f"Stock insuficiente. Disponibles: {product['stock']}."), 409
            subtotal = product['precio_centavos'] * cantidad
            con.execute('UPDATE productos SET stock=stock-? WHERE id=?', (cantidad, producto_id))
            cur = con.execute('INSERT INTO ventas(usuario_id,total_centavos,created_at) VALUES(?,?,?)',
                              (session['user_id'], subtotal, now()))
            con.execute('''INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario_centavos,subtotal_centavos)
                           VALUES(?,?,?,?,?)''',
                        (cur.lastrowid, producto_id, cantidad, product['precio_centavos'], subtotal))
            con.commit()
            return jsonify(mensaje='Venta registrada correctamente.', venta_id=cur.lastrowid,
                           total=f'{subtotal / 100:.2f}', stock_restante=product['stock'] - cantidad)
        except Exception:
            con.rollback()
            raise

    @app.get('/imagenes/<path:filename>')
    @logged_in
    def uploaded_file(filename):
        if '/' in filename or '\\' in filename or filename.startswith('.'):
            abort(404)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.errorhandler(413)
    def too_large(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Imagen demasiado grande. Máximo 5 MB.'), 413
        return 'Archivo demasiado grande', 413

    return app


if __name__ == '__main__':
    app = create_app()
    print('\nPUNTO DE VENTA UBM: http://127.0.0.1:5000')
    print('Usuario inicial: admin | Contraseña inicial: Admin123!\n')
    from waitress import serve
    serve(app, host='127.0.0.1', port=5000, threads=4)
