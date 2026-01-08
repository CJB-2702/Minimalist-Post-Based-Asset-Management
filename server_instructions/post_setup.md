# Post-setup: starting, stopping and verifying services

This file collects the common commands you'll use after setup to start/stop the systemd service, Nginx, run the app manually, and verify everything is healthy.

## Systemd service (recommended)

- Start the service:

```bash
sudo systemctl start asset-management.service
```

- Stop the service:

```bash
sudo systemctl stop asset-management.service
```

- Restart the service:

```bash
sudo systemctl restart asset-management.service
```

- Enable at boot / disable:

```bash
sudo systemctl enable asset-management.service
sudo systemctl disable asset-management.service
```

- Status and logs:

```bash
sudo systemctl status asset-management.service
sudo journalctl -u asset-management.service -f
```

## Nginx

- Start/stop/restart/reload:

```bash
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx
sudo systemctl reload nginx   # reload config without dropping connections
```

- Test config and view status:

```bash
sudo nginx -t
sudo systemctl status nginx
sudo journalctl -u nginx -f
```

## Run the app manually (developer/testing)

- Activate venv and run in foreground:

```bash
cd /home/public-asset-managment
source venv/bin/activate
python3.14 app.py
```

- Run in background via the provided script:

```bash
cd /home/public-asset-managment
./onstart.sh &> server.log &
# optional: record PID
echo $! > /tmp/asset-management.pid
```

- Stop background run (if using PID file or `pkill`):

```bash
kill $(cat /tmp/asset-management.pid)  # if you created pid file
pkill -f "python3.14 app.py"          # general stop if no pid file
```

## Quick verification checks

- Check the app is listening on port 5000 locally:

```bash
ss -ltnp | grep :5000
# or
sudo netstat -ltnp | grep :5000
```

- Check Nginx is listening on 80/443:

```bash
ss -ltnp | grep nginx
```

- Basic HTTP(S) request to the domain (edge/Cloudflare):

```bash
curl -I https://ebamscore.com
curl -I http://127.0.0.1:5000
```

- Test TLS certificate and chain:

```bash
openssl s_client -connect ebamscore.com:443 -servername ebamscore.com
# inspect certificate file
sudo openssl x509 -in /etc/ssl/certs/ebamscore.crt -noout -text
```

- Check logs for errors:

```bash
sudo journalctl -u asset-management.service -n 200
sudo tail -n 200 /var/log/nginx/error.log
sudo tail -n 200 /var/log/nginx/access.log
```

- Firewall status:

```bash
sudo ufw status verbose
```

## Troubleshooting tips

- If `nginx -t` fails: examine the exact error, open the file reported and fix syntax; then `sudo systemctl reload nginx`.
- If TLS fails: check that private key permissions are `600` and owned by `root`, and the path in the Nginx config matches the actual file.
- If the app does not respond on port 5000: run it in the foreground (`python3.14 app.py`) to see stack traces; check `journalctl` if running under systemd.
- Use `sudo journalctl -xe` for system-level errors.

## Helpful one-liners

- Restart everything (Nginx + app):

```bash
sudo systemctl restart nginx && sudo systemctl restart asset-management.service
```

- Watch both logs in separate terminals (example using `tail`):

```bash
sudo tail -f /var/log/nginx/error.log /var/log/nginx/access.log
sudo journalctl -u asset-management.service -f
```


---

File created to complement `as_server/configure_server.md` (commands-first) and `as_server/setup_nginx.md` (explanations).