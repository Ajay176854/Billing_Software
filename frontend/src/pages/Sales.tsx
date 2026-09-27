import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { Search, Receipt, Eye } from 'lucide-react';
import Pagination from '../components/Pagination';

export default function Sales() {
  const [sales, setSales] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [paymentFilter, setPaymentFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const navigate = useNavigate();

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n);

  const fetchSales = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (search) params.invoice_no = search;
      if (paymentFilter) params.payment_method = paymentFilter;
      if (statusFilter) params.status = statusFilter;
      if (startDate) params.start_date = `${startDate}T00:00:00`;
      if (endDate) params.end_date = `${endDate}T23:59:59`;
      const res = await api.get('/sales', { params });
      setSales(res.data);
      setCurrentPage(1);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchSales(); }, [search, paymentFilter, statusFilter, startDate, endDate]);

  const statusBadge = (s: string) => {
    if (s === 'completed') return <span className="inline-block rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">Completed</span>;
    if (s === 'cancelled') return <span className="inline-block rounded-full bg-danger/15 px-2 py-0.5 text-xs font-medium text-danger">Cancelled</span>;
    return <span className="inline-block rounded-full bg-warning/15 px-2 py-0.5 text-xs font-medium text-warning">{s}</span>;
  };

  const totalPages = Math.ceil(sales.length / itemsPerPage);
  const paginatedSales = sales.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Sales History</h1>
        <p className="text-sm text-text-muted">{sales.length} transactions</p>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by invoice number..." className="w-full rounded-lg border border-border bg-bg-input py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted" />
        </div>
        <select value={paymentFilter} onChange={(e) => setPaymentFilter(e.target.value)} className="rounded-lg border border-border bg-bg-input px-4 py-2.5 text-sm text-text-primary">
          <option value="">All Payments</option>
          <option value="cash">Cash</option>
          <option value="upi">UPI</option>
          <option value="card">Card</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-border bg-bg-input px-4 py-2.5 text-sm text-text-primary">
          <option value="">All Status</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <div className="flex items-center gap-2">
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" />
          <span className="text-text-muted">to</span>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" />
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-bg-secondary/50">
            <tr className="text-text-muted">
              <th className="px-4 py-3 text-left font-medium">Invoice</th>
              <th className="px-4 py-3 text-left font-medium">Date & Time</th>
              <th className="px-4 py-3 text-left font-medium">Cashier</th>
              <th className="px-4 py-3 text-center font-medium">Items</th>
              <th className="px-4 py-3 text-center font-medium">Payment</th>
              <th className="px-4 py-3 text-center font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Total</th>
              <th className="px-4 py-3 text-center font-medium w-12"></th>
            </tr>
          </thead>
          <tbody>
            {paginatedSales.map((s: any) => (
              <tr key={s.id} className="border-b border-border/30 transition-colors hover:bg-bg-hover/50 cursor-pointer" onClick={() => navigate(`/sales/${s.id}`)}>
                <td className="px-4 py-3 font-mono text-sm font-medium text-accent">{s.invoice_no}</td>
                <td className="px-4 py-3 text-text-muted text-xs">{s.created_at ? new Date(s.created_at).toLocaleString('en-IN') : ''}</td>
                <td className="px-4 py-3 text-text-primary">{s.user_name}</td>
                <td className="px-4 py-3 text-center text-text-muted">{s.items_count}</td>
                <td className="px-4 py-3 text-center"><span className="inline-block rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent capitalize">{s.payment_method}</span></td>
                <td className="px-4 py-3 text-center">{statusBadge(s.status)}</td>
                <td className="px-4 py-3 text-right font-semibold text-text-primary">{fmt(s.total)}</td>
                <td className="px-4 py-3 text-center"><Eye className="h-4 w-4 text-text-muted" /></td>
              </tr>
            ))}
            {paginatedSales.length === 0 && !loading && (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-text-muted"><Receipt className="mx-auto mb-2 h-8 w-8 opacity-30" />No sales found</td></tr>
            )}
          </tbody>
        </table>
        <Pagination 
          currentPage={currentPage} 
          totalPages={totalPages} 
          onPageChange={setCurrentPage} 
          totalItems={sales.length} 
          itemsPerPage={itemsPerPage} 
        />
      </div>
    </div>
  );
}
