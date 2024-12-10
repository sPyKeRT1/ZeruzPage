#----------------------------------------IMPORTS NECESARIOS----------------------------------------

from flask import Flask, render_template, url_for, request, redirect, session, flash
import cx_Oracle

#----------------------------------------VALORES ESTATICOS-----------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = '4495d60fb193c77b54e891a4fe200e7e'
RUT_ADMINISTRADOR = 11111

#-----------------------------------FUNCION DETECCION DE ADMIN-------------------------------------

def requiere_administrador(func):
    def wrapper(*args, **kwargs):
        if "usuario" in session and session["usuario"] == RUT_ADMINISTRADOR:
            return func(*args, **kwargs)
        flash("Acceso restringido: solo el administrador puede realizar esta acción.", "danger")
        return redirect(url_for("productos"))
    wrapper.__name__ = func.__name__
    return wrapper

#------------------------------------------RUTA INICIAL--------------------------------------------

@app.route("/", methods=["POST", "GET"])
def inicio():
    if "usuario" in session:
        return redirect(url_for("productos"))
    else:
        return render_template("inicio.html")

#--------------------------------------RUTA INICIAR SESION-----------------------------------------

@app.route("/inicio_sesion", methods=["POST", "GET"])
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

#-----------------------------------------RUTA REGISTRO--------------------------------------------

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
                conexion.commit()
                flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
            except cx_Oracle.DatabaseError as e:
                flash("Error al registrar usuario: " + str(e), "danger")
            finally:
                sentencia.close()
                conexion.close()
        else:
            flash("No se pudo realizar la conexión", "danger")
        return redirect(url_for("inicio_sesion"))
    else:  
        return redirect(url_for("inicio"))

#---------------------------------------RUTA CERRAR SESION-----------------------------------------

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

#-----------------------------------RUTA MOSTRAR PRODUCTOS/HOME------------------------------------

@app.route("/productos", methods=["GET"])
def productos():
    if "usuario" in session:
        rut_usuario = session["usuario"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            try:
                # Fetch the user's role from the database
                sentencia.execute("SELECT rol FROM USUARIO WHERE rut = :rut", {"rut": rut_usuario})
                rol_resultado = sentencia.fetchone()
                
                # Determine admin status based on rol
                es_admin = rol_resultado and rol_resultado[0] != 1
                
                # Fetch all products
                sentencia.execute("SELECT * FROM PRODUCTO")
                productos = [fila for fila in sentencia]
                
                return render_template("productos.html", productos=productos, es_admin=es_admin)
            except cx_Oracle.DatabaseError as e:
                flash("Error al obtener productos: " + str(e), "danger")
            finally:
                sentencia.close()
        else:
            flash("No se pudo realizar la conexión", "danger")
            return redirect(url_for("productos"))
    return render_template("productos.html")

#-------------------------------------RUTA INSERTAR PRODUCTO---------------------------------------

@app.route("/insertar_producto", methods=["POST", "GET"])
@requiere_administrador
def insertar_producto():
    if request.method == "POST":
        productos = {
            "codigo": request.form["codigo_producto"],
            "nombre": request.form["nombre_producto"],
            "precio": request.form["precio_producto"],
            "categoria": request.form["categoria_producto"],
            "stock": request.form["stock_producto"]
        }
        conexion = conectar_bdd()
        if conexion:
            try:
                sentencia = conexion.cursor()
                resultado = sentencia.var(cx_Oracle.STRING)
                mensaje = sentencia.var(cx_Oracle.STRING)

                sentencia.callproc(
                    "INSERTAR_PRODUCTO",
                    [
                        int(productos["codigo"]),
                        productos["nombre"],
                        int(productos["precio"]),
                        int(productos["categoria"]),
                        int(productos["stock"]),
                        resultado,
                        mensaje
                    ]
                )
                flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
            except Exception as e:
                flash(f"Error al insertar producto: {str(e)}", "danger")
            finally:
                sentencia.close()
        else:
            flash("No se pudo realizar la conexión con la base de datos", "danger")
        return redirect(url_for("productos"))

    else:
        conexion = conectar_bdd()
        if conexion:
            try:
                sentencia = conexion.cursor()
                sentencia.execute("SELECT CODIGO, NOMBRE FROM CATEGORIA")
                categorias = [fila for fila in sentencia]
            except Exception as e:
                categorias = []
                flash(f"Error al cargar categorías: {str(e)}", "danger")
            finally:
                sentencia.close()
        else:
            categorias = []
            flash("No se pudo realizar la conexión con la base de datos", "danger")
        return render_template("insertar_producto.html", categorias=categorias)

#-------------------------------------RUTA MODIFICAR PRODUCTO--------------------------------------

@app.route("/modificar_producto", methods=["POST", "GET"])
@requiere_administrador
def modificar_producto():
    if request.method == "POST":
        codigo = request.form["codigo_producto"]
        nombre = request.form["nombre_producto"]
        precio = request.form["precio_producto"]
        stock = request.form["stock_producto"]

        conexion = conectar_bdd()
        if conexion:
            try:
                cursor = conexion.cursor()
                resultado = cursor.var(cx_Oracle.STRING)
                mensaje = cursor.var(cx_Oracle.STRING)
                
                cursor.callproc("MODIFICAR_PRODUCTO", [
                    int(codigo), nombre, int(precio), int(stock), resultado, mensaje
                ])
                conexion.commit()
                
                flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
            except cx_Oracle.DatabaseError as e:
                flash(f"Error al modificar producto: {str(e)}", "danger")
            finally:
                cursor.close()
                conexion.close()
        else:
            flash("No se pudo conectar a la base de datos", "danger")
        return redirect(url_for("productos"))
    else:
        # Lógica para cargar los datos del producto a modificar
        codigo_producto = request.args.get('codigo')
        if codigo_producto:
            conexion = conectar_bdd()
            if conexion:
                try:
                    cursor = conexion.cursor()
                    cursor.prepare("SELECT * FROM PRODUCTO WHERE CODIGO = :codigo")
                    cursor.execute(None, {'codigo': int(codigo_producto)})
                    producto = cursor.fetchone()
                    
                    if producto:
                        return render_template("modificar_producto.html", producto=producto)
                    else:
                        flash("Producto no encontrado", "danger")
                except cx_Oracle.DatabaseError as e:
                    flash(f"Error al buscar producto: {str(e)}", "danger")
                finally:
                    cursor.close()
                    conexion.close()
        
        return render_template("modificar_producto.html")

#-------------------------------------RUTA ELIMINAR PRODUCTO--------------------------------------

@app.route("/eliminar_producto", methods=["POST", "GET"])
@requiere_administrador
def eliminar_producto():
    if "usuario" in session and request.method == "POST":
        codigo = request.form["eliminar_producto"]
        conexion = conectar_bdd()
        if conexion:
            sentencia = conexion.cursor()
            resultado = sentencia.var(cx_Oracle.STRING) 
            mensaje = sentencia.var(cx_Oracle.STRING)
            sentencia.callproc("ELIMINAR_PRODUCTO", (int(codigo), resultado, mensaje))
            sentencia.close()
            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        else:
            flash("No se pudo realizar la conexion", "danger")
        return redirect(url_for("productos"))
    else:
        return redirect(url_for("productos"))

#----------------------------------------RUTA PROCESAR PAGO---------------------------------------

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
        return redirect(url_for("pago"))
    else:
        flash("No se pudo conectar a la base de datos", "danger")
        return redirect(url_for("pago"))

#------------------------------------RUTA ENCUESTA SATISFACCION-----------------------------------



#------------------------------------LLAMADO A LA FUNCION MAIN------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
