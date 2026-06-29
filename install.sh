#!/bin/bash
set -e

PACKAGES=(python3-pygame python3-flask)
MISSING=()
for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING+=("$pkg")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    sudo apt update
    sudo apt install -y "${MISSING[@]}"
fi

sudo cp raspi-box.service /etc/systemd/system/
sudo cp field-ops-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable raspi-box field-ops-web

echo "Installed. Reboot to auto-start, or run:"
echo "  sudo systemctl start raspi-box"
echo "  sudo systemctl start field-ops-web"
echo ""
echo "To set up the FIELD-OPS Wi-Fi hotspot, run: bash setup_hotspot.sh"
