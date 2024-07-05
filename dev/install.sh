#!/bin/bash

# Set up variables
SEARXNG_HOME="$HOME/searxng"
SEARXNG_VENV="$SEARXNG_HOME/searx-pyenv"
SEARXNG_SRC="$SEARXNG_HOME/searxng-src"
SEARXNG_SETTINGS="$SEARXNG_HOME/settings.yml"

# Create directories
mkdir -p "$SEARXNG_HOME"

# Clone SearXNG repository
git clone "https://github.com/searxng/searxng" "$SEARXNG_SRC"

# Create and activate virtual environment
python3 -m venv "$SEARXNG_VENV"
source "$SEARXNG_VENV/bin/activate"

# Install dependencies
pip install -U pip setuptools wheel pyyaml
cd "$SEARXNG_SRC"
pip install -e .

# Configure SearXNG
cp "$SEARXNG_SRC/searx/settings.yml" "$SEARXNG_SETTINGS"

# Create a start script
cat << EOF > "$SEARXNG_HOME/start_searxng.sh"
#!/bin/bash
source "$SEARXNG_VENV/bin/activate"
cd "$SEARXNG_SRC"
export SEARXNG_SETTINGS_PATH="$SEARXNG_SETTINGS"
python searx/webapp.py
EOF

chmod +x "$SEARXNG_HOME/start_searxng.sh"

echo "SearXNG has been installed and configured."
echo "To start SearXNG, run: $SEARXNG_HOME/start_searxng.sh"
echo "SearXNG will be available at http://localhost:8888"
echo "Please make sure to update the SEARXNG_URL environment variable in your main script to point to this URL."