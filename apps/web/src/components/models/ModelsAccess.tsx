import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Search, Brain, Check, Lock, Unlock, Shield, Zap, Globe, Sparkles } from 'lucide-react';
import { useAuth } from '../../auth';
import { Card, StatusBadge, EmptyState, Tabs } from '../common';
import { useToast } from '../common';

interface ModelInfo {
  modelId: string;
  modelName: string;
  provider: string;
  description: string;
  tier: 'free' | 'standard' | 'premium';
  adminAccess: boolean;
  userAccess: boolean;
  usersWithAccess: number;
  contextWindow?: string;
  speed?: 'fast' | 'medium' | 'slow';
}

const MOCK_MODELS: ModelInfo[] = [
  { modelId: 'm1', modelName: 'Gemini 2.0 Flash', provider: 'Google AI Studio', description: 'Fast, free-tier Gemini model optimized for everyday tasks with low latency', tier: 'free', adminAccess: true, userAccess: true, usersWithAccess: 2, contextWindow: '1M', speed: 'fast' },
  { modelId: 'm2', modelName: 'Gemini 1.5 Flash', provider: 'Google AI Studio', description: 'Balanced speed and quality for mid-complexity reasoning tasks', tier: 'standard', adminAccess: true, userAccess: true, usersWithAccess: 1, contextWindow: '1M', speed: 'fast' },
  { modelId: 'm3', modelName: 'Gemini 1.5 Pro', provider: 'Google AI Studio', description: 'Highest quality Gemini model for complex multi-step reasoning', tier: 'premium', adminAccess: true, userAccess: false, usersWithAccess: 1, contextWindow: '2M', speed: 'medium' },
  { modelId: 'm4', modelName: 'GPT-4o-mini', provider: 'OpenAI', description: 'Efficient OpenAI model for quick, cost-effective responses', tier: 'standard', adminAccess: true, userAccess: true, usersWithAccess: 2, contextWindow: '128K', speed: 'fast' },
  { modelId: 'm5', modelName: 'GPT-4.1', provider: 'OpenAI', description: 'Latest full-capability GPT model with enhanced reasoning', tier: 'premium', adminAccess: true, userAccess: false, usersWithAccess: 1, contextWindow: '1M', speed: 'medium' },
  { modelId: 'm6', modelName: 'GPT-4.1-mini', provider: 'OpenAI', description: 'Compact version of GPT-4.1 for faster inference at lower cost', tier: 'standard', adminAccess: true, userAccess: false, usersWithAccess: 1, contextWindow: '1M', speed: 'fast' },
  { modelId: 'm7', modelName: 'o3-mini', provider: 'OpenAI', description: 'Reasoning-optimized model for structured analytical tasks', tier: 'premium', adminAccess: true, userAccess: false, usersWithAccess: 1, contextWindow: '200K', speed: 'slow' },
];

const tierConfig = {
  free: { label: 'Free', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: Globe },
  standard: { label: 'Standard', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Zap },
  premium: { label: 'Premium', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: Sparkles },
};

const speedBadge = {
  fast: { label: 'Fast', color: 'text-emerald-600' },
  medium: { label: 'Medium', color: 'text-amber-600' },
  slow: { label: 'Deliberate', color: 'text-blue-600' },
};

