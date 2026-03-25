import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Search, Brain, Check, Lock, Unlock, Zap, Globe, Sparkles, RefreshCw, AlertCircle, Plus, SlidersHorizontal, ShieldCheck, Link2, Trash2, Pencil, Cpu } from 'lucide-react';
import { useAuth } from '../../auth';
import { Card, StatusBadge, EmptyState, Skeleton, Button, Modal } from '../common';
import { useToast } from '../common';
import { adminApi, type ModelAccessControl } from '../../services/governanceApi';
import {
  createModelConfiguration,
  createSecretReference,
  deleteModelConfiguration,
  listModelConfigurations,
  listSecretReferences,
  updateModelConfiguration,
  validateModelConfiguration,
  type ModelConfigurationItem,
  type SecretReferenceItem,
} from '../../services/backendApi';
import { getUserFacingError } from '../../services/errorUtils';

interface ModelInfo {
  modelId: string;
  modelName: string;
  provider: string;
  description: string;
  tier: 'free' | 'standard' | 'premium';
  userAccess: boolean;
  contextWindow: string;
  speed: 'fast' | 'medium' | 'slow';
  maxTokens: number;
  rateLimit: number;
}

const MODEL_METADATA: Record<string, { provider: string; description: string; tier: 'free' | 'standard' | 'premium'; contextWindow: string; speed: 'fast' | 'medium' | 'slow' }> = {
  'gemini-2.0-flash': { provider: 'Google AI Studio', description: 'Fast, free-tier Gemini model optimized for everyday tasks', tier: 'free', contextWindow: '1M', speed: 'fast' },
  'gemini-1.5-flash': { provider: 'Google AI Studio', description: 'Balanced speed and quality for mid-complexity reasoning', tier: 'standard', contextWindow: '1M', speed: 'fast' },
  'gemini-1.5-pro': { provider: 'Google AI Studio', description: 'Highest quality Gemini for complex multi-step reasoning', tier: 'premium', contextWindow: '2M', speed: 'medium' },
  'gpt-4o-mini': { provider: 'OpenAI', description: 'Efficient OpenAI model for quick, cost-effective responses', tier: 'standard', contextWindow: '128K', speed: 'fast' },
  'gpt-4.1': { provider: 'OpenAI', description: 'Latest full-capability GPT model with enhanced reasoning', tier: 'premium', contextWindow: '1M', speed: 'medium' },
  'gpt-4.1-mini': { provider: 'OpenAI', description: 'Compact version of GPT-4.1 for faster inference', tier: 'standard', contextWindow: '1M', speed: 'fast' },
  'o3-mini': { provider: 'OpenAI', description: 'Reasoning-optimized model for structured analytical tasks', tier: 'premium', contextWindow: '200K', speed: 'slow' },
};

const tierConfig = {
  free: { label: 'Free', bg: 'bg-emerald-50', text: 'text-emerald-700', icon: Globe },
  standard: { label: 'Standard', bg: 'bg-blue-50', text: 'text-blue-700', icon: Zap },
  premium: { label: 'Premium', bg: 'bg-purple-50', text: 'text-purple-700', icon: Sparkles },
};

const speedBadge = {
  fast: { label: 'Fast', color: 'text-emerald-600' },
  medium: { label: 'Medium', color: 'text-amber-600' },
  slow: { label: 'Deliberate', color: 'text-blue-600' },
};

const TEMPERATURE_MIN = 0;
const TEMPERATURE_MAX = 2;
const MAX_TOKENS_MIN = 1;
const MAX_TOKENS_MAX = 100000;
const MAX_TOKENS_SOFT_WARNING = 32768;
const MAX_TOKENS_STRONG_WARNING = 65536;
const TIMEOUT_MIN = 1;
const TIMEOUT_MAX = 300;

