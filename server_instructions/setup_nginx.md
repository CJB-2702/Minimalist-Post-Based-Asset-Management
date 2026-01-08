# Nginx reverse proxy and basic hardening

This file contains recommended steps to run the application behind Nginx and basic server safety measures.

## Install Nginx and Certbot

## Nginx responsibilities and notes

This file explains responsibilities and alternatives. The definitive, runnable command list is in `as_server/configure_server.md`.

What `configure_server.md` does:
- Installs system packages and Python runtime
- Creates a non-root user and systemd service for the Flask app
- Installs and enables Nginx, UFW and firewall rules
- Creates an Nginx site config and enables it
- Installs TLS via Certbot OR copies Cloudflare origin certs into system paths

When to edit this file (`setup_nginx.md`):
- To change TLS hardening recommendations (ciphers, HSTS, OCSP stapling)
- To add advanced Nginx configuration (rate limiting, caching, upstream pools)
- To expand monitoring and logging instructions

Quick reference (see `configure_server.md` for exact commands):

- Create site config: `/etc/nginx/sites-available/ebamscore.com`
- Enable site: `sudo ln -s /etc/nginx/sites-available/ebamscore.com /etc/nginx/sites-enabled/`
- TLS options: Certbot (`certbot --nginx`) or Cloudflare origin certs copied to `/etc/ssl/certs` and `/etc/ssl/private`
- Test and reload: `sudo nginx -t && sudo systemctl reload nginx`

Security notes:
- Keep private keys under `/etc/ssl/private` with `chmod 600` and owned by `root`.
- Use Cloudflare `Full (strict)` if origin certs are present.
- Use `fail2ban` and `unattended-upgrades` for basic protections.

If you want me to further shorten `setup_nginx.md` or expand it with specific hardening profiles (Mozilla Modern/Intermediate), tell me which profile you prefer.
```bash
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

## Automatic updates & intrusion protection

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

## File permissions and secrets

- Keep secrets out of the repo and use environment variables or an `.env` file.
- If using `.env`, set `chmod 600 .env` and `chown assetmgr:assetmgr .env`.
- Secure uploads:

```bash
sudo chown -R assetmgr:assetmgr instance/large_attachments
sudo chmod -R 750 instance/large_attachments
```

## Monitoring

- Check service logs: `sudo journalctl -u asset-management.service -f`
- Check Nginx logs: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`
- Consider `logrotate` and external monitoring (Prometheus/Datadog) for production.

---

If you want, I can merge this content into `as_server/configure_server.md` (edit the file in-place).