#!/bin/bash
#
# Install OpenPush codecs and remotemaps for Reason
#

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This script is for macOS only."
    echo "On Windows, manually copy files to:"
    echo "  Codecs: %PROGRAMDATA%\\Propellerhead Software\\Remote\\Codecs\\Lua Codecs\\OpenPush\\"
    echo "  Maps:   %PROGRAMDATA%\\Propellerhead Software\\Remote\\Maps\\OpenPush\\"
    exit 1
fi

# Find all Reason apps (handle spaces in app names)
echo "Searching for Reason installations..."
APPS=()
while IFS= read -r -d '' app; do
    APPS+=("$app")
done < <(find /Applications -maxdepth 1 -type d -name "Reason*.app" -print0 2>/dev/null)

if [ ${#APPS[@]} -eq 0 ]; then
    echo "Error: No Reason application found in /Applications."
    exit 1
elif [ ${#APPS[@]} -eq 1 ]; then
    REASON_APP_PATH="${APPS[0]}"
    echo "Found: $REASON_APP_PATH"
else
    echo "Multiple Reason versions found:"
    for i in "${!APPS[@]}"; do
        echo "  [$i] ${APPS[$i]}"
    done
    
    echo
    read -r -p "Select version to install to (0-$((${#APPS[@]}-1))): " SELECTION
    
    if [[ ! "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -ge "${#APPS[@]}" ]; then
        echo "Invalid selection."
        exit 1
    fi
    
    REASON_APP_PATH="${APPS[$SELECTION]}"
    echo "Selected: $REASON_APP_PATH"
fi

REMOTE_BASE="$REASON_APP_PATH/Contents/Resources/Remote"
DEFAULT_CODECS_DIR="$REMOTE_BASE/DefaultCodecs/Lua Codecs/OpenPush"
DEFAULT_MAPS_DIR="$REMOTE_BASE/DefaultMaps/OpenPush"

echo
echo "Installing to:"
echo "  DefaultCodecs: $DEFAULT_CODECS_DIR"
echo "  DefaultMaps:   $DEFAULT_MAPS_DIR"
echo

# Check if Reason Remote directory exists
if [ ! -d "$REMOTE_BASE" ]; then
    echo "Error: Reason Remote directory not found within Reason.app."
    echo "Expected: $REMOTE_BASE"
    echo "This might indicate a problem with the Reason installation or an unexpected app bundle structure."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing to:"
echo "  DefaultCodecs: $DEFAULT_CODECS_DIR"
echo "  DefaultMaps:   $DEFAULT_MAPS_DIR"
echo

# Create directories if they don't exist
echo "Creating directories..."
sudo mkdir -p "$DEFAULT_CODECS_DIR"
sudo mkdir -p "$DEFAULT_MAPS_DIR"

# Copy codec files (.lua, .luacodec, .png)
echo
echo "Installing codec files..."
for ext in lua luacodec png; do
    for file in "$SCRIPT_DIR"/OpenPush*.$ext; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo "  $filename -> DefaultCodecs/"
            sudo cp "$file" "$DEFAULT_CODECS_DIR/"
        fi
    done
done

# Copy remotemap files
echo
echo "Installing remotemap files..."
for file in "$SCRIPT_DIR"/*.remotemap; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "  $filename -> DefaultMaps/"
        sudo cp "$file" "$DEFAULT_MAPS_DIR/"
    fi
done

echo
echo "Installation complete!"
echo
echo "Installed files:"
echo "  DefaultCodecs:"
ls -la "$DEFAULT_CODECS_DIR" 2>/dev/null | grep -E "\.(lua|luacodec)$" | awk '{print "    " $NF}'
echo "  DefaultMaps:"
ls -la "$DEFAULT_MAPS_DIR" 2>/dev/null | grep -E "\.remotemap$" | awk '{print "    " $NF}'
echo
echo "Next steps:"
echo "1. Start the OpenPush bridge application"
echo "2. Open Reason > Preferences > Control Surfaces"
echo "3. Add 'OpenPush Transport', 'OpenPush Devices', and 'OpenPush Mixer'"
echo "4. Assign MIDI ports to match the virtual ports:"
echo "   - OpenPush Transport -> OpenPush Transport In/Out"
echo "   - OpenPush Devices   -> OpenPush Devices In/Out"
echo "   - OpenPush Mixer     -> OpenPush Mixer In/Out"
