import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Check,
  CheckCircle2,
  Clock3,
  ExternalLink,
  GitBranch,
  GitPullRequest,
  ListTree,
  MessageSquareWarning,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  User,
  X,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { ApprovalAction, ApprovalRecord, ApprovalType } from "../types";
import shared from "./StandardPage.module.css";
import styles from "./ApprovalsPage.module.css";

const typeIcons: Record<ApprovalType, typeof ListTree> = {
  plan: ListTree,
  high_risk_change: ShieldAlert,
  create_pr: GitPullRequest,
  push_branch: GitBranch,
};

type QueueTab = "pending" | "decided";

export function ApprovalsPage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [tab, setTab] = useState<QueueTab>("pending");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const { data: approvals, isLoading, error } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => api.approvals(),
    refetchInterval: 5_000,
  });

  const pending = useMemo(
    () => (approvals ?? []).filter((item) => item.status === "awaiting_approval"),
    [approvals],
  );
  const decided = useMemo(
    () => (approvals ?? []).filter((item) => item.status !== "awaiting_approval"),
    [approvals],
  );

  const visible = useMemo(() => {
    const source = tab === "pending" ? pending : decided;
    const sorted = [...source].sort(
      (a, b) => new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime(),
    );
    return typeFilter === "all" ? sorted : sorted.filter((item) => item.approval_type === typeFilter);
  }, [tab, pending, decided, typeFilter]);

  return (
    <div className={shared.page}>
      <header className={shared.pageHeader}>
        <div>
          <span className={shared.eyebrow}>Governance</span>
          <h1>{t("approvals.title")}</h1>
          <p>{t("approvals.subtitle")}</p>
        </div>
        <span className={shared.safetyBadge}>
          <ShieldCheck size={15} />
          {t("approvals.auditProtected")}
        </span>
      </header>

      <div className={styles.queueBar}>
        <div className={styles.tabs} role="tablist" aria-label={t("approvals.title")}>
          <button type="button" role="tab" aria-selected={tab === "pending"} data-active={tab === "pending"} onClick={() => setTab("pending")}>
            {t("approvals.tabPending")}
            <span className={styles.count}>{pending.length}</span>
          </button>
          <button type="button" role="tab" aria-selected={tab === "decided"} data-active={tab === "decided"} onClick={() => setTab("decided")}>
            {t("approvals.tabDecided")}
            <span className={styles.count}>{decided.length}</span>
          </button>
        </div>
        <select
          className={styles.typeFilter}
          value={typeFilter}
          onChange={(event) => setTypeFilter(event.target.value)}
          aria-label={t("approvals.typeFilterLabel")}
        >
          <option value="all">{t("approvals.allTypes")}</option>
          {(Object.keys(typeIcons) as ApprovalType[]).map((type) => (
            <option key={type} value={type}>{t(`approvals.type.${type}`)}</option>
          ))}
        </select>
      </div>

      {error instanceof Error && <div className={styles.errorBanner} role="alert">{error.message}</div>}

      {isLoading && (
        <div className={styles.cards}>
          <div className={styles.skeletonCard} />
          <div className={styles.skeletonCard} />
        </div>
      )}

      {!isLoading && visible.length === 0 && (
        <div className={styles.emptyState}>
          <span><ShieldCheck size={22} /></span>
          <strong>{tab === "pending" ? t("approvals.emptyPending") : t("approvals.emptyDecided")}</strong>
          <p>{t("approvals.emptyHint")}</p>
        </div>
      )}

      {!isLoading && visible.length > 0 && (
        <div className={styles.cards}>
          {visible.map((approval) => (
            <ApprovalCard key={approval.id} approval={approval} canDecide={can("approval:decide")} />
          ))}
        </div>
      )}
    </div>
  );
}

