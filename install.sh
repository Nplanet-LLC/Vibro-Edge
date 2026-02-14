#!/bin/bash

# Edge Device Installation Script for Turbine Monitoring System
# Installs and configures the edge device software on Raspberry Pi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Turbine Monitoring Edge Device Installation Script   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR="/opt/turbine-monitor"
CONFIG_DIR="/etc/turbine-monitor"
LOG_DIR="/var/log/turbine-monitor"
DATA_DIR="/var/lib/turbine-monitor"

echo -e "${YELLOW}📋 Installation Configuration:${NC}"
echo "  Install Directory: $INSTALL_DIR"
echo "  Config Directory:  $CONFIG_DIR"
echo "  Log Directory:     $LOG_DIR"
echo "  Data Directory:    $DATA_DIR"
echo "  User:              $ACTUAL_USER"
echo ""

# Prompt for backend URL
read -p "Enter Backend API URL (e.g., https://api.turbine.local): " BACKEND_URL
read -p "Enter MQTT Broker Host (e.g., mqtt.turbine.local): " MQTT_HOST
read -p "Enter MQTT Broker Port (default: 8883): " MQTT_PORT
MQTT_PORT=${MQTT_PORT:-8883}
read -p "Use TLS for MQTT? (y/n, default: y): " USE_TLS
USE_TLS=${USE_TLS:-y}

echo ""
echo -e "${YELLOW}🔧 Step 1: Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    sqlite3 \
    i2c-tools \
    python3-smbus

echo -e "${GREEN}✅ System dependencies installed${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 2: Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

echo -e "${GREEN}✅ Directories created${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 3: Copying application files...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

echo -e "${GREEN}✅ Application files copied${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 4: Creating Python virtual environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Python environment configured${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 5: Creating configuration file...${NC}"
cat > "$CONFIG_DIR/config.env" <<EOF
# Turbine Monitoring Edge Device Configuration

# Backend API
BACKEND_URL=$BACKEND_URL

# MQTT Broker
MQTT_HOST=$MQTT_HOST
MQTT_PORT=$MQTT_PORT
MQTT_USE_TLS=$USE_TLS
MQTT_USERNAME=device
MQTT_PASSWORD=device123

# Device Configuration
DEVICE_CONFIG_PATH=$CONFIG_DIR/device.conf
BUFFER_DB_PATH=$DATA_DIR/buffer.db
LOG_PATH=$LOG_DIR/edge.log

# ADC Configuration
ADC_SAMPLE_RATE=1000
ADC_CHANNELS=4

# FFT Configuration
FFT_WINDOW_SIZE=1024
FFT_OVERLAP=0.5
EOF

echo -e "${GREEN}✅ Configuration file created${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 6: Creating systemd service...${NC}"
cat > /etc/systemd/system/turbine-monitor.service <<EOF
[Unit]
Description=Turbine Monitoring Edge Device
After=network.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/config.env
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/edge.log
StandardError=append:$LOG_DIR/edge-error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable turbine-monitor.service

echo -e "${GREEN}✅ Systemd service created and enabled${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 7: Setting permissions...${NC}"
chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$CONFIG_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$LOG_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$DATA_DIR"

echo -e "${GREEN}✅ Permissions set${NC}"

echo ""
echo -e "${YELLOW}🔧 Step 8: Enabling I2C (for ADC)...${NC}"
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
    echo -e "${YELLOW}⚠️  I2C enabled - reboot required${NC}"
fi

if ! grep -q "^i2c-dev" /etc/modules; then
    echo "i2c-dev" >> /etc/modules
fi

echo -e "${GREEN}✅ I2C configuration updated${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation Complete! 🎉                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo ""
echo "1. Review configuration:"
echo "   sudo nano $CONFIG_DIR/config.env"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start turbine-monitor"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status turbine-monitor"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u turbine-monitor -f"
echo "   tail -f $LOG_DIR/edge.log"
echo ""
echo "5. Reboot if I2C was just enabled:"
echo "   sudo reboot"
echo ""
echo -e "${YELLOW}📚 Useful Commands:${NC}"
echo "  Start:   sudo systemctl start turbine-monitor"
echo "  Stop:    sudo systemctl stop turbine-monitor"
echo "  Restart: sudo systemctl restart turbine-monitor"
echo "  Status:  sudo systemctl status turbine-monitor"
echo "  Logs:    sudo journalctl -u turbine-monitor -f"
echo ""
echo -e "${GREEN}Installation completed successfully!${NC}"
