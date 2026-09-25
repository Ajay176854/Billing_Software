import { useState, useRef, useEffect, useCallback } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { Search, Trash2, Plus, Minus, CreditCard, Banknote, Smartphone, Printer, X, ShoppingCart, Camera, QrCode } from 'lucide-react';
import { useGlobalScanner } from '../hooks/useGlobalScanner';
import ScannerModal from '../components/ScannerModal';

interface CartItem {
  product_id: number;
  name: string;
  barcode: string | null;
  price: number;
  tax_rate: number;
  stock_qty: number;
  quantity: number;
  discount: number;
}

interface CompletedSale {
  id: number;
  invoice_no: string;
  total: number;
  payment_method: string;
}

const CART_KEY = 'pos_cart';

function loadCart(): CartItem[] {
  try {
    const stored = sessionStorage.getItem(CART_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveCart(cart: CartItem[]) {
  sessionStorage.setItem(CART_KEY, JSON.stringify(cart));
}

export default function POS() {
  const [cart, setCart] = useState<CartItem[]>(loadCart);
  const [barcodeInput, setBarcodeInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const [billDiscount, setBillDiscount] = useState(0);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [cashReceived, setCashReceived] = useState('');
  const [showPayment, setShowPayment] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [completedSale, setCompletedSale] = useState<CompletedSale | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerPlace, setCustomerPlace] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  
  const [customerSuggestions, setCustomerSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const barcodeRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Auto-focus barcode input
  useEffect(() => {
    barcodeRef.current?.focus();
  }, [cart]);

  // Fetch customer suggestions
  useEffect(() => {
    const fetchCustomers = async () => {
      const query = customerPhone || customerName;
      if (query.length < 2) {
        setCustomerSuggestions([]);
        return;
      }
      try {
        const res = await api.get('/sales/customers/search', { params: { q: query } });
        setCustomerSuggestions(res.data);
      } catch (err) {
        setCustomerSuggestions([]);
      }
    };
    const t = setTimeout(fetchCustomers, 300);
    return () => clearTimeout(t);
  }, [customerPhone, customerName]);

  // Reusable barcode lookup
  const processBarcode = async (barcode: string) => {
    if (!barcode.trim()) return;
    try {
      const res = await api.get(`/products/barcode/${barcode.trim()}`);
      addToCart(res.data);
    } catch {
      toast.error(`Unknown barcode: ${barcode}`);
    }
  };

  // Global Bluetooth scanner listener
  useGlobalScanner(processBarcode);

  // Input barcode handler
  const handleBarcodeScan = async (e: React.KeyboardEvent) => {
    if (e.key !== 'Enter') return;
    await processBarcode(barcodeInput);
    setBarcodeInput('');
  };

  // Search products
  const handleSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setSearchResults([]); return; }
    try {
      const res = await api.get(`/products?search=${q}`);
      setSearchResults(res.data);
    } catch { setSearchResults([]); }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => handleSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery, handleSearch]);

  const addToCart = (product: any) => {
    setCart((prev) => {
      let next: CartItem[];
      const existing = prev.find((i) => i.product_id === product.id);
      if (existing) {
        if (existing.quantity >= product.stock_qty) {
          toast.error(`Only ${product.stock_qty} units available`);
          return prev;
        }
        next = prev.map((i) =>
          i.product_id === product.id ? { ...i, quantity: i.quantity + 1 } : i
        );
      } else if (product.stock_qty <= 0) {
        toast.error(`${product.name} is out of stock`);
        return prev;
      } else {
        next = [...prev, {
          product_id: product.id,
          name: product.name,
          barcode: product.barcode,
          price: product.selling_price,
          tax_rate: product.tax_rate,
          stock_qty: product.stock_qty,
          quantity: 1,
          discount: 0,
        }];
      }
      saveCart(next);
      return next;
    });
    setShowSearch(false);
    setSearchQuery('');
    setSearchResults([]);
  };

  const updateQty = (productId: number, delta: number) => {
    setCart((prev) => {
      const next = prev.map((i) => {
        if (i.product_id !== productId) return i;
        const newQty = i.quantity + delta;
        if (newQty <= 0) return i;
        if (newQty > i.stock_qty) { toast.error(`Only ${i.stock_qty} available`); return i; }
        return { ...i, quantity: newQty };
      });
      saveCart(next);
      return next;
    });
  };

  const removeItem = (productId: number) => {
    setCart((prev) => {
      const next = prev.filter((i) => i.product_id !== productId);
      saveCart(next);
      return next;
    });
  };

  // Calculations
  const subtotal = cart.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const itemDiscounts = cart.reduce((sum, i) => sum + i.discount, 0);
  const totalDiscount = itemDiscounts + billDiscount;
  const taxableAmount = subtotal - totalDiscount;
  const totalTax = cart.reduce((sum, i) => {
    const itemTotal = i.price * i.quantity - i.discount;
    return sum + itemTotal * (i.tax_rate / 100);
  }, 0);
  const grandTotal = taxableAmount + totalTax;

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n);

  // Complete sale
  const completeSale = async () => {
    if (cart.length === 0) return;

    if (!customerName.trim() || !customerPhone.trim()) {
      toast.error("Please fill in Customer Name and Phone Number before completing the sale.");
      return;
    }

    setProcessing(true);
    try {
      const res = await api.post('/billing/complete', {
        items: cart.map((i) => ({ product_id: i.product_id, quantity: i.quantity, discount: i.discount })),
        payment_method: paymentMethod,
        bill_discount: billDiscount,
        customer_name: customerName || undefined,
        customer_phone: customerPhone || undefined,
        customer_place: customerPlace || undefined,
        customer_email: customerEmail || undefined,
      });
      setCompletedSale({ id: res.data.id, invoice_no: res.data.invoice_no, total: res.data.total, payment_method: res.data.payment_method });
      const emptyCart: CartItem[] = [];
      setCart(emptyCart);
      saveCart(emptyCart);
      setBillDiscount(0);
      setShowPayment(false);
      setCustomerName('');
      setCustomerPhone('');
      setCustomerPlace('');
      setCustomerEmail('');
      toast.success(`Sale completed! Invoice: ${res.data.invoice_no}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Sale failed');
    } finally {
      setProcessing(false);
    }
  };

  const printInvoice = (saleId: number) => {
    const token = localStorage.getItem('token');
    window.open(`/api/billing/invoice/${saleId}?token=${token}`, '_blank');
  };

  return (
    <div className="flex h-[calc(100vh-48px)] gap-4">
      {/* Left — Product Area */}
      <div className="flex flex-1 flex-col">
        {/* Barcode + Search */}
        <div className="mb-4 flex gap-3">
          <div className="relative flex-1">
            <input
              ref={barcodeRef}
              id="pos-barcode"
              type="text"
              value={barcodeInput}
              onChange={(e) => setBarcodeInput(e.target.value)}
              onKeyDown={handleBarcodeScan}
              className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 pl-10 text-sm text-text-primary placeholder-text-muted"
              placeholder="Scan barcode or type & press Enter..."
              autoFocus
            />
            <ShoppingCart className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          </div>
          <button
            onClick={() => setShowScanner(true)}
            className="flex items-center gap-2 rounded-lg border border-border bg-bg-card px-4 py-3 text-sm font-medium text-text-secondary transition-all hover:border-accent hover:text-accent"
            title="Scan with Camera"
          >
            <Camera className="h-4 w-4" />
          </button>
          <button
            onClick={() => { setShowSearch(!showSearch); setTimeout(() => searchRef.current?.focus(), 100); }}
            className="flex items-center gap-2 rounded-lg border border-border bg-bg-card px-4 py-3 text-sm text-text-secondary transition-all hover:border-accent hover:text-accent"
          >
            <Search className="h-4 w-4" /> Search
          </button>
        </div>

        {/* Search Dropdown */}
        {showSearch && (
          <div className="animate-scale-in relative z-20 mb-4 rounded-xl border border-border bg-bg-card shadow-modal">
            <input
              ref={searchRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-t-xl border-b border-border bg-transparent px-4 py-3 text-sm text-text-primary placeholder-text-muted"
              placeholder="Search products by name or barcode..."
            />
            <div className="max-h-60 overflow-y-auto">
              {searchResults.map((p) => (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-bg-hover"
                >
                  <div>
                    <p className="text-sm font-medium text-text-primary">{p.name}</p>
                    <p className="text-xs text-text-muted">{p.barcode || p.sku || 'No barcode'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-accent">{fmt(p.selling_price)}</p>
                    <p className={`text-xs ${p.stock_qty > 0 ? 'text-success' : 'text-danger'}`}>
                      {p.stock_qty > 0 ? `${p.stock_qty} in stock` : 'Out of stock'}
                    </p>
                  </div>
                </button>
              ))}
              {searchQuery.length >= 2 && searchResults.length === 0 && (
                <p className="px-4 py-3 text-sm text-text-muted">No products found</p>
              )}
            </div>
          </div>
        )}

        {/* Cart Table */}
        <div className="flex-1 overflow-y-auto rounded-xl border border-border bg-bg-card">
          {cart.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-text-muted">
              <ShoppingCart className="mb-3 h-12 w-12 opacity-20" />
              <p className="text-sm">Scan a barcode or search to add products</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 border-b border-border bg-bg-card">
                <tr className="text-text-muted">
                  <th className="px-4 py-3 text-left font-medium">#</th>
                  <th className="px-4 py-3 text-left font-medium">Product</th>
                  <th className="px-4 py-3 text-center font-medium">Qty</th>
                  <th className="px-4 py-3 text-right font-medium">Price</th>
                  <th className="px-4 py-3 text-right font-medium">Tax</th>
                  <th className="px-4 py-3 text-right font-medium">Total</th>
                  <th className="px-4 py-3 text-center font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {cart.map((item, idx) => {
                  const itemTotal = item.price * item.quantity;
                  const tax = (itemTotal - item.discount) * (item.tax_rate / 100);
                  return (
                    <tr key={item.product_id} className="border-b border-border/50 transition-colors hover:bg-bg-hover/50">
                      <td className="px-4 py-3 text-text-muted">{idx + 1}</td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-text-primary">{item.name}</p>
                        <p className="text-xs text-text-muted">{item.barcode || ''}</p>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => updateQty(item.product_id, -1)} className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary"><Minus className="h-3.5 w-3.5" /></button>
                          <span className="w-8 text-center font-semibold text-text-primary">{item.quantity}</span>
                          <button onClick={() => updateQty(item.product_id, 1)} className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary"><Plus className="h-3.5 w-3.5" /></button>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-text-primary">{fmt(item.price)}</td>
                      <td className="px-4 py-3 text-right text-text-muted">{item.tax_rate}%</td>
                      <td className="px-4 py-3 text-right font-semibold text-text-primary">{fmt(itemTotal + tax - item.discount)}</td>
                      <td className="px-4 py-3 text-center">
                        <button onClick={() => removeItem(item.product_id)} className="rounded p-1 text-text-muted transition-colors hover:bg-danger/10 hover:text-danger"><Trash2 className="h-3.5 w-3.5" /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Right — Bill Summary */}
      <div className="flex w-80 flex-col rounded-xl border border-border bg-bg-card">
        <div className="border-b border-border px-5 py-4">
          <h3 className="text-sm font-semibold text-text-primary">Bill Summary</h3>
        </div>

        <div className="flex-1 space-y-3 px-5 py-4">
          <div className="flex justify-between text-sm"><span className="text-text-muted">Subtotal</span><span className="text-text-primary">{fmt(subtotal)}</span></div>
          <div className="flex justify-between text-sm"><span className="text-text-muted">Item Discounts</span><span className="text-danger">-{fmt(itemDiscounts)}</span></div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-muted">Bill Discount</span>
            <input
              type="number"
              min="0"
              value={billDiscount}
              onChange={(e) => setBillDiscount(Math.max(0, Number(e.target.value)))}
              className="w-24 rounded border border-border bg-bg-input px-2 py-1 text-right text-sm text-text-primary"
            />
          </div>
          <div className="flex justify-between text-sm"><span className="text-text-muted">Tax</span><span className="text-text-primary">+{fmt(totalTax)}</span></div>
          <div className="border-t border-border pt-3">
            <div className="flex justify-between">
              <span className="text-base font-bold text-text-primary">Grand Total</span>
              <span className="text-xl font-bold text-accent">{fmt(grandTotal)}</span>
            </div>
          </div>
        </div>

        <div className="border-t border-border p-4 space-y-3">
          <button
            onClick={() => setShowPayment(true)}
            disabled={cart.length === 0}
            className="bg-gradient-to-br from-indigo-600 to-indigo-500 w-full rounded-lg py-3 text-sm font-semibold text-white shadow-lg shadow-accent/25 transition-all hover:shadow-xl disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Proceed to Payment
          </button>
          {cart.length > 0 && (
            <button
              onClick={() => { const empty: CartItem[] = []; setCart(empty); saveCart(empty); setBillDiscount(0); }}
              className="w-full rounded-lg border border-border py-2.5 text-sm font-medium text-text-muted transition-colors hover:border-danger hover:text-danger"
            >
              Clear Cart
            </button>
          )}
        </div>
      </div>

      {/* Payment Modal */}
      {showPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="animate-scale-in w-full max-w-md rounded-2xl border border-border bg-bg-card p-6 shadow-modal">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-lg font-bold text-text-primary">Payment</h3>
              <button onClick={() => setShowPayment(false)} className="rounded-lg p-1 text-text-muted hover:text-text-primary"><X className="h-5 w-5" /></button>
            </div>

            <div className="mb-6 text-center">
              <p className="text-sm text-text-muted">Amount to collect</p>
              <p className="mt-1 text-3xl font-bold text-accent">{fmt(grandTotal)}</p>
            </div>

            {/* Customer Details */}
            <div className="mb-5 rounded-xl border border-border bg-bg-input p-4 space-y-3 relative">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Customer Details <span className="text-danger">*</span></p>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => { setCustomerName(e.target.value); setShowSuggestions(true); }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  placeholder="Customer Name"
                  className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none placeholder-text-muted focus:border-accent"
                />
                <input
                  type="tel"
                  value={customerPhone}
                  onChange={(e) => { setCustomerPhone(e.target.value); setShowSuggestions(true); }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  placeholder="Phone Number"
                  className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none placeholder-text-muted focus:border-accent"
                />
                <input
                  type="text"
                  value={customerPlace}
                  onChange={(e) => setCustomerPlace(e.target.value)}
                  placeholder="Place"
                  className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none placeholder-text-muted focus:border-accent"
                />
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  placeholder="Email ID"
                  className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary outline-none placeholder-text-muted focus:border-accent"
                />
              </div>

              {showSuggestions && customerSuggestions.length > 0 && (
                <div className="absolute left-4 right-4 top-[calc(100%-10px)] z-50 max-h-48 overflow-y-auto rounded-lg border border-border bg-bg-card shadow-xl">
                  {customerSuggestions.map((c, i) => (
                    <div 
                      key={i} 
                      className="cursor-pointer border-b border-border/50 p-3 hover:bg-bg-hover last:border-0"
                      onMouseDown={(e) => {
                        e.preventDefault(); // Prevent focus loss on input
                        setCustomerName(c.name || '');
                        setCustomerPhone(c.phone || '');
                        setCustomerPlace(c.place || '');
                        setCustomerEmail(c.email || '');
                        setShowSuggestions(false);
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-text-primary">{c.name || 'Unknown'}</span>
                        <span className="text-sm font-mono text-accent">{c.phone}</span>
                      </div>
                      {(c.place || c.email) && (
                        <div className="mt-1 flex gap-2 text-xs text-text-muted">
                          {c.place && <span>{c.place}</span>}
                          {c.email && <span>{c.email}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mb-6 grid grid-cols-3 gap-3">
              {[
                { value: 'cash', icon: Banknote, label: 'Cash' },
                { value: 'upi', icon: Smartphone, label: 'UPI' },
                { value: 'card', icon: CreditCard, label: 'Card' },
              ].map(({ value, icon: Icon, label }) => (
                <button
                  key={value}
                  onClick={() => setPaymentMethod(value)}
                  className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition-all
                    ${paymentMethod === value
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-text-muted hover:border-border-light hover:text-text-primary'
                    }`}
                >
                  <Icon className="h-6 w-6" />
                  <span className="text-xs font-medium">{label}</span>
                </button>
              ))}
            </div>

            {/* Payment Method Details */}
            <div className="mb-6 rounded-xl border border-border bg-bg-input p-4">
              {paymentMethod === 'cash' && (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-text-secondary">Cash Received</label>
                    <input 
                      type="number" 
                      min="0"
                      value={cashReceived} 
                      onChange={(e) => setCashReceived(e.target.value)} 
                      placeholder="0.00"
                      className="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-lg font-semibold text-text-primary outline-none focus:border-accent"
                      autoFocus
                    />
                  </div>
                  {Number(cashReceived) > 0 && (
                    <div className="flex justify-between border-t border-border pt-3">
                      <span className="text-sm text-text-muted">Balance (Change):</span>
                      <span className={`text-lg font-bold ${Number(cashReceived) >= grandTotal ? 'text-success' : 'text-danger'}`}>
                        {fmt(Number(cashReceived) - grandTotal)}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {paymentMethod === 'upi' && (
                <div className="flex flex-col items-center justify-center py-4 text-center animate-fade-in">
                  <QrCode className="h-24 w-24 text-text-primary mb-2 opacity-80" />
                  <p className="text-sm font-medium text-text-primary">Scan QR Code to Pay</p>
                  <p className="text-xs text-text-muted mt-1">Ask customer to scan using any UPI app</p>
                </div>
              )}

              {paymentMethod === 'card' && (
                <div className="flex flex-col items-center justify-center py-6 text-center animate-fade-in">
                  <CreditCard className="h-12 w-12 text-accent mb-3 animate-pulse" />
                  <p className="text-sm font-medium text-text-primary">Swipe or Tap Card</p>
                  <p className="text-xs text-text-muted mt-1">Please process the payment on the card machine</p>
                </div>
              )}
            </div>

            <button
              onClick={completeSale}
              disabled={processing || (paymentMethod === 'cash' && Number(cashReceived) > 0 && Number(cashReceived) < grandTotal)}
              className="bg-gradient-to-br from-emerald-500 to-emerald-400 w-full rounded-lg py-3 text-sm font-semibold text-white shadow-lg shadow-success/25 transition-all hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {processing ? 'Processing...' : `Complete Sale - ${fmt(grandTotal)}`}
            </button>
          </div>
        </div>
      )}

      {/* Completed Sale Modal */}
      {completedSale && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="animate-scale-in w-full max-w-sm rounded-2xl border border-border bg-bg-card p-6 text-center shadow-modal">
            <div className="bg-gradient-to-br from-emerald-500 to-emerald-400 mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full">
              <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            </div>
            <h3 className="text-lg font-bold text-text-primary">Sale Completed!</h3>
            <p className="mt-1 text-sm text-text-muted">Invoice: {completedSale.invoice_no}</p>
            <p className="mt-2 text-2xl font-bold text-success">{fmt(completedSale.total)}</p>
            <p className="mt-1 text-xs text-text-muted capitalize">Paid via {completedSale.payment_method}</p>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => printInvoice(completedSale.id)}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-border py-2.5 text-sm font-medium text-text-primary transition-colors hover:border-accent hover:text-accent"
              >
                <Printer className="h-4 w-4" /> Print
              </button>
              <button
                onClick={() => { setCompletedSale(null); barcodeRef.current?.focus(); }}
                className="bg-gradient-to-br from-indigo-600 to-indigo-500 flex-1 rounded-lg py-2.5 text-sm font-semibold text-white"
              >
                New Bill
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Camera Scanner Modal */}
      <ScannerModal
        isOpen={showScanner}
        onClose={() => setShowScanner(false)}
        onScan={processBarcode}
      />
    </div>
  );
}
