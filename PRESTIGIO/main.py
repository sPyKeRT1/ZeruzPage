from flask import Flask, render_template, url_for, request, redirect, session, flash
import cx_Oracle
import secrets
app = Flask(__name__, static_folder='../Styles')
app.config["SECRET_KEY"] = secrets.token_hex(16)


RUT_ADMINISTRADOR = 11111  # Definir el RUT del administrador

def requiere_administrador(func):
    def wrapper(*args, **kwargs):
        if "usuario" in session and session["usuario"] == RUT_ADMINISTRADOR:
            return func(*args, **kwargs)
        flash("Acceso restringido: solo el administrador puede realizar esta acción.", "danger")
        return redirect(url_for("Product"))
    wrapper.__name__ = func.__name__
    return wrapper

@app.route("/", methods=["POST", "GET"])  # vista de la página principal - registro
def inicio():
    if "usuario" in session:
        return redirect(url_for("vista_principal"))
    else:
        return render_template("Home.html")

@app.route("/vista_principal", methods=["POST", "GET"])  # vista de la página principal - registro
def vista_principal():
    if "usuario" in session:
        return redirect(url_for("inicio"))
    else:
        return render_template("AdminHome.html")

@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "POST":
        user = dict()
        user["name"] = request.form['username']
        user["password"] = request.form['password']
        connect = connect_db()
        if connect != False:
            query = connect.cursor()
            result = query.var(cx_Oracle.STRING)
            message = query.var(cx_Oracle.STRING)
            query.callproc("INICIAR_SESION",(int(user["name"]),user["password"],result,message))
            query.close()
            if result.getvalue() == "TRUE":
                session['user'] = user["name"]
                flash(message.getvalue(),"success")
            else:
                flash(message.getvalue(),"danger")
        else:
            flash("No fue posible conectarse a la base de datos","danger")
        return redirect(url_for('vista_principal'))
    else:
        return render_template("Login.html")
    

@app.route("/productos", methods=["GET"])  # vista de los productos
def productos():
    if "usuario" in session:
        rut_usuario = session["usuario"]
        conexion = connect_db()
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
        return render_template("Products.html")
    
@app.route("/logout")



def connect_db():
    try:
        server = cx_Oracle.makedsn('localhost', '1521', service_name='xe')
        connect = cx_Oracle.connect(user='PROYECTO', password = 'PROYECTO', dsn = server)
        return connect
    except cx_Oracle.DatabaseError as e:
        error = e.args[0]
        print(error)
        return False

if __name__ == "__main__":
    app.run(debug=True)
