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
        usuario["rol"] = "1"
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            resultado = sentencia.var(cx_Oracle.STRING) 
            mensaje = sentencia.var(cx_Oracle.STRING)

            try:
                sentencia.callproc(
                    "INSERTAR_USUARIO", 
                    (
                        int(usuario["rut"]), 
                        usuario["nombre"], 
                        usuario["apellidos"], 
                        usuario["contrasena"], 
                        int(usuario["rol"]),
                        resultado, 
                        mensaje
                    )
                )
                conexion.commit()  # Confirmar la transacción
                flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
            except cx_Oracle.DatabaseError as e:
                flash("Error al registrar usuario: " + str(e), "danger")
            finally:
                sentencia.close()
                conexion.close()
        else:
            flash("No se pudo realizar la conexión", "danger")
        return redirect(url_for("inicio"))
    else:  
        return redirect(url_for("inicio"))


@app.route("/productos", methods=["GET"])  # Vista de los productos
def productos():
    if "usuario" in session:
        rut_usuario = session["usuario"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            try:
                # Si el usuario es administrador, trae todos los productos
                if rut_usuario == 11111:
                    sentencia.prepare("SELECT * FROM PRODUCTO")
                else:
                    # Si el usuario no es administrador, solo trae los productos correspondientes a su RUT
                    sentencia.prepare("SELECT * FROM PRODUCTO WHERE RUT_USUARIO = :rut")
                    sentencia.execute(None, {'rut': int(rut_usuario)})

                productos = [fila for fila in sentencia]
                return render_template("productos.html", productos=productos, es_admin=(rut_usuario == 11111))
            except cx_Oracle.DatabaseError as e:
                flash("Error al obtener productos: " + str(e), "danger")
            finally:
                sentencia.close()
        else:
            flash("No se pudo realizar la conexión", "danger")
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
            try:
                sentencia.callproc(
                    "INICIAR_SESION", 
                    (
                        int(usuario["rut"]), 
                        usuario["contrasena"], 
                        resultado, 
                        mensaje
                    )
                )
                if resultado.getvalue() == "TRUE":
                    session["usuario"] = int(usuario["rut"])
                    flash(mensaje.getvalue(), "success")
                else:
                    flash(mensaje.getvalue(), "danger")
            except cx_Oracle.DatabaseError as e:
                flash("Error al iniciar sesión: " + str(e), "danger")
            finally:
                sentencia.close()
        else:
            flash("No se pudo realizar la conexión", "danger")
        return redirect(url_for("productos"))
    else:
        return render_template("inicio_sesion.html")

@app.route("/insertar_producto", methods=["POST", "GET"])  # Vista para insertar producto
@requiere_administrador
def insertar_producto():
    if request.method == "POST":
        # Recibir datos del formulario
        productos = {
            "codigo": request.form["codigo_producto"],
            "nombre": request.form["nombre_producto"],
            "precio": request.form["precio_producto"],
            "categoria": request.form["categoria_producto"],
            "stock": request.form["stock_producto"]
        }

        conexion = conectar_bdd()  # Conexión a la base de datos
        if conexion:
            try:
                # Preparar variables para el procedimiento
                sentencia = conexion.cursor()
                resultado = sentencia.var(cx_Oracle.STRING)
                mensaje = sentencia.var(cx_Oracle.STRING)
                rut_usuario = session["usuario"]  # Se obtiene el RUT del usuario desde la sesión

                # Llamada al procedimiento almacenado
                sentencia.callproc(
                    "INSERTAR_PRODUCTO",
                    [
                        int(productos["codigo"]),
                        productos["nombre"],
                        int(productos["precio"]),
                        int(productos["categoria"]),
                        int(productos["stock"]),
                        int(rut_usuario),
                        resultado,
                        mensaje
                    ]
                )
                flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
            except Exception as e:
                # Manejo de errores de la base de datos
                flash(f"Error al insertar producto: {str(e)}", "danger")
            finally:
                sentencia.close()
        else:
            # Error en la conexión
            flash("No se pudo realizar la conexión con la base de datos", "danger")

        return redirect(url_for("productos"))  # Redirige a la vista de productos

    else:
        # Obtener las categorías desde la base de datos para llenar el <select>
        conexion = conectar_bdd()
        if conexion:
            try:
                sentencia = conexion.cursor()
                sentencia.execute("SELECT CODIGO, NOMBRE FROM CATEGORIA")  # Trae ID y nombre
                categorias = [fila for fila in sentencia]
            except Exception as e:
                categorias = []
                flash(f"Error al cargar categorías: {str(e)}", "danger")
            finally:
                sentencia.close()
        else:
            categorias = []
            flash("No se pudo realizar la conexión con la base de datos", "danger")

        # Renderiza la plantilla con las categorías
        return render_template("insertar_producto.html", categorias=categorias)

@app.route("/procesar_pago", methods=["POST"])
def procesar_pago():
    codigo_producto = request.form["codigo_producto"]
    rut_usuario = session["usuario"]

    conexion = conectar_bdd()
    if conexion:
        try:
            cursor = conexion.cursor()
            resultado = cursor.var(cx_Oracle.STRING)
            mensaje = cursor.var(cx_Oracle.STRING)

            # Suponiendo que tienes un procedimiento almacenado para procesar el pago
            cursor.callproc("PROCESAR_PAGO", [codigo_producto, rut_usuario, resultado, mensaje])
            conexion.commit()
            cursor.close()

            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        except Exception as e:
            flash(f"Error al procesar el pago: {str(e)}", "danger")
        return redirect(url_for("productos"))
    else:
        flash("No se pudo conectar a la base de datos", "danger")
        return redirect(url_for("productos"))




@app.route("/modificar_producto", methods=["POST", "GET"])
@requiere_administrador
def modificar_producto():
    if request.method == "POST":
        codigo = request.form["codigo_producto"]
        nombre = request.form["nombre_producto"]
        precio = request.form["precio_producto"]
        stock = request.form["stock_producto"]
        rut_usuario = session["usuario"]

        conexion = conectar_bdd()
        if conexion:
            cursor = conexion.cursor()
            resultado = cursor.var(cx_Oracle.STRING)
            mensaje = cursor.var(cx_Oracle.STRING)
            
            cursor.callproc("MODIFICAR_PRODUCTO", [
                int(codigo), nombre, int(precio), int(stock), int(rut_usuario), resultado, mensaje
            ])
            conexion.commit()
            cursor.close()

            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        else:
            flash("No se pudo conectar a la base de datos", "danger")
        return redirect(url_for("productos"))
    else:
        # Aquí puedes cargar los datos del producto
        return render_template("modificar_producto.html")


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
        servidor = cx_Oracle.makedsn('localhost', '1521', service_name='xe') 
        conexion = cx_Oracle.connect(user='USUARIO', password='PROYECTO', dsn=servidor) 
        return conexion
    except cx_Oracle.DatabaseError as e:
        print("Error al conectar a la base de datos:", e)
        return False

if __name__ == "__main__":
    app.run(debug=True)
