from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os
import subprocess
import re
import configparser
import io
import shutil

app = Flask(__name__)
app.secret_key = "changeme123"  # ⚠️ change this to something secure

# File paths
METAR_CONF = "/etc/rpi_metar.conf"
WPA_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"

# Login credentials (hardcoded for now)
USERNAME = "pi"
PASSWORD = "raspberry"

# Backup Wifi network
BACKUP_NETWORK = ("rpi_metar_au", "0431101465")

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
#   METAR CONFIG
# ============================
@app.route("/metar", methods=["GET", "POST"])
def config():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    config = configparser.ConfigParser(strict=False, delimiters=("="))
    config.optionxform = str  # preserve case
    config.read(METAR_CONF)

    # Handle save
    if request.method == "POST":
        # Update airports
        airports = {}
        i = 0
        while True:
            code = request.form.get(f"airport_code_{i}")
            led = request.form.get(f"airport_led_{i}")
            if not code:
                break
            if led and led.isdigit():
                airports[code.strip()] = led.strip()
            i += 1

        config["airports"] = airports

        # Update other sections
        for section in config.sections():
            if section != "airports":
                for key in config[section]:
                    form_key = f"{section}_{key}"
                    if form_key in request.form:
                        config[section][key] = request.form[form_key]

        # Save file
        with open(METAR_CONF, "w") as f:
            config.write(f)

        return redirect(url_for("config"))

    airports = dict(config.items("airports")) if "airports" in config else {}
    settings = dict(config.items("settings")) if "settings" in config else {}
    legend = dict(config.items("legend")) if "legend" in config else {}

    return render_template("metar.html", airports=airports, settings=settings, legend=legend)

# ============================
#   WIFI CONFIG
# ============================
@app.route("/wifi", methods=["GET", "POST"])
def wifi():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # ---- Save Networks ----
    if request.method == "POST" and "save" in request.form:
        networks = []
        for i in range(len(request.form)//2):
            ssid = request.form.get(f"ssid_{i}")
            psk = request.form.get(f"psk_{i}")
            if ssid and ssid != BACKUP_NETWORK[0]:
                networks.append((ssid, psk))

        # Always include the backup network
        networks.append(BACKUP_NETWORK)

        with open(WPA_CONF, "w") as f:
            f.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
            f.write('update_config=1\n')
            f.write('country=AU\n\n')
            for ssid, psk in networks:
                f.write("network={\n")
                f.write(f'    ssid="{ssid}"\n')
                if psk:
                    f.write(f'    psk="{psk}"\n')
                f.write("}\n\n")
        return redirect(url_for("wifi"))

    # ---- Scan Wi-Fi Networks ----
    scanned = []
    if request.method == "POST" and "scan" in request.form:
        try:
            result = subprocess.run(
                ["sudo", "iwlist", "wlan0", "scan"],
                capture_output=True, text=True, check=True
            )
            scanned = sorted(set(re.findall(r'ESSID:"([^"]+)"', result.stdout)))
        except subprocess.CalledProcessError:
            scanned = ["Error scanning networks"]

    # ---- Read existing saved networks ----
    networks = []
    if os.path.exists(WPA_CONF):
        with open(WPA_CONF) as f:
            content = f.read()
        for block in re.findall(r'network=\{([^}]+)\}', content, re.DOTALL):
            ssid_match = re.search(r'ssid="([^"]+)"', block)
            psk_match = re.search(r'psk="([^"]+)"', block)
            if ssid_match:
                ssid = ssid_match.group(1)
                psk = psk_match.group(1) if psk_match else ""
                networks.append((ssid, psk))

    # Ensure backup network is always present
    if BACKUP_NETWORK not in networks:
        networks.append(BACKUP_NETWORK)

    return render_template("wifi.html", networks=networks, scanned=scanned, backup=BACKUP_NETWORK)

@app.route("/config/download")
def download_config():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return send_file(METAR_CONF, as_attachment=True, download_name="rpi_metar.conf")

@app.route("/config/upload", methods=["POST"])
def upload_config():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    file = request.files.get("file")
    if file and file.filename.endswith(".conf"):
        file.save(METAR_CONF)
    if os.path.exists(METAR_CONF):
        shutil.copy(METAR_CONF, METAR_CONF + ".bak")
    return redirect(url_for("config"))
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
