from flask import Flask, render_template, request, redirect, url_for, session
import os
import subprocess
import re

app = Flask(__name__)
app.secret_key = "changeme123"  # ⚠️ change this to something secure

# File paths
METAR_CONF = "/etc/rpi_metar.conf"
WPA_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"

# Login credentials (hardcoded for now)
USERNAME = "pi"
PASSWORD = "raspberry"

# ----------------- Helpers -----------------
def load_conf(path):
    settings = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    settings[key] = val
    return settings

def save_conf(path, settings):
    with open(path, "w") as f:
        for k, v in settings.items():
            f.write(f"{k}={v}\n")

# ----------------- Routes -----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/metar", methods=["GET", "POST"])
def metar():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        settings = {k: v for k, v in request.form.items()}
        save_conf(METAR_CONF, settings)
        return redirect(url_for("metar"))

    settings = load_conf(METAR_CONF)
    return render_template("metar.html", settings=settings)

@app.route("/wifi", methods=["GET", "POST"])
def wifi():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        ssid = request.form.get("ssid")
        psk = request.form.get("psk")
        with open(WPA_CONF, "w") as f:
            f.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
            f.write('update_config=1\n')
            f.write('country=AU\n\n')  # adjust country code
            f.write("network={\n")
            f.write(f'    ssid="{ssid}"\n')
            f.write(f'    psk="{psk}"\n')
            f.write("}\n")
        return redirect(url_for("wifi"))

    return render_template("wifi.html")

@app.route("/restart_metar")
def restart_metar():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    try:
        subprocess.run(["sudo", "systemctl", "restart", "rpi_metar_au.service"], check=True)
        msg = "METAR service restarted successfully."
    except subprocess.CalledProcessError:
        msg = "Failed to restart METAR service."
    return render_template("dashboard.html", message=msg)

@app.route("/reboot")
def reboot():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    subprocess.Popen(["sudo", "reboot"])
    return "Rebooting..."

# ----------------- Run -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
