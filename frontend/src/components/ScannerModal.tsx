import { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { X, Camera } from 'lucide-react';
import toast from 'react-hot-toast';

interface ScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScan: (barcode: string) => void;
}

export default function ScannerModal({ isOpen, onClose, onScan }: ScannerModalProps) {
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const isStoppingRef = useRef(false);
  const [cameras, setCameras] = useState<{id: string, label: string}[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [hasCameras, setHasCameras] = useState(true);

  // Fetch cameras when modal opens
  useEffect(() => {
    let isMounted = true;
    if (isOpen) {
      Html5Qrcode.getCameras().then(devices => {
        if (devices && devices.length > 0 && isMounted) {
          setCameras(devices);
          setHasCameras(true);
          // Try to select the back camera by default if it exists, else pick the first one (or DroidCam if found)
          const droidCam = devices.find(d => d.label.toLowerCase().includes('droidcam'));
          if (droidCam) {
            setSelectedCameraId(droidCam.id);
          } else {
            setSelectedCameraId(devices[0].id);
          }
        } else if (isMounted) {
          setHasCameras(false);
          toast.error("No camera found");
        }
      }).catch(err => {
        if (isMounted) {
          console.error("Camera access failed", err);
          setHasCameras(false);
          toast.error("Failed to access camera. Check browser permissions.");
        }
      });
    }
    return () => { isMounted = false; };
  }, [isOpen]);

  // Start scanner when a camera is selected
  useEffect(() => {
    let isMounted = true;
    
    if (isOpen && selectedCameraId) {
      isStoppingRef.current = false;
      
      const startScanner = async () => {
        try {
          // Stop existing scanner if running
          if (scannerRef.current) {
            await scannerRef.current.stop().catch(() => {});
            try { scannerRef.current.clear(); } catch(e) {}
          }
          
          if (!isMounted) return;
          
          const html5QrCode = new Html5Qrcode("reader");
          scannerRef.current = html5QrCode;
          
          await html5QrCode.start(
            selectedCameraId, // Use specific device ID instead of facingMode
            { fps: 10, qrbox: { width: 250, height: 150 } },
            (decodedText) => {
              if (isStoppingRef.current) return;
              isStoppingRef.current = true;
              onScan(decodedText);
              onClose();
            },
            () => { /* ignore parse errors */ }
          );
        } catch (err) {
          if (isMounted) {
            console.error("Failed to start camera feed", err);
            toast.error("Failed to start selected camera.");
          }
        }
      };

      startScanner();
    }

    return () => {
      isMounted = false;
      if (scannerRef.current) {
        isStoppingRef.current = true;
        try {
          scannerRef.current.stop().catch(() => {}).finally(() => {
            try { scannerRef.current?.clear(); } catch(e) {}
          });
        } catch (e) {}
        scannerRef.current = null;
      }
    };
  }, [isOpen, selectedCameraId, onClose, onScan]);

  return (
    <div className={`fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 ${isOpen ? '' : 'hidden'}`}>
      <div className="w-full max-w-md animate-scale-in rounded-2xl border border-border bg-bg-card p-6 shadow-modal">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-accent" />
            <h3 className="text-lg font-bold text-text-primary">Camera Scanner</h3>
          </div>
          <button onClick={() => { isStoppingRef.current = true; onClose(); }} className="rounded-lg p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {hasCameras ? (
          <div className="flex flex-col gap-4">
            {cameras.length > 1 && (
              <select
                value={selectedCameraId}
                onChange={(e) => setSelectedCameraId(e.target.value)}
                className="w-full rounded-xl border border-border bg-bg-input px-4 py-2.5 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all"
              >
                {cameras.map(cam => (
                  <option key={cam.id} value={cam.id}>
                    {cam.label || `Camera ${cam.id.substring(0, 5)}...`}
                  </option>
                ))}
              </select>
            )}
            
            <div id="reader" className="overflow-hidden rounded-xl border-2 border-dashed border-border-light bg-black"></div>
            
            <p className="text-center text-sm text-text-muted">
              Point your camera at a barcode or QR code
            </p>
          </div>
        ) : (
          <div className="py-8 text-center text-text-muted">
            <p>No camera available or permission denied.</p>
          </div>
        )}
      </div>
    </div>
  );
}
