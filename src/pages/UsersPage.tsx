import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Plus, Search, Shield, UserCog, Eye, Mail, Edit3, Trash2, Check, X } from 'lucide-react';
import { Button, Card, CardHeader, Badge, EmptyState, Skeleton, Input, Modal, useToast, Avatar } from '../components/ui';
import { cn } from '../lib/cn';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'Admin' | 'Member' | 'Viewer';
  skills: number;
  lastActive: string;
  status: 'active' | 'inactive';
}

const MOCK_USERS: User[] = [
  { id: '1', name: 'Sarah Chen', email: 'sarah@example.com', role: 'Admin', skills: 12, lastActive: '2026-04-04', status: 'active' },
  { id: '2', name: 'Mike Johnson', email: 'mike@example.com', role: 'Member', skills: 8, lastActive: '2026-04-03', status: 'active' },
  { id: '3', name: 'Emily Davis', email: 'emily@example.com', role: 'Member', skills: 5, lastActive: '2026-04-02', status: 'active' },
  { id: '4', name: 'Alex Rivera', email: 'alex@example.com', role: 'Viewer', skills: 2, lastActive: '2026-03-28', status: 'active' },
  { id: '5', name: 'Jordan Lee', email: 'jordan@example.com', role: 'Member', skills: 7, lastActive: '2026-03-25', status: 'inactive' },
  { id: '6', name: 'Taylor Kim', email: 'taylor@example.com', role: 'Viewer', skills: 1, lastActive: '2026-03-20', status: 'inactive' },
];

const roleBadgeVariant: Record<string, 'default' | 'info' | 'secondary'> = {
  Admin: 'default',
  Member: 'info',
  Viewer: 'secondary',
};

export function UsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'Member' | 'Viewer'>('Member');
  const [editingUser, setEditingUser] = useState<User | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => { setUsers(MOCK_USERS); setLoading(false); }, 400);
    return () => clearTimeout(timer);
  }, []);

  const filteredUsers = users.filter((u) =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  );

  const handleInvite = () => {
    if (!inviteEmail.trim()) return;
    const newUser: User = {
      id: `u_${Date.now()}`,
      name: inviteEmail.split('@')[0],
      email: inviteEmail.trim(),
      role: inviteRole,
      skills: 0,
      lastActive: new Date().toISOString().split('T')[0],
      status: 'active',
    };
    setUsers((prev) => [newUser, ...prev]);
    setInviteModalOpen(false);
    setInviteEmail('');
    toast('success', `Invitation sent to ${inviteEmail}`);
  };

  const handleRoleChange = (userId: string, newRole: User['role']) => {
    setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: newRole } : u));
    toast('success', 'Role updated');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" width={160} height={28} />
        <div className="flex gap-3"><Skeleton variant="rectangular" width={240} height={36} /><Skeleton variant="rectangular" width={120} height={36} /></div>
        <Card padding="none">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="px-5 py-4"><Skeleton variant="text" width="60%" height={14} /></div>)}</Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Users</h1>
          <p className="text-sm text-muted mt-1">{users.length} users in your organization</p>
        </div>
        <Button icon={<Plus className="w-4 h-4" />} onClick={() => setInviteModalOpen(true)}>Invite User</Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Search users"
          />
        </div>
      </div>

      <Card padding="none">
        {filteredUsers.length === 0 ? (
          <EmptyState icon={<UserCog className="w-8 h-8" />} title="No users found" description="Try adjusting your search." />
        ) : (
          <div className="divide-y divide-border">
            {filteredUsers.map((user, i) => (
              <motion.div
                key={user.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-center justify-between px-5 py-4 hover:bg-surface/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Avatar initials={user.name.split(' ').map(n => n[0]).join('')} alt={user.name} size="md" status={user.status === 'active' ? 'online' : 'offline'} />
                  <div>
                    <p className="text-sm font-medium text-foreground">{user.name}</p>
                    <p className="text-xs text-muted">{user.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="hidden sm:block text-center">
                    <p className="text-sm font-medium text-foreground">{user.skills}</p>
                    <p className="text-[10px] text-muted">Skills</p>
                  </div>
                  <div className="hidden md:block text-center">
                    <p className="text-xs text-muted">{new Date(user.lastActive).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</p>
                    <p className="text-[10px] text-muted">Active</p>
                  </div>
                  <Badge variant={roleBadgeVariant[user.role]} size="sm">{user.role}</Badge>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setEditingUser(user)}
                      className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface transition-colors"
                      aria-label={`Edit ${user.name}`}
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </Card>

      {/* Invite Modal */}
      <Modal
        isOpen={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        title="Invite User"
        subtitle="Send an invitation to join your organization"
        footer={
          <>
            <Button variant="secondary" onClick={() => setInviteModalOpen(false)}>Cancel</Button>
            <Button icon={<Mail className="w-4 h-4" />} onClick={handleInvite} disabled={!inviteEmail.trim()}>Send Invite</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="user@example.com"
            autoFocus
          />
          <div>
            <label className="text-sm font-medium text-foreground mb-2 block">Role</label>
            <div className="flex gap-2">
              {(['Member', 'Viewer'] as const).map((role) => (
                <button
                  key={role}
                  onClick={() => setInviteRole(role)}
                  className={cn(
                    'flex-1 flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors',
                    inviteRole === role
                      ? 'border-primary bg-primary-lighter text-primary'
                      : 'border-border bg-surface text-muted hover:border-border-hover',
                  )}
                >
                  {inviteRole === role && <Check className="w-4 h-4" />}
                  {role}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Modal>

      {/* Edit Role Modal */}
      <Modal
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
        title="Edit User Role"
        subtitle={editingUser?.name}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingUser(null)}>Cancel</Button>
            <Button onClick={() => { if (editingUser) { handleRoleChange(editingUser.id, editingUser.role); setEditingUser(null); } }}>Save</Button>
          </>
        }
      >
        {editingUser && (
          <div className="space-y-2">
            {(['Admin', 'Member', 'Viewer'] as const).map((role) => (
              <button
                key={role}
                onClick={() => setEditingUser({ ...editingUser, role })}
                className={cn(
                  'w-full flex items-center justify-between px-4 py-3 rounded-lg border text-sm transition-colors',
                  editingUser.role === role
                    ? 'border-primary bg-primary-lighter text-primary'
                    : 'border-border text-muted hover:border-border-hover',
                )}
              >
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  <span className="font-medium">{role}</span>
                </div>
                {editingUser.role === role && <Check className="w-4 h-4" />}
              </button>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
