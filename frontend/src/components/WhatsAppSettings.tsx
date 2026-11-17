import { useState, useEffect, useRef } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { Smartphone, CheckCircle2, QrCode, RefreshCw, Send, Unlink, AlertCircle } from 'lucide-react';

export default function WhatsAppSettings() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [testPhone, setTestPhone] = useState('');
  const [sendingTest, setSendingTest] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [refreshingQR, setRefreshingQR] = useState(false);
  const pollTimerRef = useRef<any>(null);

  const fetchStatus = async () => {
    try {
      const res = await api.get('/whatsapp/status');
      setStatus(res.data);
    } catch {
      setStatus({ connected: false, state: 'offline' });
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshQR = async () => {
    setRefreshingQR(true);
    try {
      await api.post('/whatsapp/refresh-qr');
      toast.success('Generating fresh QR code...');
      await fetchStatus();
    } catch {
      await fetchStatus();
    } finally {
      setRefreshingQR(false);
    }
  };

  useEffect(() => {
    fetchStatus();

    // Fast poll status every 2 seconds to auto-detect QR scan or fresh code
    pollTimerRef.current = setInterval(fetchStatus, 2000);
    return () => clearInterval(pollTimerRef.current);
  }, []);

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to unlink this WhatsApp account?')) return;
    setDisconnecting(true);
    try {
      await api.post('/whatsapp/disconnect');
      toast.success('WhatsApp unlinked. Scan new QR code to reconnect.');
      fetchStatus();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to unlink account');
    } finally {
      setDisconnecting(false);
    }
  };

  const handleSendTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testPhone.trim()) {
      toast.error('Please enter a 10-digit phone number');
      return;
    }
    setSendingTest(true);
    try {
      await api.post('/whatsapp/send-test', { phone: testPhone.trim() });
      toast.success(`Test bill sent to +91 ${testPhone}! Check WhatsApp.`);
      setTestPhone('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to send test message');
    } finally {
      setSendingTest(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${status?.connected ? 'bg-emerald-500/15 text-emerald-500' : 'bg-amber-500/15 text-amber-500'}`}>
            <Smartphone className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
              WhatsApp Autonomous E-Bill Engine
              {status?.connected && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-3 w-3" /> Linked & Active
                </span>
              )}
            </h3>
            <p className="text-xs text-text-muted">
              Sends 100% free automated WhatsApp invoices to customer mobile phones with zero manual clicks
            </p>
          </div>
        </div>

        <button
          onClick={handleRefreshQR}
          disabled={loading || refreshingQR}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-muted hover:border-accent hover:text-accent transition-colors"
          title="Regenerate a brand new QR code"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading || refreshingQR ? 'animate-spin' : ''}`} /> Reload QR
        </button>
      </div>

      {/* When Connected */}
      {status?.connected ? (
        <div className="space-y-6 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500 text-white shadow-md">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-bold text-text-primary">
                  Linked Account: +{status.user?.phone || 'Unknown'}
                </p>
                <p className="text-xs text-text-muted">
                  Name: {status.user?.name || 'Moira Luxe Billing Desk'} &bull; Ready to auto-send bills
                </p>
              </div>
            </div>

            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="flex items-center justify-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-500/20 transition-colors disabled:opacity-50"
            >
              <Unlink className="h-3.5 w-3.5" />
              {disconnecting ? 'Unlinking...' : 'Disconnect Account'}
            </button>
          </div>

          {/* Test message form */}
          <form onSubmit={handleSendTest} className="rounded-xl border border-border bg-bg-secondary/40 p-4 space-y-3">
            <p className="text-xs font-semibold text-text-primary">Send Test WhatsApp Message</p>
            <p className="text-xs text-text-muted">Verify autonomous delivery right now to your own mobile phone.</p>
            <div className="flex gap-2 max-w-md">
              <input
                type="tel"
                maxLength={10}
                value={testPhone}
                onChange={(e) => setTestPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                placeholder="Enter 10-digit mobile number"
                className="flex-1 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent"
              />
              <button
                type="submit"
                disabled={sendingTest || !testPhone}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-emerald-700 transition-colors disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
                {sendingTest ? 'Sending...' : 'Send Test'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        /* When Disconnected - Show QR Code */
        <div className="space-y-6 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Left: QR Display */}
            <div className="flex flex-col items-center justify-center p-6 rounded-2xl border-2 border-dashed border-border bg-bg-secondary/30">
              {status?.qr ? (
                <div className="space-y-3 text-center">
                  <div className="p-2 bg-white rounded-2xl shadow-lg inline-block border border-gray-200">
                    <img src={status.qr} alt="WhatsApp Link QR Code" className="w-52 h-52 object-contain rounded-xl" />
                  </div>
                  <div className="flex items-center justify-center gap-2 text-xs font-medium text-amber-500">
                    <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping" />
                    Waiting for phone scan...
                  </div>
                  <div>
                    <button
                      onClick={handleRefreshQR}
                      disabled={refreshingQR}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-card px-3 py-1.5 text-xs font-semibold text-text-primary hover:border-accent hover:text-accent shadow-sm transition-all"
                    >
                      <RefreshCw className={`h-3 w-3 ${refreshingQR ? 'animate-spin' : ''}`} />
                      {refreshingQR ? 'Generating fresh code...' : '🔄 Expired? Click to Refresh QR'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center p-4 text-center text-text-muted space-y-3 min-h-[220px]">
                  <QrCode className="h-10 w-10 text-accent/50 animate-pulse" />
                  <div>
                    <p className="text-sm font-semibold text-text-primary">Starting WhatsApp engine...</p>
                    <p className="text-xs text-text-muted mt-0.5">QR code will appear here once ready</p>
                  </div>

                  <div className="rounded-lg border border-border/80 bg-bg-card p-3 text-left text-xs space-y-1.5 max-w-xs shadow-sm">
                    <p className="font-semibold text-text-secondary flex items-center gap-1.5">
                      <AlertCircle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                      Running on another PC/Laptop?
                    </p>
                    <p className="text-[11px] text-text-muted leading-relaxed">
                      To run the WhatsApp background engine on a new computer, install <strong>Node.js</strong> once (100% free):
                    </p>
                    <a
                      href="https://nodejs.org/en/download"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-accent hover:underline pt-0.5"
                    >
                      🔗 Download Node.js (nodejs.org) &rarr;
                    </a>
                  </div>
                </div>
              )}
            </div>

            {/* Right: How to scan instructions */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-text-primary flex items-center gap-2">
                <QrCode className="h-4 w-4 text-accent" />
                How to Link Your WhatsApp Account:
              </h4>

              <ol className="space-y-3 text-xs text-text-secondary leading-relaxed">
                <li className="flex items-start gap-2.5">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-bold text-xs">1</span>
                  <span>Open <b>WhatsApp</b> on your store phone or cashier phone.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-bold text-xs">2</span>
                  <span>Tap <b>Menu (3 dots)</b> on Android or <b>Settings</b> on iPhone.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-bold text-xs">3</span>
                  <span>Select <b>Linked Devices</b> and tap <b>Link a Device</b>.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-bold text-xs">4</span>
                  <span>Point your phone camera at the QR code on this screen.</span>
                </li>
              </ol>

              <div className="rounded-lg bg-blue-500/10 p-3 text-xs text-blue-600 dark:text-blue-400 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  <b>One-Time Setup:</b> Once linked, it remains connected even after closing or restarting the software!
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
