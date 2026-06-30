#!/bin/bash
set -e

SSID="FIELD-OPS"
PASS="fieldops1"
HOTSPOT_IP="192.168.4.1"
AP_IFACE="ap0"

echo "Setting up FIELD-OPS hotspot (AP+STA mode)..."
echo "  SSID:     $SSID"
echo "  Password: $PASS"
echo "  IP:       $HOTSPOT_IP"
echo "  AP iface: $AP_IFACE (virtual, alongside wlan0)"
echo ""

# Clean up any previous NM-based hotspot attempt
sudo nmcli connection delete field-ops-hotspot 2>/dev/null || true

# Tell NetworkManager to leave ap0 alone
NM_UNMANAGED="/etc/NetworkManager/conf.d/ap0-unmanaged.conf"
if [ ! -f "$NM_UNMANAGED" ]; then
    sudo tee "$NM_UNMANAGED" > /dev/null <<EOF
[keyfile]
unmanaged-devices=interface-name:ap0
EOF
    sudo systemctl reload NetworkManager
    echo "Told NetworkManager to ignore ap0"
fi

# Install hostapd + dnsmasq if missing
PACKAGES=()
dpkg -s hostapd &>/dev/null || PACKAGES+=(hostapd)
dpkg -s dnsmasq &>/dev/null || PACKAGES+=(dnsmasq)
if [ ${#PACKAGES[@]} -gt 0 ]; then
    echo "Installing ${PACKAGES[*]}..."
    sudo apt update -qq
    sudo apt install -y "${PACKAGES[@]}"
fi

# Stop services while we configure
sudo systemctl stop hostapd 2>/dev/null || true
sudo systemctl stop dnsmasq 2>/dev/null || true

# Create virtual AP interface
if ! ip link show "$AP_IFACE" &>/dev/null; then
    echo "Creating virtual AP interface $AP_IFACE..."
    sudo iw dev wlan0 interface add "$AP_IFACE" type __ap
fi
sudo ip addr flush dev "$AP_IFACE" 2>/dev/null || true
sudo ip addr add "$HOTSPOT_IP/24" dev "$AP_IFACE"
sudo ip link set "$AP_IFACE" up

# Persist the virtual interface and its static IP across reboots via udev.
# (This system has no ifupdown/networking.service, so /etc/network/interfaces.d
# is never applied - the IP must be assigned by udev when ap0 appears.)
UDEV_RULE='/etc/udev/rules.d/90-ap0.rules'
sudo tee "$UDEV_RULE" > /dev/null <<EOF
SUBSYSTEM=="net", ACTION=="add", KERNEL=="wlan0", RUN+="/sbin/iw dev wlan0 interface add ap0 type __ap"
SUBSYSTEM=="net", ACTION=="add", KERNEL=="ap0", RUN+="/sbin/ip addr add $HOTSPOT_IP/24 dev ap0", RUN+="/sbin/ip link set ap0 up"
EOF
echo "Wrote udev rule for persistent $AP_IFACE + static IP"
sudo rm -f /etc/network/interfaces.d/ap0

# Configure hostapd
sudo tee /etc/hostapd/hostapd.conf > /dev/null <<EOF
interface=$AP_IFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
wmm_enabled=0
auth_algs=1
wpa=2
wpa_passphrase=$PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

# Point hostapd daemon config at our file
sudo sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd 2>/dev/null || true

# Configure dnsmasq for DHCP on ap0 only
DNSMASQ_CONF="/etc/dnsmasq.d/field-ops.conf"
sudo tee "$DNSMASQ_CONF" > /dev/null <<EOF
interface=$AP_IFACE
bind-interfaces
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
EOF

# Unmask hostapd (Debian masks it on install by default)
sudo systemctl unmask hostapd
sudo systemctl enable hostapd dnsmasq
sudo systemctl start hostapd
sudo systemctl start dnsmasq

echo ""
echo "Hotspot is live!"
echo "  Connect your phone to Wi-Fi '$SSID' with password '$PASS'"
echo "  Then open http://$HOTSPOT_IP:8080 in your browser"
echo ""
echo "Your existing Wi-Fi (wlan0) stays connected for SSH/Tailscale."
echo "Everything auto-starts on boot."
