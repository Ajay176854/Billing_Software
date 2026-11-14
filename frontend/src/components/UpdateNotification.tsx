import { useState, useEffect } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { Sparkles, ArrowRight, X, DownloadCloud, Loader2, CheckCircle2 } from 'lucide-react';

interface UpdateInfo {
  update_available: boolean;
  current_version: string;
  latest_version: string;
  release_name?: string;
  release_notes?: string;
  download_url?: string;
  file_size_mb?: number;
  published_at?: string;
}

export default function UpdateNotification() {
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const checkForUpdates = async () => {
      try {
        const res = await api.get('/updates/check');
        if (res.data?.update_available) {
          setUpdateInfo(res.data);
        }
      } catch (err) {
        // Silently skip if offline
      }
    };

    checkForUpdates();

    // Check periodically every 30 minutes
    const interval = setInterval(checkForUpdates, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (!updateInfo || !updateInfo.update_available || dismissed) {
    return null;
  }

  const handleApplyUpdate = async () => {
    setIsUpdating(true);
    try {
      await api.post('/updates/apply');
      toast.success('Download initiated! The application will restart in a few moments.');
    } catch (err: any) {
      setIsUpdating(false);
      toast.error(err.response?.data?.detail || 'Failed to initiate update.');
    }
  };

  return (
    <>
      {/* Floating Notification Pill */}
      <div className="fixed bottom-5 right-5 z-40 animate-bounce-in">
        <div className="flex items-center gap-3 rounded-2xl border border-indigo-500/30 bg-slate-900/95 p-3.5 shadow-2xl backdrop-blur-md text-white">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-md">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Update Available</span>
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                v{updateInfo.latest_version}
              </span>
            </div>
            <p className="text-xs text-slate-300">A new version of Moira Luxe POS is ready.</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-semibold text-white transition-all shadow-md active:scale-95 ml-2"
          >
            Update <ArrowRight className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="rounded-lg p-1 text-slate-400 hover:text-white transition-colors"
            title="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Update Details Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="animate-scale-in w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-100 shadow-modal">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
                  <DownloadCloud className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Software Update Ready</h3>
                  <p className="text-xs text-slate-400">Moira Luxe Point of Sale</p>
                </div>
              </div>
              {!isUpdating && (
                <button
                  onClick={() => setShowModal(false)}
                  className="rounded-lg p-1 text-slate-400 hover:text-white transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              )}
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-800/60 p-4">
                <div className="flex justify-between items-center text-sm py-1 border-b border-slate-700/50">
                  <span className="text-slate-400">Current Installed Version:</span>
                  <span className="font-mono text-slate-300">v{updateInfo.current_version}</span>
                </div>
                <div className="flex justify-between items-center text-sm py-1 border-b border-slate-700/50">
                  <span className="text-slate-400">New Available Version:</span>
                  <span className="font-mono font-bold text-emerald-400">v{updateInfo.latest_version}</span>
                </div>
                {updateInfo.file_size_mb ? (
                  <div className="flex justify-between items-center text-sm py-1">
                    <span className="text-slate-400">Download Size:</span>
                    <span className="text-slate-300">~{updateInfo.file_size_mb} MB</span>
                  </div>
                ) : null}
              </div>

              {updateInfo.release_notes && (
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-slate-400 uppercase">What's New:</span>
                  <div className="max-h-32 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {updateInfo.release_notes}
                  </div>
                </div>
              )}

              {isUpdating ? (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/40 p-4 text-center space-y-2 animate-pulse">
                  <Loader2 className="mx-auto h-7 w-7 animate-spin text-indigo-400" />
                  <p className="text-sm font-semibold text-white">Downloading Update & Restarting...</p>
                  <p className="text-xs text-indigo-300">
                    The software will replace the executable and automatically reopen. Please do not turn off your computer.
                  </p>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span>The update downloads in background and restarts seamlessly.</span>
                </div>
              )}
            </div>

            {!isUpdating && (
              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-xl border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
                >
                  Later
                </button>
                <button
                  type="button"
                  onClick={handleApplyUpdate}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:from-indigo-500 hover:to-purple-500 transition-all active:scale-95"
                >
                  <DownloadCloud className="h-4 w-4" /> Install & Restart Now
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

