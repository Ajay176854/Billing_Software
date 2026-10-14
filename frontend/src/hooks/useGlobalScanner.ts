import { useEffect, useRef } from 'react';

/**
 * Hook to listen for rapid keystrokes indicating a barcode scan
 * Scanners like Helett HT20 emulate USB HID keyboards and emit characters at ~10-40ms intervals,
 * terminated by an Enter keystroke.
 */
export function useGlobalScanner(onScan: (barcode: string) => void) {
  const barcodeBuffer = useRef('');
  const lastKeyTime = useRef<number>(0);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInputFocused = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');
      
      // If the dedicated barcode input has focus, let the input's own onKeyDown handle it
      if (isInputFocused && (activeEl.id === 'pos-barcode' || activeEl.id === 'add-stock-barcode')) {
        return;
      }
      
      // If user is actively typing inside customer name/phone/notes fields, don't hijack unless scanned fast
      const currentTime = Date.now();
      const timeDiff = currentTime - lastKeyTime.current;
      
      // If Enter is pressed
      if (e.key === 'Enter') {
        const cleaned = barcodeBuffer.current.trim();
        if (cleaned.length >= 2) {
          onScan(cleaned);
          barcodeBuffer.current = '';
          e.preventDefault();
          return;
        }
        barcodeBuffer.current = '';
        return;
      }

      // Ignore non-printable keys
      if (e.key.length !== 1) return;

      // Helett HT20 USB HID typing speed: characters arrive within 65ms
      if (timeDiff > 65) {
        barcodeBuffer.current = '';
      }

      lastKeyTime.current = currentTime;
      barcodeBuffer.current += e.key;
    };

    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [onScan]);
}

