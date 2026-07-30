How to install from scratch. Half tested.

## Install unrar with

sudo apt install unrar

## Copy METARgui.rar to pi and extract them

sudo cp METARgui.rar /opt/METARgui.rar
cd /opt
unrar x -r METARgui.rar

## Run installer

sudo bash /opt/METARgui/install_austrlaian_metar_map.sh

## Change permissions of files so the program can write to them

sudo chown pi:pi /etc/wpa_supplicant/wpa_supplicant.conf
sudo chmod 664 /etc/wpa_supplicant/wpa_supplicant.conf
sudo chown pi:pi /etc/rpi_metar.conf
sudo chmod 664 /etc/rpi_metar.conf


## Things I'm not sure about right now that may need to happen first

sudo su
apt install python3-venv
python3 -m venv /opt/METARgui
source /opt/METARgui/bin/activate
exit










About

Install
sudo su
apt install python3-venv
python3 -m venv /opt/METARgui
source /opt/METARgui/bin/activate
pip install METARgui


[Service]
ExecStart=/opt/rpi_metar/bin/rpi_metar
User=root
Group=root
Restart=always

[Install]
WantedBy=multi-user.target
Make systemd aware of the changes:

systemctl daemon-reload
Make sure it's set to run at boot:

systemctl enable rpi_metar
Start the service:

systemctl start rpi_metar