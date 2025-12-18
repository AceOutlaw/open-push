#!/bin/bash
#
# Install OpenPush codecs and remotemaps for Reason
#

REMOTE_BASE="/Library/Application Support/Propellerhead Software/Remote"
CODECS_DIR="$REMOTE_BASE/Codecs/Lua Codecs/OpenPush"
MAPS_DIR="$REMOTE_BASE/Maps/OpenPush"

echo "OpenPush Codec Installer"
echo "========================"
echo

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This script is for macOS only."
    echo "On Windows, manually copy files to:"
    echo "  Codecs: %PROGRAMDATA%\\Propellerhead Software\\Remote\\Codecs\\Lua Codecs\\OpenPush\\"
    echo "  Maps:   %PROGRAMDATA%\\Propellerhead Software\\Remote\\Maps\\OpenPush\\"
    exit 1
fi

# Check if Reason Remote directory exists
if [ ! -d "$REMOTE_BASE" ]; then
    echo "Error: Reason Remote directory not found."
    echo "Expected: $REMOTE_BASE"
    echo
    echo "Make sure Reason is installed."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing to:"
echo "  Codecs: $CODECS_DIR"
echo "  Maps:   $MAPS_DIR"
echo

# Create directories if they don't exist
echo "Creating directories..."
sudo mkdir -p "$CODECS_DIR"
sudo mkdir -p "$MAPS_DIR"

# Copy codec files (.lua and .luacodec)
echo
echo "Installing codec files..."
for ext in lua luacodec; do
    for file in "$SCRIPT_DIR"/OpenPush*.$ext; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo "  $filename -> Codecs/"
            sudo cp "$file" "$CODECS_DIR/"
        fi
    done
done

# Copy remotemap files
echo
echo "Installing remotemap files..."
for file in "$SCRIPT_DIR"/*.remotemap; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "  $filename -> Maps/"
        sudo cp "$file" "$MAPS_DIR/"
    fi
done

echo
echo "Installation complete!"
echo
echo "Installed files:"
echo "  Codecs:"
ls -la "$CODECS_DIR" 2>/dev/null | grep -E "\.(lua|luacodec)$" | awk '{print "    " $NF}'
echo "  Maps:"
ls -la "$MAPS_DIR" 2>/dev/null | grep -E "\.remotemap$" | awk '{print "    " $NF}'
echo
echo "Next steps:"
echo "1. Start the OpenPush bridge application"
echo "2. Open Reason > Preferences > Control Surfaces"
echo "3. Add 'OpenPush Transport', 'OpenPush Devices', and 'OpenPush Mixer'"
echo "4. Assign MIDI ports to match the virtual ports:"
echo "   - OpenPush Transport -> OpenPush Transport In/Out"
echo "   - OpenPush Devices   -> OpenPush Devices In/Out"
echo "   - OpenPush Mixer     -> OpenPush Mixer In/Out"
