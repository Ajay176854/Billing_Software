import { useEffect, useRef } from 'react';

/**
 * Hook to listen for rapid keystrokes indicating a barcode scan
 * Scanners emulate a keyboard but type incredibly fast (e.g. 5-30ms per character).
 */
export function useGlobalScanner(onScan: (barcode: string) => void) {
  const barcodeBuffer = useRef('');
  const lastKeyTime = useRef<number>(0);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if user is explicitly typing into an input field,
      // EXCEPT if it's the barcode input itself (we let the input handle it, or we handle it here).
      const activeEl = document.activeElement;
      const isInputFocused = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');
      
      // If the barcode input has focus, let the input's own onKeyDown handle it
      if (isInputFocused && activeEl.id === 'pos-barcode') return;
      if (isInputFocused && activeEl.id === 'add-stock-barcode') return;
      
      // We only care about single printable characters or Enter
      if (e.key.length !== 1 && e.key !== 'Enter') return;

      const currentTime = Date.now();
      
      // If more than 50ms passed since last key, reset buffer (it's human typing)
      if (currentTime - lastKeyTime.current > 50) {
        barcodeBuffer.current = '';
      }

      lastKeyTime.current = currentTime;

      if (e.key === 'Enter') {
        if (barcodeBuffer.current.length > 2) { // Valid barcode length check
          onScan(barcodeBuffer.current);
          e.preventDefault();
        }
        barcodeBuffer.current = '';
      } else {
        barcodeBuffer.current += e.key;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onScan]);
}
