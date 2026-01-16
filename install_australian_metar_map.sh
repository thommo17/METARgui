#!/bin/bash
set -e

AP_SSID="Australian_METAR_Map"
AP_IP="10.0.0.1"
APP_DIR="/opt/METARgui"
APP_FILE="webconfig.py"
APP_PORT="5000"

STATE_FILE="/etc/metar_wifi_failcount"
MAX_FAILS=3

echo "======================================"
echo " Australian METAR Map Installer"
echo "======================================"

echo "[1/10] Installing packages..."
apt update
apt install -y python3 python3-pip hostapd dnsmasq iw

systemctl unmask hostapd || true

echo "[2/10] Backing up dhcpcd client config..."
cp /etc/dhcpcd.conf /etc/dhcpcd.conf.client || true

echo "[3/10] Creating AP dhcpcd config..."
cat > /etc/dhcpcd.conf.ap <<EOF
interface wlan0
    static ip_address=${AP_IP}/24
    nohook wpa_supplicant
EOF

echo "[4/10] Configuring dnsmasq..."
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.backup 2>/dev/null || true
cat > /etc/dnsmasq.conf <<EOF
interface=wlan0
dhcp-range=10.0.0.2,10.0.0.50,255.255.255.0,12h
address=/#/${AP_IP}
EOF

echo "[5/10] Configuring hostapd (open AP)..."
cat > /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
ssid=${AP_SSID}
hw_mode=g
channel=7
auth_algs=1
ignore_broadcast_ssid=0
EOF

echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > /etc/default/hostapd

echo "[6/10] Creating boot-time WiFi reset script..."
cat > /usr/local/bin/wifi_reset_client.sh <<EOF
#!/bin/bash

cp /etc/dhcpcd.conf.client /etc/dhcpcd.conf 2>/dev/null || true
sed -i '/nohook wpa_supplicant/d' /etc/dhcpcd.conf

systemctl stop hostapd dnsmasq 2>/dev/null || true

ip link set wlan0 down
sleep 1
ip link set wlan0 up

systemctl restart dhcpcd
systemctl restart wpa_supplicant 2>/dev/null || true
EOF

chmod +x /usr/local/bin/wifi_reset_client.sh

cat > /etc/systemd/system/metar-wifi-reset.service <<EOF
[Unit]
Description=Reset WiFi to client mode at boot
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/wifi_reset_client.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable metar-wifi-reset.service

echo "[7/10] Creating Wi-Fi mode controller..."
echo "0" > ${STATE_FILE}

cat > /usr/local/bin/wifi_check.sh <<EOF
#!/bin/bash

STATE_FILE="${STATE_FILE}"
MAX_FAILS=${MAX_FAILS}

SSID=\$(iwgetid -r 2>/dev/null || true)
FAILS=\$(cat "\${STATE_FILE}" 2>/dev/null || echo 0)

if [ -n "\${SSID}" ]; then
    echo "0" > "\${STATE_FILE}"
    systemctl stop hostapd dnsmasq 2>/dev/null || true
    exit 0
fi

if [ -n "$SSID" ]; then
    echo "0" > "$STATE_FILE"
    systemctl stop hostapd dnsmasq 2>/dev/null || true
    exit 0
fi

FAILS=$((FAILS + 1))
echo "$FAILS" > "$STATE_FILE"

if [ "$FAILS" -lt "$MAX_FAILS" ]; then
    exit 0
fi

# Switch to AP mode
systemctl stop wpa_supplicant 2>/dev/null || true
cp /etc/dhcpcd.conf.ap /etc/dhcpcd.conf
systemctl restart dhcpcd
systemctl start dnsmasq hostapd
EOF

chmod +x /usr/local/bin/wifi_check.sh

echo "[8/10] Creating systemd timer..."
cat > /etc/systemd/system/wifi-check.service <<EOF
[Unit]
Description=Australian METAR WiFi Mode Manager
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/wifi_check.sh
EOF

cat > /etc/systemd/system/wifi-check.timer <<EOF
[Unit]
Description=Run WiFi check every minute

[Timer]
OnBootSec=60
OnUnitActiveSec=30

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable wifi-check.timer

echo "[9/10] Installing Flask GUI autostart..."
pip3 install flask

cat > /etc/systemd/system/metar-gui.service <<EOF
[Unit]
Description=Australian METAR Map Web GUI
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${APP_DIR}/${APP_FILE}
WorkingDirectory=${APP_DIR}
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

systemctl enable metar-gui

echo "[10/10] Permissions..."
chown -R pi:pi ${APP_DIR}

echo "======================================"
echo " INSTALL COMPLETE"
echo "--------------------------------------"
echo " Setup Wi-Fi SSID: ${AP_SSID}"
echo " Password: (none)"
echo " Portal: http://${AP_IP}:${APP_PORT}"
echo " Grace period: ${MAX_FAILS} failed checks"
echo "--------------------------------------"
echo " Rebooting in 5 seconds..."
sleep 5
reboot
