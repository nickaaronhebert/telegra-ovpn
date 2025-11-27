# Telegra OpenVPN Manager

Flask-based web UI for managing OpenVPN clients and certificates.

## Installation

The service is configured to run via systemd on port 8082.

### Starting the Service

```bash
sudo systemctl start openvpn-manager
sudo systemctl status openvpn-manager
```

### Web Interface

Access the web UI at: http://localhost:8082

## Deployment

To update the service with the latest changes from Git:

```bash
./deploy.sh
```

The deployment script:
1. Pulls the latest changes from Git
2. Restarts the service
3. Verifies the status

## Directory Structure

- `openvpn_manager.py` - Flask application
- `deploy.sh` - Deployment script
- `.gitignore` - Git ignore rules
- `README.md` - This file

## Logs

Service logs are stored in `/home/ubuntu/openvpn_manager.log`

```bash
tail -f /home/ubuntu/openvpn_manager.log
```

## Development Workflow

1. Make changes to the code
2. Push to Git: `git push origin main`
3. Run deployment: `./deploy.sh`

Or combine both:
```bash
git push origin main && ./deploy.sh
```
