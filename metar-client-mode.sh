#!/bin/bash

echo "[METAR] Forcing client mode..."

# Stop AP services first (safe)
systemctl stop hostapd dnsmasq 2>/dev/null || true

# Restore client DHCP config
cp /etc/dhcpcd.conf.client /etc/dhcpcd.conf 2>/dev/null || true
sed -i '/nohook wpa_supplicant/d' /etc/dhcpcd.conf

# Clear WiFi fail counter
echo "0" > /etc/metar_wifi_failcount

# Restart networking cleanly
systemctl restart dhcpcd

# Delay before restarting wpa_supplicant so SSH can exit cleanly
(
    sleep 5
    ip link set wlan0 down
    sleep 2
    ip link set wlan0 up
    systemctl restart wpa_supplicant
) &

echo "[METAR] Client mode restore scheduled."
echo "[METAR] SSH may disconnect in a few seconds."
