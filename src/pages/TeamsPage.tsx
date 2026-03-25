import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Plus, Search, Users, UserCog, Edit3, Trash2, ArrowRight } from 'lucide-react';
import { Button, Card, CardHeader, Badge, EmptyState, Skeleton, Modal, useToast, Avatar } from '../components/ui';

interface Team {
  id: string;
  name: string;
  description: string;
  members: number;
  skills: string[];
  createdAt: string;
}

const MOCK_TEAMS: Team[] = [
  { id: '1', name: 'Data Engineering', description: 'Builds and maintains data pipelines and infrastructure', members: 8, skills: ['SQL Optimizer', 'ETL Pipeline Builder', 'Data Architect'], createdAt: '2025-09-15' },
  { id: '2', name: 'Analytics', description: 'Business intelligence and reporting team', members: 12, skills: ['Analytics Engineer', 'Data Explorer', 'Warehouse Monitor'], createdAt: '2025-10-01' },
  { id: '3', name: 'ML Research', description: 'Machine learning model development and research', members: 5, skills: ['ML Engineer', 'Data Quality Engineer'], createdAt: '2025-11-20' },
  { id: '4', name: 'Security', description: 'Data security, compliance, and access management', members: 3, skills: ['Security Auditor'], createdAt: '2026-01-10' },
];

export function TeamsPage() {
  const { toast } = useToast();
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDesc, setNewTeamDesc] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => { setTeams(MOCK_TEAMS); setLoading(false); }, 400);
    return () => clearTimeout(timer);
  }, []);

  const filteredTeams = teams.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.description.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = () => {
    if (!newTeamName.trim()) return;
    const newTeam: Team = {
      id: `t_${Date.now()}`,
      name: newTeamName.trim(),
      description: newTeamDesc.trim(),
      members: 0,
      skills: [],
      createdAt: new Date().toISOString().split('T')[0],
    };
    setTeams((prev) => [newTeam, ...prev]);
    setCreateModalOpen(false);
    setNewTeamName('');
    setNewTeamDesc('');
    toast('success', `Team "${newTeam.name}" created`);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" width={160} height={28} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height={160} className="rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Teams</h1>
          <p className="text-sm text-muted mt-1">{teams.length} teams in your organization</p>
        </div>
        <Button icon={<Plus className="w-4 h-4" />} onClick={() => setCreateModalOpen(true)}>Create Team</Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search teams..."
          className="w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          aria-label="Search teams"
        />
      </div>

      {filteredTeams.length === 0 ? (
        <EmptyState
          icon={<Users className="w-8 h-8" />}
          title="No teams found"
          description="Create a team to start organizing your users."
          action={<Button icon={<Plus className="w-4 h-4" />} onClick={() => setCreateModalOpen(true)}>Create Team</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredTeams.map((team, i) => (
            <motion.div
              key={team.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card hover interactive>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary-light text-primary">
                      <Users className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">{team.name}</h3>
                      <p className="text-xs text-muted mt-0.5">{team.description}</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 text-xs text-muted">
                      <UserCog className="w-3.5 h-3.5" />
                      {team.members} members
                    </span>
                    <span className="flex items-center gap-1 text-xs text-muted">
                      <ArrowRight className="w-3.5 h-3.5" />
                      {team.skills.length} skills
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface transition-colors" aria-label="Edit team">
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 rounded-md text-muted hover:text-error hover:bg-error-light/50 transition-colors" aria-label="Delete team">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {team.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {team.skills.map((skill) => (
                      <Badge key={skill} variant="outline" size="sm">{skill}</Badge>
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Team"
        subtitle="Add a new team to your organization"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!newTeamName.trim()}>Create Team</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">Team Name</label>
            <input
              type="text"
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              placeholder="e.g., Data Engineering"
              className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              autoFocus
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">Description</label>
            <textarea
              value={newTeamDesc}
              onChange={(e) => setNewTeamDesc(e.target.value)}
              placeholder="Describe the team's purpose..."
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 resize-none"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
