# RC Fleet Manager - Build Instructions

## Prerequisites

### Windows
- **Python 3.8+** — download from python.org
- **Node.js** — download from nodejs.org (includes npm)
- **OpenSSL** — download from slproweb.com (light version)

### Mac
- **Python 3.8+** — `brew install python3`
- **Node.js** — `brew install node`
- **OpenSSL** — `brew install openssl` (usually pre-installed)

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3 python3-pip nodejs npm openssl
```

## Setup

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Node dependencies**
   ```bash
   npm install
   ```

## Development

Run the app in development mode (Electron + Flask):
```bash
npm run electron-dev
```

## Build Desktop Installer

Create installers for Windows, Mac, and Linux:

```bash
npm run dist
```

This will:
1. Compile the Flask app to a standalone `.exe` (Windows) / app bundle (Mac/Linux)
2. Bundle with Electron
3. Generate installers in the `dist/` folder

> Note: The packaged Electron installer launches only the Electron app window. It no longer opens the system browser automatically.

### Platform-Specific Builds

**Windows only:**
```bash
npm run build-exe && electron-builder --win
```

**Mac only:**
```bash
npm run build-exe && electron-builder --mac
```

**Linux only:**
```bash
npm run build-exe && electron-builder --linux
```

## Distribution

After building, installers will be in the `dist/` folder:
- **Windows:** `RC Inventory Setup 1.0.0.exe` (NSIS installer)
- **Mac:** `RC Inventory Setup 1.0.0.dmg`
- **Linux:** `RC Inventory Setup 1.0.0.AppImage` or `.deb` package

## How It Works

1. **Electron launches** → spawns Flask subprocess
2. **Self-signed certificate** → auto-generated in user's app folder
3. **Flask runs on HTTPS** → on port 5000
4. **Electron window opens** → points to `https://localhost:5000`
5. **Data stored locally** → SQLite database in app folder

## Accessing from Mobile Devices

**Same network access:**
1. Find your computer's IP address (e.g., `192.168.1.100`)
2. On mobile, open: `http://192.168.1.100:5000` (HTTP, not HTTPS for local network)
3. Tap "Add to Home Screen" → install as PWA

**Optional: Custom hostname setup**

If you want to access via a custom name like `rcinventory` on your network:

**Windows:**
1. Edit `C:\Windows\System32\drivers\etc\hosts`
2. Add: `127.0.0.1  rcinventory`
3. Access from same computer: `https://rcinventory:5000`

**Mac/Linux:**
1. Edit `/etc/hosts`
2. Add: `127.0.0.1  rcinventory`
3. Access from same computer: `https://rcinventory:5000`

## User Installation

Users simply download the installer for their platform and click to install. The app runs standalone with no external dependencies.
