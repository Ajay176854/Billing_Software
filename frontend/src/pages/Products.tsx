import { useEffect, useState } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { Plus, Search, Edit2, X, Package, Printer, Trash2, Tag } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ProductLabelModal from '../components/ProductLabelModal';
import Pagination from '../components/Pagination';
import { ConfirmModal } from '../components/ConfirmModal';

interface Product {
  id: number; barcode: string | null; sku: string | null; name: string; category_id: number | null;
  category_name: string | null; purchase_price: number; selling_price: number; tax_rate: number;
  stock_qty: number; reorder_level: number; unit: string; status: string;
}

interface Category { id: number; name: string; }

export default function Products() {
  const { hasRole } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [printProduct, setPrintProduct] = useState<Product | null>(null);
  const [editing, setEditing] = useState<Product | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Product | null>(null);
  const [form, setForm] = useState({ barcode: '', sku: '', name: '', category_id: '', purchase_price: '', selling_price: '', tax_rate: '18', stock_qty: '0', reorder_level: '10', unit: 'pcs' });
  const [loading, setLoading] = useState(true);

  // Category modal state
  const [showCatModal, setShowCatModal] = useState(false);
  const [catForm, setCatForm] = useState({ name: '', prefix: '' });
  const [savingCat, setSavingCat] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const canManage = hasRole('admin', 'inventory');
  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n);

  const fetchProducts = async () => {
    try {
      const params: any = {};
      if (search) params.search = search;
      if (catFilter) params.category_id = catFilter;
      const res = await api.get('/products', { params });
      setProducts(res.data);
      setCurrentPage(1);
    } catch { toast.error('Failed to load products'); }
    setLoading(false);
  };

  const fetchCategories = async () => {
    try { const res = await api.get('/categories'); setCategories(res.data); } catch {}
  };

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catForm.name.trim()) return;
    setSavingCat(true);
    try {
      await api.post('/categories', { name: catForm.name.trim(), prefix: catForm.prefix.trim() || undefined });
      toast.success(`Category "${catForm.name}" created`);
      setCatForm({ name: '', prefix: '' });
      setShowCatModal(false);
      fetchCategories();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create category');
    }
    setSavingCat(false);
  };

  useEffect(() => { fetchCategories(); }, []);
  useEffect(() => { fetchProducts(); }, [search, catFilter]);

  const openAdd = () => {
    setEditing(null);
    setForm({ barcode: '', sku: '', name: '', category_id: '', purchase_price: '', selling_price: '', tax_rate: '18', stock_qty: '0', reorder_level: '10', unit: 'pcs' });
    setShowModal(true);
  };

  const openEdit = (p: Product) => {
    setEditing(p);
    setForm({
      barcode: p.barcode || '', sku: p.sku || '', name: p.name,
      category_id: p.category_id ? String(p.category_id) : '',
      purchase_price: String(p.purchase_price), selling_price: String(p.selling_price),
      tax_rate: String(p.tax_rate), stock_qty: String(p.stock_qty),
      reorder_level: String(p.reorder_level), unit: p.unit,
    });
    setShowModal(true);
  };

  const handleGenerateCode = async () => {
    try {
      const res = await api.get('/products/next-code', {
        params: { category_id: form.category_id || undefined }
      });
      setForm({ ...form, barcode: res.data.next_code, sku: res.data.next_code });
      toast.success(`Generated ID: ${res.data.next_code}`);
    } catch (err: any) {
      toast.error('Failed to generate code');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const body: any = {
      name: form.name,
      barcode: form.barcode || null,
      sku: form.sku || null,
      category_id: form.category_id ? Number(form.category_id) : null,
      purchase_price: Number(form.purchase_price),
      selling_price: Number(form.selling_price),
      tax_rate: Number(form.tax_rate),
      reorder_level: Number(form.reorder_level),
      unit: form.unit,
    };
    try {
      if (editing) {
        await api.put(`/products/${editing.id}`, body);
        toast.success('Product updated');
      } else {
        body.stock_qty = Number(form.stock_qty);
        await api.post('/products', body);
        toast.success('Product created');
      }
      setShowModal(false);
      fetchProducts();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const handleDelete = (p: Product) => {
    setConfirmDelete(p);
  };

  const executeDelete = async () => {
    if (!confirmDelete) return;
    try {
      await api.delete(`/products/${confirmDelete.id}`);
      toast.success(`"${confirmDelete.name}" deleted`);
      fetchProducts();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const stockBadge = (p: Product) => {
    if (p.stock_qty === 0) return <span className="inline-block rounded-full bg-danger/15 px-2 py-0.5 text-xs font-medium text-danger">Out of Stock</span>;
    if (p.stock_qty <= p.reorder_level) return <span className="inline-block rounded-full bg-warning/15 px-2 py-0.5 text-xs font-medium text-warning">Low Stock</span>;
    return <span className="inline-block rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">In Stock</span>;
  };

  const totalPages = Math.ceil(products.length / itemsPerPage);
  const paginatedProducts = products.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Products</h1>
          <p className="text-sm text-text-muted">{products.length} products</p>
        </div>
        {canManage && (
          <div className="flex gap-2">
            <button onClick={() => { setCatForm({ name: '', prefix: '' }); setShowCatModal(true); }} className="flex items-center gap-2 rounded-lg border border-border bg-bg-card px-4 py-2.5 text-sm font-semibold text-text-secondary transition-all hover:border-accent hover:text-accent">
              <Tag className="h-4 w-4" /> Add Category
            </button>
            <button onClick={openAdd} className="bg-gradient-to-br from-indigo-600 to-indigo-500 flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25 transition-all hover:shadow-xl">
              <Plus className="h-4 w-4" /> Add Product
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name, barcode, or SKU..." className="w-full rounded-lg border border-border bg-bg-input py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted" />
        </div>
        <select value={catFilter} onChange={(e) => setCatFilter(e.target.value)} className="rounded-lg border border-border bg-bg-input px-4 py-2.5 text-sm text-text-primary">
          <option value="">All Categories</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-bg-secondary/50">
            <tr className="text-text-muted">
              <th className="px-4 py-3 text-left font-medium">Product</th>
              <th className="px-4 py-3 text-left font-medium">Barcode/SKU</th>
              <th className="px-4 py-3 text-left font-medium">Category</th>
              {canManage && <th className="px-4 py-3 text-right font-medium">Buy Price</th>}
              <th className="px-4 py-3 text-right font-medium">Sell Price</th>
              <th className="px-4 py-3 text-right font-medium">Tax</th>
              <th className="px-4 py-3 text-center font-medium">Stock</th>
              <th className="px-4 py-3 text-center font-medium">Status</th>
              {canManage && <th className="px-4 py-3 text-center font-medium w-12"></th>}
            </tr>
          </thead>
          <tbody>
            {paginatedProducts.map((p) => (
              <tr key={p.id} className="border-b border-border/30 transition-colors hover:bg-bg-hover/50">
                <td className="px-4 py-3 font-medium text-text-primary">{p.name}</td>
                <td className="px-4 py-3 text-text-muted font-mono text-xs">{p.barcode || p.sku || '-'}</td>
                <td className="px-4 py-3 text-text-muted">{p.category_name || '-'}</td>
                {canManage && <td className="px-4 py-3 text-right text-text-muted">{fmt(p.purchase_price)}</td>}
                <td className="px-4 py-3 text-right font-semibold text-text-primary">{fmt(p.selling_price)}</td>
                <td className="px-4 py-3 text-right text-text-muted">{p.tax_rate}%</td>
                <td className="px-4 py-3 text-center font-semibold text-text-primary">{p.stock_qty}</td>
                <td className="px-4 py-3 text-center">{stockBadge(p)}</td>
                {canManage && (
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => setPrintProduct(p)} className="rounded p-1 text-text-muted hover:text-accent" title="Print Label"><Printer className="h-4 w-4" /></button>
                      <button onClick={() => openEdit(p)} className="rounded p-1 text-text-muted hover:text-accent" title="Edit"><Edit2 className="h-4 w-4" /></button>
                      <button onClick={() => handleDelete(p)} className="rounded p-1 text-text-muted hover:text-danger transition-colors" title="Delete"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {paginatedProducts.length === 0 && !loading && (
              <tr><td colSpan={9} className="px-4 py-12 text-center text-text-muted"><Package className="mx-auto mb-2 h-8 w-8 opacity-30" />No products found</td></tr>
            )}
          </tbody>
        </table>
        <Pagination 
          currentPage={currentPage} 
          totalPages={totalPages} 
          onPageChange={setCurrentPage} 
          totalItems={products.length} 
          itemsPerPage={itemsPerPage} 
        />
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="animate-scale-in w-full max-w-lg rounded-2xl border border-border bg-bg-card p-6 shadow-modal">
            <div className="mb-5 flex items-center justify-between">
              <h3 className="text-lg font-bold text-text-primary">{editing ? 'Edit Product' : 'Add Product'}</h3>
              <button type="button" onClick={() => setShowModal(false)} className="rounded-lg p-1 text-text-muted hover:text-text-primary"><X className="h-5 w-5" /></button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-text-secondary">Product Name *</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Barcode</label>
                <div className="flex gap-2">
                  <input value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" />
                  <button type="button" onClick={handleGenerateCode} className="rounded-lg bg-bg-secondary px-3 text-xs font-medium text-text-primary hover:bg-bg-hover whitespace-nowrap">Auto</button>
                </div>
              </div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">SKU</label><input value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Category</label><select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary"><option value="">Select</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Unit</label><input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Purchase Price *</label><input required type="number" step="0.01" min="0" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Selling Price *</label><input required type="number" step="0.01" min="0" value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Tax Rate (%)</label><input type="number" step="0.1" min="0" max="100" value={form.tax_rate} onChange={(e) => setForm({ ...form, tax_rate: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              {!editing && <div><label className="mb-1 block text-xs font-medium text-text-secondary">Initial Stock</label><input type="number" min="0" value={form.stock_qty} onChange={(e) => setForm({ ...form, stock_qty: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>}
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Reorder Level</label><input type="number" min="0" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
            </div>
            <div className="mt-6 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowModal(false)} className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-text-muted hover:text-text-primary">Cancel</button>
              <button type="submit" className="bg-gradient-to-br from-indigo-600 to-indigo-500 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25">{editing ? 'Save Changes' : 'Add Product'}</button>
            </div>
          </form>
        </div>
      )}
      {/* Product Label Modal */}
      {printProduct && (
        <ProductLabelModal
          isOpen={!!printProduct}
          onClose={() => setPrintProduct(null)}
          productCode={printProduct.barcode || printProduct.sku || ''}
          productName={printProduct.name}
        />
      )}

      {/* Add Category Modal */}
      {showCatModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleAddCategory} className="animate-scale-in w-full max-w-sm rounded-2xl border border-border bg-bg-card p-6 shadow-modal">
            <div className="mb-5 flex items-center justify-between">
              <h3 className="text-lg font-bold text-text-primary">Add Category</h3>
              <button type="button" onClick={() => setShowCatModal(false)} className="rounded-lg p-1 text-text-muted hover:text-text-primary"><X className="h-5 w-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Category Name *</label>
                <input
                  required
                  autoFocus
                  value={catForm.name}
                  onChange={(e) => setCatForm({ ...catForm, name: e.target.value })}
                  placeholder="e.g. Bangles"
                  className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Prefix (Optional)</label>
                <input
                  value={catForm.prefix}
                  onChange={(e) => setCatForm({ ...catForm, prefix: e.target.value })}
                  placeholder="e.g. BGL"
                  maxLength={10}
                  className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary outline-none focus:border-accent"
                />
                <p className="mt-1 text-xs text-text-muted">Used for auto-generating barcodes (e.g. BGL-001)</p>
              </div>
            </div>
            <div className="mt-6 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowCatModal(false)} className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-text-muted hover:text-text-primary">Cancel</button>
              <button type="submit" disabled={savingCat} className="bg-gradient-to-br from-indigo-600 to-indigo-500 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25 disabled:opacity-50">
                {savingCat ? 'Saving...' : 'Create Category'}
              </button>
            </div>
          </form>
        </div>
      )}

      <ConfirmModal
        isOpen={!!confirmDelete}
        title="Delete Product"
        message={`Delete "${confirmDelete?.name}"? It will be hidden from products and POS but sales history is preserved.`}
        onConfirm={executeDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
