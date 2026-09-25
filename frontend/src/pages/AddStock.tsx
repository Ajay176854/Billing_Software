import { useState, useEffect } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { PackagePlus, Search, Plus, Printer } from 'lucide-react';
import ProductLabelModal from '../components/ProductLabelModal';

export default function AddStock() {
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [quantity, setQuantity] = useState('');
  const [reason, setReason] = useState('Stock purchase');
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<'new' | 'existing'>('new');
  const [categories, setCategories] = useState<any[]>([]);
  const [printProduct, setPrintProduct] = useState<any>(null);

  // New state for inline product creation
  const [newProductForm, setNewProductForm] = useState({ name: '', barcode: '', category_id: '', purchase_price: '', selling_price: '', tax_rate: '' });

  // New state for inline category creation
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryPrefix, setNewCategoryPrefix] = useState('');
  const [creatingCategory, setCreatingCategory] = useState(false);

  useEffect(() => {
    const fetchCategories = async () => {
      try { const res = await api.get('/categories'); setCategories(res.data); } catch { }
    };
    fetchCategories();
  }, []);

  const handleGenerateCode = async () => {
    try {
      const res = await api.get('/products/next-code', {
        params: { category_id: newProductForm.category_id || undefined }
      });
      setNewProductForm({ ...newProductForm, barcode: res.data.next_code });
      toast.success(`Generated ID: ${res.data.next_code}`);
    } catch (err: any) {
      toast.error('Failed to generate code');
    }
  };

  const handleSearch = async (q: string) => {
    setSearch(q);
    if (q.length < 2) { setResults([]); return; }
    try {
      const res = await api.get(`/products?search=${q}`);
      setResults(res.data);
    } catch { }
  };

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) return;
    setCreatingCategory(true);
    try {
      const res = await api.post('/categories', { name: newCategoryName, prefix: newCategoryPrefix });
      setCategories([...categories, res.data]);
      setNewProductForm({ ...newProductForm, category_id: res.data.id.toString() });
      setIsCreatingCategory(false);
      setNewCategoryName('');
      setNewCategoryPrefix('');
      toast.success('Category created');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create category');
    } finally {
      setCreatingCategory(false);
    }
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProductForm.barcode.trim()) {
      toast.error('Barcode/SKU is required. Scan, type, or click Auto.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/products', {
        name: newProductForm.name,
        barcode: newProductForm.barcode,
        category_id: newProductForm.category_id ? Number(newProductForm.category_id) : null,
        purchase_price: Number(newProductForm.purchase_price),
        selling_price: Number(newProductForm.selling_price),
        stock_qty: Number(quantity) || 0,
        tax_rate: Number(newProductForm.tax_rate) || 0,
        reorder_level: 10,   // Default values
        unit: 'pcs'          // Default values
      });
      toast.success('New product added to database and stock updated!');
      setPrintProduct(res.data); // Prompt to print label
      setNewProductForm({ name: '', barcode: '', category_id: '', purchase_price: '', selling_price: '', tax_rate: '' });
      setQuantity('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create product');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !quantity) return;
    setSubmitting(true);
    try {
      await api.post('/inventory/stock-in', { product_id: selected.id, quantity: Number(quantity), reason });
      toast.success(`Added ${quantity} units to ${selected.name}`);
      setSelected(null); setQuantity(''); setReason('Stock purchase');
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
    setSubmitting(false);
  };

  const fmt = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Add Stock</h1>
          <p className="text-sm text-text-muted">Register new products or add stock to existing ones</p>
        </div>
        <div className="flex rounded-lg border border-border bg-bg-card p-1">
          <button onClick={() => { setActiveTab('new'); setSelected(null); setResults([]); setSearch(''); }} className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'new' ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>
            New Product
          </button>
          <button onClick={() => setActiveTab('existing')} className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'existing' ? 'bg-accent text-white shadow' : 'text-text-muted hover:text-text-primary'}`}>
            Existing Product
          </button>
        </div>
      </div>

      {activeTab === 'new' && (
        <form onSubmit={handleCreateProduct} className="animate-fade-in space-y-6 rounded-xl border border-accent/20 bg-bg-card p-6 shadow-sm">
          <div>
            <h3 className="text-lg font-bold text-text-primary">Register New Product</h3>
            <p className="text-sm text-text-muted">This barcode isn't in the database. Add it now.</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-text-secondary">Product Name *</label>
              <input required value={newProductForm.name} onChange={(e) => setNewProductForm({ ...newProductForm, name: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="E.g. Paracetamol 500mg" />
            </div>
            <div className="col-span-2">
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-medium text-text-secondary">Category *</label>
                <button type="button" onClick={() => setIsCreatingCategory(!isCreatingCategory)} className="text-xs text-accent hover:underline">
                  {isCreatingCategory ? 'Cancel' : '+ Add New Category'}
                </button>
              </div>

              {isCreatingCategory ? (
                <div className="flex gap-2">
                  <input autoFocus value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} placeholder="Category Name *" className="flex-1 rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary" />
                  <input value={newCategoryPrefix} onChange={(e) => setNewCategoryPrefix(e.target.value)} placeholder="Prefix (Optional)" className="w-32 rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary" />
                  <button type="button" onClick={handleCreateCategory} disabled={creatingCategory || !newCategoryName.trim()} className="rounded-lg bg-accent px-4 py-2 text-xs font-medium text-white disabled:opacity-50">
                    {creatingCategory ? 'Saving...' : 'Save'}
                  </button>
                </div>
              ) : (
                <select required={!isCreatingCategory} value={newProductForm.category_id} onChange={(e) => setNewProductForm({ ...newProductForm, category_id: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary">
                  <option value="">Select Category</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              )}
            </div>

            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-text-secondary">Barcode / SKU *</label>
              <div className="flex gap-2">
                <input required value={newProductForm.barcode} onChange={(e) => setNewProductForm({ ...newProductForm, barcode: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="Scan or Auto-generate" />
                <button type="button" onClick={handleGenerateCode} className="rounded-lg bg-bg-secondary px-3 text-xs font-medium text-text-primary hover:bg-bg-hover whitespace-nowrap">Auto</button>
              </div>
            </div>

            <div className="col-span-2 grid grid-cols-3 gap-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Purchase Price *</label>
                <input required type="number" step="0.01" value={newProductForm.purchase_price} onChange={(e) => setNewProductForm({ ...newProductForm, purchase_price: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="0.00" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Selling Price *</label>
                <input required type="number" step="0.01" value={newProductForm.selling_price} onChange={(e) => setNewProductForm({ ...newProductForm, selling_price: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="0.00" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">GST % *</label>
                <input required type="number" step="0.01" value={newProductForm.tax_rate} onChange={(e) => setNewProductForm({ ...newProductForm, tax_rate: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="18" />
              </div>
            </div>
          </div>

          <div className="border-t border-border pt-4">
            <h4 className="text-sm font-semibold text-text-primary mb-3">Initial Stock (Optional)</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Quantity to Add</label>
                <input type="number" min="0" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="Enter quantity" />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={submitting} className="flex items-center gap-2 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-400 px-6 py-2.5 text-sm font-semibold text-white shadow-lg hover:shadow-xl disabled:opacity-50">
              <Plus className="h-4 w-4" /> {submitting ? 'Saving...' : 'Add Product & Stock'}
            </button>
          </div>
        </form>
      )}

      {/* Search Product */}
      {activeTab === 'existing' && !selected && (
        <div className="animate-fade-in rounded-xl border border-border bg-bg-card p-5 shadow-sm">
          <label className="mb-2 block text-xs font-medium text-text-secondary">Or Search Product</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input value={search} onChange={(e) => handleSearch(e.target.value)} placeholder="Search by name..." className="w-full rounded-lg border border-border bg-bg-input py-3 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted" />
          </div>
          {results.length > 0 && (
            <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-border">
              {results.map((p) => (
                <button key={p.id} onClick={() => { setSelected(p); setResults([]); setSearch(''); }}
                  className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-bg-hover">
                  <div><p className="text-sm font-medium text-text-primary">{p.name}</p><p className="text-xs text-text-muted">{p.barcode || 'No barcode'}</p></div>
                  <p className="text-sm text-text-muted">Stock: {p.stock_qty}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Selected Product + Add Quantity Form */}
      {selected && (
        <form onSubmit={handleSubmit} className="animate-fade-in space-y-4">
          <div className="rounded-xl border border-accent/30 bg-accent/5 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-bold text-text-primary">{selected.name}</p>
                <p className="text-sm text-text-muted">{selected.barcode || selected.sku || 'No barcode'} &bull; {selected.category_name || 'Uncategorized'}</p>
              </div>
              <div className="flex items-center gap-4 text-right">
                <button type="button" onClick={() => setPrintProduct(selected)} className="flex items-center gap-2 rounded-lg bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-100 transition-colors">
                  <Printer className="h-4 w-4" /> Print Label
                </button>
                <div>
                  <p className="text-sm text-text-muted">Current Stock</p>
                  <p className="text-2xl font-bold text-accent">{selected.stock_qty}</p>
                </div>
              </div>
            </div>
            <div className="mt-3 flex gap-4 text-sm text-text-muted">
              <span>Buy: {fmt(selected.purchase_price)}</span>
              <span>Sell: {fmt(selected.selling_price)}</span>
              <span>Tax: {selected.tax_rate}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Quantity to Add *</label>
              <input required type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" placeholder="Enter quantity" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Reason</label>
              <input value={reason} onChange={(e) => setReason(e.target.value)} className="w-full rounded-lg border border-border bg-bg-input px-4 py-3 text-sm text-text-primary" />
            </div>
          </div>

          <div className="flex gap-3">
            <button type="button" onClick={() => setSelected(null)} className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-text-muted hover:text-text-primary">Cancel</button>
            <button type="submit" disabled={submitting} className="bg-gradient-to-br from-emerald-500 to-emerald-400 flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-success/25 disabled:opacity-50">
              <PackagePlus className="h-4 w-4" /> {submitting ? 'Adding...' : 'Add Stock'}
            </button>
          </div>
        </form>
      )}

      {printProduct && (
        <ProductLabelModal
          isOpen={!!printProduct}
          onClose={() => setPrintProduct(null)}
          productCode={printProduct.barcode || printProduct.sku || ''}
          productName={printProduct.name}
        />
      )}
    </div>
  );
}
