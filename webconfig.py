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

# ============================
#   METAR CONFIG (IMPROVED)
# ============================
@app.route("/metar", methods=["GET", "POST"])
def metar():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect airports
        airports = []
        i = 0
        while True:
            code = request.form.get(f"airport_{i}")
            led = request.form.get(f"led_{i}")
            if code is None:
                break
            if code.strip():
                airports.append(f"{code.strip()}={led.strip()}")
            i += 1

        # Collect other settings
        others = request.form.get("other_settings", "").strip().splitlines()

        with open(METAR_CONF, "w") as f:
            for a in airports:
                f.write(a + "\n")
            f.write("\n")
            for line in others:
                f.write(line + "\n")

        return redirect(url_for("metar"))

    # ---- Parse config file ----
    airports = []
    others = []
    if os.path.exists(METAR_CONF):
        with open(METAR_CONF) as f:
            for line in f:
                line = line.strip()
                if re.match(r"^[A-Z]{4}=\d+$", line):
                    code, led = line.split("=")
                    airports.append((code, led))
                elif line:
                    others.append(line)

    return render_template("metar.html", airports=airports, others="\n".join(others))

# ============================
#   WIFI CONFIG (IMPROVED)
# ============================


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