function ApprovalCard({ approval, canDecide }: { approval: ApprovalRecord; canDecide: boolean }) {
  const { t } = useTranslation();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [decidingAction, setDecidingAction] = useState<ApprovalAction | null>(null);
  const [comment, setComment] = useState("");

  const mutation = useMutation({
    mutationFn: (payload: { action: ApprovalAction; comment?: string }) =>
      api.decideApproval(approval.id, payload.action, payload.comment),
    onSuccess: () => {
      setDecidingAction(null);
      setComment("");
      void queryClient.invalidateQueries({ queryKey: ["approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["operations-summary"] });
    },
  });

  const Icon = typeIcons[approval.approval_type] ?? ShieldQuestion;
  const isPending = approval.status === "awaiting_approval";
  const waitMs = Date.now() - new Date(approval.requested_at).getTime();

  return (
    <article className={styles.card}>
      <div className={styles.cardTop}>
        <span className={styles.typeChip} data-type={approval.approval_type}>
          <span><Icon size={15} /></span>
          {t(`approvals.type.${approval.approval_type}`)}
        </span>
        <span className={styles.statusBadge} data-status={approval.status}>
          {approval.status === "awaiting_approval" && <Clock3 size={11} />}
          {approval.status === "completed" && <CheckCircle2 size={11} />}
          {(approval.status === "failed" || approval.status === "canceled") && <X size={11} />}
          {t(`approvals.status.${approval.status}`)}
        </span>
        {can("task:read") && (
          <Link className={styles.taskLink} to={`/tasks/${approval.task_id}`}>
            <ExternalLink size={11} />
            {approval.task_id.slice(-10)}
          </Link>
        )}
      </div>

      <div className={styles.cardBody}>
        <p className={styles.reason}>{approval.reason}</p>
        <details className={styles.rawToggle}>
          <summary>{t("approvals.rawRecord")}</summary>
          <pre>{JSON.stringify(approval, null, 2)}</pre>
        </details>
      </div>

      <div className={styles.cardMeta}>
        <span><Clock3 size={11} />{t("approvals.requestedAt")} {new Date(approval.requested_at).toLocaleString()}</span>
        {isPending && <span><ShieldQuestion size={11} />{t("approvals.waiting", { duration: formatDuration(waitMs) })}</span>}
        {approval.decided_at && (
          <span className={styles.decisionSummary}>
            <User size={11} />
            <strong>{approval.decided_by ?? "system"}</strong>
            {new Date(approval.decided_at).toLocaleString()}
            {approval.comment && ` · ${approval.comment}`}
          </span>
        )}
      </div>

      {isPending && canDecide && !decidingAction && (
        <div className={styles.cardActions}>
          <button type="button" className={styles.approveBtn} onClick={() => setDecidingAction("approve")}>
            <Check size={13} />
            {t("task.approve")}
          </button>
          <button type="button" className={styles.changesBtn} onClick={() => setDecidingAction("changes_requested")}>
            <MessageSquareWarning size={13} />
            {t("task.requestChanges")}
          </button>
          <button type="button" className={styles.rejectBtn} onClick={() => setDecidingAction("reject")}>
            <X size={13} />
            {t("task.reject")}
          </button>
        </div>
      )}

      {isPending && canDecide && decidingAction && (
        <div className={styles.commentArea}>
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder={t("approvals.commentPlaceholder")}
            aria-label={t("approvals.commentPlaceholder")}
            autoFocus
          />
          <div className={styles.commentActions}>
            <button type="button" className={styles.cancelBtn} onClick={() => { setDecidingAction(null); setComment(""); }}>
              {t("common.cancel")}
            </button>
            <button
              type="button"
              className={styles.confirmBtn}
              data-danger={decidingAction === "reject"}
              data-primary={decidingAction === "approve"}
              disabled={mutation.isPending}
              onClick={() => mutation.mutate({ action: decidingAction, comment: comment.trim() || undefined })}
            >
              {mutation.isPending
                ? t("approvals.deciding")
                : decidingAction === "approve"
                  ? t("task.approve")
                  : decidingAction === "reject"
                    ? t("task.reject")
                    : t("task.requestChanges")}
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

function formatDuration(ms: number): string {
  const minutes = Math.max(1, Math.round(ms / 60_000));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}
