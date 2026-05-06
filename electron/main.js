const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');
const https = require('https');
const http = require('http');

let mainWindow;
let flaskProcess;
const appDataPath = path.join(os.homedir(), 'AppData', 'Local', 'RCInventory');
const logPath = path.join(appDataPath, 'electron.log');

app.commandLine.appendSwitch('ignore-certificate-errors');

function log(message) {
  try {
    fs.appendFileSync(logPath, `${new Date().toISOString()} ${message}\n`);
  } catch (e) {
    console.warn('Could not write log:', e);
  }
}

// Ensure app data directory exists
if (!fs.existsSync(appDataPath)) {
  fs.mkdirSync(appDataPath, { recursive: true });
}

app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
  if (url.startsWith('https://localhost:5000')) {
    event.preventDefault();
    callback(true);
  } else {
    callback(false);
  }
});

const certPath = path.join(appDataPath, 'cert.pem');
const keyPath = path.join(appDataPath, 'key.pem');

// Generate self-signed certificate if it doesn't exist
function ensureCertificate() {
  if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
    return;
  }

  const { execSync } = require('child_process');
  try {
    const cmd = `openssl req -x509 -newkey rsa:4096 -nodes -out "${certPath}" -keyout "${keyPath}" -days 365 -subj "/CN=rcinventory"`;
    execSync(cmd, { stdio: 'ignore' });
  } catch (error) {
    console.warn('Could not generate certificate with OpenSSL. Using HTTP fallback.');
  }
}

// Launch Flask app
function startFlaskApp() {
  const flaskScript = path.join(__dirname, '..', 'app.py');
  const unpackedExePath = path.join(process.resourcesPath, 'app.asar.unpacked', 'dist', 'rc_inventory.exe');
  const unpackedDistPath = path.join(process.resourcesPath, 'dist', 'rc_inventory.exe');
  const exePath = fs.existsSync(unpackedExePath)
    ? unpackedExePath
    : fs.existsSync(unpackedDistPath)
    ? unpackedDistPath
    : null;
  const pythonExe = process.env.PYTHON_EXE || 'python';

  let command;
  let spawnArgs;

  if (exePath) {
    command = exePath;
    spawnArgs = [];
  } else {
    command = pythonExe;
    spawnArgs = [flaskScript];
  }

  log(`Starting backend: ${command} ${spawnArgs.join(' ')}`);

  flaskProcess = spawn(command, spawnArgs, {
    env: {
      ...process.env,
      FLASK_ENV: 'production',
      APP_DATA_PATH: appDataPath,
      CERT_FILE: certPath,
      KEY_FILE: keyPath,
      NO_BROWSER: '1'
    },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  flaskProcess.stdout.on('data', (data) => log(`backend stdout: ${data.toString().trim()}`));
  flaskProcess.stderr.on('data', (data) => log(`backend stderr: ${data.toString().trim()}`));

  flaskProcess.on('error', (err) => {
    log(`Failed to start backend: ${err}`);
    console.error('Failed to start Flask:', err);
  });
}

// Kill Flask on exit
function stopFlaskApp() {
  if (flaskProcess) {
    flaskProcess.kill();
  }
}

// Create window
async function waitForServerReady(url, timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await new Promise((resolve, reject) => {
        const client = url.startsWith('https') ? https : http;
        const req = client.request(url, { method: 'HEAD', rejectUnauthorized: false }, (res) => {
          res.on('data', () => {});
          res.on('end', resolve);
        });
        req.on('error', reject);
        req.end();
      });
      return true;
    } catch (err) {
      await new Promise(r => setTimeout(r, 500));
    }
  }
  return false;
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 600,
    minHeight: 400,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, '..', 'static', 'icons', 'icon.svg')
  });

  const useHttps = fs.existsSync(certPath) && fs.existsSync(keyPath);
  const url = useHttps ? 'https://localhost:5000/' : 'http://localhost:5000/';
  const ready = await waitForServerReady(url);
  if (ready) {
    mainWindow.loadURL(url);
  } else {
    const errorPageHtml = `
      <html>
        <head>
          <title>RC Inventory Startup Error</title>
          <style>
            body { font-family: Arial, sans-serif; background: #f8fafc; color: #111827; margin: 0; padding: 40px; }
            .container { max-width: 800px; margin: auto; }
            h1 { color: #1f2937; }
            p { line-height: 1.6; }
            .log-link { display: inline-block; margin-top: 20px; padding: 10px 16px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; }
            .log-path { word-break: break-all; font-family: monospace; background: #e5e7eb; padding: 10px; border-radius: 6px; }
          </style>
        </head>
        <body>
          <div class="container">
            <h1>RC Inventory failed to start</h1>
            <p>The Electron shell could not connect to the local backend server on <strong>https://localhost:5000/</strong>.</p>
            <p>Possible causes:</p>
            <ul>
              <li>The backend process failed to launch.</li>
              <li>Python is not available on the system path.</li>
              <li>The installed app could not start its local Flask server.</li>
            </ul>
            <p>Check the log file for details:</p>
            <div class="log-path">${logPath}</div>
            <p>If you are running the installer version, reinstalling or running the app as administrator may help.</p>
          </div>
        </body>
      </html>
    `;

    const errorPage = `data:text/html,${encodeURIComponent(errorPageHtml)}`;
    mainWindow.loadURL(errorPage);
    log('Backend did not respond before timeout.');
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', () => {
  ensureCertificate();
  startFlaskApp();
  createWindow();
});

app.on('window-all-closed', () => {
  stopFlaskApp();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  stopFlaskApp();
  app.quit();
});
