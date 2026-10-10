import { useEffect, useState } from 'react';
import api from '../api/client';
import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';
import { BarChart3, Download, X, Phone, MapPin, Mail, ShoppingBag, ChevronRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Pagination from '../components/Pagination';

export default function Reports() {
  const [tab, setTab] = useState<'sales' | 'products' | 'customers' | 'monitoring'>('sales');
  const [salesData, setSalesData] = useState<any[]>([]);
  const [productData, setProductData] = useState<any[]>([]);
  const [itemizedData, setItemizedData] = useState<any[]>([]);
  const [customerTrafficData, setCustomerTrafficData] = useState<any[]>([]);
  const [monitoringData, setMonitoringData] = useState<any[]>([]);
  
  const [monitoringPeriod, setMonitoringPeriod] = useState<'daily'|'monthly'>('daily');
  const [monitoringGroup, setMonitoringGroup] = useState<'overall'|'product'>('overall');
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const [currentPageSales, setCurrentPageSales] = useState(1);
  const [currentPageProducts, setCurrentPageProducts] = useState(1);
  const [currentPageCustomer, setCurrentPageCustomer] = useState(1);
  const [currentPageMonitoring, setCurrentPageMonitoring] = useState(1);
  const itemsPerPage = 15;

  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [customerDetail, setCustomerDetail] = useState<any>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Monitoring detail drawer
  const [selectedMonitoringRow, setSelectedMonitoringRow] = useState<any>(null);
  const [monitoringDetailData, setMonitoringDetailData] = useState<any[] | null>(null);
  const [loadingMonitoringDetail, setLoadingMonitoringDetail] = useState(false);

  const openMonitoringDetail = async (row: any) => {
    setSelectedMonitoringRow(row);
    setLoadingMonitoringDetail(true);
    try {
      const dateStr = row.date;
      let start_date, end_date;
      if (dateStr.length === 7) { // YYYY-MM
          const [y, m] = dateStr.split('-');
          start_date = `${dateStr}-01T00:00:00`;
          const lastDay = new Date(parseInt(y), parseInt(m), 0).getDate();
          end_date = `${dateStr}-${lastDay}T23:59:59`;
      } else {
          start_date = `${dateStr}T00:00:00`;
          end_date = `${dateStr}T23:59:59`;
      }

      if (monitoringGroup === 'overall') {
        const res = await api.get('/reports/product-sales', { params: { start_date, end_date } });
        setMonitoringDetailData(res.data);
      } else {
        const res = await api.get('/reports/itemized-sales', { params: { start_date, end_date } });
        // Filter itemized sales by product_name
        const filtered = res.data.filter((item: any) => item.product_name === row.product_name);
        setMonitoringDetailData(filtered);
      }
    } catch (err) {
      setMonitoringDetailData([]);
    }
    setLoadingMonitoringDetail(false);
  };

  const openCustomerDetail = async (c: any) => {
    setSelectedCustomer(c);
    setLoadingDetail(true);
    try {
      const res = await api.get('/reports/customer-detail', { params: { phone: c.customer_phone } });
      setCustomerDetail(res.data);
    } catch {
      setCustomerDetail(null);
    }
    setLoadingDetail(false);
  };

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const params: any = {};
        if (startDate) params.start_date = `${startDate}T00:00:00`;
        if (endDate) params.end_date = `${endDate}T23:59:59`;

        const [salesRes, productRes, itemizedRes, customerRes, monitoringRes] = await Promise.all([
          api.get('/reports/sales-by-date', { params }),
          api.get('/reports/product-sales', { params }),
          api.get('/reports/itemized-sales', { params }),
          api.get('/reports/customer-traffic', { params }),
          api.get('/reports/monitoring', { params: { ...params, period: monitoringPeriod, group_by: monitoringGroup } })
        ]);
        setSalesData(salesRes.data);
        setProductData(productRes.data);
        setItemizedData(itemizedRes.data);
        setCustomerTrafficData(customerRes.data);
        setMonitoringData(monitoringRes.data);
      } catch (err) {
        console.error("Failed to load reports", err);
      }
      setLoading(false);
    };
    fetchData();
  }, [startDate, endDate, monitoringPeriod, monitoringGroup]);

  const exportToExcel = async () => {
    try {
      const workbook = new ExcelJS.Workbook();

    // --- Sheet 1: Detailed Itemized Sales ---
    const wsItemized = workbook.addWorksheet('Detailed Sales');
    wsItemized.columns = [
      { header: 'Date & Time', key: 'date', width: 20 },
      { header: 'Invoice No', key: 'invoice_no', width: 22 },
      { header: 'Product Name', key: 'product_name', width: 35 },
      { header: 'Barcode', key: 'barcode', width: 18 },
      { header: 'Qty', key: 'quantity', width: 10, style: { numFmt: '#,##0' } },
      { header: 'Price', key: 'price', width: 15, style: { numFmt: '₹#,##0.00' } },
      { header: 'Tax', key: 'tax', width: 15, style: { numFmt: '₹#,##0.00' } },
      { header: 'Total', key: 'total', width: 15, style: { numFmt: '₹#,##0.00' } },
      { header: 'Profit', key: 'profit', width: 15, style: { numFmt: '₹#,##0.00' } },
    ];

    const rowsItemized = itemizedData.map(d => [
      d.date, d.invoice_no, d.product_name || '-', d.barcode || '-', d.quantity, d.price, d.tax, d.total, d.profit
    ]);

    if (rowsItemized.length > 0) {
      wsItemized.addTable({
        name: 'ItemizedTable',
        ref: 'A1',
        headerRow: true,
        totalsRow: true,
        style: { theme: 'TableStyleMedium4', showRowStripes: true },
        columns: [
          { name: 'Date & Time', filterButton: true },
          { name: 'Invoice No', filterButton: true },
          { name: 'Product Name', filterButton: true },
          { name: 'Barcode', filterButton: true },
          { name: 'Qty', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Price', filterButton: true },
          { name: 'Tax', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Total', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Profit', filterButton: true, totalsRowFunction: 'sum' },
        ],
        rows: rowsItemized,
      });
      wsItemized.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    }

    // --- Sheet 2: Daily Sales ---
    const wsSales = workbook.addWorksheet('Daily Sales Summary');
    wsSales.columns = [
      { header: 'Date', key: 'date', width: 15 },
      { header: 'Bills Count', key: 'bills', width: 15, style: { numFmt: '#,##0' } },
      { header: 'Total Sales', key: 'sales', width: 20, style: { numFmt: '₹#,##0.00' } },
      { header: 'Discount', key: 'discount', width: 20, style: { numFmt: '₹#,##0.00' } },
      { header: 'Tax', key: 'tax', width: 20, style: { numFmt: '₹#,##0.00' } },
      { header: 'Profit', key: 'profit', width: 20, style: { numFmt: '₹#,##0.00' } },
    ];

    const rowsSales = salesData.map(d => [d.date, d.total_bills, d.total_sales, d.total_discount, d.total_tax, d.total_profit]);

    if (rowsSales.length > 0) {
      wsSales.addTable({
        name: 'SalesTable',
        ref: 'A1',
        headerRow: true,
        totalsRow: true,
        style: { theme: 'TableStyleMedium2', showRowStripes: true },
        columns: [
          { name: 'Date', filterButton: true },
          { name: 'Bills Count', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Total Sales', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Discount', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Tax', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Profit', filterButton: true, totalsRowFunction: 'sum' },
        ],
        rows: rowsSales,
      });
      wsSales.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    }

    // --- Sheet 2: Product Sales ---
    const wsProd = workbook.addWorksheet('Product Sales');
    wsProd.columns = [
      { header: 'Rank', key: 'rank', width: 10, style: { numFmt: '#,##0' } },
      { header: 'Product Name', key: 'product', width: 40 },
      { header: 'Barcode', key: 'barcode', width: 20 },
      { header: 'Units Sold', key: 'units', width: 15, style: { numFmt: '#,##0' } },
      { header: 'Total Revenue', key: 'revenue', width: 20, style: { numFmt: '₹#,##0.00' } },
      { header: 'Total Profit', key: 'profit', width: 20, style: { numFmt: '₹#,##0.00' } },
    ];

    const rowsProd = productData.map((p, i) => [i + 1, p.product_name || '-', p.barcode || '-', p.total_qty_sold, p.total_revenue, p.total_profit]);

    if (rowsProd.length > 0) {
      wsProd.addTable({
        name: 'ProductsTable',
        ref: 'A1',
        headerRow: true,
        totalsRow: true,
        style: { theme: 'TableStyleMedium3', showRowStripes: true },
        columns: [
          { name: 'Rank', filterButton: true },
          { name: 'Product Name', filterButton: true },
          { name: 'Barcode', filterButton: true },
          { name: 'Units Sold', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Total Revenue', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Total Profit', filterButton: true, totalsRowFunction: 'sum' },
        ],
        rows: rowsProd,
      });
      wsProd.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    }

    // --- Sheet 4: Customer Traffic ---
    const wsCustomer = workbook.addWorksheet('Customer Traffic');
    wsCustomer.columns = [
      { header: 'Rank', key: 'rank', width: 10, style: { numFmt: '#,##0' } },
      { header: 'Customer Name', key: 'name', width: 30 },
      { header: 'Phone', key: 'phone', width: 20 },
      { header: 'Total Visits', key: 'visits', width: 15, style: { numFmt: '#,##0' } },
      { header: 'Total Spent', key: 'spent', width: 20, style: { numFmt: '₹#,##0.00' } },
      { header: 'Last Visit', key: 'last_visit', width: 25 },
    ];
    
    const rowsCustomer = customerTrafficData.map((c, i) => [
      i + 1, c.customer_name || 'Unknown', c.customer_phone, c.total_visits, c.total_spent, 
      c.last_visit ? new Date(c.last_visit).toLocaleString() : '-'
    ]);
    if (rowsCustomer.length > 0) {
      wsCustomer.addTable({
        name: 'CustomersTable',
        ref: 'A1',
        headerRow: true,
        totalsRow: true,
        style: { theme: 'TableStyleMedium5', showRowStripes: true },
        columns: [
          { name: 'Rank', filterButton: true },
          { name: 'Customer Name', filterButton: true },
          { name: 'Phone', filterButton: true },
          { name: 'Total Visits', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Total Spent', filterButton: true, totalsRowFunction: 'sum' },
          { name: 'Last Visit', filterButton: true },
        ],
        rows: rowsCustomer,
      });
      wsCustomer.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    }

    // --- Sheet 5: Monitoring Data ---
    if (monitoringData && monitoringData.length > 0) {
      const wsMonitoring = workbook.addWorksheet('Monitoring Data');
      if (monitoringGroup === 'overall') {
        wsMonitoring.columns = [
          { header: 'Date', key: 'date', width: 15 },
          { header: 'Bills Count', key: 'bills', width: 15, style: { numFmt: '#,##0' } },
          { header: 'Total Sales', key: 'sales', width: 20, style: { numFmt: '₹#,##0.00' } },
          { header: 'Total Profit', key: 'profit', width: 20, style: { numFmt: '₹#,##0.00' } },
        ];
        
        const rowsMonitoring = monitoringData.map(d => [d.date, d.total_bills, d.total_sales, d.total_profit]);
        
        wsMonitoring.addTable({
          name: 'MonitoringOverallTable',
          ref: 'A1',
          headerRow: true,
          totalsRow: true,
          style: { theme: 'TableStyleMedium6', showRowStripes: true },
          columns: [
            { name: 'Date', filterButton: true },
            { name: 'Bills Count', filterButton: true, totalsRowFunction: 'sum' },
            { name: 'Total Sales', filterButton: true, totalsRowFunction: 'sum' },
            { name: 'Total Profit', filterButton: true, totalsRowFunction: 'sum' },
          ],
          rows: rowsMonitoring,
        });
      } else {
        wsMonitoring.columns = [
          { header: 'Date', key: 'date', width: 15 },
          { header: 'Product Name', key: 'product', width: 40 },
          { header: 'Units Sold', key: 'qty', width: 15, style: { numFmt: '#,##0' } },
          { header: 'Revenue', key: 'revenue', width: 20, style: { numFmt: '₹#,##0.00' } },
          { header: 'Profit', key: 'profit', width: 20, style: { numFmt: '₹#,##0.00' } },
        ];
        
        const rowsMonitoring = monitoringData.map(d => [d.date, d.product_name, d.qty_sold, d.revenue, d.profit]);
        
        wsMonitoring.addTable({
          name: 'MonitoringProductTable',
          ref: 'A1',
          headerRow: true,
          totalsRow: true,
          style: { theme: 'TableStyleMedium6', showRowStripes: true },
          columns: [
            { name: 'Date', filterButton: true },
            { name: 'Product Name', filterButton: true },
            { name: 'Units Sold', filterButton: true, totalsRowFunction: 'sum' },
            { name: 'Revenue', filterButton: true, totalsRowFunction: 'sum' },
            { name: 'Profit', filterButton: true, totalsRowFunction: 'sum' },
          ],
          rows: rowsMonitoring,
        });
      }
      wsMonitoring.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };
    }

      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      saveAs(blob, `Business_Report_${new Date().toISOString().split('T')[0]}.xlsx`);
      import('react-hot-toast').then(({ default: toast }) => toast.success('Export successful!'));
    } catch (err: any) {
      console.error(err);
      import('react-hot-toast').then(({ default: toast }) => toast.error('Export failed: ' + (err.message || 'Unknown error')));
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Reports</h1>
        <p className="text-sm text-text-muted">Business analytics and insights</p>
      </div>

      <div className="flex justify-between items-center">
        <div className="flex gap-1 rounded-xl border border-border bg-bg-card p-1">
          <button onClick={() => setTab('sales')} className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${tab === 'sales' ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>Sales Report</button>
          <button onClick={() => setTab('products')} className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${tab === 'products' ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>Product Sales</button>
          <button onClick={() => setTab('customers')} className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${tab === 'customers' ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>Customer Traffic</button>
          <button onClick={() => setTab('monitoring')} className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${tab === 'monitoring' ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>Monitoring</button>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary" />
            <span className="text-text-muted text-sm">to</span>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary" />
          </div>
          <button
            onClick={exportToExcel}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-border bg-bg-card px-4 py-2 text-sm font-medium text-text-primary transition-all hover:border-accent hover:text-accent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="h-4 w-4" /> Export
          </button>
        </div>
      </div>

      {(() => {
        const totalPagesSales = Math.ceil(salesData.length / itemsPerPage);
        const paginatedSales = salesData.slice((currentPageSales - 1) * itemsPerPage, currentPageSales * itemsPerPage);

        const totalPagesProducts = Math.ceil(productData.length / itemsPerPage);
        const paginatedProducts = productData.slice((currentPageProducts - 1) * itemsPerPage, currentPageProducts * itemsPerPage);

        const totalPagesCustomer = Math.ceil(customerTrafficData.length / itemsPerPage);
        const paginatedCustomers = customerTrafficData.slice((currentPageCustomer - 1) * itemsPerPage, currentPageCustomer * itemsPerPage);

        const totalPagesMonitoring = Math.ceil(monitoringData.length / itemsPerPage);
        const paginatedMonitoring = monitoringData.slice((currentPageMonitoring - 1) * itemsPerPage, currentPageMonitoring * itemsPerPage);

        return loading ? (
          <div className="flex h-64 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" /></div>
        ) : tab === 'sales' ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-bg-card p-5">
              <h3 className="mb-4 text-sm font-semibold text-text-primary">Daily Sales (Last 30 Days)</h3>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={salesData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
                    <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                    <Tooltip contentStyle={{ background: '#1a1f35', border: '1px solid #2a3050', borderRadius: '8px', color: '#f1f5f9', fontSize: '12px' }} formatter={(value: any, name: string) => [fmt(value), name === 'total_sales' ? 'Sales' : 'Profit']} />
                    <Bar dataKey="total_sales" name="Sales" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="total_profit" name="Profit" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-bg-secondary/50">
                  <tr className="text-text-muted">
                    <th className="px-4 py-3 text-left font-medium">Date</th>
                    <th className="px-4 py-3 text-right font-medium">Bills</th>
                    <th className="px-4 py-3 text-right font-medium">Sales</th>
                    <th className="px-4 py-3 text-right font-medium">Profit</th>
                    <th className="px-4 py-3 text-right font-medium">Discount</th>
                    <th className="px-4 py-3 text-right font-medium">Tax</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedSales.map((d: any) => (
                    <tr key={d.date} className="border-b border-border/30 hover:bg-bg-hover/50">
                      <td className="px-4 py-3 text-text-primary">{d.date}</td>
                      <td className="px-4 py-3 text-right text-text-muted">{d.total_bills}</td>
                      <td className="px-4 py-3 text-right font-semibold text-success">{fmt(d.total_sales)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-accent">{fmt(d.total_profit)}</td>
                      <td className="px-4 py-3 text-right text-text-muted">{fmt(d.total_discount)}</td>
                      <td className="px-4 py-3 text-right text-text-muted">{fmt(d.total_tax)}</td>
                    </tr>
                  ))}
                  {paginatedSales.length === 0 && <tr><td colSpan={6} className="px-4 py-12 text-center text-text-muted">No sales data</td></tr>}
                </tbody>
              </table>
              <Pagination
                currentPage={currentPageSales}
                totalPages={totalPagesSales}
                onPageChange={setCurrentPageSales}
                totalItems={salesData.length}
                itemsPerPage={itemsPerPage}
              />
            </div>
          </div>
        ) : tab === 'products' ? (
          <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-bg-secondary/50">
                <tr className="text-text-muted">
                  <th className="px-4 py-3 text-left font-medium">#</th>
                  <th className="px-4 py-3 text-left font-medium">Product</th>
                  <th className="px-4 py-3 text-left font-medium">Barcode</th>
                  <th className="px-4 py-3 text-right font-medium">Units Sold</th>
                  <th className="px-4 py-3 text-right font-medium">Revenue</th>
                  <th className="px-4 py-3 text-right font-medium">Profit</th>
                </tr>
              </thead>
              <tbody>
                {paginatedProducts.map((p: any, i: number) => (
                  <tr key={p.product_id} className="border-b border-border/30 hover:bg-bg-hover/50">
                    <td className="px-4 py-3 text-text-muted">{(currentPageProducts - 1) * itemsPerPage + i + 1}</td>
                    <td className="px-4 py-3 font-medium text-text-primary">{p.product_name}</td>
                    <td className="px-4 py-3 text-text-muted font-mono text-xs">{p.barcode || '-'}</td>
                    <td className="px-4 py-3 text-right font-semibold text-text-primary">{p.total_qty_sold}</td>
                    <td className="px-4 py-3 text-right font-semibold text-success">{fmt(p.total_revenue)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-accent">{fmt(p.total_profit)}</td>
                  </tr>
                ))}
                {paginatedProducts.length === 0 && <tr><td colSpan={6} className="px-4 py-12 text-center text-text-muted"><BarChart3 className="mx-auto mb-2 h-8 w-8 opacity-30" />No product sales data</td></tr>}
              </tbody>
            </table>
            <Pagination
              currentPage={currentPageProducts}
              totalPages={totalPagesProducts}
              onPageChange={setCurrentPageProducts}
              totalItems={productData.length}
              itemsPerPage={itemsPerPage}
            />
          </div>
        ) : tab === 'monitoring' ? (
          <div className="space-y-4">
            <div className="flex gap-4">
               <select value={monitoringPeriod} onChange={(e) => setMonitoringPeriod(e.target.value as any)} className="rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary">
                 <option value="daily">Daily</option>
                 <option value="monthly">Monthly</option>
               </select>
               <select value={monitoringGroup} onChange={(e) => setMonitoringGroup(e.target.value as any)} className="rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary">
                 <option value="overall">Overall Business</option>
                 <option value="product">By Product</option>
               </select>
            </div>
            
            <div className="rounded-xl border border-border bg-bg-card p-5">
              <h3 className="mb-4 text-sm font-semibold text-text-primary">
                 {monitoringPeriod === 'daily' ? 'Daily' : 'Monthly'} {monitoringGroup === 'overall' ? 'Overall Trends' : 'Product Trends'}
              </h3>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={monitoringData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
                    <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                    <Tooltip contentStyle={{ background: '#1a1f35', border: '1px solid #2a3050', borderRadius: '8px', color: '#f1f5f9', fontSize: '12px' }} formatter={(value: any, name: string) => [fmt(value), name]} />
                    {monitoringGroup === 'overall' ? (
                       <>
                         <Bar dataKey="total_sales" name="Sales" fill="#6366f1" radius={[4, 4, 0, 0]} />
                         <Bar dataKey="total_profit" name="Profit" fill="#10b981" radius={[4, 4, 0, 0]} />
                       </>
                    ) : (
                       <>
                         <Bar dataKey="revenue" name="Revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
                         <Bar dataKey="profit" name="Profit" fill="#10b981" radius={[4, 4, 0, 0]} />
                       </>
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-bg-secondary/50">
                  <tr className="text-text-muted">
                    <th className="px-4 py-3 text-left font-medium">Date</th>
                    {monitoringGroup === 'product' && <th className="px-4 py-3 text-left font-medium">Product Name</th>}
                    {monitoringGroup === 'overall' && <th className="px-4 py-3 text-right font-medium">Bills</th>}
                    {monitoringGroup === 'product' && <th className="px-4 py-3 text-right font-medium">Units Sold</th>}
                    <th className="px-4 py-3 text-right font-medium">{monitoringGroup === 'overall' ? 'Total Sales' : 'Revenue'}</th>
                    <th className="px-4 py-3 text-right font-medium">Profit</th>
                    <th className="px-4 py-3 w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedMonitoring.map((d: any, i: number) => (
                    <tr key={i} className="border-b border-border/30 hover:bg-bg-hover/50 cursor-pointer transition-colors" onClick={() => openMonitoringDetail(d)}>
                      <td className="px-4 py-3 text-text-primary">{d.date}</td>
                      {monitoringGroup === 'product' && <td className="px-4 py-3 text-text-primary">{d.product_name}</td>}
                      {monitoringGroup === 'overall' && <td className="px-4 py-3 text-right text-text-muted">{d.total_bills}</td>}
                      {monitoringGroup === 'product' && <td className="px-4 py-3 text-right text-text-muted">{d.qty_sold}</td>}
                      <td className="px-4 py-3 text-right font-semibold text-success">{fmt(monitoringGroup === 'overall' ? d.total_sales : d.revenue)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-accent">{fmt(monitoringGroup === 'overall' ? d.total_profit : d.profit)}</td>
                      <td className="px-4 py-3 text-center"><ChevronRight className="h-4 w-4 text-text-muted" /></td>
                    </tr>
                  ))}
                  {paginatedMonitoring.length === 0 && <tr><td colSpan={7} className="px-4 py-12 text-center text-text-muted">No monitoring data</td></tr>}
                </tbody>
              </table>
              <Pagination
                currentPage={currentPageMonitoring}
                totalPages={totalPagesMonitoring}
                onPageChange={setCurrentPageMonitoring}
                totalItems={monitoringData.length}
                itemsPerPage={itemsPerPage}
              />
            </div>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-bg-secondary/50">
                <tr className="text-text-muted">
                  <th className="px-4 py-3 text-left font-medium">#</th>
                  <th className="px-4 py-3 text-left font-medium">Customer Name</th>
                  <th className="px-4 py-3 text-left font-medium">Phone</th>
                  <th className="px-4 py-3 text-right font-medium">Total Visits</th>
                  <th className="px-4 py-3 text-right font-medium">Total Spent</th>
                  <th className="px-4 py-3 text-right font-medium">Last Visit</th>
                  <th className="px-4 py-3 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {paginatedCustomers.map((c: any, i: number) => (
                  <tr
                    key={c.customer_phone}
                    className="border-b border-border/30 hover:bg-bg-hover/50 cursor-pointer transition-colors"
                    onClick={() => openCustomerDetail(c)}
                  >
                    <td className="px-4 py-3 text-text-muted">{(currentPageCustomer - 1) * itemsPerPage + i + 1}</td>
                    <td className="px-4 py-3 font-medium text-accent hover:underline">{c.customer_name || 'Unknown'}</td>
                    <td className="px-4 py-3 text-text-muted font-mono">{c.customer_phone}</td>
                    <td className="px-4 py-3 text-right font-semibold text-text-primary">{c.total_visits}</td>
                    <td className="px-4 py-3 text-right font-semibold text-success">{fmt(c.total_spent)}</td>
                    <td className="px-4 py-3 text-right text-text-muted text-xs">
                      {c.last_visit ? new Date(c.last_visit).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-3 text-center"><ChevronRight className="h-4 w-4 text-text-muted" /></td>
                  </tr>
                ))}
                  {paginatedCustomers.length === 0 && <tr><td colSpan={7} className="px-4 py-12 text-center text-text-muted"><BarChart3 className="mx-auto mb-2 h-8 w-8 opacity-30" />No customer traffic data</td></tr>}
              </tbody>
            </table>
            <Pagination
              currentPage={currentPageCustomer}
              totalPages={totalPagesCustomer}
              onPageChange={setCurrentPageCustomer}
              totalItems={customerTrafficData.length}
              itemsPerPage={itemsPerPage}
            />
          </div>
        );
      })()}

      {/* Customer Detail Drawer */}
      {selectedCustomer && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => { setSelectedCustomer(null); setCustomerDetail(null); }} />
          <div className="relative w-full max-w-md h-full bg-bg-card border-l border-border flex flex-col shadow-2xl overflow-hidden animate-slide-in">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div>
                <h2 className="text-lg font-bold text-text-primary">{selectedCustomer.customer_name || 'Unknown'}</h2>
                <p className="text-xs text-text-muted">Customer Profile</p>
              </div>
              <button onClick={() => { setSelectedCustomer(null); setCustomerDetail(null); }} className="rounded-lg p-2 text-text-muted hover:text-text-primary hover:bg-bg-hover">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {loadingDetail ? (
                <div className="flex h-40 items-center justify-center">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                </div>
              ) : customerDetail ? (
                <>
                  {/* Contact Info */}
                  <div className="rounded-xl border border-border bg-bg-secondary/30 p-4 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-3">Contact Info</p>
                    <div className="flex items-center gap-3 text-sm">
                      <Phone className="h-4 w-4 text-accent shrink-0" />
                      <span className="text-text-primary font-mono">{customerDetail.phone}</span>
                    </div>
                    {customerDetail.place && (
                      <div className="flex items-center gap-3 text-sm">
                        <MapPin className="h-4 w-4 text-accent shrink-0" />
                        <span className="text-text-primary">{customerDetail.place}</span>
                      </div>
                    )}
                    {customerDetail.email && (
                      <div className="flex items-center gap-3 text-sm">
                        <Mail className="h-4 w-4 text-accent shrink-0" />
                        <span className="text-text-primary">{customerDetail.email}</span>
                      </div>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-border bg-bg-secondary/30 p-4 text-center">
                      <p className="text-2xl font-bold text-accent">{customerDetail.total_visits}</p>
                      <p className="text-xs text-text-muted mt-1">Total Visits</p>
                    </div>
                    <div className="rounded-xl border border-border bg-bg-secondary/30 p-4 text-center">
                      <p className="text-xl font-bold text-success">{fmt(customerDetail.total_spent)}</p>
                      <p className="text-xs text-text-muted mt-1">Total Spent</p>
                    </div>
                  </div>

                  {/* Purchase History */}
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-3 flex items-center gap-2">
                      <ShoppingBag className="h-3.5 w-3.5" /> Purchase History
                    </p>
                    <div className="space-y-3">
                      {customerDetail.purchases.map((p: any) => (
                        <div key={p.id} className="rounded-xl border border-border bg-bg-secondary/20 p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-mono text-sm font-semibold text-accent">{p.invoice_no}</span>
                            <span className="text-sm font-bold text-text-primary">{fmt(p.total)}</span>
                          </div>
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-xs text-text-muted">{p.created_at ? new Date(p.created_at).toLocaleString('en-IN') : ''}</span>
                            <span className="inline-block rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent capitalize">{p.payment_method}</span>
                          </div>
                          <div className="space-y-1">
                            {p.items.map((item: any, idx: number) => (
                              <div key={idx} className="flex items-center justify-between text-xs">
                                <span className="text-text-secondary">{item.product_name} × {item.quantity}</span>
                                <span className="text-text-muted">{fmt(item.subtotal)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-text-muted text-center py-8">Failed to load customer details.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Monitoring Detail Drawer */}
      {selectedMonitoringRow && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => { setSelectedMonitoringRow(null); setMonitoringDetailData(null); }} />
          <div className="relative w-full max-w-2xl h-full bg-bg-card border-l border-border flex flex-col shadow-2xl overflow-hidden animate-slide-in">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div>
                <h2 className="text-lg font-bold text-text-primary">
                  {monitoringGroup === 'overall' ? 'Product Sales Breakdown' : 'Itemized Sales Breakdown'}
                </h2>
                <p className="text-xs text-text-muted">
                  {monitoringGroup === 'overall' ? `For ${selectedMonitoringRow.date}` : `${selectedMonitoringRow.product_name} - ${selectedMonitoringRow.date}`}
                </p>
              </div>
              <button onClick={() => { setSelectedMonitoringRow(null); setMonitoringDetailData(null); }} className="rounded-lg p-2 text-text-muted hover:text-text-primary hover:bg-bg-hover">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {loadingMonitoringDetail ? (
                <div className="flex h-40 items-center justify-center">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                </div>
              ) : monitoringDetailData && monitoringDetailData.length > 0 ? (
                <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
                  <table className="w-full text-sm">
                    <thead className="border-b border-border bg-bg-secondary/50">
                      <tr className="text-text-muted">
                        {monitoringGroup === 'overall' ? (
                          <>
                            <th className="px-4 py-3 text-left font-medium">Product Name</th>
                            <th className="px-4 py-3 text-right font-medium">Qty</th>
                            <th className="px-4 py-3 text-right font-medium">Revenue</th>
                            <th className="px-4 py-3 text-right font-medium">Profit</th>
                          </>
                        ) : (
                          <>
                            <th className="px-4 py-3 text-left font-medium">Time</th>
                            <th className="px-4 py-3 text-left font-medium">Invoice No</th>
                            <th className="px-4 py-3 text-right font-medium">Qty</th>
                            <th className="px-4 py-3 text-right font-medium">Price</th>
                            <th className="px-4 py-3 text-right font-medium">Total</th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {monitoringDetailData.map((row: any, idx: number) => (
                        <tr key={idx} className="border-b border-border/30 hover:bg-bg-hover/50">
                          {monitoringGroup === 'overall' ? (
                            <>
                              <td className="px-4 py-3 text-text-primary font-medium">{row.product_name}</td>
                              <td className="px-4 py-3 text-right text-text-muted">{row.total_qty_sold}</td>
                              <td className="px-4 py-3 text-right font-semibold text-success">{fmt(row.total_revenue)}</td>
                              <td className="px-4 py-3 text-right font-semibold text-accent">{fmt(row.total_profit)}</td>
                            </>
                          ) : (
                            <>
                              <td className="px-4 py-3 text-text-primary">{row.date?.split(' ')[1] || row.date}</td>
                              <td className="px-4 py-3 text-text-muted font-mono">{row.invoice_no}</td>
                              <td className="px-4 py-3 text-right text-text-muted">{row.quantity}</td>
                              <td className="px-4 py-3 text-right text-text-muted">{fmt(row.price)}</td>
                              <td className="px-4 py-3 text-right font-semibold text-success">{fmt(row.total)}</td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-text-muted text-center py-8">No detailed data found for this selection.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
