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