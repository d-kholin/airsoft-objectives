#!/bin/bash
set -e

sudo apt update
sudo apt install -y python3-pygame

sudo cp raspi-box.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable raspi-box

echo "Installed. Reboot to auto-start, or run: sudo systemctl start raspi-box"
