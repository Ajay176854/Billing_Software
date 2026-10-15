import React, { useRef, useState, useEffect } from 'react';
import Barcode from 'react-barcode';
import { QRCodeSVG } from 'qrcode.react';
import { Printer, X, Zap } from 'lucide-react';
import api from '../api/client';
import axios from 'axios';
import toast from 'react-hot-toast';

interface ProductLabelModalProps {
  isOpen: boolean;
  onClose: () => void;
  productCode: string;
  productName: string;
  price?: number;
  currencySymbol?: string;
}

export type LabelLayout = '50x30' | '50x25' | '40x30' | 'standard';

const ProductLabelModal: React.FC<ProductLabelModalProps> = ({
  isOpen,
  onClose,
  productCode,
  productName,
  price,
  currencySymbol = '₹',
}) => {
  const printRef = useRef<HTMLDivElement>(null);
  const [labelSize, setLabelSize] = useState<LabelLayout>('50x30');
  const [showPrice, setShowPrice] = useState(true);
  const [showQr, setShowQr] = useState(false);
  const [showStoreHeader, setShowStoreHeader] = useState(true);
  const [copies, setCopies] = useState(1);
  const [storeName, setStoreName] = useState(() => {
    return localStorage.getItem('store_name') || 'MOIRA LUXE';
  });
  const [printingDirect, setPrintingDirect] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('hardware_label_size') as LabelLayout;
    if (saved) setLabelSize(saved);

    // Fetch dynamic store name from settings
    api.get('/settings/store-profile').then(res => {
      if (res.data?.store_name) {
        setStoreName(res.data.store_name);
        localStorage.setItem('store_name', res.data.store_name);
      }
    }).catch(() => {});
  }, []);

  if (!isOpen) return null;

  // Direct USB RAW TSPL printing (instantly prints directly to printer without any browser popup)
  const handleDirectPrint = async () => {
    setPrintingDirect(true);
    try {
      const dimensions = labelSize === '50x25'
        ? { width: 50, height: 25 }
        : labelSize === '40x30'
          ? { width: 40, height: 30 }
          : { width: 50, height: 30 };

      // Send directly to local FastAPI server on port 8000
      let res;
      try {
        res = await axios.post('http://127.0.0.1:8000/api/printer/print-label', {
          product_name: productName,
          barcode: productCode,
          price: showPrice ? price : undefined,
          store_name: showStoreHeader ? storeName : '',
          copies: copies,
          width_mm: dimensions.width,
          height_mm: dimensions.height,
          show_price: showPrice,
          show_header: showStoreHeader,
        });
      } catch {
        res = await api.post('/printer/print-label', {
          product_name: productName,
          barcode: productCode,
          price: showPrice ? price : undefined,
          store_name: showStoreHeader ? storeName : '',
          copies: copies,
          width_mm: dimensions.width,
          height_mm: dimensions.height,
          show_price: showPrice,
          show_header: showStoreHeader,
        });
      }

      toast.success(res.data?.message || `Printed ${copies} label(s) directly to DEV 632-L58P!`);
      localStorage.setItem('hardware_label_size', labelSize);
      onClose();
    } catch (err: any) {
      console.error("Direct hardware print error:", err);
      toast.error(err.response?.data?.detail || "Could not reach hardware printer. Ensure backend is running.");
    } finally {
      setPrintingDirect(false);
    }
  };

  // Browser Print Preview Fallback
  const handleBrowserPrint = () => {
    if (!printRef.current) return;
    localStorage.setItem('hardware_label_size', labelSize);

    let combinedLabelsHtml = '';
    for (let i = 0; i < Math.max(1, copies); i++) {
      combinedLabelsHtml += `
        <div class="label-page">
          ${printRef.current.innerHTML}
        </div>
      `;
    }

    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = 'none';
    document.body.appendChild(iframe);

    const iframeDoc = iframe.contentWindow?.document;
    if (iframeDoc) {
      iframeDoc.open();
      iframeDoc.write('<!DOCTYPE html><html><head><title>Print Label</title>');
      iframeDoc.write('<style>');
      iframeDoc.write(`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; 
          text-align: center; 
          margin: 0; 
          padding: 0; 
          background: #fff;
          color: #000;
        }
        .label-page {
          width: 50mm;
          min-height: 30mm;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 1mm 1.5mm;
          page-break-after: always;
        }
        .label-header-row { display: flex; justify-content: space-between; align-items: flex-start; width: 100%; margin-bottom: 2px; }
        .store-header { font-size: 11px; font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase; text-align: left; }
        .price-tag { font-size: 11px; font-weight: 700; white-space: nowrap; margin-left: 4px; text-align: right; }
        .product-name { font-weight: 700; font-size: 13px; margin: 2px 0 3px 0; max-height: 34px; overflow: hidden; line-height: 1.15; word-break: break-word; text-align: center; width: 100%; }
        .barcode-wrap { margin-top: 2px; display: flex; justify-content: center; width: 100%; }
        svg { max-width: 100%; height: auto; shape-rendering: crispEdges; }
        @media print {
          @page { 
            margin: 0; 
            size: ${labelSize === '50x25' ? '50mm 25mm' : labelSize === '40x30' ? '40mm 30mm' : '50mm 30mm'};
          }
          body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .label-page { border: none !important; width: 100%; height: 100%; padding: 1mm; }
        }
      `);
      iframeDoc.write('</style></head><body>');
      iframeDoc.write(combinedLabelsHtml);
      iframeDoc.write('</body></html>');
      iframeDoc.close();

      setTimeout(() => {
        iframe.contentWindow?.focus();
        iframe.contentWindow?.print();
        setTimeout(() => {
          document.body.removeChild(iframe);
        }, 1200);
      }, 300);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-gray-100 animate-scale-in">
        {/* Header */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-gray-100 bg-gray-50/70">
          <div>
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Printer className="w-5 h-5 text-indigo-600" />
              DEV 632-L58P Direct Label Print
            </h2>
            <p className="text-xs text-gray-500">Instant direct thermal hardware printing</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Label Preview Card */}
          <div className="flex flex-col items-center justify-center p-4 bg-slate-50 border border-slate-200 rounded-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">Live Thermal Label Preview</span>

            <div
              ref={printRef}
              style={{
                width: labelSize === '40x30' ? '180px' : '210px',
                minHeight: labelSize === '50x25' ? '110px' : '135px',
              }}
              className="bg-white border-2 border-dashed border-gray-300 rounded-lg p-2.5 flex flex-col items-center justify-center text-center shadow-xs"
            >
              {/* Top row: Shop name on left/center & Price on top right */}
              <div className="label-header-row flex items-baseline justify-between w-full border-b border-gray-300 pb-0.5 mb-1.5">
                {showStoreHeader ? (
                  <div className="store-header text-[11px] font-bold tracking-wider text-black">
                    {storeName}
                  </div>
                ) : (
                  <div></div>
                )}

                {showPrice && price !== undefined && (
                  <div className="price-tag text-[11px] font-bold text-black tracking-tight whitespace-nowrap ml-auto">
                    {currencySymbol}{Number(price).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
                  </div>
                )}
              </div>

              {/* Product name slightly smaller */}
              <div className="product-name text-[13px] font-bold text-black leading-tight line-clamp-2 px-1 text-center w-full my-0.5">
                {productName}
              </div>

              {showQr && (
                <div className="my-1">
                  {productCode ? (
                    <QRCodeSVG value={productCode} size={64} level="M" />
                  ) : (
                    <div className="text-[10px] text-gray-400">No Code</div>
                  )}
                </div>
              )}

              <div className="barcode-wrap flex justify-center w-full mt-1">
                {productCode ? (
                  <Barcode
                    value={productCode}
                    height={labelSize === '50x25' ? 38 : 48}
                    width={2.2}
                    fontSize={13}
                    margin={0}
                    displayValue={true}
                    background="#ffffff"
                  />
                ) : (
                  <span className="text-[10px] text-gray-400">No Barcode</span>
                )}
              </div>
            </div>
          </div>

          {/* Controls & Presets */}
          <div className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-xl text-xs">
            <div>
              <label className="font-semibold text-gray-700 block mb-1.5">Label Size</label>
              <select
                value={labelSize}
                onChange={(e) => setLabelSize(e.target.value as LabelLayout)}
                className="w-full bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 font-medium text-gray-800"
              >
                <option value="50x30">50 × 30 mm (Recommended)</option>
                <option value="50x25">50 × 25 mm (Compact)</option>
                <option value="40x30">40 × 30 mm</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-gray-700 block mb-1.5">Number of Labels</label>
              <input
                type="number"
                min="1"
                max="100"
                value={copies}
                onChange={(e) => setCopies(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 font-medium text-gray-800"
              />
            </div>

            <div className="col-span-2 flex flex-wrap gap-4 pt-1">
              <label className="flex items-center gap-1.5 text-gray-700 font-medium cursor-pointer">
                <input
                  type="checkbox"
                  checked={showPrice}
                  onChange={(e) => setShowPrice(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                Show MRP Price
              </label>

              <label className="flex items-center gap-1.5 text-gray-700 font-medium cursor-pointer">
                <input
                  type="checkbox"
                  checked={showStoreHeader}
                  onChange={(e) => setShowStoreHeader(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                Store Header
              </label>

              <label className="flex items-center gap-1.5 text-gray-700 font-medium cursor-pointer">
                <input
                  type="checkbox"
                  checked={showQr}
                  onChange={(e) => setShowQr(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                Include QR Code
              </label>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex justify-between items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleBrowserPrint}
              className="text-xs text-gray-500 hover:text-gray-800 underline decoration-dotted"
              title="Open browser print preview dialog"
            >
              Use Print Preview dialog
            </button>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-100 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={printingDirect}
                onClick={handleDirectPrint}
                className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-700 hover:to-emerald-600 text-white rounded-xl shadow-lg shadow-emerald-600/25 transition-all flex items-center gap-2 text-sm font-semibold disabled:opacity-50"
              >
                <Zap className="w-4 h-4 fill-current" />
                {printingDirect ? 'Printing...' : `Direct (${copies})`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductLabelModal;
