from flask import Flask, render_template, url_for, request, redirect, session, flash
import cx_Oracle

app = Flask(__name__)
app.config["SECRET_KEY"] = '4495d60fb193c77b54e891a4fe200e7e'


RUT_ADMINISTRADOR = 11111  # Definir el RUT del administrador

def requiere_administrador(func):
    def wrapper(*args, **kwargs):
        if "usuario" in session and session["usuario"] == RUT_ADMINISTRADOR:
            return func(*args, **kwargs)
        flash("Acceso restringido: solo el administrador puede realizar esta acción.", "danger")
        return redirect(url_for("productos"))
    wrapper.__name__ = func.__name__
    return wrapper

@app.route("/", methods=["POST", "GET"])  # vista de la página principal - registro
def inicio():
    if "usuario" in session:
        return redirect(url_for("productos"))
    else:
        return render_template("inicio.html")

@app.route("/vista_principal", methods=["POST", "GET"])  # vista de la página principal - registro
def vista_principal():
    if "usuario" in session:
        return redirect(url_for("productos"))
    else:
        return render_template("vista_principal.html")

@app.route("/registrar_usuario", methods=["POST", "GET"])
def registrar_usuario():
    if request.method == "POST":
        usuario = dict()
        usuario["rut"] = request.form["rut_usuario"]
        usuario["nombre"] = request.form["nombre_usuario"]
        usuario["apellidos"] = request.form["apellidos_usuario"]
        usuario["contrasena"] = request.form["contrasena_usuario"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            resultado = sentencia.var(cx_Oracle.STRING) 
            mensaje = sentencia.var(cx_Oracle.STRING)
            sentencia.callproc("INSERTAR_USUARIO", (int(usuario["rut"]), usuario["nombre"], usuario["apellidos"], usuario["contrasena"], resultado, mensaje))
            sentencia.close()
            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        else:
            flash("No se pudo realizar la conexion", "danger")
        return redirect(url_for("inicio"))
    else:  
        return redirect(url_for("inicio"))

@app.route("/productos", methods=["GET"])  # vista de los productos
def productos():
    if "usuario" in session:
        rut_usuario = session["usuario"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            sentencia.prepare("SELECT * FROM PRODUCTO WHERE RUT_USUARIO = :rut")
            sentencia.execute(None, {'rut': int(rut_usuario)})
            productos = [fila for fila in sentencia]
            sentencia.close()
            return render_template("productos.html", productos=productos)
        else:
            flash("No se pudo realizar la conexion", "danger")
            return redirect(url_for("productos"))
    else:
        return render_template("productos.html")

@app.route("/inicio_sesion", methods=["POST", "GET"])  # vista inicio sesión
def inicio_sesion():   
    if request.method == "POST":
        usuario = dict()
        usuario["rut"] = request.form["rut_usuario"]
        usuario["contrasena"] = request.form["contrasena_usuario"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            resultado = sentencia.var(cx_Oracle.STRING) 
            mensaje = sentencia.var(cx_Oracle.STRING)
            sentencia.callproc("INICIAR_SESION", (int(usuario["rut"]), usuario["contrasena"], resultado, mensaje))
            sentencia.close()
            if resultado.getvalue() == "TRUE":
                session["usuario"] = int(usuario["rut"])
                flash(mensaje.getvalue(), "success")
            else:
                flash(mensaje.getvalue(), "danger")
        else:
            flash("No se pudo realizar la conexion", "danger")
        return redirect(url_for("productos"))
    else:
        return render_template("inicio_sesion.html")


@app.route("/insertar_producto", methods=["POST", "GET"])  # vista insertar producto
@requiere_administrador
def insertar_producto():
    if request.method == "POST":
        productos = dict()
        productos["codigo"] = request.form["codigo_producto"]
        productos["nombre"] = request.form["nombre_producto"]
        productos["precio"] = request.form["precio_producto"]
        productos["categoria"] = request.form["categoria_producto"]
        productos["stock"] = request.form["stock_producto"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            resultado = sentencia.var(cx_Oracle.STRING) 
            mensaje = sentencia.var(cx_Oracle.STRING)
            rut_usuario = session["usuario"]
            sentencia.callproc("INSERTAR_PRODUCTO", (int(productos["codigo"]), productos["nombre"], int(productos["precio"]), int(productos["categoria"]), int(productos["stock"]), int(rut_usuario), resultado, mensaje))
            sentencia.close()
            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        else:
            flash("No se pudo realizar la conexion", "danger")
        return redirect(url_for("productos"))
    else:
        conexion = conectar_bdd()
        sentencia = conexion.cursor()
        sentencia.execute("SELECT * FROM CATEGORIA")
        categorias = [fila for fila in sentencia]
        sentencia.close()
        return render_template("insertar_producto.html", categorias=categorias)

@app.route("/modificar_producto", methods=["POST", "GET"])  # vista modificar producto
@requiere_administrador
def modificar_producto():
    if "usuario" in session and request.method == "POST":
        codigo = request.form["modificar_producto"]
        rut_usuario = session["usuario"]
        conexion = conectar_bdd()
        sentencia = conexion.cursor()
        sentencia.prepare("SELECT * FROM PRODUCTO WHERE CODIGO = :codigo")
        sentencia.execute(None, {'codigo': int(codigo)})
        producto = sentencia.fetchone()
        sentencia.close()
        return render_template("modificar_producto.html", producto=producto)
    else:
        return redirect(url_for("productos"))

@app.route("/eliminar_producto", methods=["POST", "GET"])  # vista eliminar producto
@requiere_administrador
def eliminar_producto():
    if "usuario" in session and request.method == "POST":
        codigo = request.form["eliminar_producto"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            resultado = sentencia.var(cx_Oracle.STRING) 
            mensaje = sentencia.var(cx_Oracle.STRING)
            rut_usuario = session["usuario"]
            sentencia.callproc("ELIMINAR_PRODUCTO", (int(codigo), int(rut_usuario), resultado, mensaje))
            sentencia.close()
            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        else:
            flash("No se pudo realizar la conexion", "danger")
        return redirect(url_for("productos"))
    else:
        return redirect(url_for("productos"))

@app.route("/cerrar_sesion")
def cerrar_sesion():
    session.pop("usuario", None)
    return redirect(url_for("inicio"))

def conectar_bdd():
    try:    
        servidor = cx_Oracle.makedsn('localhost', '1522', service_name='xe') 
        conexion = cx_Oracle.connect(user='camila', password='camila', dsn=servidor) 
        return conexion
    except cx_Oracle.DatabaseError as e:
        return False

if __name__ == "__main__":
    app.run(debug=True)
