#----------------------------------------IMPORTS NECESARIOS----------------------------------------
# Importación de las librerías necesarias para el funcionamiento de la aplicación.

from flask import Flask, render_template, url_for, request, redirect, session, flash
import random
import cx_Oracle

#----------------------------------------VALORES ESTATICOS-----------------------------------------
# Configuración básica de Flask y definición de constantes, como la clave secreta y el rol de administrador.

app = Flask(__name__)
app.config["SECRET_KEY"] = '4495d60fb193c77b54e891a4fe200e7e'
ROL_ADMINISTRADOR = 2

#-----------------------------------FUNCION DETECCION DE ADMIN-------------------------------------
# Funcion para restringir el acceso a ciertas rutas únicamente a usuarios con rol de administrador.


def requiere_administrador(func):
    def wrapper(*args, **kwargs):
        if "usuario" in session and session["rol"] == ROL_ADMINISTRADOR:
            return func(*args, **kwargs)
        flash("Acceso restringido: solo el administrador puede realizar esta acción.", "danger")
        return redirect(url_for("productos"))
    wrapper.__name__ = func.__name__
    return wrapper

#------------------------------------------RUTA INICIAL--------------------------------------------
# Página inicial. Si hay un usuario autenticado, redirige a la vista de productos, de lo contrario,
# muestra la página de inicio de sesion.

@app.route("/", methods=["POST", "GET"])
def inicio():
    if "usuario" in session:
        return redirect(url_for("productos"))
    else:
        return render_template("inicio.html")

#------------------------------------------RUTA HOME--------------------------------------------
# Muestra los productos disponibles desde la base de datos para usuarios registrados.
# Gestiona posibles errores de conexión o consulta.

@app.route("/home", methods=["GET"])
def home():
    conexion = conectar_bdd()
    if conexion:
        try:
            sentencia = conexion.cursor()
            sentencia.execute("SELECT * FROM PRODUCTO")
            productos = [fila for fila in sentencia]
            return render_template("home.html", productos=productos)
        except cx_Oracle.DatabaseError as e:
            flash(f"Error al cargar productos: {str(e)}", "danger")
        finally:
            sentencia.close()
    else:
        flash("No se pudo conectar a la base de datos", "danger")
    return redirect(url_for("inicio"))
#--------------------------------------RUTA INICIAR SESION-----------------------------------------
# Gestiona la autenticación de usuarios haciendo llamados a la base de datos para verificar las credenciales.
# Configura la sesión y redirige según el rol del usuario
# se utiliza el procedure INICIAR_SESION.

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
            rol_usuario = sentencia.var(cx_Oracle.NUMBER)  
            try:
                sentencia.callproc(
                    "INICIAR_SESION", 
                    (
                        int(usuario["rut"]), 
                        usuario["contrasena"], 
                        resultado, 
                        mensaje,
                        rol_usuario 
                    )
                )

                if resultado.getvalue() == "TRUE":
                    session["usuario"] = int(usuario["rut"])
                    rol = rol_usuario.getvalue()
                    session["rol"] = rol if rol is not None else None

                    if rol == 1:
                        flash(mensaje.getvalue(), "success")
                        return redirect(url_for("home")) 
                    elif rol == ROL_ADMINISTRADOR: 
                        flash(mensaje.getvalue(), "success")
                        return redirect(url_for("productos")) 
                    else:
                        flash("Rol no reconocido.", "danger")
                else:
                    flash(mensaje.getvalue(), "danger")
                    return render_template("inicio_sesion.html")
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
# Permite registrar nuevos usuarios obteniendo sus datos desde el form HTML.
# luego se utiliza el procedure INSERTAR_USUARIO para agregarlos.

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
# Cierra la sesión del usuario eliminando su información de la sesión.

@app.route("/cerrar_sesion")
def cerrar_sesion():
    session.pop("usuario", None)
    return redirect(url_for("inicio"))

#---------------------------------------Conexion a la base de datos--------------------------------
# Establece y retorna una conexión con la base de datos Oracle local.
# En caso de error, muestra un mensaje en consola y retorna `False`.

def conectar_bdd():
    try:    
        servidor = cx_Oracle.makedsn('localhost', '1521', service_name='xe') 
        conexion = cx_Oracle.connect(user='USUARIO', password='PROYECTO', dsn=servidor) 
        return conexion
    except cx_Oracle.DatabaseError as e:
        print("Error al conectar a la base de datos:", e)
        return False

#-----------------------------------RUTA MOSTRAR PRODUCTOS/HOME------------------------------------
# Muestra una lista de productos desde la base de datos.
# Verifica si el usuario es administrador para habilitar funciones adicionales CRUD.

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
# Permite a los administradores agregar nuevos productos.


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
# Permite a los administradores modificar los detalles de un producto existente, excepto su id.
# se utiliza el procedure MODIFICAR_PRODUCTO

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

