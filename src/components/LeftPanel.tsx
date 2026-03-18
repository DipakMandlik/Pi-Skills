import React, { useState } from 'react';
import { useStore } from '../store';
import * as Icons from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import sqlGenerationSkillMd from '../skills/sql-generation.skill.md?raw';
import storedProcedureSkillMd from '../skills/snowflake-stored-procedures.skill.md?raw';
import queryOptimizerSkillMd from '../skills/snowflake-query-optimizer.skill.md?raw';
import dataArchitectSkillMd from '../skills/data-architect.skill.md?raw';
import analyticsEngineerSkillMd from '../skills/analytics-engineer.skill.md?raw';

type SkillTemplate = {
  objective: string;
  responsibilities: string[];
  workflow: string[];
  checks: string[];
  outputs: string[];
  prompts: string[];
};

const SKILL_TEMPLATES: Record<string, SkillTemplate> = {
  'Data Architect': {
    objective: 'Design reliable analytical data models and domain boundaries for Snowflake workloads.',
    responsibilities: [
      'Define subject areas and source-to-model lineage.',
      'Recommend star/snowflake schemas for BI and ML workloads.',
      'Set naming conventions for databases, schemas, tables, and views.',
      'Align grain strategy for facts and dimensions.',
    ],
    workflow: [
      'Gather business entities, KPIs, and source systems.',
      'Define model grain, keys, and SCD strategy.',
      'Design conformed dimensions and reusable marts.',
      'Review query performance and clustering opportunities.',
    ],
    checks: [
      'No ambiguous primary business key definitions.',
      'Fact table grain is explicit and testable.',
      'Slowly changing attributes have a declared policy.',
      'Model supports both exploration and governed reporting.',
    ],
    outputs: [
      'Domain model blueprint.',
      'Table-by-table logical model contract.',
      'Migration/rollout sequencing plan.',
    ],
    prompts: [
      'Design a customer 360 mart across payments and accounts.',
      'Define an events model for daily KPI reporting.',
    ],
  },
  'Analytics Engineer': {
    objective: 'Transform raw data into analytics-ready models with strong testing and documentation.',
    responsibilities: [
      'Create clean intermediate and mart layers.',
      'Implement data quality tests and freshness checks.',
      'Document metric logic and semantic assumptions.',
      'Optimize transformation SQL for predictable runtimes.',
    ],
    workflow: [
      'Profile raw source columns and null distributions.',
      'Build staging models with deterministic renaming.',
      'Create metric-ready marts with repeatable tests.',
      'Validate outputs against stakeholder KPI definitions.',
    ],
    checks: [
      'Critical columns are tested for null/uniqueness.',
      'Business filters are applied consistently across marts.',
      'Late-arriving records are handled explicitly.',
      'Versioned model contracts are maintained.',
    ],
    outputs: [
      'Transformation SQL artifacts.',
      'Data tests and accepted thresholds.',
      'Model-level data dictionary.',
    ],
    prompts: [
      'Build a daily revenue mart with source reconciliation.',
      'Create tests for duplicate account identifiers.',
    ],
  },
  'ML Engineer': {
    objective: 'Prepare trustworthy feature datasets and evaluate model-ready signal quality.',
    responsibilities: [
      'Define feature windows and leakage-safe joins.',
      'Create training snapshots with clear as-of timestamps.',
      'Track feature drift and distribution shifts.',
      'Document model-serving feature contracts.',
    ],
    workflow: [
      'Identify target variable and scoring cadence.',
      'Build feature extraction queries with point-in-time correctness.',
      'Evaluate missingness, outliers, and drift metrics.',
      'Publish reusable feature views for scoring.',
    ],
    checks: [
      'No target leakage across training windows.',
      'Feature definitions are deterministic and reproducible.',
      'Drift checks include both mean and distribution shifts.',
      'Serving path uses same transformations as training.',
    ],
    outputs: [
      'Feature dataset SQL.',
      'Data quality and drift report.',
      'Scoring-ready view contract.',
    ],
    prompts: [
      'Create churn prediction features from transactions.',
      'Build point-in-time features for fraud scoring.',
    ],
  },
  'SQL Writer': {
    objective: 'Generate correct, readable, and optimized Snowflake SQL for analysis and reporting.',
    responsibilities: [
      'Translate natural language into executable SQL.',
      'Apply safe defaults for filters, ordering, and limits.',
      'Use explicit aliases and stable grouping semantics.',
      'Prefer maintainable query structure over clever syntax.',
    ],
    workflow: [
      'Parse business intent, metrics, and grain.',
      'Map to selected tables and required joins.',
      'Generate SQL with transparent assumptions.',
      'Return validation notes for quick human review.',
    ],
    checks: [
      'Query has deterministic ORDER BY when using LIMIT.',
      'Date filters are explicit and timezone-safe.',
      'Aggregations and GROUP BY columns are aligned.',
      'No destructive SQL in dev/prod safety modes.',
    ],
    outputs: [
      'Executable SQL draft.',
      'Assumption notes for reviewer confirmation.',
      'Optional alternative query variants.',
    ],
    prompts: [
      'Show top 20 customers by revenue in last 30 days.',
      'Count active accounts by segment for this quarter.',
    ],
  },
  'Query Optimizer': {
    objective: 'Improve query runtime, cost, and stability without changing business results.',
    responsibilities: [
      'Identify expensive scans, skewed joins, and spill risks.',
      'Recommend predicate pushdown and projection pruning.',
      'Refactor CTEs/subqueries for planner efficiency.',
      'Suggest clustering/materialization opportunities.',
    ],
    workflow: [
      'Inspect baseline SQL and expected row cardinality.',
      'Remove nonessential columns and intermediate sorts.',
      'Rewrite joins and aggregations with lower scan cost.',
      'Compare before/after execution characteristics.',
    ],
    checks: [
      'Result set semantics remain unchanged.',
      'Filters are sargable and pushed early.',
      'High-cardinality joins are constrained.',
      'Warehouse size recommendation matches workload.',
    ],
    outputs: [
      'Optimized SQL version.',
      'Performance rationale and trade-offs.',
      'Operational tuning checklist.',
    ],
    prompts: [
      'Optimize this monthly KPI query for faster runtime.',
      'Reduce warehouse cost for daily dashboard refresh.',
    ],
  },
  'Data Explorer': {
    objective: 'Discover relevant datasets quickly and map user intent to the right tables.',
    responsibilities: [
      'List databases, schemas, and candidate tables.',
      'Surface joinable entities and naming signals.',
      'Guide users to minimal table set for a question.',
      'Promote trusted sources over raw duplicates.',
    ],
    workflow: [
      'Start from business question and domain context.',
      'Traverse database->schema->table hierarchy.',
      'Shortlist tables and verify key columns.',
      'Pass selected tables to SQL generation stage.',
    ],
    checks: [
      'Selected table set is complete but minimal.',
      'Ambiguous similarly named tables are clarified.',
      'Schema ownership and freshness are understood.',
      'Selected tables align with requested grain.',
    ],
    outputs: [
      'Table shortlist and rationale.',
      'Suggested join path.',
      'Prompt-ready context for SQL drafting.',
    ],
    prompts: [
      'Find tables needed for loan default trend by month.',
      'Which schema has customer-account relationship tables?',
    ],
  },
  'Warehouse Monitor': {
    objective: 'Monitor Snowflake consumption and identify practical efficiency improvements.',
    responsibilities: [
      'Track warehouse utilization and credit trends.',
      'Detect idle time, queueing, and burst patterns.',
      'Flag unusually expensive query windows.',
      'Recommend sizing and schedule adjustments.',
    ],
    workflow: [
      'Collect warehouse usage windows and query volume.',
      'Compare utilization against SLA thresholds.',
      'Correlate spikes with workload classes.',
      'Propose operational changes and validation plan.',
    ],
    checks: [
      'Recommendations include measurable KPIs.',
      'Cost reductions do not violate SLA.',
      'Peak windows are explicitly protected.',
      'Changes are reversible with rollback criteria.',
    ],
    outputs: [
      'Usage summary report.',
      'Top cost drivers with evidence.',
      'Tuning action plan with expected impact.',
    ],
    prompts: [
      'Summarize warehouse credits used in last 14 days.',
      'Find high-cost hours and recommend right-sizing.',
    ],
  },
  'Metadata Inspector': {
    objective: 'Expose schema details and structural context for reliable SQL generation and governance.',
    responsibilities: [
      'Inspect column types, nullability, and defaults.',
      'Highlight naming anomalies and type mismatches.',
      'Identify keys and likely join columns.',
      'Document table contracts for downstream users.',
    ],
    workflow: [
      'Describe table structures and key fields.',
      'Validate business-critical columns and formats.',
      'Compare related tables for compatibility.',
      'Publish metadata notes for query authors.',
    ],
    checks: [
      'Data types align with expected aggregations.',
      'Nullable fields are handled in query logic.',
      'Join keys have compatible types and semantics.',
      'Schema changes are captured in documentation.',
    ],
    outputs: [
      'Column-level metadata summary.',
      'Join and compatibility notes.',
      'Schema quality observations.',
    ],
    prompts: [
      'Describe ACCOUNT table and identify join keys.',
      'Compare column compatibility between ACCOUNT and TRANSACTION.',
    ],
  },
};

