import { useEffect, useState } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';
import { UserPlus, X, Shield, ShieldCheck, Warehouse as WarehouseIcon } from 'lucide-react';
import Pagination from '../components/Pagination';

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: '', username: '', email: '', password: '', role: 'staff' });

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const fetchUsers = async () => { try { const res = await api.get('/users'); setUsers(res.data); setCurrentPage(1); } catch {} };
  useEffect(() => { fetchUsers(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/users', form);
      toast.success('User created');
      setShowModal(false);
      setForm({ name: '', username: '', email: '', password: '', role: 'staff' });
      fetchUsers();
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const toggleStatus = async (user: any) => {
    try {
      await api.put(`/users/${user.id}`, { status: user.status === 'active' ? 'inactive' : 'active' });
      toast.success(`User ${user.status === 'active' ? 'deactivated' : 'activated'}`);
      fetchUsers();
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const roleIcon = (role: string) => {
    if (role === 'admin') return <ShieldCheck className="h-4 w-4 text-accent" />;
    if (role === 'inventory') return <WarehouseIcon className="h-4 w-4 text-warning" />;
    return <Shield className="h-4 w-4 text-success" />;
  };

  const totalPages = Math.ceil(users.length / itemsPerPage);
  const paginatedUsers = users.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Users & Roles</h1>
          <p className="text-sm text-text-muted">{users.length} users</p>
        </div>
        <button onClick={() => setShowModal(true)} className="bg-gradient-to-br from-indigo-600 to-indigo-500 flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25"><UserPlus className="h-4 w-4" /> Add User</button>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-bg-card">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-bg-secondary/50">
            <tr className="text-text-muted">
              <th className="px-4 py-3 text-left font-medium">Name</th>
              <th className="px-4 py-3 text-left font-medium">Username</th>
              <th className="px-4 py-3 text-left font-medium">Email</th>
              <th className="px-4 py-3 text-center font-medium">Role</th>
              <th className="px-4 py-3 text-center font-medium">Status</th>
              <th className="px-4 py-3 text-center font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {paginatedUsers.map((u: any) => (
              <tr key={u.id} className="border-b border-border/30 hover:bg-bg-hover/50">
                <td className="px-4 py-3 font-medium text-text-primary">{u.name}</td>
                <td className="px-4 py-3 text-text-muted font-mono text-xs">{u.username}</td>
                <td className="px-4 py-3 text-text-muted">{u.email || '-'}</td>
                <td className="px-4 py-3 text-center"><span className="inline-flex items-center gap-1 rounded-full bg-bg-hover px-2.5 py-1 text-xs font-medium text-text-primary capitalize">{roleIcon(u.role)} {u.role}</span></td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${u.status === 'active' ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'}`}>{u.status}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => toggleStatus(u)} className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${u.status === 'active' ? 'text-danger hover:bg-danger/10' : 'text-success hover:bg-success/10'}`}>
                    {u.status === 'active' ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination 
          currentPage={currentPage} 
          totalPages={totalPages} 
          onPageChange={setCurrentPage} 
          totalItems={users.length} 
          itemsPerPage={itemsPerPage} 
        />
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="animate-scale-in w-full max-w-md rounded-2xl border border-border bg-bg-card p-6 shadow-modal">
            <div className="mb-5 flex items-center justify-between"><h3 className="text-lg font-bold text-text-primary">Add User</h3><button type="button" onClick={() => setShowModal(false)} className="rounded-lg p-1 text-text-muted hover:text-text-primary"><X className="h-5 w-5" /></button></div>
            <div className="space-y-4">
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Full Name *</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Username *</label><input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Email</label><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Password *</label><input required type="password" minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary" /></div>
              <div><label className="mb-1 block text-xs font-medium text-text-secondary">Role</label><select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-full rounded-lg border border-border bg-bg-input px-3 py-2.5 text-sm text-text-primary"><option value="staff">Billing Staff</option><option value="inventory">Inventory Staff</option><option value="admin">Administrator</option></select></div>
            </div>
            <div className="mt-6 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowModal(false)} className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-text-muted">Cancel</button>
              <button type="submit" className="bg-gradient-to-br from-indigo-600 to-indigo-500 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-accent/25">Create User</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
