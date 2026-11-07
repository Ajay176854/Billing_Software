import React, { useRef, useState, useEffect } from 'react';
import Barcode from 'react-barcode';
import { QRCodeSVG } from 'qrcode.react';
import { Printer, X, Zap, Tag, Sparkles } from 'lucide-react';
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

export type LabelLayout = '50x30' | '50x25' | '40x30' | '14x100' | 'standard';
export type LabelMode = 'normal' | 'tagging';

const ProductLabelModal: React.FC<ProductLabelModalProps> = ({
  isOpen,
  onClose,
  productCode,
  productName,
  price,
  currencySymbol = 'Rs.',
}) => {
  const printRef = useRef<HTMLDivElement>(null);
  
  // Section Mode: 'normal' (Standard Box/Product Sticker) or 'tagging' (Jewellery Dumbbell 3-Up Tag)
  const [labelMode, setLabelMode] = useState<LabelMode>(() => {
    const saved = localStorage.getItem('label_mode');
    if (saved === 'tagging' || saved === 'normal') return saved;
    const oldSize = localStorage.getItem('hardware_label_size');
    return oldSize === '14x100' ? 'tagging' : 'normal';
  });

  const [normalSize, setNormalSize] = useState<'50x30' | '50x25' | '40x30'>(() => {
    const saved = localStorage.getItem('hardware_normal_size');
    return saved === '50x25' || saved === '40x30' ? saved : '50x30';
  });

  const [showPrice, setShowPrice] = useState(true);
  const [showQr, setShowQr] = useState(false);
  const [showStoreHeader, setShowStoreHeader] = useState(true);
  const [copies, setCopies] = useState(1);
  const [storeName, setStoreName] = useState(() => {
    return localStorage.getItem('store_name') || 'Moira Luxe';
  });
  const [printingDirect, setPrintingDirect] = useState(false);

  useEffect(() => {
    // Fetch dynamic store name from settings
    api.get('/settings/store-profile').then(res => {
      if (res.data?.store_name) {
        setStoreName(res.data.store_name);
        localStorage.setItem('store_name', res.data.store_name);
      }
    }).catch(() => {});
  }, []);

  if (!isOpen) return null;

  const isTagging = labelMode === 'tagging';

  // Direct USB RAW TSPL printing (instantly prints directly to printer without any browser popup)
  const handleDirectPrint = async () => {
    setPrintingDirect(true);
    try {
      const dimensions = isTagging
        ? { width: 14.3, height: 100 }
        : normalSize === '50x25'
          ? { width: 50, height: 25 }
          : normalSize === '40x30'
            ? { width: 40, height: 30 }
            : { width: 50, height: 30 };

      const payload = {
        product_name: productName,
        barcode: productCode,
        price: showPrice ? price : undefined,
        store_name: showStoreHeader ? storeName : '',
        copies: copies,
        width_mm: dimensions.width,
        height_mm: dimensions.height,
        label_type: labelMode,
        show_price: showPrice,
        show_header: showStoreHeader,
        show_qr: showQr,
      };

      // Send directly to local FastAPI server via configured api client
      let res;
      try {
        res = await api.post('/printer/print-label', payload);
      } catch {
        res = await axios.post('http://127.0.0.1:8000/api/printer/print-label', payload);
      }

      toast.success(res.data?.message || `Printed ${copies} ${isTagging ? 'tag' : 'label'}(s) directly to DEV 632-L58P!`);
      localStorage.setItem('label_mode', labelMode);
      if (isTagging) {
        localStorage.setItem('hardware_label_size', '14x100');
      } else {
        localStorage.setItem('hardware_normal_size', normalSize);
        localStorage.setItem('hardware_label_size', normalSize);
      }
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
    localStorage.setItem('label_mode', labelMode);

    let combinedLabelsHtml = '';
    const printIterations = isTagging ? Math.max(1, Math.ceil(copies / 3)) : Math.max(1, copies);

    for (let i = 0; i < printIterations; i++) {
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
          width: ${isTagging ? '50mm' : '50mm'};
          min-height: ${isTagging ? '100mm' : '30mm'};
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: ${isTagging ? 'flex-start' : 'flex-start'};
          padding: ${isTagging ? '2mm 1mm' : '8.5mm 2mm 1.5mm 2mm'};
          page-break-after: always;
        }
        .label-header-row { display: flex; justify-content: space-between; align-items: baseline; width: 100%; margin-bottom: 2px; }
        .store-header { font-size: 13px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; text-align: left; }
        .price-tag { font-size: 13px; font-weight: 800; white-space: nowrap; text-align: right; margin-left: auto; }
        .product-name-row { width: 100%; text-align: left; margin-bottom: 2px; }
        .product-name { font-weight: 700; font-size: 11.5px; line-height: 1.2; text-align: left; width: 100%; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .barcode-wrap { margin-top: 4px; display: flex; justify-content: center; width: 100%; }
        svg { max-width: 100%; height: auto; shape-rendering: crispEdges; }
        @media print {
          @page { 
            margin: 0; 
            size: ${isTagging ? '50mm 100mm' : normalSize === '50x25' ? '50mm 25mm' : normalSize === '40x30' ? '40mm 30mm' : '50mm 30mm'};
          }
          body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .label-page { 
            border: none !important; 
            width: 100%; 
            height: 100%; 
            padding: ${isTagging ? '1mm 0.5mm !important' : (normalSize === '50x25' ? '6.5mm' : '8mm') + ' 1.5mm 1.5mm 1.5mm !important'}; 
          }
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
              Thermal Label Printing
            </h2>
            <p className="text-xs text-gray-500">Direct hardware print to DEV 632-L58P / Xprinter</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Section Selector: Normal Label vs Tagging Label */}
        <div className="px-6 pt-4">
          <div className="flex bg-gray-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => {
                setLabelMode('normal');
                localStorage.setItem('label_mode', 'normal');
              }}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                labelMode === 'normal'
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <Tag className="w-4 h-4" />
              Normal Label
            </button>
            <button
              type="button"
              onClick={() => {
                setLabelMode('tagging');
                localStorage.setItem('label_mode', 'tagging');
              }}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                labelMode === 'tagging'
                  ? 'bg-amber-500 text-white shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Tagging Label
            </button>
          </div>
        </div>

        <div className="p-6 pt-3 space-y-5">
          {/* Label Preview Card */}
          <div className="flex flex-col items-center justify-center p-4 bg-slate-50 border border-slate-200 rounded-xl">
            <div className="flex items-center justify-between w-full mb-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {isTagging ? 'Jewellery Tagging Preview (Landscape 3-Up)' : 'Standard Normal Label Preview'}
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                isTagging ? 'bg-amber-100 text-amber-800 border border-amber-300' : 'bg-indigo-100 text-indigo-800'
              }`}>
                {isTagging ? '14.3 × 100 mm (3-Up)' : `${normalSize} mm`}
              </span>
            </div>

            {isTagging ? (
              /* Specialized Seznik 14.3mm x 100mm 3-Up Jewellery Dumbbell Tags Preview */
              <div className="flex flex-col items-center w-full">
                <div className="flex items-center gap-1.5 mb-2.5 px-3 py-1 bg-amber-100/80 border border-amber-300 rounded-full text-amber-900 text-[10px] font-bold">
                  <span>✨ 3-Up Jewellery Tags: 3 Stickers per row with Instant 360° QR Scanning</span>
                </div>
                <div
                  ref={printRef}
                  className="w-full flex justify-center items-start gap-2.5 py-2 px-2 bg-slate-100/70 border-2 border-dashed border-amber-300 rounded-xl overflow-x-auto"
                >
                  {[0, 1, 2].map((idx) => (
                    <div
                      key={idx}
                      className="w-[122px] shrink-0 flex flex-col items-center bg-white border border-amber-300 rounded-lg shadow-xs overflow-hidden"
                    >
                      {/* Flap: Divided into Front Face and Back Face with Solid Center Divider | */}
                      <div className="w-full bg-amber-50/40 p-1.5 flex flex-col items-center">
                        <span className="text-[7.5px] uppercase tracking-wider text-amber-900 font-bold bg-amber-200/80 px-1.5 py-0.2 rounded mb-1">
                          {idx === 0 ? 'Left' : idx === 1 ? 'Center' : 'Right'} #{idx + 1}
                        </span>

                        {/* Part 1: Front Face Details (Line 1: Store Name, Line 2: Product Name, Line 3: Price) */}
                        <div className="w-full text-center py-0.5">
                          {showStoreHeader && storeName && (
                            <div className="text-[9px] font-bold text-gray-800 leading-tight uppercase tracking-wider truncate">
                              {storeName}
                            </div>
                          )}
                          <div className="text-[9.5px] font-black text-black leading-tight uppercase truncate mt-0.5">
                            {productName}
                          </div>
                          {showPrice && price !== undefined && (
                            <div className="text-[9.5px] font-extrabold text-emerald-700 mt-0.5">
                              {currencySymbol} {Number(price).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}/-
                            </div>
                          )}
                        </div>

                        {/* Fold Guide Line */}
                        <div className="w-full my-1 relative flex items-center justify-between px-0.5">
                          <div className="w-2 border-t-2 border-amber-600" />
                          <span className="text-[6.5px] font-bold text-amber-700 uppercase tracking-widest">
                            Fold
                          </span>
                          <div className="w-2 border-t-2 border-amber-600" />
                        </div>

                        {/* Part 2: Back Face 2D QR Code Tag (Jewellery Industry Standard) */}
                        <div className="flex flex-col items-center justify-center w-full py-1">
                          {productCode ? (
                            <>
                              <div className="p-0.5 bg-white border border-gray-200 rounded-xs shadow-2xs">
                                <QRCodeSVG value={productCode} size={42} level="M" />
                              </div>
                              <span className="text-[7.5px] font-bold text-gray-800 mt-0.5 tracking-wider">
                                {productCode}
                              </span>
                            </>
                          ) : (
                            <span className="text-[7.5px] text-gray-400">No Code</span>
                          )}
                        </div>
                      </div>

                      {/* Middle Tail: Looping Strap */}
                      <div className="w-[14px] h-8 my-1 border-x border-dashed border-amber-400 bg-amber-50/20 flex items-center justify-center relative">
                        <span className="text-[6px] font-bold text-amber-700 rotate-90 whitespace-nowrap tracking-wider uppercase">
                          Strap
                        </span>
                      </div>

                      {/* Flap 2: Fold-Over Tab */}
                      <div className="w-full p-1 border-t border-dashed border-gray-200 bg-gray-50/50 flex flex-col items-center justify-center text-center">
                        <span className="text-[7px] text-gray-400 font-medium">
                          Blank Fold-Over
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* Standard Normal Label Preview */
              <div
                ref={printRef}
                style={{
                  width: normalSize === '40x30' ? '180px' : '210px',
                  minHeight: normalSize === '50x25' ? '110px' : '135px',
                }}
                className="bg-white border-2 border-dashed border-gray-300 rounded-lg pt-9 px-3 pb-3 flex flex-col items-center justify-start text-center shadow-xs"
              >
                {/* Row 1: Store Name on left & Price on top right corner */}
                <div className="label-header-row flex items-baseline justify-between w-full mb-1 pl-1 pr-1">
                  {showStoreHeader ? (
                    <span className="store-header text-[13px] font-extrabold tracking-wider text-black uppercase text-left">
                      {storeName}
                    </span>
                  ) : <div />}

                  {showPrice && price !== undefined && (
                    <span className="price-tag text-[13px] font-black text-black tracking-tight whitespace-nowrap ml-auto">
                      {currencySymbol} {Number(price).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}/-
                    </span>
                  )}
                </div>

                {/* Row 2: Full-width Product Name (up to 26+ characters) */}
                <div className="product-name-row w-full text-left mb-1 pl-1 pr-1">
                  <span className="product-name text-[12px] font-bold text-black block truncate">
                    {productName}
                  </span>
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
                      height={normalSize === '50x25' ? 42 : 56}
                      width={2.4}
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
            )}
          </div>

          {/* Controls & Configuration */}
          {isTagging ? (
            /* Tagging Label Specific Controls */
            <div className="grid grid-cols-2 gap-3 bg-amber-50/50 border border-amber-200/80 p-4 rounded-xl text-xs">
              <div>
                <label className="font-semibold text-gray-700 block mb-1.5">Store / Brand Name (Line 1)</label>
                <input
                  type="text"
                  placeholder="e.g. Moira Luxe"
                  value={storeName}
                  onChange={(e) => {
                    setStoreName(e.target.value);
                    localStorage.setItem('store_name', e.target.value);
                  }}
                  className="w-full bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 font-medium text-gray-800"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1.5">Quantity (Copies)</label>
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
                    checked={showStoreHeader}
                    onChange={(e) => setShowStoreHeader(e.target.checked)}
                    className="rounded text-amber-600 focus:ring-0"
                  />
                  Show Store Name (Line 1)
                </label>

                <label className="flex items-center gap-1.5 text-gray-700 font-medium cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showPrice}
                    onChange={(e) => setShowPrice(e.target.checked)}
                    className="rounded text-amber-600 focus:ring-0"
                  />
                  Show MRP Price (Line 3)
                </label>
              </div>
            </div>
          ) : (
            /* Normal Label Specific Controls */
            <div className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-xl text-xs">
              <div>
                <label className="font-semibold text-gray-700 block mb-1.5">Label Size</label>
                <select
                  value={normalSize}
                  onChange={(e) => {
                    const val = e.target.value as '50x30' | '50x25' | '40x30';
                    setNormalSize(val);
                    localStorage.setItem('hardware_normal_size', val);
                  }}
                  className="w-full bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 font-medium text-gray-800"
                >
                  <option value="50x30">50 × 30 mm (Standard Product Tag)</option>
                  <option value="50x25">50 × 25 mm (Compact)</option>
                  <option value="40x30">40 × 30 mm (Small Tag)</option>
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
          )}

          {/* Action buttons */}
          <div className="flex justify-between items-center gap-3 pt-1">
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
                className={`px-5 py-2.5 text-white rounded-xl shadow-lg transition-all flex items-center gap-2 text-sm font-semibold disabled:opacity-50 ${
                  isTagging
                    ? 'bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-700 hover:to-amber-600 shadow-amber-600/25'
                    : 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-700 hover:to-emerald-600 shadow-emerald-600/25'
                }`}
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