const buildDetailedSkillMarkdown = (skill: any) => {
  if (skill.name === 'Data Architect') {
    return dataArchitectSkillMd;
  }

  if (skill.name === 'SQL Writer') {
    return sqlGenerationSkillMd;
  }

  if (skill.name === 'Stored Procedure Writer') {
    return storedProcedureSkillMd;
  }

  if (skill.name === 'Query Optimizer') {
    return queryOptimizerSkillMd;
  }

  if (skill.name === 'Analytics Engineer') {
    return analyticsEngineerSkillMd;
  }

  const slug = skill.name.toLowerCase().replace(/\s+/g, '-');
  const template = SKILL_TEMPLATES[skill.name] || {
    objective: skill.description || `Execute tasks related to ${skill.name}.`,
    responsibilities: [
      `Handle requests in the ${skill.name} domain.`,
      'Provide clear, reviewable recommendations.',
      'Maintain safety and reproducibility in outputs.',
    ],
    workflow: [
      'Understand request objective and constraints.',
      'Prepare draft output with explicit assumptions.',
      'Return actionable result and validation guidance.',
    ],
    checks: [
      'Output is complete and reviewable.',
      'Assumptions are explicit.',
      'Recommendations are operationally safe.',
    ],
    outputs: [
      'Task-ready guidance.',
      'Execution checklist.',
      'Review notes.',
    ],
    prompts: [
      `Help me with ${skill.name.toLowerCase()} for my data workflow.`,
    ],
  };

  return `---
name: ${slug}
description: ${skill.description}
license: Complete terms in LICENSE.txt
---

# ${skill.name}

## Objective

${template.objective}

## Responsibilities

${template.responsibilities.map((item) => `- ${item}`).join('\n')}

## Workflow

${template.workflow.map((item, idx) => `${idx + 1}. ${item}`).join('\n')}

## Validation Checks

${template.checks.map((item) => `- ${item}`).join('\n')}

## Expected Outputs

${template.outputs.map((item) => `- ${item}`).join('\n')}

## Example Prompts

${template.prompts.map((item) => `- ${item}`).join('\n')}

## Usage Notes

- Keep outputs concise, verifiable, and aligned with business intent.
- Prefer deterministic SQL and documented assumptions.
- Review generated output before execution in production.
`;
};