function isValidHttpUrl(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function mapToModelInfo(config: ModelAccessControl): ModelInfo {
  const meta = MODEL_METADATA[config.model_id] || {
    provider: 'Unknown',
    description: config.model_id,
    tier: 'standard' as const,
    contextWindow: '—',
    speed: 'medium' as const,
  };
  return {
    modelId: config.model_id,
    modelName: config.model_id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    provider: meta.provider,
    description: meta.description,
    tier: meta.tier,
    userAccess: config.enabled && config.allowed_roles.includes('user'),
    contextWindow: meta.contextWindow,
    speed: meta.speed,
    maxTokens: config.max_tokens_per_request,
    rateLimit: config.rate_limit_per_minute,
  };
}

export function ModelsAccess() {
  const { permissions } = useAuth();
  const { toast } = useToast();
  const isAdmin = permissions.manageModels;

  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTier, setFilterTier] = useState<'all' | 'free' | 'standard' | 'premium'>('all');
  const [toggling, setToggling] = useState<string | null>(null);
  const [savingConfig, setSavingConfig] = useState(false);
  const [savingSecret, setSavingSecret] = useState(false);
  const [validatingConfigId, setValidatingConfigId] = useState<string | null>(null);
  const [deletingConfigId, setDeletingConfigId] = useState<string | null>(null);

  const [configs, setConfigs] = useState<ModelConfigurationItem[]>([]);
  const [secrets, setSecrets] = useState<SecretReferenceItem[]>([]);

  const [secretModalOpen, setSecretModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ModelConfigurationItem | null>(null);

  const [secretForm, setSecretForm] = useState({
    reference_key: '',
    provider: '',
    secret_value: '',
  });

  const [configForm, setConfigForm] = useState({
    model_id: '',
    provider: '',
    base_url: '',
    secret_reference_key: '',
    temperature: '0.2',
    max_tokens: '2048',
    request_timeout_seconds: '30',
    parameters: '{}',
    is_active: true,
  });

  const resetSecretForm = () => {
    setSecretForm({ reference_key: '', provider: '', secret_value: '' });
  };

  const resetConfigForm = () => {
    setConfigForm({
      model_id: '',
      provider: '',
      base_url: '',
      secret_reference_key: '',
      temperature: '0.2',
      max_tokens: '2048',
      request_timeout_seconds: '30',
      parameters: '{}',
      is_active: true,
    });
  };

  const loadAdminConfig = async () => {
    if (!isAdmin) return;
    try {
      const [secretRows, configRows] = await Promise.all([
        listSecretReferences(),
        listModelConfigurations(),
      ]);
      setSecrets(secretRows);
      setConfigs(configRows);
    } catch (err) {
      toast('error', getUserFacingError(err, 'Failed to load model configuration data'));
    }
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const { configs } = await adminApi.listModelAccess();
      setModels(configs.map(mapToModelInfo));
      await loadAdminConfig();
    } catch (err) {
      setError(getUserFacingError(err, 'Failed to load models'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    if (!configModalOpen && !editingConfig) {
      resetConfigForm();
    }
  }, [configModalOpen, editingConfig]);

  const openCreateConfigModal = () => {
    setEditingConfig(null);
    resetConfigForm();
    setConfigModalOpen(true);
  };

  const openEditConfigModal = (row: ModelConfigurationItem) => {
    setEditingConfig(row);
    setConfigForm({
      model_id: row.model_id,
      provider: row.provider,
      base_url: row.base_url,
      secret_reference_key: row.secret_reference_key,
      temperature: String(row.temperature),
      max_tokens: String(row.max_tokens),
      request_timeout_seconds: String(row.request_timeout_seconds),
      parameters: JSON.stringify(row.parameters || {}, null, 2),
      is_active: row.is_active,
    });
    setConfigModalOpen(true);
  };

  const handleCreateSecret = async () => {
    if (!secretForm.reference_key.trim() || !secretForm.provider.trim() || !secretForm.secret_value.trim()) {
      toast('warning', 'Reference key, provider, and secret value are required.');
      return;
    }

    setSavingSecret(true);
    try {
      await createSecretReference({
        reference_key: secretForm.reference_key.trim(),
        provider: secretForm.provider.trim(),
        secret_value: secretForm.secret_value,
      });
      toast('success', 'Secret reference saved.');
      setSecretModalOpen(false);
      resetSecretForm();
      await loadAdminConfig();
    } catch (err) {
      toast('error', getUserFacingError(err, 'Failed to save secret reference'));
    } finally {
      setSavingSecret(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!isConfigFormValid) {
      const firstError = Object.values(configValidationErrors).find((msg) => Boolean(msg));
      toast('warning', firstError || 'Please fix invalid configuration values.');
      return;
    }

    let parsedParameters: Record<string, unknown> = {};
    if (configForm.parameters.trim()) {
      try {
        parsedParameters = JSON.parse(configForm.parameters);
      } catch {
        toast('warning', 'Parameters must be valid JSON.');
        return;
      }
    }

    const payload = {
      model_id: configForm.model_id.trim(),
      provider: configForm.provider.trim(),
      base_url: configForm.base_url.trim(),
      secret_reference_key: configForm.secret_reference_key.trim(),
      temperature: Number(configForm.temperature),
      max_tokens: Number(configForm.max_tokens),
      request_timeout_seconds: Number(configForm.request_timeout_seconds),
      parameters: parsedParameters,
    };

    setSavingConfig(true);
    try {
      if (editingConfig) {
        await updateModelConfiguration(editingConfig.id, {
          base_url: payload.base_url,
          secret_reference_key: payload.secret_reference_key,
          temperature: payload.temperature,
          max_tokens: payload.max_tokens,
          request_timeout_seconds: payload.request_timeout_seconds,
          parameters: payload.parameters,
          is_active: configForm.is_active,
        });
        toast('success', 'Model configuration updated.');
      } else {
        await createModelConfiguration(payload);
        toast('success', 'Model configuration created.');
      }
      setConfigModalOpen(false);
      setEditingConfig(null);
      resetConfigForm();
      await loadAdminConfig();
    } catch (err) {
      toast('error', getUserFacingError(err, 'Failed to save model configuration'));
    } finally {
      setSavingConfig(false);
    }
  };

  const handleValidateConfig = async (cfg: ModelConfigurationItem) => {
    setValidatingConfigId(cfg.id);
    try {
      const result = await validateModelConfiguration({
        provider: cfg.provider,
        base_url: cfg.base_url,
        secret_reference_key: cfg.secret_reference_key,
      });
      toast(result.valid ? 'success' : 'warning', `${cfg.model_id}: ${result.message}`);
    } catch (err) {
      toast('error', getUserFacingError(err, 'Connectivity validation failed'));
    } finally {
      setValidatingConfigId(null);
    }
  };

  const handleDeleteConfig = async (cfg: ModelConfigurationItem) => {
    setDeletingConfigId(cfg.id);
    try {
      await deleteModelConfiguration(cfg.id);
      toast('success', `${cfg.model_id} configuration deleted.`);
      await loadAdminConfig();
    } catch (err) {
      toast('error', getUserFacingError(err, 'Failed to delete configuration'));
    } finally {
      setDeletingConfigId(null);
    }
  };

  const filteredModels = models.filter((m) => {
    const matchesSearch = m.modelName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.provider.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTier = filterTier === 'all' || m.tier === filterTier;
    return matchesSearch && matchesTier;
  });

  const visibleModels = isAdmin ? filteredModels : filteredModels.filter((m) => m.userAccess);

  const parsedTemperature = Number(configForm.temperature);
  const parsedMaxTokens = Number(configForm.max_tokens);
  const parsedTimeout = Number(configForm.request_timeout_seconds);

  const configValidationErrors = {
    model_id: configForm.model_id.trim() ? '' : 'Model ID is required.',
    provider: configForm.provider.trim() ? '' : 'Provider is required.',
    base_url: configForm.base_url.trim()
      ? (isValidHttpUrl(configForm.base_url) ? '' : 'Base URL must be a valid http/https URL.')
      : 'Base URL is required.',
    secret_reference_key: configForm.secret_reference_key.trim() ? '' : 'Secret reference key is required.',
    temperature:
      Number.isFinite(parsedTemperature) && parsedTemperature >= TEMPERATURE_MIN && parsedTemperature <= TEMPERATURE_MAX
        ? ''
        : `Temperature must be between ${TEMPERATURE_MIN} and ${TEMPERATURE_MAX}.`,
    max_tokens:
      Number.isInteger(parsedMaxTokens) && parsedMaxTokens >= MAX_TOKENS_MIN && parsedMaxTokens <= MAX_TOKENS_MAX
        ? ''
        : `Max tokens must be an integer between ${MAX_TOKENS_MIN} and ${MAX_TOKENS_MAX}.`,
    request_timeout_seconds:
      Number.isInteger(parsedTimeout) && parsedTimeout >= TIMEOUT_MIN && parsedTimeout <= TIMEOUT_MAX
        ? ''
        : `Timeout must be an integer between ${TIMEOUT_MIN} and ${TIMEOUT_MAX} seconds.`,
    parameters: (() => {
      if (!configForm.parameters.trim()) return '';
      try {
        JSON.parse(configForm.parameters);
        return '';
      } catch {
        return 'Parameters must be valid JSON.';
      }
    })(),
  };

  const isConfigFormValid = Object.values(configValidationErrors).every((value) => !value);
  const showHighTokenSoftWarning =
    Number.isInteger(parsedMaxTokens)
    && parsedMaxTokens > MAX_TOKENS_SOFT_WARNING
    && parsedMaxTokens <= MAX_TOKENS_MAX;
  const showVeryHighTokenSoftWarning =
    Number.isInteger(parsedMaxTokens)
    && parsedMaxTokens > MAX_TOKENS_STRONG_WARNING
    && parsedMaxTokens <= MAX_TOKENS_MAX;

  const toggleUserAccess = async (modelId: string) => {
    setToggling(modelId);
    const model = models.find((m) => m.modelId === modelId);
    if (!model) return;
    try {
      await adminApi.setModelAccess({
        model_id: modelId,
        enabled: !model.userAccess,
        allowed_roles: model.userAccess ? ['admin'] : ['admin', 'user'],
        max_tokens_per_request: model.maxTokens,
        rate_limit_per_minute: model.rateLimit,
      });
      setModels(models.map((m) => m.modelId === modelId ? { ...m, userAccess: !m.userAccess } : m));
      toast('success', `${model.modelName} user access ${model.userAccess ? 'revoked' : 'granted'}`);
    } catch (err) {
      toast('error', getUserFacingError(err, 'Failed to update access'));
    } finally {
      setToggling(null);
    }
  };

  const accessibleCount = models.filter((m) => m.userAccess).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-main)]">
            {isAdmin ? 'Model Access' : 'Available Models'}
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {isAdmin ? 'Manage AI model access across your organization' : 'AI models available for your workspace'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadData} disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl transition-colors disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {isAdmin && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg text-xs font-medium text-blue-700">
              <Brain className="w-3.5 h-3.5" />
              {accessibleCount}/{models.length} user-accessible
            </div>
          )}
        </div>
      </motion.div>

      {/* Error */}
      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={loadData} className="ml-auto text-xs font-medium text-red-600 hover:text-red-700 underline">Retry</button>
        </motion.div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-light)]" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search models..."
            className="w-full pl-9 pr-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-sm text-[var(--color-text-main)] placeholder:text-[var(--color-text-light)] focus:outline-none focus:border-[var(--color-accent)] focus:bg-white focus:ring-2 focus:ring-[var(--color-accent)]/10 transition-all" />
        </div>
        <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-0.5">
          {(['all', 'free', 'standard', 'premium'] as const).map((tier) => (
            <button key={tier} onClick={() => setFilterTier(tier)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                filterTier === tier ? 'bg-white text-[var(--color-text-main)] shadow-sm' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'
              }`}>
              {tier.charAt(0).toUpperCase() + tier.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Models Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} padding="md">
              <div className="flex items-start justify-between mb-4">
                <Skeleton variant="rectangular" width={44} height={44} className="rounded-xl" />
                <Skeleton variant="rectangular" width={60} height={20} className="rounded-full" />
              </div>
              <Skeleton variant="text" width="70%" height={16} />
              <Skeleton variant="text" width="50%" height={12} className="mt-1" />
              <Skeleton variant="text" width="90%" height={12} className="mt-3" />
              <Skeleton variant="text" width="100%" height={1} className="mt-4" />
              <div className="flex justify-between mt-3">
                <Skeleton variant="text" width={80} height={14} />
                <Skeleton variant="rectangular" width={100} height={28} className="rounded-lg" />
              </div>
            </Card>
          ))}
        </div>
      ) : visibleModels.length === 0 ? (
        <EmptyState icon={<Brain className="w-8 h-8" />} title="No models found"
          message="No AI models match your search or filter criteria." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {visibleModels.map((model, i) => {
            const tier = tierConfig[model.tier];
            const TierIcon = tier.icon;
            const speed = speedBadge[model.speed];
            return (
              <motion.div key={model.modelId} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.35 }}>
                <Card hover className="h-full flex flex-col group/card">
                  <div className="flex items-start justify-between mb-4">
                    <div className={`w-11 h-11 rounded-xl ${tier.bg} flex items-center justify-center transition-transform group-hover/card:scale-110`}>
                      <Brain className={`w-5 h-5 ${tier.text}`} />
                    </div>
                    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${tier.bg} ${tier.text}`}>
                      <TierIcon className="w-3 h-3" /> {tier.label}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-[var(--color-text-main)] mb-0.5">{model.modelName}</h4>
                  <p className="text-[11px] text-[var(--color-text-muted)] mb-1.5">{model.provider}</p>
                  <p className="text-xs text-[var(--color-text-muted)] leading-relaxed mb-4 flex-1">{model.description}</p>

                  <div className="flex items-center gap-3 mb-4">
                    <div className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] bg-[var(--color-surface)] px-2 py-1 rounded-md">
                      <span className="font-mono font-medium">{model.contextWindow}</span><span>context</span>
                    </div>
                    <div className={`flex items-center gap-1 text-[10px] font-medium ${speed.color} bg-[var(--color-surface)] px-2 py-1 rounded-md`}>
                      <Zap className="w-3 h-3" /> {speed.label}
                    </div>
                    <div className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] bg-[var(--color-surface)] px-2 py-1 rounded-md">
                      <span className="font-mono font-medium">{(model.maxTokens / 1000).toFixed(0)}K</span><span>max</span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[var(--color-border)]">
                    {isAdmin ? (
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[var(--color-text-muted)]">
                          <span className="font-mono font-medium text-[var(--color-text-main)]">{model.rateLimit}</span>/min
                        </span>
                        <button
                          onClick={() => toggleUserAccess(model.modelId)}
                          disabled={toggling === model.modelId}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all disabled:opacity-50 ${
                            model.userAccess
                              ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
                              : 'bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200'
                          }`}
                        >
                          {toggling === model.modelId ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : model.userAccess ? (
                            <><Unlock className="w-3 h-3" /> User Access</>
                          ) : (
                            <><Lock className="w-3 h-3" /> Admin Only</>
                          )}
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
                        <Check className="w-3.5 h-3.5" /> Accessible in your workspace
                      </div>
                    )}
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {isAdmin && (
        <>
          <div className="pt-2">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[var(--color-text-main)] flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[var(--color-accent)]" /> Secret References
              </h3>
              <Button size="sm" variant="secondary" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setSecretModalOpen(true)}>
                Add Secret
              </Button>
            </div>

            {secrets.length === 0 ? (
              <Card>
                <EmptyState icon={<Link2 className="w-6 h-6" />} title="No secret references"
                  message="Create a secret reference before adding model configurations." />
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {secrets.map((secret) => (
                  <Card key={secret.reference_key} className="p-4">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="min-w-0">
                        <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wide">Reference</p>
                        <p className="text-sm font-semibold text-[var(--color-text-main)] truncate">{secret.reference_key}</p>
                      </div>
                      <StatusBadge status={secret.is_active ? 'active' : 'revoked'} label={secret.is_active ? 'active' : 'inactive'} />
                    </div>
                    <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
                      <span>{secret.provider}</span>
                      <span>{new Date(secret.created_at).toLocaleDateString()}</span>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          <div className="pt-2">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[var(--color-text-main)] flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[var(--color-accent)]" /> Model Configurations
              </h3>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="ghost" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={loadAdminConfig}>Reload</Button>
                <Button size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={openCreateConfigModal}>Create Config</Button>
              </div>
            </div>

            {configs.length === 0 ? (
              <Card>
                <EmptyState icon={<SlidersHorizontal className="w-6 h-6" />} title="No model configurations"
                  message="Create model configurations to define provider endpoints, secret references, and runtime parameters." />
              </Card>
            ) : (
              <div className="space-y-3">
                {configs.map((cfg) => (
                  <Card key={cfg.id} className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-[var(--color-text-main)]">{cfg.model_id}</p>
                          <StatusBadge status={cfg.is_active ? 'active' : 'revoked'} label={cfg.is_active ? 'active' : 'inactive'} />
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-[var(--color-surface)] text-[var(--color-text-muted)]">{cfg.provider}</span>
                        </div>
                        <p className="text-xs text-[var(--color-text-muted)] mt-1 truncate">{cfg.base_url}</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3 text-xs">
                          <div className="bg-[var(--color-surface)] rounded-lg px-2 py-1.5">
                            <p className="text-[var(--color-text-light)]">Secret</p>
                            <p className="font-mono text-[var(--color-text-main)] truncate">{cfg.secret_reference_key}</p>
                          </div>
                          <div className="bg-[var(--color-surface)] rounded-lg px-2 py-1.5">
                            <p className="text-[var(--color-text-light)]">Temp</p>
                            <p className="font-mono text-[var(--color-text-main)]">{cfg.temperature}</p>
                          </div>
                          <div className="bg-[var(--color-surface)] rounded-lg px-2 py-1.5">
                            <p className="text-[var(--color-text-light)]">Max Tokens</p>
                            <p className="font-mono text-[var(--color-text-main)]">{cfg.max_tokens}</p>
                          </div>
                          <div className="bg-[var(--color-surface)] rounded-lg px-2 py-1.5">
                            <p className="text-[var(--color-text-light)]">Timeout</p>
                            <p className="font-mono text-[var(--color-text-main)]">{cfg.request_timeout_seconds}s</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleValidateConfig(cfg)}
                          disabled={validatingConfigId === cfg.id}
                          className="p-2 text-[var(--color-text-light)] hover:text-[var(--color-accent)] hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Validate connectivity"
                        >
                          {validatingConfigId === cfg.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => openEditConfigModal(cfg)}
                          className="p-2 text-[var(--color-text-light)] hover:text-[var(--color-accent)] hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit configuration"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteConfig(cfg)}
                          disabled={deletingConfigId === cfg.id}
                          className="p-2 text-[var(--color-text-light)] hover:text-[var(--color-error)] hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Delete configuration"
                        >
                          {deletingConfigId === cfg.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <Modal
        isOpen={secretModalOpen}
        onClose={() => setSecretModalOpen(false)}
        title="Add Secret Reference"
        subtitle="Secrets are encrypted at rest and referenced by key in model configurations."
        footer={(
          <>
            <Button variant="ghost" onClick={() => setSecretModalOpen(false)}>Cancel</Button>
            <Button loading={savingSecret} onClick={handleCreateSecret}>Save Secret</Button>
          </>
        )}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">Reference Key</label>
            <input
              value={secretForm.reference_key}
              onChange={(e) => setSecretForm((prev) => ({ ...prev, reference_key: e.target.value }))}
              placeholder="OPENAI_API_KEY_PROD"
              className="w-full px-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">Provider</label>
            <input
              value={secretForm.provider}
              onChange={(e) => setSecretForm((prev) => ({ ...prev, provider: e.target.value }))}
              placeholder="openai"
              className="w-full px-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">Secret Value</label>
            <input
              type="password"
              value={secretForm.secret_value}
              onChange={(e) => setSecretForm((prev) => ({ ...prev, secret_value: e.target.value }))}
              placeholder="sk-..."
              className="w-full px-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={configModalOpen}
        onClose={() => {
          setConfigModalOpen(false);
          setEditingConfig(null);
        }}
        size="xl"
        title={editingConfig ? 'Edit Model Configuration' : 'Create Model Configuration'}
        subtitle="Set endpoint, secret reference, and runtime controls for this model."
        footer={(
          <>
            <Button variant="ghost" onClick={() => {
              setConfigModalOpen(false);
              setEditingConfig(null);
            }}>Cancel</Button>
            <Button loading={savingConfig} onClick={handleSaveConfig} disabled={!isConfigFormValid}>{editingConfig ? 'Update Config' : 'Create Config'}</Button>
          </>
        )}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">Model ID</label>
            <input
              value={configForm.model_id}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, model_id: e.target.value }))}
              disabled={Boolean(editingConfig)}
              placeholder="gpt-4.1"
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] disabled:opacity-60 ${configValidationErrors.model_id ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.model_id && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.model_id}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">Provider</label>
            <input
              value={configForm.provider}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, provider: e.target.value }))}
              disabled={Boolean(editingConfig)}
              placeholder="openai"
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] disabled:opacity-60 ${configValidationErrors.provider ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.provider && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.provider}</p>}
          </div>
          <div className="md:col-span-2">
            <label className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-muted)] mb-1">
              Base URL
              <span title="Use a fully-qualified URL, for example: https://api.openai.com/v1/models">
                <AlertCircle className="w-3.5 h-3.5 text-[var(--color-text-light)]" />
              </span>
            </label>
            <input
              value={configForm.base_url}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, base_url: e.target.value }))}
              placeholder="https://api.openai.com/v1/models"
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] ${configValidationErrors.base_url ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.base_url && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.base_url}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">Secret Reference Key</label>
            <input
              list="secret-reference-options"
              value={configForm.secret_reference_key}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, secret_reference_key: e.target.value }))}
              placeholder="OPENAI_API_KEY_PROD"
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] ${configValidationErrors.secret_reference_key ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.secret_reference_key && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.secret_reference_key}</p>}
            <datalist id="secret-reference-options">
              {secrets.map((s) => <option key={s.reference_key} value={s.reference_key} />)}
            </datalist>
          </div>
          <div className="flex items-end">
            <label className="inline-flex items-center gap-2 text-sm text-[var(--color-text-main)]">
              <input
                type="checkbox"
                checked={configForm.is_active}
                onChange={(e) => setConfigForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                className="rounded border-[var(--color-border)]"
              />
              Active configuration
            </label>
          </div>
          <div>
            <label className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-muted)] mb-1">
              Temperature
              <span title={`Allowed range: ${TEMPERATURE_MIN} to ${TEMPERATURE_MAX}`}>
                <AlertCircle className="w-3.5 h-3.5 text-[var(--color-text-light)]" />
              </span>
            </label>
            <input
              type="number"
              step="0.1"
              min={TEMPERATURE_MIN}
              max={TEMPERATURE_MAX}
              value={configForm.temperature}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, temperature: e.target.value }))}
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] ${configValidationErrors.temperature ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.temperature && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.temperature}</p>}
          </div>
          <div>
            <label className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-muted)] mb-1">
              Max Tokens
              <span title={`Allowed range: ${MAX_TOKENS_MIN} to ${MAX_TOKENS_MAX}`}>
                <AlertCircle className="w-3.5 h-3.5 text-[var(--color-text-light)]" />
              </span>
            </label>
            <input
              type="number"
              min={MAX_TOKENS_MIN}
              max={MAX_TOKENS_MAX}
              step="1"
              value={configForm.max_tokens}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, max_tokens: e.target.value }))}
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] ${configValidationErrors.max_tokens ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.max_tokens && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.max_tokens}</p>}
            {!configValidationErrors.max_tokens && showVeryHighTokenSoftWarning && (
              <p className="mt-1 text-[11px] text-red-700">
                Very high token setting warning: values above {MAX_TOKENS_STRONG_WARNING} can significantly increase latency, queueing risk, and cost.
              </p>
            )}
            {!configValidationErrors.max_tokens && !showVeryHighTokenSoftWarning && showHighTokenSoftWarning && (
              <p className="mt-1 text-[11px] text-amber-700">
                High token setting warning: values above {MAX_TOKENS_SOFT_WARNING} can increase latency and cost.
              </p>
            )}
          </div>
          <div>
            <label className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-muted)] mb-1">
              Timeout (seconds)
              <span title={`Allowed range: ${TIMEOUT_MIN} to ${TIMEOUT_MAX} seconds`}>
                <AlertCircle className="w-3.5 h-3.5 text-[var(--color-text-light)]" />
              </span>
            </label>
            <input
              type="number"
              min={TIMEOUT_MIN}
              max={TIMEOUT_MAX}
              step="1"
              value={configForm.request_timeout_seconds}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, request_timeout_seconds: e.target.value }))}
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] ${configValidationErrors.request_timeout_seconds ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.request_timeout_seconds && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.request_timeout_seconds}</p>}
          </div>
          <div className="md:col-span-2">
            <label className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-muted)] mb-1">
              Parameters (JSON)
              <span title={'Must be valid JSON, for example: {"top_p":0.95}'}>
                <AlertCircle className="w-3.5 h-3.5 text-[var(--color-text-light)]" />
              </span>
            </label>
            <textarea
              value={configForm.parameters}
              onChange={(e) => setConfigForm((prev) => ({ ...prev, parameters: e.target.value }))}
              rows={6}
              className={`w-full px-3 py-2 bg-[var(--color-surface)] border rounded-lg text-xs font-mono focus:outline-none focus:border-[var(--color-accent)] ${configValidationErrors.parameters ? 'border-red-300' : 'border-[var(--color-border)]'}`}
            />
            {configValidationErrors.parameters && <p className="mt-1 text-[11px] text-red-600">{configValidationErrors.parameters}</p>}
          </div>
        </div>
      </Modal>
    </div>
  );
}
