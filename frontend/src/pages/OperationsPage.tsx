import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CheckCircle2, ClipboardCheck, Clock3, ListChecks, ShieldCheck } from "lucide-react";

import { agentIcons, agentLabels } from "../components/agentVisuals";
import {
  AgentCostChart,
  AgentDurationChart,
  ChartCard,
  DataTable,
  SuccessRing,
  TaskTrendChart,
  TokenTrendChart,
  deriveAgentStats,
  deriveSuccessRate,
  deriveTaskTrend,
} from "../components/charts";
import { api } from "../lib/api";
import type { AgentName, TaskStatus } from "../types";
import styles from "./StandardPage.module.css";

const TRACE_SAMPLE = 12;

export function OperationsPage() {
  const { t } = useTranslation();
  const { data: summary } = useQuery({ queryKey: ["operations-summary"], queryFn: api.operationsSummary, refetchInterval: 3_000 });
  const { data: audit } = useQuery({ queryKey: ["audit-logs"], queryFn: () => api.auditLogs({ limit: 100 }), refetchInterval: 3_000 });
  const { data: rules } = useQuery({ queryKey: ["collaboration-rules"], queryFn: api.collaborationRules });
  const { data: taskPage } = useQuery({ queryKey: ["operations-tasks"], queryFn: () => api.tasks({ limit: 200 }), refetchInterval: 15_000 });

  const traceIds = useMemo(
    () => (taskPage?.items ?? []).map((task) => task.trace_id).filter(Boolean).slice(0, TRACE_SAMPLE),
    [taskPage],
  );
  const { data: traces = [] } = useQuery({
    queryKey: ["operations-traces", traceIds.join(",")],
    queryFn: () => Promise.all(traceIds.map((traceId) => api.trace(traceId))),
    enabled: traceIds.length > 0,
    refetchInterval: 30_000,
  });

  const trend = useMemo(() => deriveTaskTrend(taskPage?.items ?? []), [taskPage]);
  const success = useMemo(() => deriveSuccessRate(summary?.status_counts ?? ({} as Record<TaskStatus, number>)), [summary]);
  const agentStats = useMemo(() => deriveAgentStats(traces), [traces]);
  const sampleNote = t("operations.sampleNote", { count: TRACE_SAMPLE });

  const metrics = [
    { label: t("operations.tasks"), value: summary?.total_tasks ?? 0, icon: ListChecks, tone: "accent" },
    { label: t("operations.completion"), value: summary?.status_counts.completed ?? 0, icon: CheckCircle2, tone: "green" },
    { label: t("operations.approvals"), value: summary?.pending_approvals ?? 0, icon: ClipboardCheck, tone: "yellow" },
    { label: t("operations.failures"), value: summary?.status_counts.failed ?? 0, icon: AlertTriangle, tone: "red" },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.eyebrow}>{t("operations.eyebrow")}</span>
          <h1>{t("operations.title")}</h1>
          <p>{t("operations.subtitle")}</p>
        </div>
        <span className={styles.safetyBadge}><ShieldCheck size={15} />{t("operations.policyEnforced")}</span>
      </header>

      <div className={styles.metricsGrid}>
        {metrics.map(({ label, value, icon: Icon, tone }) => (
          <section key={label} className={styles.metric} data-tone={tone}>
            <span><Icon size={18} /></span>
            <div><small>{label}</small><strong>{value}</strong></div>
          </section>
        ))}
      </div>

      <div className={styles.chartGrid}>
        <div className={styles.chartSpan2}>
          <ChartCard
            title={t("operations.trendTitle")}
            chart={<TaskTrendChart data={trend} />}
            table={<DataTable headers={[t("operations.date"), t("operations.trendCreated"), t("operations.trendCompleted")]} rows={trend.map((point) => [point.label, point.created, point.completed])} />}
          />
        </div>
        <ChartCard
          title={t("operations.successTitle")}
          chart={<SuccessRing data={success} />}
          table={<DataTable headers={[t("task.completed"), t("task.failed"), t("task.canceled")]} rows={[[success.completed, success.failed, success.canceled]]} />}
        />
        <ChartCard
          title={t("operations.costTitle")}
          subtitle={sampleNote}
          chart={<AgentCostChart data={agentStats.agents} />}
          table={<DataTable headers={[t("operations.agent"), t("operations.cost")]} rows={agentStats.agents.map((item) => [agentLabels[item.agent as AgentName] ?? item.agent, item.cost])} />}
        />
        <ChartCard
          title={t("operations.durationTitle")}
          subtitle={sampleNote}
          chart={<AgentDurationChart data={agentStats.agents} />}
          table={<DataTable headers={[t("operations.agent"), t("operations.avgDuration")]} rows={agentStats.agents.filter((item) => item.avgLatencyMs != null).map((item) => [agentLabels[item.agent as AgentName] ?? item.agent, `${item.avgLatencyMs} ms`])} />}
        />
        <ChartCard
          title={t("operations.tokenTitle")}
          subtitle={sampleNote}
          chart={<TokenTrendChart data={agentStats.tokenTrend} />}
          table={<DataTable headers={[t("operations.date"), t("operations.tokens")]} rows={agentStats.tokenTrend.map((point) => [point.label, point.tokens])} />}
        />
      </div>

      <section className={styles.operationsTable}>
        <div className={styles.panelTitle}><span>{t("operations.audit")}</span><small>{audit?.total ?? 0} {t("operations.records")}</small></div>
        <div className={styles.operationHead}>
          <span>{t("operations.auditAction")}</span><span>{t("operations.auditActor")}</span><span>{t("operations.auditTask")}</span><span>{t("operations.auditDetails")}</span><span>{t("operations.auditTime")}</span>
        </div>
        {audit?.items.map((item) => (
          <div key={item.id} className={styles.operationRow}>
            <strong>{item.action}</strong>
            <span>{item.actor}</span>
            <code>{item.task_id?.slice(-10) ?? "system"}</code>
            <span>{summarize(item.details)}</span>
            <time><Clock3 size={12} />{new Date(item.created_at).toLocaleString()}</time>
          </div>
        ))}
        {!audit?.items.length && <div className={styles.inlineEmpty}>{t("common.noData")}</div>}
      </section>

      <section className={styles.rulesPanel}>
        <div className={styles.panelTitle}><span>{t("operations.ruleModel")}</span><small>{t("operations.ruleVersion", { version: rules?.version ?? "1.0" })}</small></div>
        <div className={styles.ruleSummary}>
          <span><ShieldCheck size={16} /><strong>{t("operations.failClosed")}</strong><small>{t("operations.failClosedHelp")}</small></span>
          <span><ClipboardCheck size={16} /><strong>{t("operations.qualityConsensus")}</strong><small>{t("operations.qualityConsensusHelp")}</small></span>
          <span><ListChecks size={16} /><strong>{t("operations.versionedContext")}</strong><small>{t("operations.versionedContextHelp")}</small></span>
        </div>
        <div className={styles.ruleRows}>
          {rules?.agents.map((contract) => {
            const Icon = agentIcons[contract.agent_name];
            return (
              <div key={contract.agent_name}>
                <span className={styles.ruleAgent}><Icon size={16} /><strong>{agentLabels[contract.agent_name]}</strong></span>
                <span><small>{t("operations.ruleIn")}</small>{contract.required_inputs.join(", ")}</span>
                <span><small>{t("operations.ruleOut")}</small>{contract.required_outputs.join(", ")}</span>
                <span><small>{t("operations.ruleNext")}</small>{contract.allowed_handoffs.map((name) => agentLabels[name]).join(", ") || t("operations.ruleComplete")}</span>
              </div>
            );
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
