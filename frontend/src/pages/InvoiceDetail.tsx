import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/client';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { ArrowLeft, Printer, XCircle } from 'lucide-react';
import { ConfirmModal } from '../components/ConfirmModal';

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const [sale, setSale] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [confirmCancel, setConfirmCancel] = useState(false);

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n);

  useEffect(() => {
    const fetch = async () => {
      try { const res = await api.get(`/sales/${id}`); setSale(res.data); } catch { toast.error('Sale not found'); navigate('/sales'); }
      setLoading(false);
    };
    fetch();
  }, [id]);

  const handleCancelClick = () => {
    setConfirmCancel(true);
  };

  const executeCancel = async () => {
    try {
      await api.post(`/sales/${id}/cancel`);
      toast.success('Sale cancelled, stock restored');
      const res = await api.get(`/sales/${id}`);
      setSale(res.data);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const printInvoice = () => { 
    const token = localStorage.getItem('token');
    window.open(`/api/billing/invoice/${id}?token=${token}`, '_blank'); 
  };

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" /></div>;
  if (!sale) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/sales')} className="rounded-lg border border-border p-2 text-text-muted hover:text-text-primary"><ArrowLeft className="h-5 w-5" /></button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-text-primary">{sale.invoice_no}</h1>
          <p className="text-sm text-text-muted">{sale.created_at ? new Date(sale.created_at).toLocaleString('en-IN') : ''}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={printInvoice} className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-primary hover:border-accent hover:text-accent"><Printer className="h-4 w-4" /> Print</button>
          {isAdmin && sale.status === 'completed' && (
            <button onClick={handleCancelClick} className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/5 px-4 py-2 text-sm font-medium text-danger hover:bg-danger/10"><XCircle className="h-4 w-4" /> Cancel Sale</button>
          )}
        </div>
      </div>

      {/* Status Badge */}
      <div className="flex gap-4 flex-wrap items-center">
        <span className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${sale.status === 'completed' ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'}`}>{sale.status.toUpperCase()}</span>
        <span className="inline-block rounded-full bg-accent/10 px-3 py-1 text-sm font-medium text-accent capitalize">{sale.payment_method}</span>
        <span className="text-sm text-text-muted">Cashier: {sale.user_name}</span>
      </div>

      {/* Customer Details */}
      {(sale.customer_name || sale.customer_phone || sale.customer_place || sale.customer_email) && (
        <div className="rounded-xl border border-border bg-bg-card px-5 py-4">
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Customer Details</h4>
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {sale.customer_name && (
              <div><span className="text-text-muted">Name:</span> <span className="text-text-primary font-medium">{sale.customer_name}</span></div>
            )}
            {sale.customer_phone && (
              <div><span className="text-text-muted">Phone:</span> <span className="text-text-primary font-medium">{sale.customer_phone}</span></div>
            )}
            {sale.customer_place && (
              <div><span className="text-text-muted">Place:</span> <span className="text-text-primary font-medium">{sale.customer_place}</span></div>
            )}
            {sale.customer_email && (
              <div><span className="text-text-muted">Email:</span> <span className="text-text-primary font-medium">{sale.customer_email}</span></div>
            )}
          </div>
        </div>
      )}

      {/* Items Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-bg-secondary/50">
            <tr className="text-text-muted">
              <th className="px-4 py-3 text-left font-medium">#</th>
              <th className="px-4 py-3 text-left font-medium">Product</th>
              <th className="px-4 py-3 text-center font-medium">Qty</th>
              <th className="px-4 py-3 text-right font-medium">Price</th>
              <th className="px-4 py-3 text-right font-medium">Discount</th>
              <th className="px-4 py-3 text-right font-medium">Tax</th>
              <th className="px-4 py-3 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {sale.items.map((item: any, idx: number) => (
              <tr key={item.id} className="border-b border-border/30">
                <td className="px-4 py-3 text-text-muted">{idx + 1}</td>
                <td className="px-4 py-3"><p className="font-medium text-text-primary">{item.product_name}</p><p className="text-xs text-text-muted">{item.product_barcode || ''}</p></td>
                <td className="px-4 py-3 text-center text-text-primary">{item.quantity}</td>
                <td className="px-4 py-3 text-right text-text-primary">{fmt(item.unit_price)}</td>
                <td className="px-4 py-3 text-right text-text-muted">{fmt(item.discount)}</td>
                <td className="px-4 py-3 text-right text-text-muted">{item.tax_rate}%</td>
                <td className="px-4 py-3 text-right font-semibold text-text-primary">{fmt(item.subtotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Totals */}
      <div className="ml-auto w-72 rounded-xl border border-border bg-bg-card p-5 space-y-2">
        <div className="flex justify-between text-sm"><span className="text-text-muted">Subtotal</span><span className="text-text-primary">{fmt(sale.subtotal)}</span></div>
        <div className="flex justify-between text-sm"><span className="text-text-muted">Discount</span><span className="text-danger">-{fmt(sale.discount)}</span></div>
        <div className="flex justify-between text-sm"><span className="text-text-muted">Tax</span><span className="text-text-primary">+{fmt(sale.tax)}</span></div>
        <div className="border-t border-border pt-2 flex justify-between"><span className="text-base font-bold text-text-primary">Grand Total</span><span className="text-xl font-bold text-accent">{fmt(sale.total)}</span></div>
      </div>

      <ConfirmModal
        isOpen={confirmCancel}
        title="Cancel Sale"
        message="Are you sure you want to cancel this sale? Stock will be restored."
        onConfirm={executeCancel}
        onCancel={() => setConfirmCancel(false)}
      />
    </div>
  );
}
