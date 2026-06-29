#!/bin/bash
set -e

# ── Field Ops — Full Install ─────────────────────────────────────────
# Run this once on a fresh Pi to install everything:
#   packages, hotspot, systemd services, auto-start on boot.
#
# Usage:  bash install.sh
# ──────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_USER="$(whoami)"
INSTALL_UID="$(id -u)"

SSID="FIELD-OPS"
WIFI_PASS="fieldops1"
HOTSPOT_IP="192.168.4.1"
AP_IFACE="ap0"
WEB_PORT=8080

echo "╔══════════════════════════════════════╗"
echo "║         FIELD OPS INSTALLER          ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Project dir : $SCRIPT_DIR"
echo "  User        : $INSTALL_USER"
echo "  Hotspot SSID: $SSID"
echo "  Hotspot Pass: $WIFI_PASS"
echo "  Web UI      : http://$HOTSPOT_IP:$WEB_PORT"
echo ""

# ── 1. Install packages ──────────────────────────────────────────────
echo "[1/5] Checking packages..."
PACKAGES=(python3-pygame python3-flask hostapd dnsmasq)
MISSING=()
for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -s "$pkg" &>/dev/null; then
        MISSING+=("$pkg")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  Installing: ${MISSING[*]}"
    sudo apt update -qq
    sudo apt install -y "${MISSING[@]}"
else
    echo "  All packages present."
fi

# ── 2. Hotspot (AP+STA via hostapd + dnsmasq) ────────────────────────
echo ""
echo "[2/5] Configuring FIELD-OPS hotspot..."

# Clean up any old NM-based hotspot
sudo nmcli connection delete field-ops-hotspot 2>/dev/null || true

# Tell NetworkManager to leave ap0 alone
NM_UNMANAGED="/etc/NetworkManager/conf.d/ap0-unmanaged.conf"
if [ ! -f "$NM_UNMANAGED" ]; then
    sudo tee "$NM_UNMANAGED" > /dev/null <<EOF
[keyfile]
unmanaged-devices=interface-name:$AP_IFACE
EOF
    sudo systemctl reload NetworkManager 2>/dev/null || true
    echo "  NetworkManager told to ignore $AP_IFACE"
fi

# Stop services while we configure
sudo systemctl stop hostapd 2>/dev/null || true
sudo systemctl stop dnsmasq 2>/dev/null || true

# Create virtual AP interface
if ! ip link show "$AP_IFACE" &>/dev/null; then
    sudo iw dev wlan0 interface add "$AP_IFACE" type __ap
    echo "  Created virtual interface $AP_IFACE"
fi
sudo ip addr flush dev "$AP_IFACE" 2>/dev/null || true
sudo ip addr add "$HOTSPOT_IP/24" dev "$AP_IFACE" 2>/dev/null || true
sudo ip link set "$AP_IFACE" up

# Persist ap0 across reboots via udev
UDEV_RULE='/etc/udev/rules.d/90-ap0.rules'
if [ ! -f "$UDEV_RULE" ]; then
    echo "SUBSYSTEM==\"net\", ACTION==\"add\", KERNEL==\"wlan0\", RUN+=\"/sbin/iw dev wlan0 interface add $AP_IFACE type __ap\"" \
        | sudo tee "$UDEV_RULE" > /dev/null
fi

# Static IP for ap0
sudo mkdir -p /etc/network/interfaces.d
sudo tee "/etc/network/interfaces.d/$AP_IFACE" > /dev/null <<EOF
auto $AP_IFACE
iface $AP_IFACE inet static
    address $HOTSPOT_IP
    netmask 255.255.255.0
EOF

# hostapd config
sudo mkdir -p /etc/hostapd
sudo tee /etc/hostapd/hostapd.conf > /dev/null <<EOF
interface=$AP_IFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
wmm_enabled=0
auth_algs=1
wpa=2
wpa_passphrase=$WIFI_PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF
sudo sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd 2>/dev/null || true

# dnsmasq — DHCP for phones on ap0 only
sudo tee /etc/dnsmasq.d/field-ops.conf > /dev/null <<EOF
interface=$AP_IFACE
bind-interfaces
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
EOF

# Unmask hostapd (Debian masks it on install)
sudo systemctl unmask hostapd 2>/dev/null || true
sudo systemctl enable hostapd dnsmasq
sudo systemctl start hostapd
sudo systemctl start dnsmasq
echo "  Hotspot live: $SSID ($HOTSPOT_IP)"

# ── 3. Generate systemd services ─────────────────────────────────────
echo ""
echo "[3/5] Installing systemd services..."

sudo tee /etc/systemd/system/raspi-box.service > /dev/null <<EOF
[Unit]
Description=Field Ops — Game Display
After=graphical.target

[Service]
Type=simple
User=$INSTALL_USER
Environment=SDL_VIDEODRIVER=wayland
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/$INSTALL_UID
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/main.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

sudo tee /etc/systemd/system/field-ops-web.service > /dev/null <<EOF
[Unit]
Description=Field Ops — Web Control Panel
After=network.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 -c "from config_store import ConfigStore; from game_controller import GameController; from web_server import run_web_server; run_web_server(ConfigStore(), GameController())"
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# ── 4. Enable and start ──────────────────────────────────────────────
echo ""
echo "[4/5] Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable raspi-box field-ops-web
sudo systemctl restart field-ops-web
echo "  field-ops-web: started"
echo "  raspi-box: will start on next boot (needs display)"

# ── 5. Data directory ────────────────────────────────────────────────
echo ""
echo "[5/5] Ensuring data directory..."
mkdir -p "$SCRIPT_DIR/data"

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║           INSTALL COMPLETE           ║"
echo "╠══════════════════════════════════════╣"
echo "║                                      ║"
echo "║  1. Connect phone to Wi-Fi:          ║"
echo "║     SSID: $SSID               ║"
echo "║     Pass: $WIFI_PASS              ║"
echo "║                                      ║"
echo "║  2. Open in browser:                 ║"
echo "║     http://$HOTSPOT_IP:$WEB_PORT         ║"
echo "║                                      ║"
echo "║  3. Reboot to start the display:     ║"
echo "║     sudo reboot                      ║"
echo "║                                      ║"
echo "╚══════════════════════════════════════╝"
