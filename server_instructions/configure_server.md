# Server Configuration Guide

This guide walks through setting up the Public Asset Management server without Docker.

## Prerequisites

- Linux-based system with `apt-get` package manager
- Git installed
- sudo access

## Step-by-Step Configuration

### 1. Update System Packages

```bash
sudo apt-get update
```

### 2. Install deadsnakes PPA

The deadsnakes PPA provides newer Python versions not available in standard repositories.

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
```

### 3. Install Python 3.14

```bash
sudo apt-get install -y python3.14 python3.14-venv python3.14-dev
```

This installs:
````markdown
# Server configuration — full commands

This file lists the exact commands to run on a fresh Ubuntu/Debian droplet to:
- install and run the Flask application
- install and configure Nginx as a reverse proxy
- install or use TLS certificates (Certbot or Cloudflare origin certs)

Adjust `ebamscore.com`/paths to your domain and locations. Run these commands as a user with `sudo` access.

1) Update and base packages

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl software-properties-common
```

2) Python (3.14 via deadsnakes) and app dependencies

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.14 python3.14-venv python3.14-dev build-essential

# clone or update repository
cd /home
git clone https://your.git.repo/public-asset-managment.git || true
cd public-asset-managment || exit
git pull || true

# create venv and install requirements
python3.14 -m venv venv
./venv/bin/pip install --upgrade pip setuptools wheel
./venv/bin/pip install -r requirements.txt

# app directories
mkdir -p instance/large_attachments
chown -R $USER:$USER instance/large_attachments
chmod 750 instance/large_attachments
```

3) Create a system user for the service (do not run as root)

```bash
sudo adduser --system --group --no-create-home assetmgr
sudo chown -R assetmgr:assetmgr /home/public-asset-managment
```

4) Install and configure systemd service

```bash
sudo tee /etc/systemd/system/asset-management.service > /dev/null <<'SERVICE'
[Unit]
Description=Public Asset Management Server
After=network.target

[Service]
Type=simple
User=assetmgr
Group=assetmgr
WorkingDirectory=/home/public-asset-managment
ExecStart=/home/public-asset-managment/onstart.sh
Restart=on-failure
RestartSec=10
PIDFile=/home/public-asset-managment/asset-management.pid

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable asset-management.service
sudo systemctl start asset-management.service
sudo systemctl status asset-management.service
```

5) Install Nginx (reverse proxy) and firewall

```bash
sudo apt install -y nginx ufw
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo systemctl enable --now nginx
```

6) Nginx site config (example)

Create `/etc/nginx/sites-available/ebamscore.com` (replace domain):

```bash
sudo tee /etc/nginx/sites-available/ebamscore.com > /dev/null <<'NGINX'
server {
	listen 80;
	listen [::]:80;
	server_name ebamscore.com www.ebamscore.com;

	# Redirect HTTP to HTTPS
	return 301 https://$host$request_uri;
}

server {
	listen 443 ssl http2;
	listen [::]:443 ssl http2;
	server_name ebamscore.com www.ebamscore.com;

	# TLS certificate paths (either Certbot or Cloudflare origin certs)
	ssl_certificate /etc/ssl/certs/ebamscore.crt;
	ssl_certificate_key /etc/ssl/private/ebamscore.key;

	ssl_protocols TLSv1.2 TLSv1.3;
	ssl_prefer_server_ciphers on;
	ssl_ciphers HIGH:!aNULL:!MD5;

	location / {
		proxy_pass http://127.0.0.1:5000;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
	}
}
NGINX

sudo ln -s /etc/nginx/sites-available/ebamscore.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

7) Install TLS certificate — choose one of these options:

- Option A — Use Certbot (Let's Encrypt) and let it modify Nginx automatically

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ebamscore.com -d www.ebamscore.com
```

- Option B — Use provided Cloudflare origin certs (you said you have them at `/home/public-asset-managment/certs`)

```bash
# copy cert files into system locations and secure the private key
sudo mkdir -p /etc/ssl/certs /etc/ssl/private
sudo cp /home/public-asset-managment/certs/ebamscore.crt /etc/ssl/certs/
sudo cp /home/public-asset-managment/certs/ebamscore.key /etc/ssl/private/
sudo chown root:root /etc/ssl/certs/ebamscore.crt /etc/ssl/private/ebamscore.key
sudo chmod 644 /etc/ssl/certs/ebamscore.crt
sudo chmod 600 /etc/ssl/private/ebamscore.key

# update Nginx and reload
sudo nginx -t
sudo systemctl reload nginx
```

8) Cloudflare settings

 - In Cloudflare DNS, create an A record for `ebamscore.com` and `www` pointing to your droplet IP and enable proxy (orange cloud) if you want Cloudflare features.
 - In Cloudflare Dashboard → SSL/TLS set the mode to `Full (strict)` when using origin certs or a valid CA-signed cert.

9) Verify

```bash
sudo journalctl -u asset-management.service -f
sudo tail -f /var/log/nginx/error.log
```

Open a browser at: https://ebamscore.com

Notes
- This file is intended as an executable command list; see `setup_nginx.md` for explanations and alternatives.
- If you want me to run these steps automatically (generate config files, move certs), tell me which actions to perform here in the workspace and I will produce the exact patches.

````
|---------|---------|
