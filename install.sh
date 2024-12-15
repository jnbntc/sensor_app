#!/bin/bash
# Definir el directorio base del proyecto
BASE_DIR="/home/juan/sensor_app"

# Actualizar el sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar dependencias
sudo apt-get install -y python3-pip python3-dev python3-setuptools python3-venv nginx

# Crear un entorno virtual
python3 -m venv /home/juan/sensor_env
source /home/juan/sensor_env/bin/activate

# Instalar las bibliotecas de Python necesarias
pip install Adafruit_DHT Flask gunicorn RPi.GPIO flask-cors

# Configurar el servicio systemd
sudo tee /etc/systemd/system/sensor_app.service > /dev/null <<EOT
[Unit]
Description=Sensor Application
After=network.target

[Service]
ExecStart=/home/juan/sensor_env/bin/gunicorn --workers 1 --bind unix:$BASE_DIR/sensor_app.sock -m 007 app:app
WorkingDirectory=$BASE_DIR
User=juan
Group=www-data
Restart=always

[Install]
WantedBy=multi-user.target
EOT

# Permisos para el socket
sudo chmod 755 $BASE_DIR
sudo chown juan:www-data $BASE_DIR

# Recargar systemd, iniciar y habilitar el servicio
sudo systemctl daemon-reload
sudo systemctl start sensor_app
sudo systemctl enable sensor_app

# Configurar Nginx
sudo tee /etc/nginx/sites-available/sensor_app > /dev/null <<EOT
server {
    listen 80 default_server;
    server_name _;

    location / {
        include proxy_params;
        proxy_pass http://unix:$BASE_DIR/sensor_app.sock;
    }
}
EOT

# Eliminar el enlace simbólico predeterminado si existe
sudo rm -f /etc/nginx/sites-enabled/default

# Crear enlace simbólico para nuestro sitio
sudo ln -sf /etc/nginx/sites-available/sensor_app /etc/nginx/sites-enabled/

# Verificar la configuración de Nginx
sudo nginx -t

# Abrir puertos en el firewall
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Reiniciar Nginx
sudo systemctl restart nginx

echo "Instalación completada. La aplicación debería estar accesible en http://$(hostname -I | awk '{print $1}')"
