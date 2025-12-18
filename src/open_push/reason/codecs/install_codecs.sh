#!/bin/bash
#
# Install OpenPush codecs for Reason
#

CODECS_DIR="/Library/Application Support/Propellerhead Software/Remote/Codecs"

echo "OpenPush Codec Installer"
echo "========================"
echo

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This script is for macOS only."
    echo "On Windows, manually copy files to:"
    echo "  %PROGRAMDATA%\\Propellerhead Software\\Remote\\Codecs\\"
    exit 1
fi

# Check if Reason codecs directory exists
if [ ! -d "$CODECS_DIR" ]; then
    echo "Error: Reason codecs directory not found."
    echo "Expected: $CODECS_DIR"
    echo
    echo "Make sure Reason is installed."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing codecs to:"
echo "  $CODECS_DIR"
echo

# Copy codec files
for ext in lua luacodec; do
    for file in "$SCRIPT_DIR"/OpenPush*.$ext; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo "  Copying $filename..."
            sudo cp "$file" "$CODECS_DIR/"
        fi
    done
done

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Start the OpenPush bridge application"
echo "2. Open Reason > Preferences > Control Surfaces"
echo "3. Add OpenPush Transport, Devices, and Mixer"
echo "4. Set MIDI ports to match the virtual ports"
