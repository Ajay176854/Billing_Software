import React, { useRef } from 'react';
import Barcode from 'react-barcode';
import { QRCodeSVG } from 'qrcode.react';

interface ProductLabelModalProps {
  isOpen: boolean;
  onClose: () => void;
  productCode: string;
  productName: string;
}

const ProductLabelModal: React.FC<ProductLabelModalProps> = ({ isOpen, onClose, productCode, productName }) => {
  const printRef = useRef<HTMLDivElement>(null);

  if (!isOpen) return null;

  const handlePrint = () => {
    if (printRef.current) {
      const printContent = printRef.current.innerHTML;
      
      // Create a hidden iframe for printing to avoid 'about:blank' popup issues in PyWebView
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
        iframeDoc.write('<html><head><title>Print Label</title>');
        iframeDoc.write('<style>');
        iframeDoc.write(`
          body { font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }
          .label-container { border: 1px dashed #ccc; padding: 20px; display: inline-block; }
          .product-name { font-weight: bold; font-size: 1.2rem; margin-bottom: 10px; }
          .qr-code { margin-bottom: 10px; }
          @media print {
            @page { margin: 0; size: auto; }
            body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .label-container { border: none; padding: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; width: 100%; height: 100%; page-break-inside: avoid; }
            /* Ensure barcode and QR codes render crisply on thermal printers */
            svg { max-width: 100%; height: auto; shape-rendering: crispEdges; }
          }
        `);
        iframeDoc.write('</style></head><body>');
        iframeDoc.write(printContent);
        iframeDoc.write('</body></html>');
        iframeDoc.close();
        
        // Wait for rendering
        setTimeout(() => {
          iframe.contentWindow?.focus();
          iframe.contentWindow?.print();
          // Cleanup iframe after printing
          setTimeout(() => {
            document.body.removeChild(iframe);
          }, 1000);
        }, 250);
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">Print Product Label</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <div 
            ref={printRef}
            className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-200 rounded-lg mb-6 bg-white"
          >
            <div className="label-container flex flex-col items-center">
              <div className="text-center mb-2">
                <h3 className="font-bold tracking-widest text-sm" style={{ color: '#000' }}>MOIRA LUXE</h3>
                <div className="h-px w-12 bg-gray-300 mx-auto mt-1"></div>
              </div>
              <div className="product-name mt-2 mb-4 text-center font-bold text-gray-800">{productName}</div>
              <div className="qr-code mb-4 bg-white p-2 border border-gray-100 rounded">
                {productCode ? (
                  <QRCodeSVG value={productCode} size={128} level="M" includeMargin={true} />
                ) : (
                  <div className="w-32 h-32 flex items-center justify-center bg-gray-50 text-gray-400 text-sm text-center">No Code</div>
                )}
              </div>
              <div className="barcode">
                {productCode ? (
                  <Barcode value={productCode} height={40} width={1.5} fontSize={14} background="#ffffff" />
                ) : (
                  <div className="h-10 text-gray-400 text-sm">No Barcode</div>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-200 text-gray-600 rounded-md hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
            <button
              onClick={handlePrint}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              Print Label
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductLabelModal;