#------------------------------------RUTA PARA MOSTRAR PAGO----------------------------------------
# Muestra los detalles de un producto seleccionado para proceder al pago.

@app.route("/pago", methods=["GET"])
def mostrar_pago():
    codigo_producto = request.args.get("codigo_producto")
    if not codigo_producto:
        flash("Código de producto no válido", "danger")
        return redirect(url_for("productos"))

    conexion = conectar_bdd()
    if conexion:
        try:
            sentencia = conexion.cursor()
            sentencia.prepare("""
                SELECT p.*, c.nombre AS categoria
                FROM PRODUCTO p
                JOIN CATEGORIA c ON p.codigo_categoria = c.codigo
                WHERE p.codigo = :codigo
            """)
            sentencia.execute(None, {"codigo": int(codigo_producto)})
            producto = sentencia.fetchone()

            if producto:
                return render_template("pago.html", producto=producto)
            else:
                flash("Producto no encontrado", "danger")
        except cx_Oracle.DatabaseError as e:
            flash(f"Error al buscar producto: {str(e)}", "danger")
        finally:
            sentencia.close()
    else:
        flash("No se pudo conectar a la base de datos", "danger")
    return redirect(url_for("productos"))

#-------------------------------------RUTA ELIMINAR PRODUCTO--------------------------------------
# Permite a los administradores eliminar un producto.
# se utiliza el procedure ELIMINAR_PRODUCTO

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
# Procesa una compra, actualizando el stock del producto adquirido en la base de datos.
# se utiliza el procedure DESCONTAR_STOCK

@app.route("/procesar_pago", methods=["POST"])
def procesar_pago():
    codigo_producto = request.form["codigo_producto"]
    cantidad = int(request.form["cantidad"])  # Obtener cantidad de productos comprados
    rut_usuario = session.get("usuario")  # Uso de get para asegurar que 'usuario' exista en session

    conexion = conectar_bdd()
    if conexion:
        try:
            cursor = conexion.cursor()
            resultado = cursor.var(cx_Oracle.STRING)
            mensaje = cursor.var(cx_Oracle.STRING)

            # Llamar al procedimiento para descontar el stock
            cursor.callproc("DESCONTAR_STOCK", [codigo_producto, cantidad, resultado, mensaje])
            
            conexion.commit()
            cursor.close()

            flash(mensaje.getvalue(), "success" if resultado.getvalue() == "TRUE" else "danger")
        except cx_Oracle.DatabaseError as e:
            error, = e.args  # Obtener el primer error
            flash(f"Error al procesar el pago: {error.message}", "danger")
        except Exception as e:
            flash(f"Error desconocido: {str(e)}", "danger")
        return redirect(url_for("resena"))  # Redirigir a la página de reseñas después de procesar el pago
    else:
        flash("No se pudo conectar a la base de datos", "danger")
        return redirect(url_for("pago"))


#------------------------------------RUTA ENCUESTA SATISFACCION-----------------------------------
# Permite a los usuarios enviar una reseña con calificación y comentarios sobre su experiencia.
# se utiliza el procedure REGISTRAR_ENCUESTA


@app.route("/resena", methods=["POST", "GET"])  
def resena():
    if request.method == "POST":
        try:
            codigo_pedido = int(request.form["codigo_pedido"]) 
            rating = int(request.form["rating"]) 
            comentarios = request.form["comentarios"]
        except (KeyError, ValueError): 
            flash("Error: Datos de la reseña incompletos o inválidos.", "danger")
            return redirect(url_for('home')) 

        conexion = conectar_bdd()
        if conexion:
            try:
                sentencia = conexion.cursor()
                resultado = sentencia.var(cx_Oracle.STRING)
                mensaje = sentencia.var(cx_Oracle.STRING)

                sentencia.callproc(
                    "REGISTRAR_ENCUESTA",
                    (codigo_pedido, rating, comentarios, resultado, mensaje)
                )

                if resultado.getvalue() == "TRUE":
                    flash(mensaje.getvalue(), "success")
                else:
                    flash(mensaje.getvalue(), "danger")

            except cx_Oracle.DatabaseError as e:
                flash(f"Error al registrar la reseña: {e}", "danger")
            finally:
                sentencia.close()
                conexion.close()
        else:
            flash("No se pudo conectar a la base de datos.", "danger")


        return redirect(url_for('home'))
    else: 
        codigo_pedido = random.randint(100000, 999999)
        nombre_producto = request.args.get('nombre_producto')
        precio_producto = request.args.get('precio_producto')
        cantidad = request.args.get('cantidad')
        return render_template("resena.html", codigo_pedido=codigo_pedido, nombre_producto=nombre_producto,  precio_producto=precio_producto, cantidad=cantidad)

#------------------------------------LLAMADO A LA FUNCION MAIN------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
