import { useEffect, useState } from 'react';
import axios from 'axios';
import api from '../api/client';
import toast from 'react-hot-toast';
import { Save, Database, Download, Edit2, Check, X, Trash2, Lock } from 'lucide-react';
import { ConfirmModal } from '../components/ConfirmModal';

export default function SettingsPage() {
  const [form, setForm] = useState({ store_name: '', store_address: '', store_phone: '', store_email: '', store_gst: '', invoice_prefix: 'INV', currency_symbol: '' });
  const [saving, setSaving] = useState(false);
  const [backingUp, setBackingUp] = useState(false);

  // Security: Admin Password Change State
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [changingPassword, setChangingPassword] = useState(false);
  
  const [categories, setCategories] = useState<any[]>([]);
  const [editingCategory, setEditingCategory] = useState<number | null>(null);
  const [editCategoryName, setEditCategoryName] = useState('');
  const [editCategoryPrefix, setEditCategoryPrefix] = useState('');
  const [confirmDeleteCat, setConfirmDeleteCat] = useState<any>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try { const res = await api.get('/settings/store-profile'); setForm(res.data); } catch {}
    };
    const fetchCategories = async () => {
      try { const res = await api.get('/categories'); setCategories(res.data); } catch {}
    };
    fetchSettings();
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

  const handleExportData = async () => {
    setBackingUp(true);
    try {
      const res = await api.get('/backup/export', { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const dateStr = new Date().toISOString().slice(0, 10);
      a.download = `moira_luxe_store_backup_${dateStr}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Store data exported and saved to your laptop!');
    } catch (err: any) {
      toast.error('Failed to export data');
      console.error(err);
    }
    setBackingUp(false);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwordForm.new_password.length < 6) {
      toast.error('New password must be at least 6 characters');
      return;
    }
    setChangingPassword(true);
    try {
      await api.post('/auth/change-password', {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success('Admin password changed successfully!');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to change password');
    }
    setChangingPassword(false);
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

      {/* Security: Change Password */}
      <form onSubmit={handleChangePassword} className="rounded-xl border border-border bg-bg-card p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Lock className="h-4 w-4 text-accent" />
              Change Admin Password
            </h3>
            <p className="text-xs text-text-muted mt-0.5">Update the master login password for your administrator account</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Current Password *</label>
            <input
              type="password"
              required
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
              placeholder="••••••••"
              className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">New Password *</label>
            <input
              type="password"
              required
              minLength={6}
              value={passwordForm.new_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
              placeholder="Min 6 characters"
              className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Confirm New Password *</label>
            <input
              type="password"
              required
              minLength={6}
              value={passwordForm.confirm_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
              placeholder="Repeat new password"
              className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={changingPassword}
          className="bg-gradient-to-br from-indigo-600 to-indigo-500 flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25 disabled:opacity-50"
        >
          <Lock className="h-4 w-4" /> {changingPassword ? 'Updating...' : 'Update Password'}
        </button>
      </form>

      {/* Hardware Configuration: Helett HT20 & DEV 632-L58P */}
      <div className="rounded-xl border border-border bg-bg-card p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Hardware & POS Peripherals
            </h3>
            <p className="text-xs text-text-muted mt-0.5">Configuration for Helett HT20 Scanner & DEV 632-L58P 2-in-1 Printer</p>
          </div>
          <span className="rounded-md bg-accent/10 px-2 py-0.5 text-[11px] font-semibold text-accent">USB Plug & Play</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Scanner Card */}
          <div className="rounded-lg border border-border bg-bg-hover/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-text-primary">Barcode Scanner</span>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-500 uppercase">Ready</span>
            </div>
            <div className="text-xs space-y-1">
              <p className="font-medium text-text-primary">Helett HT20 (USB)</p>
              <p className="text-text-muted text-[11px]">Mode: USB HID Keyboard Emulation</p>
              <p className="text-text-muted text-[11px]">Speed buffer: 65ms auto-intercept</p>
            </div>
            <div className="pt-2 border-t border-border/50">
              <label className="mb-1 block text-[11px] font-medium text-text-secondary">Scan Test Box (Try scanning any barcode):</label>
              <input
                type="text"
                placeholder="Scan barcode here to test..."
                className="w-full rounded-md border border-border bg-bg-input px-2.5 py-1.5 text-xs text-text-primary focus:border-accent"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    toast.success(`HT20 Detected Barcode: ${(e.target as HTMLInputElement).value}`);
                  }
                }}
              />
            </div>
          </div>

          {/* Printer Card */}
          <div className="rounded-lg border border-border bg-bg-hover/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-text-primary">2-in-1 Thermal Printer</span>
              <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-400 uppercase">DEV 632-L58P</span>
            </div>
            
            <div className="space-y-2">
              <div>
                <label className="mb-1 block text-[11px] font-medium text-text-secondary">Receipt Roll Width</label>
                <select
                  value={(form as any).receipt_width || '58mm'}
                  onChange={(e) => setForm({ ...form, receipt_width: e.target.value } as any)}
                  className="w-full rounded-md border border-border bg-bg-input px-2.5 py-1.5 text-xs text-text-primary"
                >
                  <option value="58mm">58mm Thermal (DEV L58P Native)</option>
                  <option value="80mm">80mm Thermal (Standard POS)</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-medium text-text-secondary">Product Label Paper Size</label>
                <select
                  value={(form as any).label_size || '50x30mm'}
                  onChange={(e) => setForm({ ...form, label_size: e.target.value } as any)}
                  className="w-full rounded-md border border-border bg-bg-input px-2.5 py-1.5 text-xs text-text-primary"
                >
                  <option value="50x30mm">50 × 30 mm Thermal Die-Cut</option>
                  <option value="50x25mm">50 × 25 mm Compact</option>
                  <option value="40x30mm">40 × 30 mm Jewellery / Small Item</option>
                </select>
              </div>
            </div>

            <div className="pt-2 flex gap-2">
              <button
                type="button"
                onClick={async () => {
                  try {
                    const width = (form as any).receipt_width || '80mm';
                    await axios.post(`http://127.0.0.1:8000/api/printer/test-receipt?paper_width=${width}`);
                    toast.success(`Sent ${width} test receipt directly to printer!`);
                  } catch (err: any) {
                    toast.error(`Direct print failed: ${err?.response?.data?.detail || err.message}`);
                  }
                }}
                className="w-full rounded-md border border-border py-1.5 text-xs font-medium text-text-primary hover:border-accent hover:text-accent transition-colors flex items-center justify-center gap-1.5"
              >
                🖨️ Test {(form as any).receipt_width || '80mm'} Receipt (Direct)
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Export Store Data */}
      <div className="rounded-xl border border-border bg-bg-card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Database className="h-4 w-4 text-accent" /> Export Store Data (Backup)
            </h3>
            <p className="mt-1 text-xs text-text-muted">
              Download all your Products, Invoices, Customers, and Settings directly from Supabase to your laptop as a JSON backup file.
            </p>
          </div>
          <button 
            type="button"
            onClick={handleExportData} 
            disabled={backingUp} 
            className="flex items-center justify-center gap-2 rounded-lg bg-accent/10 border border-accent/30 text-accent px-4 py-2 text-sm font-medium hover:bg-accent hover:text-white transition-all disabled:opacity-50 shrink-0"
          >
            <Download className="h-4 w-4" /> {backingUp ? 'Exporting...' : 'Export to Laptop'}
          </button>
        </div>
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
