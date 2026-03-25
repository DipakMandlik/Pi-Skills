import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  Shield, CreditCard, Brain, Settings, Users, BarChart3,
  Check, X, Plus, RefreshCw, AlertCircle, ChevronDown, ChevronUp, FileText
} from 'lucide-react';
import { Card, StatusBadge, Skeleton } from '../components/common/index';
import { adminApi, governanceApi } from '../services/governanceApi';
import { getUserFacingError } from '../services/errorUtils';
import type { Subscription, ModelAccessControl, FeatureFlag, TokenUsage } from '../services/governanceApi';

interface Policy {
  id: string;
  policy_name: string;
  policy_type: string;
  description: string;
  conditions: Record<string, unknown>;
  actions: Record<string, unknown>;
  priority: string;
  enabled: boolean;
}

type GovernanceTabErrorKey = 'subscriptions' | 'models' | 'features' | 'policies' | 'users';

export function GovernanceAdminPage() {
  const [activeTab, setActiveTab] = useState<'subscriptions' | 'models' | 'features' | 'policies' | 'users'>('subscriptions');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [modelAccess, setModelAccess] = useState<ModelAccessControl[]>([]);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);
  const [tabErrors, setTabErrors] = useState<Record<GovernanceTabErrorKey, string | null>>({
    subscriptions: null,
    models: null,
    features: null,
    policies: null,
    users: null,
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    setTabErrors({
      subscriptions: null,
      models: null,
      features: null,
      policies: null,
      users: null,
    });
    try {
      const [subs, access, flags, pols, usage] = await Promise.allSettled([
        adminApi.listSubscriptions(),
        adminApi.listModelAccess(),
        adminApi.listFeatureFlags(),
        adminApi.listPolicies(),
        governanceApi.getTokenUsage(),
      ]);
      const nextErrors: Record<GovernanceTabErrorKey, string | null> = {
        subscriptions: null,
        models: null,
        features: null,
        policies: null,
        users: null,
      };

      if (subs.status === 'fulfilled') {
        setSubscriptions(subs.value.subscriptions);
      } else {
        nextErrors.subscriptions = getUserFacingError(subs.reason, 'Failed to load subscriptions');
        setSubscriptions([]);
      }

      if (access.status === 'fulfilled') {
        setModelAccess(access.value.configs);
      } else {
        nextErrors.models = getUserFacingError(access.reason, 'Failed to load model access');
        setModelAccess([]);
      }

      if (flags.status === 'fulfilled') {
        setFeatureFlags(flags.value.flags);
      } else {
        nextErrors.features = getUserFacingError(flags.reason, 'Failed to load feature flags');
        setFeatureFlags([]);
      }

      if (pols.status === 'fulfilled') {
        setPolicies(pols.value.policies);
      } else {
        nextErrors.policies = getUserFacingError(pols.reason, 'Failed to load governance policies');
        setPolicies([]);
      }

      if (usage.status === 'fulfilled') {
        setTokenUsage(usage.value.usage);
      } else {
        nextErrors.users = getUserFacingError(usage.reason, 'Failed to load token usage');
        setTokenUsage(null);
      }

      setTabErrors(nextErrors);
      const hasAnySuccess = [subs, access, flags, pols, usage].some((r) => r.status === 'fulfilled');
      if (!hasAnySuccess) {
        setError('Failed to load governance data. Please refresh after re-authentication.');
      }
    } catch (err) {
      setError(getUserFacingError(err, 'Failed to load governance data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const tabs = [
    { id: 'subscriptions', label: 'Subscriptions', icon: CreditCard },
    { id: 'models', label: 'Model Access', icon: Brain },
    { id: 'features', label: 'Feature Flags', icon: Settings },
    { id: 'policies', label: 'Policies', icon: FileText },
    { id: 'users', label: 'User Tokens', icon: BarChart3 },
  ] as const;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-main)] flex items-center gap-2">
            <Shield className="w-5 h-5 text-[var(--color-accent)]" />
            AI Governance
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            Manage subscriptions, model access, and token limits
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl hover:border-[var(--color-border-strong)] transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </motion.div>

      {/* Error */}
      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <span className="text-sm text-red-700">{error}</span>
        </motion.div>
      )}

      {!error && tabErrors[activeTab] && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
          <span className="text-sm text-amber-700">{tabErrors[activeTab]}</span>
        </motion.div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-white text-[var(--color-text-main)] shadow-sm'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} padding="sm">
              <Skeleton variant="text" width="60%" height={20} />
              <Skeleton variant="text" width="40%" height={14} className="mt-2" />
            </Card>
          ))}
        </div>
      ) : (
        <>
          {activeTab === 'subscriptions' && (
            <div className="space-y-4">
              {subscriptions.map((plan) => (
                <Card key={plan.plan_name} padding="sm">
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setExpandedPlan(expandedPlan === plan.plan_name ? null : plan.plan_name)}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        plan.priority === 'critical' ? 'bg-purple-50' :
                        plan.priority === 'high' ? 'bg-blue-50' :
                        plan.priority === 'standard' ? 'bg-emerald-50' : 'bg-gray-50'
                      }`}>
                        <CreditCard className={`w-5 h-5 ${
                          plan.priority === 'critical' ? 'text-purple-500' :
                          plan.priority === 'high' ? 'text-blue-500' :
                          plan.priority === 'standard' ? 'text-emerald-500' : 'text-gray-500'
                        }`} />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-[var(--color-text-main)]">{plan.display_name}</h3>
                        <p className="text-[11px] text-[var(--color-text-muted)]">
                          {plan.monthly_token_limit.toLocaleString()} tokens/mo · {plan.allowed_models.length} models
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge
                        status={plan.priority === 'critical' ? 'active' : plan.priority === 'high' ? 'active' : 'pending'}
                        label={plan.priority}
                      />
                      {expandedPlan === plan.plan_name ? (
                        <ChevronUp className="w-4 h-4 text-[var(--color-text-muted)]" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
                      )}
                    </div>
                  </div>

                  {expandedPlan === plan.plan_name && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-4 pt-4 border-t border-[var(--color-border)] space-y-3"
                    >
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Token Limit</p>
                          <p className="text-sm font-semibold text-[var(--color-text-main)]">{plan.monthly_token_limit.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Max per Request</p>
                          <p className="text-sm font-semibold text-[var(--color-text-main)]">{plan.max_tokens_per_request.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Rate Limit</p>
                          <p className="text-sm font-semibold text-[var(--color-text-main)]">{plan.rate_limit_per_minute}/min</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Cost Budget</p>
                          <p className="text-sm font-semibold text-[var(--color-text-main)]">${plan.cost_budget_monthly}/mo</p>
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Allowed Models</p>
                        <div className="flex flex-wrap gap-1.5">
                          {plan.allowed_models.map((model) => (
                            <span key={model} className="px-2 py-0.5 text-[11px] font-medium bg-[var(--color-surface)] rounded-md text-[var(--color-text-main)]">
                              {model}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Features</p>
                        <div className="flex flex-wrap gap-1.5">
                          {plan.features.map((feature) => (
                            <span key={feature} className="px-2 py-0.5 text-[11px] font-medium bg-blue-50 rounded-md text-blue-600">
                              {feature}
                            </span>
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </Card>
              ))}
            </div>
          )}

          {activeTab === 'models' && (
            <div className="space-y-4">
              {modelAccess.map((config) => (
                <Card key={config.model_id} padding="sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
                        <Brain className="w-5 h-5 text-purple-500" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-[var(--color-text-main)] font-mono">{config.model_id}</h3>
                        <p className="text-[11px] text-[var(--color-text-muted)]">
                          Max {config.max_tokens_per_request.toLocaleString()} tokens · {config.rate_limit_per_minute}/min rate limit
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge
                        status={config.enabled ? 'active' : 'expired'}
                        label={config.enabled ? 'Enabled' : 'Disabled'}
                      />
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
                    <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Allowed Roles</p>
                    <div className="flex flex-wrap gap-1.5">
                      {config.allowed_roles.map((role) => (
                        <span key={role} className={`px-2 py-0.5 text-[11px] font-medium rounded-md ${
                          role === 'admin' ? 'bg-purple-50 text-purple-600' :
                          role === 'user' ? 'bg-blue-50 text-blue-600' : 'bg-gray-50 text-gray-600'
                        }`}>
                          {role}
                        </span>
                      ))}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {activeTab === 'features' && (
            <div className="space-y-4">
              {featureFlags.length > 0 ? featureFlags.map((flag) => (
                <Card key={`${flag.feature_name}-${flag.model_id}`} padding="sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${flag.enabled ? 'bg-emerald-50' : 'bg-gray-50'}`}>
                        <Settings className={`w-5 h-5 ${flag.enabled ? 'text-emerald-500' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-[var(--color-text-main)]">{flag.feature_name}</h3>
                        <p className="text-[11px] text-[var(--color-text-muted)] font-mono">Model: {flag.model_id}</p>
                      </div>
                    </div>
                    <StatusBadge
                      status={flag.enabled ? 'active' : 'expired'}
                      label={flag.enabled ? 'Enabled' : 'Disabled'}
                    />
                  </div>
                </Card>
              )) : (
                <Card padding="lg">
                  <div className="text-center py-8">
                    <Settings className="w-8 h-8 text-[var(--color-text-light)] mx-auto mb-2" />
                    <p className="text-sm text-[var(--color-text-muted)]">No feature flags configured</p>
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab === 'policies' && (
            <div className="space-y-4">
              {policies.length > 0 ? policies.map((policy) => (
                <Card key={policy.id} padding="sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${policy.enabled ? 'bg-blue-50' : 'bg-gray-50'}`}>
                        <FileText className={`w-5 h-5 ${policy.enabled ? 'text-blue-500' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-[var(--color-text-main)]">{policy.policy_name}</h3>
                        <p className="text-[11px] text-[var(--color-text-muted)]">{policy.description || policy.policy_type}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 text-[10px] font-medium bg-[var(--color-surface)] rounded-md text-[var(--color-text-muted)]">
                        {policy.policy_type}
                      </span>
                      <StatusBadge
                        status={policy.enabled ? 'active' : 'expired'}
                        label={policy.enabled ? 'Enabled' : 'Disabled'}
                      />
                    </div>
                  </div>
                </Card>
              )) : (
                <Card padding="lg">
                  <div className="text-center py-8">
                    <FileText className="w-8 h-8 text-[var(--color-text-light)] mx-auto mb-2" />
                    <p className="text-sm text-[var(--color-text-muted)]">No governance policies configured</p>
                    <p className="text-xs text-[var(--color-text-light)] mt-1">Policies allow fine-grained control over AI access</p>
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab === 'users' && (
            <Card padding="lg">
              {tokenUsage ? (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-[var(--color-text-main)]">Your Token Usage</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-3 bg-[var(--color-surface)] rounded-xl">
                      <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Period</p>
                      <p className="text-lg font-bold text-[var(--color-text-main)]">{tokenUsage.period}</p>
                    </div>
                    <div className="p-3 bg-[var(--color-surface)] rounded-xl">
                      <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Used</p>
                      <p className="text-lg font-bold text-[var(--color-text-main)]">{tokenUsage.tokens_used.toLocaleString()}</p>
                    </div>
                    <div className="p-3 bg-[var(--color-surface)] rounded-xl">
                      <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Limit</p>
                      <p className="text-lg font-bold text-[var(--color-text-main)]">{tokenUsage.tokens_limit.toLocaleString()}</p>
                    </div>
                    <div className="p-3 bg-[var(--color-surface)] rounded-xl">
                      <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Remaining</p>
                      <p className="text-lg font-bold text-emerald-600">{tokenUsage.remaining_tokens.toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-[var(--color-text-muted)]">Token Usage</span>
                      <span className="text-xs font-mono text-[var(--color-text-main)]">
                        {Math.round((tokenUsage.tokens_used / tokenUsage.tokens_limit) * 100)}%
                      </span>
                    </div>
                    <div className="h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--color-accent)] rounded-full transition-all"
                        style={{ width: `${Math.min(100, (tokenUsage.tokens_used / tokenUsage.tokens_limit) * 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl">
                    <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Cost Accumulated</p>
                    <p className="text-lg font-bold text-[var(--color-text-main)]">${tokenUsage.cost_accumulated.toFixed(4)}</p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <BarChart3 className="w-8 h-8 text-[var(--color-text-light)] mx-auto mb-2" />
                  <p className="text-sm text-[var(--color-text-muted)]">No token usage data available</p>
                  <p className="text-xs text-[var(--color-text-light)] mt-1">Token tracking begins after your first AI request</p>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
