#!/bin/bash

# SearXNG management script

SEARXNG_USER="searxng"
SEARXNG_HOME="/usr/local/searxng"
SEARXNG_SETTINGS="/etc/searxng/settings.yml"
SEARXNG_SERVICE="searxng.service"

# Function to check if the script is run as root
check_root() {
    if [ "$(id -u)" != "0" ]; then
        echo "This script must be run as root" 1>&2
        exit 1
    fi
}

# Function to install SearXNG
install_searxng() {
    check_root
    
    # Update and install required packages
    apt-get update
    apt-get install -y python3-dev python3-babel python3-venv \
        uwsgi uwsgi-plugin-python3 \
        git build-essential libxslt-dev zlib1g-dev libffi-dev libssl-dev

    # Create SearXNG user
    useradd --shell /bin/bash --system \
        --home-dir "$SEARXNG_HOME" \
        --comment 'Privacy-respecting metasearch engine' \
        $SEARXNG_USER

    mkdir -p "$SEARXNG_HOME"
    chown -R "$SEARXNG_USER:$SEARXNG_USER" "$SEARXNG_HOME"

    # Install SearXNG
    su - $SEARXNG_USER -c "
        git clone https://github.com/searxng/searxng $SEARXNG_HOME/searxng-src
        python3 -m venv $SEARXNG_HOME/searx-pyenv
        echo '. $SEARXNG_HOME/searx-pyenv/bin/activate' >> $SEARXNG_HOME/.profile
        . $SEARXNG_HOME/searx-pyenv/bin/activate
        pip install -U pip setuptools wheel pyyaml
        cd $SEARXNG_HOME/searxng-src
        pip install -e .
    "

    # Configure SearXNG
    mkdir -p /etc/searxng
    cp $SEARXNG_HOME/searxng-src/searx/settings.yml $SEARXNG_SETTINGS

    # Create systemd service
    cat << EOF > /etc/systemd/system/$SEARXNG_SERVICE
[Unit]
Description=SearXNG service
After=network.target

[Service]
Type=simple
User=$SEARXNG_USER
Group=$SEARXNG_USER
WorkingDirectory=$SEARXNG_HOME/searxng-src
Environment=SEARXNG_SETTINGS_PATH=$SEARXNG_SETTINGS
ExecStart=$SEARXNG_HOME/searx-pyenv/bin/python $SEARXNG_HOME/searxng-src/searx/webapp.py

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable $SEARXNG_SERVICE
    
    echo "SearXNG has been installed and configured."
}

# Function to start SearXNG
start_searxng() {
    check_root
    systemctl start $SEARXNG_SERVICE
    echo "SearXNG service started."
}

# Function to stop SearXNG
stop_searxng() {
    check_root
    systemctl stop $SEARXNG_SERVICE
    echo "SearXNG service stopped."
}

# Function to restart SearXNG
restart_searxng() {
    check_root
    systemctl restart $SEARXNG_SERVICE
    echo "SearXNG service restarted."
}

# Function to check SearXNG status
status_searxng() {
    check_root
    systemctl status $SEARXNG_SERVICE
}

# Function to update SearXNG
update_searxng() {
    check_root
    su - $SEARXNG_USER -c "
        cd $SEARXNG_HOME/searxng-src
        git pull
        . $SEARXNG_HOME/searx-pyenv/bin/activate
        pip install -U .
    "
    restart_searxng
    echo "SearXNG has been updated."
}

# Function to edit SearXNG settings
edit_settings() {
    check_root
    ${EDITOR:-nano} $SEARXNG_SETTINGS
    restart_searxng
    echo "Settings updated and SearXNG restarted."
}

# Main menu
show_menu() {
    echo "SearXNG Management Script"
    echo "1. Install SearXNG"
    echo "2. Start SearXNG"
    echo "3. Stop SearXNG"
    echo "4. Restart SearXNG"
    echo "5. Check SearXNG Status"
    echo "6. Update SearXNG"
    echo "7. Edit SearXNG Settings"
    echo "8. Exit"
    echo -n "Enter your choice [1-8]: "
}

# Main logic
while true; do
    show_menu
    read choice
    case $choice in
        1) install_searxng ;;
        2) start_searxng ;;
        3) stop_searxng ;;
        4) restart_searxng ;;
        5) status_searxng ;;
        6) update_searxng ;;
        7) edit_settings ;;
        8) exit 0 ;;
        *) echo "Invalid option. Please try again." ;;
    esac
    echo
    echo "Press Enter to continue..."
    read
    clear
done