const getIcon = (name: string) => {
  const Icon = (Icons as any)[name] || Icons.Wrench;
  return <Icon className="w-4 h-4" />;
};

export function LeftPanel() {
  const { skills, activeSkills, toggleSkill, addSkill, updateSkill, deleteSkill } = useStore();
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');

  const handleAddSave = () => {
    if (!editName.trim()) return;
    addSkill({
      id: `custom-${Date.now()}`,
      name: editName,
      description: editDesc,
      iconName: 'Wrench',
      isCustom: true
    });
    setIsAdding(false);
    setEditName('');
    setEditDesc('');
  };

  const handleEditSave = (id: string) => {
    if (!editName.trim()) return;
    updateSkill(id, { name: editName, description: editDesc });
    setEditingId(null);
  };

  const startEdit = (skill: any) => {
    setEditingId(skill.id);
    setEditName(skill.name);
    setEditDesc(skill.description);
  };

  const handleDownloadSkill = (skill: any) => {
    const slug = skill.name.toLowerCase().replace(/\s+/g, '-');
    const mdContent = buildDetailedSkillMarkdown(skill);

    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${slug}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-[280px] h-full bg-panel border-r border-border flex flex-col shrink-0 z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
      <div className="h-16 px-6 border-b border-border flex items-center justify-center bg-panel shrink-0">
        <div className="flex flex-col items-center justify-center scale-90 origin-center">
          <div className="flex items-center gap-1.5">
            <span className="text-[#1d4ed8] font-serif text-[32px] font-bold italic leading-none">π</span>
            <span className="text-[#eab308] font-serif text-xl italic leading-none mt-2">by</span>
            <div className="bg-[#38bdf8] text-white rounded-md w-8 h-8 flex items-center justify-center font-bold text-xl relative ml-0.5">
              3
              <span className="absolute -top-1 -right-3 text-[8px] text-[#1d4ed8] font-sans">TM</span>
            </div>
          </div>
          <span className="text-[#1d4ed8] text-[9px] font-medium tracking-wide mt-1 whitespace-nowrap">Transforming Enterprises for Future</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">AI Skills (Max 3)</div>
          <button onClick={() => { setIsAdding(true); setEditName(''); setEditDesc(''); }} title="Add Custom Skill" className="text-accent hover:text-accent-secondary transition-colors p-1">
            <Icons.Plus className="w-4 h-4" />
          </button>
        </div>

        <AnimatePresence>
          {isAdding && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="bg-bg-base p-3 rounded-xl border border-border mb-3 overflow-hidden">
              <input autoFocus value={editName} onChange={e => setEditName(e.target.value)} placeholder="Skill Name" className="w-full bg-panel border border-border rounded px-2 py-1 text-sm mb-2 outline-none focus:border-accent" />
              <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} placeholder="Description" className="w-full bg-panel border border-border rounded px-2 py-1 text-xs mb-2 outline-none focus:border-accent resize-none" rows={2} />
              <div className="flex justify-end gap-2">
                <button onClick={() => setIsAdding(false)} className="text-xs text-text-muted hover:text-text-main">Cancel</button>
                <button onClick={handleAddSave} className="text-xs bg-accent text-white px-2 py-1 rounded hover:bg-accent/90">Save</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {skills.map((skill) => {
          const isActive = activeSkills.includes(skill.name);
          const isEditing = editingId === skill.id;
          
          if (isEditing) {
            return (
              <div key={skill.id} className="bg-bg-base p-3 rounded-xl border border-border mb-3">
                <input autoFocus value={editName} onChange={e => setEditName(e.target.value)} className="w-full bg-panel border border-border rounded px-2 py-1 text-sm mb-2 outline-none focus:border-accent" />
                <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} className="w-full bg-panel border border-border rounded px-2 py-1 text-xs mb-2 outline-none focus:border-accent resize-none" rows={2} />
                <div className="flex justify-end gap-2">
                  <button onClick={() => setEditingId(null)} className="text-xs text-text-muted hover:text-text-main">Cancel</button>
                  <button onClick={() => handleEditSave(skill.id)} className="text-xs bg-accent text-white px-2 py-1 rounded hover:bg-accent/90">Save</button>
                </div>
              </div>
            );
          }

          return (
            <motion.div
              key={skill.id}
              layout
              className={`w-full text-left p-3 rounded-xl border transition-all duration-200 relative group ${
                isActive 
                  ? 'bg-accent/5 border-accent/30 shadow-[0_2px_10px_rgba(37,99,235,0.05)]' 
                  : 'bg-panel border-border hover:border-accent/30 hover:shadow-sm'
              }`}
            >
              <button onClick={() => toggleSkill(skill.name)} className="w-full text-left">
                <div className="flex items-center gap-3 mb-1.5">
                  <div className={`${isActive ? 'text-accent' : 'text-text-muted group-hover:text-accent'}`}>
                    {getIcon(skill.iconName)}
                  </div>
                  <span className={`font-medium text-sm ${isActive ? 'text-accent' : 'text-text-main'}`}>
                    {skill.name}
                  </span>
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  {skill.description}
                </p>
              </button>
              
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                <button onClick={(e) => { e.stopPropagation(); handleDownloadSkill(skill); }} className="p-1 text-text-muted hover:text-accent bg-panel rounded shadow-sm border border-border" title="Download Skill"><Icons.Download className="w-3 h-3" /></button>
                <button onClick={(e) => { e.stopPropagation(); startEdit(skill); }} className="p-1 text-text-muted hover:text-accent bg-panel rounded shadow-sm border border-border" title="Edit Skill"><Icons.Edit2 className="w-3 h-3" /></button>
                <button onClick={(e) => { e.stopPropagation(); deleteSkill(skill.id); }} className="p-1 text-text-muted hover:text-red-500 bg-panel rounded shadow-sm border border-border" title="Delete Skill"><Icons.Trash2 className="w-3 h-3" /></button>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
