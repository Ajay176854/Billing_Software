import { useEffect, useState } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { Save, Database, Download, Edit2, Check, X, Trash2 } from 'lucide-react';
import { ConfirmModal } from '../components/ConfirmModal';

export default function SettingsPage() {
  const [form, setForm] = useState({ store_name: '', store_address: '', store_phone: '', store_email: '', store_gst: '', invoice_prefix: 'INV', currency_symbol: '' });
  const [backups, setBackups] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [backingUp, setBackingUp] = useState(false);
  
  const [categories, setCategories] = useState<any[]>([]);
  const [editingCategory, setEditingCategory] = useState<number | null>(null);
  const [editCategoryName, setEditCategoryName] = useState('');
  const [editCategoryPrefix, setEditCategoryPrefix] = useState('');
  const [confirmDeleteCat, setConfirmDeleteCat] = useState<any>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try { const res = await api.get('/settings/store-profile'); setForm(res.data); } catch {}
    };
    const fetchBackups = async () => {
      try { const res = await api.get('/backup/list'); setBackups(res.data.backups || []); } catch {}
    };
    const fetchCategories = async () => {
      try { const res = await api.get('/categories'); setCategories(res.data); } catch {}
    };
    fetchSettings();
    fetchBackups();
    fetchCategories();
  }, []);

  const handleUpdateCategory = async (id: number) => {
    if (!editCategoryName.trim()) return;
    try {
      const res = await api.put(`/categories/${id}`, { name: editCategoryName, prefix: editCategoryPrefix });
      setCategories(categories.map(c => c.id === id ? res.data : c));
      setEditingCategory(null);
      toast.success('Category updated');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update category');
    }
  };

  const handleDeleteCategory = (c: any) => {
    setConfirmDeleteCat(c);
  };

  const executeDeleteCategory = async () => {
    if (!confirmDeleteCat) return;
    const c = confirmDeleteCat;
    try {
      await api.delete(`/categories/${c.id}`);
      setCategories(categories.filter((cat: any) => cat.id !== c.id));
      toast.success(`Category "${c.name}" deleted`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete category');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put('/settings', { settings: form });
      toast.success('Settings saved');
    } catch (err: any) { 
      toast.error(err.response?.data?.detail || err.message || 'Failed to save settings');
      console.error("Save settings error:", err);
    }
    setSaving(false);
  };

  const createBackup = async () => {
    setBackingUp(true);
    try {
      const res = await api.post('/backup/create');
      toast.success(`Backup created: ${res.data.filename}`);
      const bkRes = await api.get('/backup/list');
      setBackups(bkRes.data.backups || []);
    } catch (err: any) { toast.error('Backup failed'); }
    setBackingUp(false);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-sm text-text-muted">Store profile and application settings</p>
      </div>

      {/* Store Profile */}
      <form onSubmit={handleSave} className="rounded-xl border border-border bg-bg-card p-6 space-y-4">
        <h3 className="text-sm font-semibold text-text-primary mb-4">Store Profile</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-text-secondary">Store Name</label><input value={form.store_name} onChange={(e) => setForm({ ...form, store_name: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
          <div className="col-span-2"><label className="mb-1 block text-xs font-medium text-text-secondary">Address</label><input value={form.store_address} onChange={(e) => setForm({ ...form, store_address: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
          <div><label className="mb-1 block text-xs font-medium text-text-secondary">Phone</label><input value={form.store_phone} onChange={(e) => setForm({ ...form, store_phone: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
          <div><label className="mb-1 block text-xs font-medium text-text-secondary">Email</label><input value={form.store_email} onChange={(e) => setForm({ ...form, store_email: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
          <div><label className="mb-1 block text-xs font-medium text-text-secondary">GSTIN</label><input value={form.store_gst} onChange={(e) => setForm({ ...form, store_gst: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
          <div><label className="mb-1 block text-xs font-medium text-text-secondary">Invoice Prefix</label><input value={form.invoice_prefix} onChange={(e) => setForm({ ...form, invoice_prefix: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
        </div>
        <button type="submit" disabled={saving} className="bg-gradient-to-br from-indigo-600 to-indigo-500 flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25 disabled:opacity-50">
          <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>

      {/* Backup */}
      <div className="rounded-xl border border-border bg-bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-text-primary">Database Backup</h3>
          <button onClick={createBackup} disabled={backingUp} className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-primary hover:border-accent hover:text-accent disabled:opacity-50">
            <Database className="h-4 w-4" /> {backingUp ? 'Creating...' : 'Create Backup'}
          </button>
        </div>
        {backups.length > 0 ? (
          <div className="space-y-2">
            {backups.map((b: any) => (
              <div key={b.filename} className="flex items-center justify-between rounded-lg bg-bg-hover/50 px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-text-primary">{b.filename}</p>
                  <p className="text-xs text-text-muted">{b.size_mb} MB &bull; {b.created ? new Date(b.created).toLocaleString('en-IN') : ''}</p>
                </div>
                <a href={`/api/backup/download/${b.filename}`} className="flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-accent hover:bg-accent/10">
                  <Download className="h-3.5 w-3.5" /> Download
                </a>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No backups yet. Create your first backup above.</p>
        )}
      </div>

      {/* Categories Management */}
      <div className="rounded-xl border border-border bg-bg-card p-6">
        <h3 className="text-sm font-semibold text-text-primary mb-4">Manage Categories</h3>
        {categories.length > 0 ? (
          <div className="space-y-2">
            {categories.map((c) => (
              <div key={c.id} className="flex items-center justify-between rounded-lg bg-bg-hover/50 px-4 py-3">
                {editingCategory === c.id ? (
                  <div className="flex gap-2 w-full">
                    <input 
                      autoFocus
                      value={editCategoryName} 
                      onChange={(e) => setEditCategoryName(e.target.value)} 
                      placeholder="Category Name" 
                      className="flex-1 rounded-lg border border-border bg-bg-input px-3 py-1.5 text-sm" 
                    />
                    <input 
                      value={editCategoryPrefix} 
                      onChange={(e) => setEditCategoryPrefix(e.target.value)} 
                      placeholder="Prefix" 
                      className="w-24 rounded-lg border border-border bg-bg-input px-3 py-1.5 text-sm" 
                    />
                    <div className="flex gap-1 ml-2">
                      <button onClick={() => handleUpdateCategory(c.id)} className="p-1.5 text-emerald-500 hover:bg-emerald-500/10 rounded-md">
                        <Check className="h-4 w-4" />
                      </button>
                      <button onClick={() => setEditingCategory(null)} className="p-1.5 text-rose-500 hover:bg-rose-500/10 rounded-md">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{c.name}</p>
                      <p className="text-xs text-text-muted">{c.prefix ? `Prefix: ${c.prefix}` : 'No prefix'}</p>
                    </div>
                    <div className="flex gap-1">
                      <button 
                        onClick={() => { 
                          setEditingCategory(c.id); 
                          setEditCategoryName(c.name); 
                          setEditCategoryPrefix(c.prefix || ''); 
                        }} 
                        className="p-2 text-text-muted hover:text-accent rounded-lg hover:bg-accent/10"
                        title="Edit"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteCategory(c)}
                        className="p-2 text-text-muted hover:text-danger rounded-lg hover:bg-danger/10 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No categories found.</p>
        )}
      </div>

      <ConfirmModal
        isOpen={!!confirmDeleteCat}
        title="Delete Category"
        message={`Delete category "${confirmDeleteCat?.name}"? Existing products in this category will remain but be uncategorized.`}
        onConfirm={executeDeleteCategory}
        onCancel={() => setConfirmDeleteCat(null)}
      />
    </div>
  );
}
