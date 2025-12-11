#!/bin/bash
set -e

# Check if swap file already exists
if [ -f /swapfile ]; then
    echo "Swap file already exists."
    exit 0
fi

echo "Creating 2GB swap file..."
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make it permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

echo "Swap created successfully."
free -h
