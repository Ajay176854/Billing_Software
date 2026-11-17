const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const QRCode = require('qrcode');
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  Browsers
} = require('@whiskeysockets/baileys');
const pino = require('pino');

const app = express();
const PORT = process.env.WHATSAPP_PORT || 3001;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

function getSessionDir() {
  if (process.env.APPDATA) {
    const dir = path.join(process.env.APPDATA, 'MoiraLuxe', 'whatsapp_session');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    return dir;
  }
  const dir = path.join(__dirname, 'session');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

const SESSION_DIR = getSessionDir();

let sock = null;
let qrCodeDataUrl = null;
let qrRaw = null;
let connectionState = 'disconnected'; // 'disconnected' | 'connecting' | 'connected'
let connectedUser = { id: null, phone: null, name: null };
let lastError = null;
let reconnectTimer = null;

async function initWhatsApp() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (sock) {
    try {
      sock.ev.removeAllListeners('connection.update');
      sock.ev.removeAllListeners('creds.update');
      sock.end(undefined);
    } catch (_) {}
    sock = null;
  }

  try {
    connectionState = 'connecting';
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
    let version = [2, 3000, 1043857760];
    try {
      const v = await fetchLatestBaileysVersion();
      if (v && v.version) version = v.version;
    } catch (_) {}

    sock = makeWASocket({
      version,
      auth: state,
      logger: pino({ level: 'silent' }),
      printQRInTerminal: false,
      browser: ['Moira Luxe Billing', 'Chrome', '1.0.0'],
      syncFullHistory: false,
      connectTimeoutMs: 60000,
      defaultQueryTimeoutMs: 60000,
      keepAliveIntervalMs: 25000,
      retryRequestDelayMs: 2000,
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        qrRaw = qr;
        try {
          qrCodeDataUrl = await QRCode.toDataURL(qr, { width: 300, margin: 2 });
          console.log('📲 QR Code generated successfully for scanning');
        } catch (e) {
          console.error('Failed to generate QR data URL:', e);
        }
        connectionState = 'disconnected';
      }

      if (connection === 'close') {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const isLoggedOut = statusCode === DisconnectReason.loggedOut;
        connectionState = 'disconnected';
        connectedUser = { id: null, phone: null, name: null };
        qrCodeDataUrl = null; // Clear stale QR immediately
        qrRaw = null;

        console.log(`WhatsApp connection closed (code: ${statusCode || 'unknown'}). isLoggedOut=${isLoggedOut}`);

        if (isLoggedOut) {
          console.log('WhatsApp logged out. Clearing session files...');
          clearSessionFiles();
          if (!reconnectTimer) {
            reconnectTimer = setTimeout(initWhatsApp, 2000);
          }
        } else {
          // Restart quickly in 1.5s to generate the next fresh QR code
          console.log(`Generating fresh QR code in 1.5s...`);
          if (!reconnectTimer) {
            reconnectTimer = setTimeout(initWhatsApp, 1500);
          }
        }
      } else if (connection === 'open') {
        connectionState = 'connected';
        qrCodeDataUrl = null;
        qrRaw = null;
        lastError = null;

        const userJid = sock.user?.id || '';
        const phone = userJid.split(':')[0].replace(/\D/g, '');
        const name = sock.user?.name || 'Moira Luxe Billing';

        connectedUser = { id: userJid, phone, name };
        console.log(`✅ WhatsApp Connected successfully: +${phone} (${name})`);
      }
    });
  } catch (err) {
    console.error('Error in initWhatsApp:', err);
    connectionState = 'disconnected';
    lastError = err.message;
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(initWhatsApp, 5000);
    }
  }
}

function clearSessionFiles() {
  try {
    if (fs.existsSync(SESSION_DIR)) {
      fs.rmSync(SESSION_DIR, { recursive: true, force: true });
      fs.mkdirSync(SESSION_DIR, { recursive: true });
    }
  } catch (err) {
    console.error('Error clearing session files:', err);
  }
}

// 1. Status endpoint
app.get('/api/whatsapp/status', (req, res) => {
  res.json({
    connected: connectionState === 'connected',
    state: connectionState,
    user: connectedUser,
    qr: qrCodeDataUrl,
    lastError: lastError,
  });
});

// 2. Disconnect / Unlink endpoint
app.post('/api/whatsapp/disconnect', async (req, res) => {
  try {
    if (sock) {
      await sock.logout().catch(() => {});
      sock.end(undefined);
    }
  } catch (err) {
    console.warn('Logout error (ignored):', err.message);
  }

  clearSessionFiles();
  connectionState = 'disconnected';
  connectedUser = { id: null, phone: null, name: null };
  qrCodeDataUrl = null;
  qrRaw = null;

  // Re-init to immediately provide a fresh QR code
  setTimeout(initWhatsApp, 1500);

  res.json({ success: true, message: 'WhatsApp session unlinked successfully' });
});

// 3. Force Refresh / Regenerate QR endpoint
app.post('/api/whatsapp/refresh-qr', async (req, res) => {
  try {
    if (connectionState === 'connected') {
      return res.json({ success: true, message: 'Already connected', connected: true });
    }
    if (sock) {
      try {
        sock.ev.removeAllListeners('connection.update');
        sock.ev.removeAllListeners('creds.update');
        sock.end(undefined);
      } catch (_) {}
      sock = null;
    }
    qrCodeDataUrl = null;
    qrRaw = null;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    // Re-initialize immediately to generate a fresh QR
    setTimeout(initWhatsApp, 300);
    res.json({ success: true, message: 'Regenerating fresh QR code...' });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// 4. Send text bill endpoint
app.post('/api/whatsapp/send', async (req, res) => {
  const { phone, message } = req.body;

  if (connectionState !== 'connected' || !sock) {
    return res.status(400).json({
      success: false,
      error: 'WhatsApp is not connected. Please scan the QR code in Settings.'
    });
  }

  if (!phone || !message) {
    return res.status(400).json({ success: false, error: 'Phone and message are required' });
  }

  let cleanPhone = String(phone).replace(/\D/g, '');
  if (cleanPhone.length === 10) {
    cleanPhone = '91' + cleanPhone;
  }

  if (cleanPhone.length < 10) {
    return res.status(400).json({ success: false, error: 'Invalid phone number' });
  }

  const jid = `${cleanPhone}@s.whatsapp.net`;

  try {
    const result = await sock.sendMessage(jid, { text: message });
    console.log(`📤 Bill delivered to ${cleanPhone}`);
    res.json({ success: true, messageId: result.key?.id });
  } catch (err) {
    console.error(`Failed to send message to ${cleanPhone}:`, err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`🚀 Moira Luxe WhatsApp Engine listening on http://127.0.0.1:${PORT}`);
  initWhatsApp();
});
