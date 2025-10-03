from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import subprocess
import os
from shared_modules.config import Config


app = Flask(__name__)
# Secret Key sicher aus Umgebungsvariable oder .env laden
config = Config()
app.secret_key = config.get_secret("FLASK_SECRET_KEY", "unsicherer_fallback")

login_manager = LoginManager()
login_manager.init_app(app)

# Dummy-User
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == "stephan":
        return User(user_id)
    return None

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Sichere Passwortprüfung: Passwort aus Umgebungsvariable/.env
        valid_user = config.get_secret("APP_USER", "stephan")
        valid_password = config.get_secret("APP_PASSWORD", "test")
        if username == valid_user and password == valid_password:
            user = User(username)
            login_user(user)
            return redirect(url_for("menu"))
        else:
            return render_template("login.html", error="Falsche Zugangsdaten!")
    return render_template("login.html")

@app.route("/menu")
@login_required
def menu():
    return render_template("menu.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/rechnungen", methods=["GET", "POST"])
@login_required
def rechnungen():
    if request.method == "POST":
        monat = request.form["monat"]
        jahr = request.form["jahr"]
        abrechnungsmonat = f"{monat}.{jahr}"
        # Starte das Rechnungsmodul (z.B. als Subprozess)
        subprocess.Popen(["python3", "src/rechnungen/rechnungen_oo.py", abrechnungsmonat])
        return render_template("success.html", msg=f"Rechnungen für {abrechnungsmonat} werden erstellt.")
    return render_template("abrechnung.html", title="Rechnungen erstellen")

@app.route("/ab_bogen", methods=["GET", "POST"])
@login_required
def ab_bogen():
    if request.method == "POST":
        monat = request.form["monat"]
        jahr = request.form["jahr"]
        abrechnungsmonat = f"{jahr}-{monat.zfill(2)}"
        # Starte das Zeiterfassungsmodul (z.B. als Subprozess)
        subprocess.Popen(["python3", "src/zeiterfassungen/neuen_monat_anlegen.py", abrechnungsmonat])
        return render_template("success.html", msg=f"Abrechnungsbögen für {abrechnungsmonat} werden erstellt.")
    return render_template("abrechnung.html", title="Abrechnungsbögen erstellen")

@app.route("/ueber")
@login_required
def ueber():
    return render_template("ueber.html")

if __name__ == "__main__":
    app.run(debug=True)