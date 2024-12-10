from flask import Flask, render_template, url_for, request, redirect, session, flash
import cx_Oracle
import secrets
app = Flask(__name__, static_folder='../Styles')
app.config["SECRET_KEY"] = secrets.token_hex(16)

@app.route("/login", methoods=["POST","GET"])
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
        return redirect(url_for('login'))
    else:
        return render_template("../Pages/Login.html")
    
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