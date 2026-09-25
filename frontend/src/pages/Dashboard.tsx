import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { IndianRupee, Receipt, AlertTriangle, TrendingUp, CreditCard, X } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DashboardData {
  today_sales: number;
  today_bills: number;
  total_products: number;
  low_stock_count: number;
  out_of_stock_count: number;
  total_inventory_value: number;
  recent_sales: any[];
  top_products: any[];
  payment_summary: any[];
  low_stock_products: any[];
}

function StatCard({ icon: Icon, label, value, gradient, subtitle, onClick }: any) {
  return (
    <div 
      onClick={onClick}
      className="group relative overflow-hidden rounded-xl border border-border bg-bg-card p-5 transition-all duration-300 hover:border-border-light hover:shadow-card cursor-pointer"
    >
      <div className={`${gradient} absolute -right-4 -top-4 h-20 w-20 rounded-full opacity-10 transition-all group-hover:opacity-20`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</p>
          <p className="mt-2 text-2xl font-bold text-text-primary">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-text-muted">{subtitle}</p>}
        </div>
        <div className={`${gradient} flex h-10 w-10 items-center justify-center rounded-lg`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [salesChart, setSalesChart] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalContent, setModalContent] = useState<{ title: string; desc: React.ReactNode; path: string; btnText: string } | null>(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashRes, chartRes] = await Promise.all([
          api.get('/reports/dashboard'),
          api.get('/reports/sales-by-date'),
        ]);
        setData(dashRes.data);
        setSalesChart(chartRes.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  if (!data) return null;

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-6 relative">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-sm text-text-muted">Today's overview and business insights</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard 
          icon={IndianRupee} 
          label="Today's Sales" 
          value={fmt(data.today_sales)} 
          gradient="bg-gradient-to-br from-emerald-500 to-emerald-400" 
          subtitle={`${data.today_bills} bills`}
          onClick={() => setModalContent({
            title: "Today's Sales (Recent)",
            desc: (
              <div className="space-y-3">
                <p>Total Revenue today: <b>{fmt(data.today_sales)}</b> ({data.today_bills} bills)</p>
                {(data.recent_sales || []).length > 0 && (
                  <div className="rounded-lg border border-border bg-bg-secondary p-3 space-y-2">
                    {(data.recent_sales || []).map(s => (
                      <div key={s.id} className="flex justify-between items-center text-sm border-b border-border/50 pb-1 last:border-0 last:pb-0">
                        <span className="font-medium text-text-primary">{s.invoice_no}</span>
                        <span className="font-semibold text-text-primary">{fmt(s.total)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ),
            path: "/sales",
            btnText: "View All Sales"
          })}
        />
        <StatCard 
          icon={Receipt} 
          label="Total Products" 
          value={data.total_products} 
          gradient="bg-gradient-to-br from-indigo-500 to-indigo-400" 
          onClick={() => setModalContent({
            title: "Top Selling Products",
            desc: (
              <div className="space-y-3">
                <p>You have <b>{data.total_products}</b> active products. Top sellers:</p>
                {(data.top_products || []).length > 0 && (
                  <div className="rounded-lg border border-border bg-bg-secondary p-3 space-y-2">
                    {(data.top_products || []).map((p, i) => (
                      <div key={p.product_id} className="flex justify-between items-center text-sm border-b border-border/50 pb-1 last:border-0 last:pb-0">
                        <span className="font-medium text-text-primary truncate mr-2">{i+1}. {p.product_name}</span>
                        <span className="text-text-muted">{p.total_sold} units</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ),
            path: "/products",
            btnText: "Manage Products"
          })}
        />
        <StatCard 
          icon={AlertTriangle} 
          label="Low Stock" 
          value={data.low_stock_count} 
          gradient="bg-gradient-to-br from-amber-500 to-orange-400" 
          subtitle={`${data.out_of_stock_count} out of stock`}
          onClick={() => setModalContent({
            title: "Low Stock Alerts",
            desc: (
              <div className="space-y-3">
                <p><b>{data.low_stock_count}</b> low stock, <b>{data.out_of_stock_count}</b> out of stock.</p>
                {(data.low_stock_products || []).length > 0 && (
                  <div className="rounded-lg border border-border bg-bg-secondary p-3 space-y-2">
                    {(data.low_stock_products || []).map((p: any) => (
                      <div key={p.id} className="flex justify-between items-center text-sm border-b border-border/50 pb-1 last:border-0 last:pb-0">
                        <span className="font-medium text-text-primary truncate mr-2">{p.name}</span>
                        <span className={`font-semibold ${p.stock_qty === 0 ? 'text-danger' : 'text-amber-500'}`}>{p.stock_qty} left</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ),
            path: "/inventory",
            btnText: "Check Inventory"
          })}
        />
        <StatCard 
          icon={TrendingUp} 
          label="Inventory Value" 
          value={fmt(data.total_inventory_value)} 
          gradient="bg-gradient-to-br from-blue-500 to-blue-400" 
          onClick={() => setModalContent({
            title: "Inventory Value",
            desc: (
              <div className="space-y-3">
                <p>The total calculated value of your current active inventory is <b>{fmt(data.total_inventory_value)}</b> (based on purchase price).</p>
                <div className="rounded-lg bg-blue-500/10 p-3 text-sm text-blue-600 dark:text-blue-400">
                  Value is calculated by multiplying the current stock quantity by the purchase price of each item.
                </div>
              </div>
            ),
            path: "/inventory",
            btnText: "View Inventory Details"
          })}
        />
      </div>

      {/* Grid Modal */}
      {modalContent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="animate-scale-in w-full max-w-sm rounded-2xl border border-border bg-bg-card p-6 shadow-modal">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-text-primary">{modalContent.title}</h3>
              <button onClick={() => setModalContent(null)} className="rounded-lg p-1 text-text-muted hover:text-text-primary transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mb-6 text-sm text-text-muted leading-relaxed">
              {modalContent.desc}
            </div>
            <button
              onClick={() => {
                setModalContent(null);
                navigate(modalContent.path);
              }}
              className="w-full rounded-lg bg-gradient-to-br from-indigo-600 to-indigo-500 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25 transition-all hover:shadow-xl"
            >
              {modalContent.btnText}
            </button>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Sales Trend */}
        <div className="lg:col-span-2 min-w-0 rounded-xl border border-border bg-bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold text-text-primary">Sales Trend (Last 30 Days)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={salesChart}>
                <defs>
                  <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', color: '#0f172a', fontSize: '12px', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}
                  formatter={(value: number) => [fmt(value), 'Sales']}
                />
                <Area type="monotone" dataKey="total_sales" stroke="#4f46e5" fill="url(#salesGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Products */}
        <div className="rounded-xl border border-border bg-bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold text-text-primary">Top Selling Products</h3>
          <div className="space-y-3">
            {data.top_products.length === 0 && (
              <p className="text-sm text-text-muted">No sales data yet</p>
            )}
            {data.top_products.map((p: any, i: number) => (
              <div key={p.product_id} className="flex items-center gap-3 rounded-lg bg-bg-hover/50 p-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-text-primary">{p.product_name}</p>
                  <p className="text-xs text-text-muted">{p.total_sold} units sold</p>
                </div>
                <span className="text-sm font-semibold text-success">{fmt(p.total_revenue)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Sales */}
        <div className="rounded-xl border border-border bg-bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold text-text-primary">Recent Sales</h3>
          <div className="space-y-2">
            {data.recent_sales.length === 0 && (
              <p className="text-sm text-text-muted">No recent sales</p>
            )}
            {data.recent_sales.map((s: any) => (
              <div key={s.id} className="flex items-center justify-between rounded-lg bg-bg-hover/50 px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-text-primary">{s.invoice_no}</p>
                  <p className="text-xs text-text-muted">{s.created_at ? new Date(s.created_at).toLocaleString('en-IN') : ''}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-text-primary">{fmt(s.total)}</p>
                  <span className="inline-block rounded-full bg-accent/15 px-2 py-0.5 text-xs font-medium text-accent capitalize">{s.payment_method}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Payment Summary */}
        <div className="rounded-xl border border-border bg-bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold text-text-primary">Payment Methods (Today)</h3>
          <div className="space-y-3">
            {data.payment_summary.length === 0 && (
              <p className="text-sm text-text-muted">No payments today</p>
            )}
            {data.payment_summary.map((p: any) => (
              <div key={p.payment_method} className="flex items-center gap-3">
                <CreditCard className="h-4 w-4 text-text-muted" />
                <div className="flex-1">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-text-primary capitalize">{p.payment_method}</span>
                    <span className="font-semibold text-text-primary">{fmt(p.total_amount)}</span>
                  </div>
                  <p className="text-xs text-text-muted">{p.count} transactions</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
