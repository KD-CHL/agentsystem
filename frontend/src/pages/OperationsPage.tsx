import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CheckCircle2, ClipboardCheck, Clock3, ListChecks, ShieldCheck } from "lucide-react";

import { agentIcons, agentLabels } from "../components/agentVisuals";
import { api } from "../lib/api";
import styles from "./StandardPage.module.css";

export function OperationsPage() {
  const { t } = useTranslation();
  const { data: summary } = useQuery({ queryKey: ["operations-summary"], queryFn: api.operationsSummary, refetchInterval: 3_000 });
  const { data: audit } = useQuery({ queryKey: ["audit-logs"], queryFn: () => api.auditLogs({ limit: 100 }), refetchInterval: 3_000 });
  const { data: rules } = useQuery({ queryKey: ["collaboration-rules"], queryFn: api.collaborationRules });
  const metrics = [
    { label: t("operations.tasks"), value: summary?.total_tasks ?? 0, icon: ListChecks, tone: "accent" },
    { label: t("operations.completion"), value: summary?.status_counts.completed ?? 0, icon: CheckCircle2, tone: "green" },
    { label: t("operations.approvals"), value: summary?.pending_approvals ?? 0, icon: ClipboardCheck, tone: "yellow" },
    { label: t("operations.failures"), value: summary?.status_counts.failed ?? 0, icon: AlertTriangle, tone: "red" },
  ];
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}><div><span className={styles.eyebrow}>Control / Governance</span><h1>{t("operations.title")}</h1><p>Local task health, approvals, and audit-ready execution status.</p></div><span className={styles.safetyBadge}><ShieldCheck size={15} />Policy enforced</span></header>
      <div className={styles.metricsGrid}>
        {metrics.map(({ label, value, icon: Icon, tone }) => <section key={label} className={styles.metric} data-tone={tone}><span><Icon size={18} /></span><div><small>{label}</small><strong>{value}</strong></div></section>)}
      </div>
      <section className={styles.operationsTable}>
        <div className={styles.panelTitle}><span>{t("operations.audit")}</span><small>{audit?.total ?? 0} records</small></div>
        <div className={styles.operationHead}><span>Action</span><span>Actor</span><span>Task</span><span>Details</span><span>Time</span></div>
        {audit?.items.map((item) => <div key={item.id} className={styles.operationRow}><strong>{item.action}</strong><span>{item.actor}</span><code>{item.task_id?.slice(-10) ?? "system"}</code><span>{summarize(item.details)}</span><time><Clock3 size={12} />{new Date(item.created_at).toLocaleString()}</time></div>)}
        {!audit?.items.length && <div className={styles.inlineEmpty}>{t("common.noData")}</div>}
      </section>
      <section className={styles.rulesPanel}>
        <div className={styles.panelTitle}><span>Collaboration rule model</span><small>v{rules?.version ?? "1.0"} · enforced</small></div>
        <div className={styles.ruleSummary}>
          <span><ShieldCheck size={16} /><strong>Fail closed</strong><small>Missing handoff data blocks the run</small></span>
          <span><ClipboardCheck size={16} /><strong>Quality consensus</strong><small>Test + Security + Review</small></span>
          <span><ListChecks size={16} /><strong>Versioned context</strong><small>Approval resumes the same snapshot</small></span>
        </div>
        <div className={styles.ruleRows}>
          {rules?.agents.map((contract) => {
            const Icon = agentIcons[contract.agent_name];
            return <div key={contract.agent_name}><span className={styles.ruleAgent}><Icon size={16} /><strong>{agentLabels[contract.agent_name]}</strong></span><span><small>IN</small>{contract.required_inputs.join(", ")}</span><span><small>OUT</small>{contract.required_outputs.join(", ")}</span><span><small>NEXT</small>{contract.allowed_handoffs.map((name) => agentLabels[name]).join(", ") || "Complete"}</span></div>;
          })}
        </div>
      </section>
    </div>
  );
}

function summarize(details: Record<string, unknown>): string {
  const value = Object.entries(details).slice(0, 3).map(([key, item]) => `${key}=${String(item)}`).join(" · ");
  return value || "-";
}
