import { useEffect, useState } from 'react';
import api from '../api/client';
import { Warehouse, AlertTriangle, XCircle, ArrowDownUp, RefreshCw } from 'lucide-react';
import Pagination from '../components/Pagination';

export default function Inventory() {
  const [tab, setTab] = useState<'all' | 'low' | 'out' | 'history'>('all');
  const [products, setProducts] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [currentPage, setCurrentPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);
  const itemsPerPage = 15;

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n);

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      if (tab === 'low') { const res = await api.get('/inventory/low-stock'); setProducts(res.data); }
      else if (tab === 'out') { const res = await api.get('/inventory/out-of-stock'); setProducts(res.data); }
      else if (tab === 'history') { const res = await api.get('/inventory/transactions?limit=500'); setTransactions(res.data); }
      else { const res = await api.get('/products'); setProducts(res.data); }
    } catch {}
    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => { 
    fetchData(); 
    setCurrentPage(1);
  }, [tab]);

  const tabs = [
    { key: 'all', label: 'All Products', icon: Warehouse },
    { key: 'low', label: 'Low Stock', icon: AlertTriangle },
    { key: 'out', label: 'Out of Stock', icon: XCircle },
    { key: 'history', label: 'Stock History', icon: ArrowDownUp },
  ];

  const currentData = tab === 'history' ? transactions : products;
  const totalPages = Math.ceil(currentData.length / itemsPerPage);
  const paginatedData = currentData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Inventory</h1>
          <p className="text-sm text-text-muted">Stock overview and movement history</p>
        </div>
        <button
          onClick={() => { fetchData(true); setCurrentPage(1); }}
          disabled={refreshing || loading}
          className="flex items-center gap-2 rounded-lg border border-border bg-bg-card px-4 py-2 text-sm font-medium text-text-secondary transition-all hover:border-accent hover:text-accent disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border border-border bg-bg-card p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key as any)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all
              ${tab === t.key ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" /></div>
      ) : tab === 'history' ? (
        <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-bg-secondary/50">
              <tr className="text-text-muted">
                <th className="px-4 py-3 text-left font-medium">Date</th>
                <th className="px-4 py-3 text-left font-medium">Product</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-right font-medium">Qty</th>
                <th className="px-4 py-3 text-left font-medium">Reason</th>
                <th className="px-4 py-3 text-left font-medium">User</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((t: any) => (
                <tr key={t.id} className="border-b border-border/30 hover:bg-bg-hover/50">
                  <td className="px-4 py-3 text-text-muted text-xs">{t.created_at ? new Date(t.created_at).toLocaleString('en-IN') : ''}</td>
                  <td className="px-4 py-3 font-medium text-text-primary">{t.product_name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium
                      ${t.type === 'STOCK_IN' ? 'bg-success/15 text-success' : t.type === 'SALE' ? 'bg-info/15 text-info' : t.type === 'RETURN' ? 'bg-warning/15 text-warning' : 'bg-accent/15 text-accent'}`}>
                      {t.type}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${t.quantity > 0 ? 'text-success' : 'text-danger'}`}>{t.quantity > 0 ? `+${t.quantity}` : t.quantity}</td>
                  <td className="px-4 py-3 text-text-muted text-xs">{t.reason || '-'}</td>
                  <td className="px-4 py-3 text-text-muted">{t.user_name}</td>
                </tr>
              ))}
              {paginatedData.length === 0 && <tr><td colSpan={6} className="px-4 py-12 text-center text-text-muted">No transactions found</td></tr>}
            </tbody>
          </table>
          <Pagination 
            currentPage={currentPage} 
            totalPages={totalPages} 
            onPageChange={setCurrentPage} 
            totalItems={currentData.length} 
            itemsPerPage={itemsPerPage} 
          />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-bg-secondary/50">
              <tr className="text-text-muted">
                <th className="px-4 py-3 text-left font-medium">Product</th>
                <th className="px-4 py-3 text-left font-medium">Barcode</th>
                <th className="px-4 py-3 text-left font-medium">Category</th>
                <th className="px-4 py-3 text-right font-medium">Stock</th>
                <th className="px-4 py-3 text-right font-medium">Reorder</th>
                <th className="px-4 py-3 text-right font-medium">Value</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((p: any) => (
                <tr key={p.id} className="border-b border-border/30 hover:bg-bg-hover/50">
                  <td className="px-4 py-3 font-medium text-text-primary">{p.name}</td>
                  <td className="px-4 py-3 text-text-muted font-mono text-xs">{p.barcode || '-'}</td>
                  <td className="px-4 py-3 text-text-muted">{p.category_name || '-'}</td>
                  <td className={`px-4 py-3 text-right font-bold ${p.stock_qty === 0 ? 'text-danger' : p.stock_qty <= p.reorder_level ? 'text-warning' : 'text-success'}`}>{p.stock_qty}</td>
                  <td className="px-4 py-3 text-right text-text-muted">{p.reorder_level}</td>
                  <td className="px-4 py-3 text-right text-text-primary">{fmt(p.stock_qty * p.purchase_price)}</td>
                </tr>
              ))}
              {paginatedData.length === 0 && <tr><td colSpan={6} className="px-4 py-12 text-center text-text-muted">No products found</td></tr>}
            </tbody>
          </table>
          <Pagination 
            currentPage={currentPage} 
            totalPages={totalPages} 
            onPageChange={setCurrentPage} 
            totalItems={currentData.length} 
            itemsPerPage={itemsPerPage} 
          />
        </div>
      )}
    </div>
  );
}