export function ModelsAccess() {
  const { permissions } = useAuth();
  const { toast } = useToast();
  const isAdmin = permissions.manageModels;

  const [models, setModels] = useState<ModelInfo[]>(MOCK_MODELS);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTier, setFilterTier] = useState<'all' | 'free' | 'standard' | 'premium'>('all');

  const filteredModels = models.filter((m) => {
    const matchesSearch = m.modelName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.provider.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTier = filterTier === 'all' || m.tier === filterTier;
    return matchesSearch && matchesTier;
  });

  const visibleModels = isAdmin ? filteredModels : filteredModels.filter((m) => m.userAccess);

  const toggleUserAccess = (modelId: string) => {
    const model = models.find((m) => m.modelId === modelId);
    setModels(models.map((m) =>
      m.modelId === modelId
        ? { ...m, userAccess: !m.userAccess, usersWithAccess: m.userAccess ? m.usersWithAccess - 1 : m.usersWithAccess + 1 }
        : m,
    ));
    toast('success', `${model?.modelName} user access ${model?.userAccess ? 'revoked' : 'granted'}`);
  };

  const accessibleCount = models.filter((m) => m.userAccess).length;
  const totalCount = models.length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-main)]">
            {isAdmin ? 'Model Access' : 'Available Models'}
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {isAdmin ? 'Manage AI model access across your organization' : 'AI models available for your workspace'}
          </p>
        </div>
        {isAdmin && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg text-xs font-medium text-blue-700">
            <Brain className="w-3.5 h-3.5" />
            {accessibleCount}/{totalCount} user-accessible
          </div>
        )}
      </motion.div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-light)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search models..."
            className="w-full pl-9 pr-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-sm text-[var(--color-text-main)] placeholder:text-[var(--color-text-light)] focus:outline-none focus:border-[var(--color-accent)] focus:bg-white focus:ring-2 focus:ring-[var(--color-accent)]/10 transition-all"
          />
        </div>
        <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-0.5">
          {(['all', 'free', 'standard', 'premium'] as const).map((tier) => (
            <button
              key={tier}
              onClick={() => setFilterTier(tier)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                filterTier === tier
                  ? 'bg-white text-[var(--color-text-main)] shadow-sm'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'
              }`}
            >
              {tier.charAt(0).toUpperCase() + tier.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Models Grid */}
      {visibleModels.length === 0 ? (
        <EmptyState icon={<Brain className="w-8 h-8" />} title="No models found" message="No AI models match your search or filter criteria." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {visibleModels.map((model, i) => {
            const tier = tierConfig[model.tier];
            const TierIcon = tier.icon;
            const speed = model.speed ? speedBadge[model.speed] : null;
            return (
              <motion.div
                key={model.modelId}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.35 }}
              >
                <Card hover className="h-full flex flex-col group/card">
                  <div className="flex items-start justify-between mb-4">
                    <div className={`w-11 h-11 rounded-xl ${tier.bg} flex items-center justify-center transition-transform group-hover/card:scale-110`}>
                      <Brain className={`w-5 h-5 ${tier.text}`} />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${tier.bg} ${tier.text}`}>
                        <TierIcon className="w-3 h-3" />
                        {tier.label}
                      </span>
                    </div>
                  </div>

                  <h4 className="text-sm font-bold text-[var(--color-text-main)] mb-0.5">{model.modelName}</h4>
                  <p className="text-[11px] text-[var(--color-text-muted)] mb-1.5">{model.provider}</p>
                  <p className="text-xs text-[var(--color-text-muted)] leading-relaxed mb-4 flex-1">{model.description}</p>

                  {/* Specs */}
                  <div className="flex items-center gap-3 mb-4">
                    {model.contextWindow && (
                      <div className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] bg-[var(--color-surface)] px-2 py-1 rounded-md">
                        <span className="font-mono font-medium">{model.contextWindow}</span>
                        <span>context</span>
                      </div>
                    )}
                    {speed && (
                      <div className={`flex items-center gap-1 text-[10px] font-medium ${speed.color} bg-[var(--color-surface)] px-2 py-1 rounded-md`}>
                        <Zap className="w-3 h-3" />
                        {speed.label}
                      </div>
                    )}
                  </div>

                  {/* Access controls */}
                  <div className="pt-3 border-t border-[var(--color-border)]">
                    {isAdmin ? (
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[var(--color-text-muted)]">
                          <span className="font-mono font-medium text-[var(--color-text-main)]">{model.usersWithAccess}</span> users
                        </span>
                        <button
                          onClick={() => toggleUserAccess(model.modelId)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            model.userAccess
                              ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
                              : 'bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200'
                          }`}
                        >
                          {model.userAccess ? <><Unlock className="w-3 h-3" /> User Access</> : <><Lock className="w-3 h-3" /> Admin Only</>}
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
                        <Check className="w-3.5 h-3.5" />
                        Accessible in your workspace
                      </div>
                    )}
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
