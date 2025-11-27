#!/bin/bash

# Deploy script for OpenVPN Manager
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting deployment..."

# Change to repo directory
cd /home/ubuntu/telegra-ovpn || exit 1

# Pull latest changes
echo "Pulling latest changes from Git..."
git pull origin main

# Restart service
echo "Restarting OpenVPN Manager service..."
sudo systemctl restart openvpn-manager

# Wait for service to start
sleep 2

# Check status
if sudo systemctl is-active --quiet openvpn-manager; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deployment successful!"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Service failed to start!"
    exit 1
fi
