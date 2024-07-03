#!/bin/bash

# Update and install required packages
sudo apt-get update
sudo apt-get install -y python3-dev python3-babel python3-venv \
    uwsgi uwsgi-plugin-python3 \
    git build-essential libxslt-dev zlib1g-dev libffi-dev libssl-dev

# Create a user for SearXNG
sudo useradd --shell /bin/bash --system \
    --home-dir "/usr/local/searxng" \
    --comment 'Privacy-respecting metasearch engine' \
    searxng

sudo mkdir "/usr/local/searxng"
sudo chown -R "searxng:searxng" "/usr/local/searxng"

# Install SearXNG and its dependencies
sudo -H -u searxng bash << EOF
git clone "https://github.com/searxng/searxng" "/usr/local/searxng/searxng-src"
python3 -m venv "/usr/local/searxng/searx-pyenv"
echo ". /usr/local/searxng/searx-pyenv/bin/activate" >> "/usr/local/searxng/.profile"
. /usr/local/searxng/searx-pyenv/bin/activate
pip install -U pip setuptools wheel pyyaml
cd "/usr/local/searxng/searxng-src"
pip install -e .
EOF

# Configure SearXNG
sudo mkdir -p /etc/searxng
sudo cp /usr/local/searxng/searxng-src/searx/settings.yml /etc/searxng/settings.yml

# Set up a systemd service for SearXNG
cat << EOF | sudo tee /etc/systemd/system/searxng.service
[Unit]
Description=SearXNG service
After=network.target

[Service]
Type=simple
User=searxng
Group=searxng
WorkingDirectory=/usr/local/searxng/searxng-src
Environment=SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml
ExecStart=/usr/local/searxng/searx-pyenv/bin/python searx/webapp.py

[Install]
WantedBy=multi-user.target
EOF

# Start and enable the SearXNG service
sudo systemctl daemon-reload
sudo systemctl enable searxng
sudo systemctl start searxng

echo "SearXNG has been installed and configured. It should now be running on http://localhost:8888"
echo "Please make sure to update the SEARXNG_URL environment variable in your main script to point to this URL."
