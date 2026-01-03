#!/bin/bash
#
# Deploy MIDI Bridge to pimini (Pi Zero 2W)
# ==========================================
#
# This script deploys the MIDI-only bridge to the Pi Zero 2W.
#
# Usage:
#   ./deploy_pimini.sh              # Sync and restart service
#   ./deploy_pimini.sh --install    # First-time installation
#   ./deploy_pimini.sh --status     # Check service status
#   ./deploy_pimini.sh --logs       # View recent logs
#

set -e

# Configuration
PI_HOST="pimini@pimini.local"
PI_DIR="/home/pimini/open-push"
SERVICE_NAME="open-push-midi"
LOCAL_DIR="$(dirname "$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  MIDI Bridge Deployment - pimini"
echo "========================================"
echo ""

# Check SSH connection
check_connection() {
    echo -n "Checking connection to pimini... "
    if ssh -o ConnectTimeout=5 "$PI_HOST" "echo ok" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "Cannot connect to $PI_HOST"
        echo "Make sure pimini is powered on and connected to WiFi"
        exit 1
    fi
}

# Sync files to Pi
sync_files() {
    echo "Syncing files to pimini..."
    rsync -avz --delete \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        --exclude='Content/' \
        "$LOCAL_DIR/" "$PI_HOST:$PI_DIR/"
    echo -e "${GREEN}Files synced${NC}"
}

# Install dependencies
install_deps() {
    echo "Installing dependencies on pimini..."
    ssh "$PI_HOST" "pip3 install --user mido python-rtmidi"
    echo -e "${GREEN}Dependencies installed${NC}"
}

# Create systemd service
create_service() {
    echo "Creating systemd service..."

    SERVICE_FILE="[Unit]
Description=OpenPush MIDI Bridge
After=network.target sound.target

[Service]
Type=simple
User=pimini
WorkingDirectory=$PI_DIR
ExecStart=/usr/bin/python3 -m open_push.midi.app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target"

    ssh "$PI_HOST" "echo '$SERVICE_FILE' | sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null"
    ssh "$PI_HOST" "sudo systemctl daemon-reload"
    echo -e "${GREEN}Service created${NC}"
}

# Enable and start service
enable_service() {
    echo "Enabling service..."
    ssh "$PI_HOST" "sudo systemctl enable ${SERVICE_NAME}.service"
    echo -e "${GREEN}Service enabled${NC}"
}

start_service() {
    echo "Starting service..."
    ssh "$PI_HOST" "sudo systemctl start ${SERVICE_NAME}.service"
    echo -e "${GREEN}Service started${NC}"
}

restart_service() {
    echo "Restarting service..."
    ssh "$PI_HOST" "sudo systemctl restart ${SERVICE_NAME}.service"
    echo -e "${GREEN}Service restarted${NC}"
}

stop_service() {
    echo "Stopping service..."
    ssh "$PI_HOST" "sudo systemctl stop ${SERVICE_NAME}.service"
    echo -e "${GREEN}Service stopped${NC}"
}

# Show service status
show_status() {
    echo "Service Status:"
    echo "---------------"
    ssh "$PI_HOST" "sudo systemctl status ${SERVICE_NAME}.service --no-pager" || true
}

# Show logs
show_logs() {
    echo "Recent Logs:"
    echo "------------"
    ssh "$PI_HOST" "sudo journalctl -u ${SERVICE_NAME}.service -n 50 --no-pager"
}

# Setup USB gadget mode
setup_gadget() {
    echo "Setting up USB gadget mode..."

    # Check if already configured
    if ssh "$PI_HOST" "grep -q 'dtoverlay=dwc2' /boot/config.txt"; then
        echo -e "${YELLOW}dwc2 overlay already in config.txt${NC}"
    else
        ssh "$PI_HOST" "echo 'dtoverlay=dwc2' | sudo tee -a /boot/config.txt"
        echo -e "${GREEN}Added dwc2 overlay${NC}"
    fi

    # Check cmdline.txt
    if ssh "$PI_HOST" "grep -q 'modules-load=dwc2,g_midi' /boot/cmdline.txt"; then
        echo -e "${YELLOW}g_midi already in cmdline.txt${NC}"
    else
        ssh "$PI_HOST" "sudo sed -i 's/rootwait/rootwait modules-load=dwc2,g_midi/' /boot/cmdline.txt"
        echo -e "${GREEN}Added g_midi module${NC}"
    fi

    echo ""
    echo -e "${YELLOW}NOTE: Reboot required for USB gadget changes${NC}"
    echo "Run: ssh $PI_HOST 'sudo reboot'"
}

# Full installation
full_install() {
    check_connection
    sync_files
    install_deps
    create_service
    enable_service
    setup_gadget
    start_service
    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    show_status
}

# Quick deploy (sync and restart)
quick_deploy() {
    check_connection
    sync_files
    restart_service
    echo ""
    echo -e "${GREEN}Deployment complete!${NC}"
    sleep 2
    show_status
}

# Parse arguments
case "${1:-}" in
    --install)
        full_install
        ;;
    --status)
        check_connection
        show_status
        ;;
    --logs)
        check_connection
        show_logs
        ;;
    --stop)
        check_connection
        stop_service
        ;;
    --start)
        check_connection
        start_service
        ;;
    --gadget)
        check_connection
        setup_gadget
        ;;
    --help|-h)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (none)      Quick deploy - sync files and restart service"
        echo "  --install   Full installation (first-time setup)"
        echo "  --status    Show service status"
        echo "  --logs      Show recent logs"
        echo "  --start     Start service"
        echo "  --stop      Stop service"
        echo "  --gadget    Setup USB gadget mode"
        echo "  --help      Show this help"
        ;;
    *)
        quick_deploy
        ;;
esac
