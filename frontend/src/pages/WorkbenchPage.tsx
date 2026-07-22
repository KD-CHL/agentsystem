import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock3,
  FileCode2,
  GitBranch,
  History,
  MessageSquare,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  Search,
  ShieldCheck,
  Square,
  TerminalSquare,
  X,
  XCircle,
} from "lucide-react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";

import { agentIcons, agentLabels, agentOrder } from "../components/agentVisuals";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { AgentName, AgentSummary, Approval, Artifact, TaskRecord, TaskView, Trace } from "../types";
import styles from "./WorkbenchPage.module.css";

type Tab = "overview" | "artifacts" | "trace";
const ACTIVE_TASK_STATUSES = ["queued", "running", "awaiting_approval", "input_required"];

export function WorkbenchPage() {
  const { t, i18n } = useTranslation();
  const { can } = useAuth();
  const { taskId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { openTaskDrawer } = useOutletContext<{ openTaskDrawer: () => void }>();
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedAgent, setSelectedAgent] = useState<AgentName>("orchestrator");
  const [chatInput, setChatInput] = useState("");
  const [consolePaused, setConsolePaused] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<"tasks" | "agents" | null>(null);
  const [taskScope, setTaskScope] = useState<"all" | "active">("all");
  const [taskSearch, setTaskSearch] = useState("");
  const debouncedTaskSearch = useDebouncedValue(taskSearch, 250);

  const tasksQuery = useQuery({
    queryKey: ["tasks", taskScope, debouncedTaskSearch],
    queryFn: () => api.tasks({ status: taskScope === "active" ? ACTIVE_TASK_STATUSES : undefined, q: debouncedTaskSearch.trim() || undefined }),
    refetchInterval: 2_000,
  });
  const allCountQuery = useQuery({ queryKey: ["task-count", "all"], queryFn: () => api.tasks({ limit: 1 }), refetchInterval: 5_000 });
  const activeCountQuery = useQuery({ queryKey: ["task-count", "active"], queryFn: () => api.tasks({ status: ACTIVE_TASK_STATUSES, limit: 1 }), refetchInterval: 5_000 });
  const tasks = tasksQuery.data?.items ?? [];
  const selectedTaskId = taskId ?? tasks[0]?.id;
  const taskQuery = useQuery({
    queryKey: ["task", selectedTaskId],
    queryFn: () => api.task(selectedTaskId!),
    enabled: Boolean(selectedTaskId),
    refetchInterval: consolePaused ? false : 1_500,
  });
  const agentsQuery = useQuery({
    queryKey: ["agents", selectedTaskId],
    queryFn: () => api.agents(selectedTaskId),
    enabled: Boolean(selectedTaskId),
    refetchInterval: consolePaused ? false : 1_500,
  });
  const traceQuery = useQuery({
    queryKey: ["trace", taskQuery.data?.task.trace_id],
    queryFn: () => api.trace(taskQuery.data!.task.trace_id),
    enabled: Boolean(taskQuery.data?.task.trace_id),
    refetchInterval: consolePaused ? false : 2_000,
  });
  const messagesQuery = useQuery({
    queryKey: ["messages", selectedTaskId],
    queryFn: () => api.messages(selectedTaskId!),
    enabled: Boolean(selectedTaskId),
    refetchInterval: consolePaused ? false : 2_000,
  });

  useEffect(() => {
    if (!selectedTaskId) return;
    const source = new EventSource(`/api/v1/tasks/${selectedTaskId}/events?follow=true`);
    const invalidate = () => {
      void queryClient.invalidateQueries({ queryKey: ["task", selectedTaskId] });
      void queryClient.invalidateQueries({ queryKey: ["agents", selectedTaskId] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["task-count"] });
      if (taskQuery.data?.task.trace_id) {
        void queryClient.invalidateQueries({ queryKey: ["trace", taskQuery.data.task.trace_id] });
      }
    };
    ["step.started", "agent.started", "agent.completed", "agent.failed", "approval.requested", "workflow.completed", "workflow.failed", "workflow.canceled", "chat.message"].forEach((name) => source.addEventListener(name, invalidate));
    return () => source.close();
  }, [selectedTaskId, queryClient, taskQuery.data?.task.trace_id]);

  useEffect(() => {
    const current = taskQuery.data?.task.current_step;
    if (current && agentOrder.includes(current as AgentName)) setSelectedAgent(current as AgentName);
  }, [taskQuery.data?.task.current_step]);

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["task", selectedTaskId] });
    void queryClient.invalidateQueries({ queryKey: ["agents", selectedTaskId] });
    void queryClient.invalidateQueries({ queryKey: ["trace", taskQuery.data?.task.trace_id] });
  };

  const decision = useMutation({
    mutationFn: ({ approval, action }: { approval: Approval; action: "approve" | "reject" | "changes_requested" }) => api.decideApproval(approval.id, action),
    onSuccess: refresh,
  });
  const cancelTask = useMutation({ mutationFn: api.cancelTask, onSuccess: refresh });
  const rerunTask = useMutation({ mutationFn: api.rerunTask, onSuccess: refresh });
  const sendMessage = useMutation({
    mutationFn: () => api.sendMessage(selectedTaskId!, selectedAgent, chatInput.trim()),
    onSuccess: () => {
      setChatInput("");
      void queryClient.invalidateQueries({ queryKey: ["messages", selectedTaskId] });
      refresh();
    },
  });

  const pendingApproval = taskQuery.data?.approvals.find((item) => item.status === "awaiting_approval");
  const selectedAgentData = agentsQuery.data?.find((agent) => agent.agent_name === selectedAgent);

  return (
    <div className={styles.workbench}>
      <TaskSidebar
        tasks={tasks}
        total={allCountQuery.data?.total ?? tasks.length}
        activeTotal={activeCountQuery.data?.total ?? 0}
        scope={taskScope}
        search={taskSearch}
        selectedTaskId={selectedTaskId}
        open={mobilePanel === "tasks"}
        onClose={() => setMobilePanel(null)}
        onSelect={(id) => { navigate(`/tasks/${id}`); setMobilePanel(null); }}
        onNew={can("task:write") ? openTaskDrawer : undefined}
        onScope={setTaskScope}
        onSearch={setTaskSearch}
      />

      <section className={styles.workspace}>
        <div className={styles.mobileToolbar}>
          <button type="button" onClick={() => setMobilePanel("tasks")}><History size={16} />{t("workbench.taskQueue")}</button>
          <button type="button" onClick={() => setMobilePanel("agents")}><MessageSquare size={16} />{t("workbench.agents")}</button>
        </div>
        {taskQuery.data ? (
          <>
            <TaskHeader
              view={taskQuery.data}
              pendingApproval={pendingApproval}
              onDecision={(action) => pendingApproval && decision.mutate({ approval: pendingApproval, action })}
              onCancel={() => cancelTask.mutate(taskQuery.data!.task.id)}
              onRerun={() => rerunTask.mutate(taskQuery.data!.task.id)}
              onRefresh={refresh}
              canManage={can("task:write")}
              canApprove={can("approval:decide")}
            />
            <PhaseRail view={taskQuery.data} agents={agentsQuery.data ?? []} onSelectAgent={setSelectedAgent} />
            <div className={styles.tabs} role="tablist">
              {(["overview", "artifacts", "trace"] as Tab[]).map((item) => (
                <button key={item} type="button" role="tab" aria-selected={tab === item} className={tab === item ? styles.activeTab : ""} onClick={() => setTab(item)}>
                  {t(`workbench.${item}`)}
                  {item === "artifacts" && <span>{taskQuery.data!.artifacts.length}</span>}
                </button>
              ))}
            </div>
            <div className={styles.canvas}>
              {tab === "overview" && <Overview view={taskQuery.data} trace={traceQuery.data} />}
              {tab === "artifacts" && <Artifacts artifacts={taskQuery.data.artifacts} />}
              {tab === "trace" && <TraceView trace={traceQuery.data} />}
            </div>
          </>
        ) : (
          <EmptyWorkspace loading={taskQuery.isLoading || tasksQuery.isLoading} onNew={can("task:write") ? openTaskDrawer : undefined} />
        )}
      </section>

      <AgentInspector
        agents={agentsQuery.data ?? []}
        selected={selectedAgent}
        selectedData={selectedAgentData}
        messages={messagesQuery.data ?? []}
        input={chatInput}
        open={mobilePanel === "agents"}
        onClose={() => setMobilePanel(null)}
        onSelect={setSelectedAgent}
        onInput={setChatInput}
        onSend={() => chatInput.trim() && sendMessage.mutate()}
        canChat={can("task:chat")}
      />

      <EventConsole
        trace={traceQuery.data}
        paused={consolePaused}
        onToggle={() => setConsolePaused((value) => !value)}
        onRefresh={refresh}
      />
    </div>
  );
}

function TaskSidebar({ tasks, total, activeTotal, scope, search, selectedTaskId, open, onClose, onSelect, onNew, onScope, onSearch }: { tasks: TaskRecord[]; total: number; activeTotal: number; scope: "all" | "active"; search: string; selectedTaskId?: string; open: boolean; onClose: () => void; onSelect: (id: string) => void; onNew?: () => void; onScope: (scope: "all" | "active") => void; onSearch: (value: string) => void }) {
  const { t } = useTranslation();
  return (
    <aside className={`${styles.taskSidebar} ${open ? styles.mobileOpen : ""}`}>
      <div className={styles.panelHeader}>
        <span>{t("workbench.taskQueue")}</span>
        <div>
          {onNew && <button type="button" onClick={onNew} title={t("workbench.newTask")} aria-label={t("workbench.newTask")}><Plus size={15} /></button>}
          <button className={styles.mobileClose} type="button" onClick={onClose} title={t("common.close")} aria-label={t("common.close")}><X size={15} /></button>
        </div>
      </div>
      <div className={styles.queueFilters}>
        <button type="button" className={scope === "all" ? styles.filterActive : ""} onClick={() => onScope("all")}>All <span>{total}</span></button>
        <button type="button" className={scope === "active" ? styles.filterActive : ""} onClick={() => onScope("active")}>Active <span>{activeTotal}</span></button>
      </div>
      <label className={styles.taskSearch}><Search size={13} /><input value={search} onChange={(event) => onSearch(event.target.value)} placeholder={t("workbench.searchTasks")} aria-label={t("workbench.searchTasks")} /></label>
      <div className={styles.taskList}>
        {tasks.map((task) => (
          <button key={task.id} type="button" className={`${styles.taskItem} ${selectedTaskId === task.id ? styles.selectedTask : ""}`} onClick={() => onSelect(task.id)}>
            <span className={`${styles.statusDot} ${styles[`status_${task.status}`]}`} />
            <span className={styles.taskItemBody}>
              <strong>{task.prompt}</strong>
              <small><GitBranch size={11} />{task.repo_id}</small>
              <em>{formatRelative(task.updated_at)}</em>
            </span>
          </button>
        ))}
        {tasks.length === 0 && <p className={styles.emptyList}>{t("common.noData")}</p>}
      </div>
      <div className={styles.sidebarFooter}>
        <ShieldCheck size={14} />
        <span>{t("agents.providerConfigured")}</span>
      </div>
    </aside>
  );
}

function TaskHeader({ view, pendingApproval, onDecision, onCancel, onRerun, onRefresh, canManage, canApprove }: { view: TaskView; pendingApproval?: Approval; onDecision: (action: "approve" | "reject" | "changes_requested") => void; onCancel: () => void; onRerun: () => void; onRefresh: () => void; canManage: boolean; canApprove: boolean }) {
  const { t } = useTranslation();
  const terminal = ["completed", "failed", "canceled"].includes(view.task.status);
  return (
    <header className={styles.taskHeader}>
      <div className={styles.taskTitle}>
        <div className={styles.titleMeta}>
          <StatusBadge status={view.task.status} />
          <span>{view.task.id.slice(-8)}</span>
          <span><GitBranch size={12} />{view.task.base_branch}</span>
        </div>
        <h1>{view.task.prompt}</h1>
        <p>{view.task.workspace_path ?? view.task.repo_id}</p>
      </div>
      <div className={styles.taskActions}>
        {pendingApproval && canApprove && (
          <>
            <button type="button" className={styles.rejectButton} onClick={() => onDecision("reject")}><XCircle size={15} />{t("task.reject")}</button>
            <button type="button" className={styles.approveButton} onClick={() => onDecision("approve")}><CheckCircle2 size={15} />{t("task.approve")}</button>
          </>
        )}
        {canManage && (terminal ? (
          <button type="button" className={styles.commandButton} onClick={onRerun}><RotateCcw size={15} />{t("task.rerun")}</button>
        ) : (
          <button type="button" className={styles.iconCommand} onClick={onCancel} title={t("task.stop")} aria-label={t("task.stop")}><Square size={14} /></button>
        ))}
        <button type="button" className={styles.iconCommand} onClick={onRefresh} title={t("common.refresh")} aria-label={t("common.refresh")}><RefreshCw size={15} /></button>
      </div>
    </header>
  );
}

function PhaseRail({ view, agents, onSelectAgent }: { view: TaskView; agents: AgentSummary[]; onSelectAgent: (name: AgentName) => void }) {
  const statuses = new Map(agents.map((agent) => [agent.agent_name, agent.status]));
  return (
    <div className={styles.phaseRail} aria-label="Workflow stages">
      {agentOrder.map((name, index) => {
        const Icon = agentIcons[name];
        const state = statuses.get(name) ?? "pending";
        return (
          <button key={name} type="button" data-agent={name} className={`${styles.phase} ${styles[`phase_${state}`] ?? ""}`} onClick={() => onSelectAgent(name)}>
            <span className={styles.phaseIcon}><Icon size={16} /></span>
            <span><strong>{agentLabels[name]}</strong><small>{state.replaceAll("_", " ")}</small></span>
            {index < agentOrder.length - 1 && <ArrowRight className={styles.phaseArrow} size={13} />}
          </button>
        );
      })}
      <span className={styles.runMeta}>Run {view.runs.at(-1)?.attempt ?? 1}</span>
    </div>
  );
}

function Overview({ view, trace }: { view: TaskView; trace?: Trace }) {
  const { t } = useTranslation();
  const latestStep = view.steps.at(-1);
  const pending = view.approvals.find((item) => item.status === "awaiting_approval");
  const testArtifact = view.artifacts.findLast((item) => item.kind === "test_report");
  const reviewArtifact = view.artifacts.findLast((item) => item.kind === "review_report");
  return (
    <div className={styles.overviewGrid}>
      <section className={styles.objectiveBand}>
        <div>
          <span className={styles.sectionLabel}>Current objective</span>
          <h2>{view.task.prompt}</h2>
          <p>{view.task.workspace_path ? `Isolated collaboration copy of ${view.task.workspace_path}` : view.task.repo_id}</p>
        </div>
        <div className={styles.objectiveFacts}>
          <span><Clock3 size={14} />{latestStep?.name ?? view.task.current_step}</span>
          <span><GitBranch size={14} />{view.task.branch_name ?? view.task.base_branch}</span>
          <span><FileCode2 size={14} />{view.artifacts.length} artifacts</span>
        </div>
      </section>

      {(pending || view.task.failure_reason) && (
        <section className={`${styles.alertBand} ${view.task.status === "failed" ? styles.failureBand : ""}`}>
          <AlertTriangle size={18} />
          <div>
            <span>{pending ? t("workbench.currentBlocker") : view.task.failure_code}</span>
            <strong>{pending?.reason ?? view.task.failure_reason}</strong>
          </div>
        </section>
      )}

      <section className={styles.flowMap}>
        <div className={styles.sectionHeader}><span>Agent handoff map</span><small>{trace?.agent_runs.length ?? 0} agent runs</small></div>
        <div className={styles.flowNodes}>
          {agentOrder.map((name, index) => {
            const run = trace?.agent_runs.findLast((item) => item.agent_name === name);
            const Icon = agentIcons[name];
            return (
              <div key={name} className={`${styles.flowNode} ${run ? styles.flowNodeDone : ""}`} data-agent={name}>
                <span><Icon size={18} /></span>
                <strong>{agentLabels[name]}</strong>
                <small>{run?.latency_ms != null ? `${run.latency_ms}ms` : "waiting"}</small>
                {index < agentOrder.length - 1 && <i />}
              </div>
            );
          })}
        </div>
      </section>

      <section className={styles.summaryPanel}>
        <div className={styles.sectionHeader}><span>Quality gates</span><small>Deterministic</small></div>
        <GateRow label="Tests" passed={Boolean(testArtifact)} detail={testArtifact?.content ?? "Waiting for test agent"} />
        <GateRow label="Security" passed={view.steps.some((step) => step.name === "security" && step.status === "completed")} detail="Secret scan and permission policy" />
        <GateRow label="Review" passed={Boolean(reviewArtifact)} detail={reviewArtifact?.content ?? "Waiting for review agent"} />
      </section>

      <section className={styles.summaryPanel}>
        <div className={styles.sectionHeader}><span>Run facts</span><small>{view.task.trace_id.slice(-10)}</small></div>
        <dl className={styles.factList}>
          <div><dt>Policy</dt><dd>{view.task.approval_policy}</dd></div>
          <div><dt>Priority</dt><dd>{view.task.priority}</dd></div>
          <div><dt>Steps</dt><dd>{view.steps.filter((step) => step.status === "completed").length} / {agentOrder.length}</dd></div>
          <div><dt>Model calls</dt><dd>{trace?.model_calls.length ?? 0} · {trace?.model_calls.filter((call) => !call.simulated).length ?? 0} {t("common.live")} / {trace?.model_calls.filter((call) => call.simulated).length ?? 0} {t("common.simulated")}</dd></div>
          <div><dt>Tool calls</dt><dd>{trace?.tool_calls.length ?? 0}</dd></div>
          <div><dt>Next action</dt><dd>{pending ? "Human approval" : nextAction(view.task)}</dd></div>
        </dl>
      </section>
    </div>
  );
}

function GateRow({ label, passed, detail }: { label: string; passed: boolean; detail: string }) {
  return <div className={styles.gateRow}>{passed ? <CheckCircle2 size={15} /> : <Circle size={15} />}<span><strong>{label}</strong><small>{detail}</small></span><em>{passed ? "passed" : "pending"}</em></div>;
}

function Artifacts({ artifacts }: { artifacts: Artifact[] }) {
  const [selected, setSelected] = useState<string | undefined>(artifacts.at(-1)?.id);
  const artifact = artifacts.find((item) => item.id === selected) ?? artifacts[0];
  return (
    <div className={styles.artifactLayout}>
      <div className={styles.artifactList}>
        {artifacts.map((item) => (
          <button key={item.id} type="button" className={item.id === artifact?.id ? styles.selectedArtifact : ""} onClick={() => setSelected(item.id)}>
            <FileCode2 size={15} /><span><strong>{item.name}</strong><small>{item.kind}</small></span>
          </button>
        ))}
      </div>
      <pre className={styles.artifactContent}>{artifact?.content ?? "No artifact generated yet."}</pre>
    </div>
  );
}

function TraceView({ trace }: { trace?: Trace }) {
  if (!trace) return <div className={styles.loading}>Loading trace...</div>;
  return (
    <div className={styles.traceTable}>
      <div className={styles.traceHead}><span>Time</span><span>Actor</span><span>Event</span><span>Payload</span></div>
      {trace.events.toReversed().map((event) => (
        <div key={event.id} className={styles.traceRow}>
          <time>{formatTime(event.created_at)}</time><span>{event.actor}</span><strong>{event.event_type}</strong><code>{compactPayload(event.payload)}</code>
        </div>
      ))}
    </div>
  );
}

function AgentInspector({ agents, selected, selectedData, messages, input, open, onClose, onSelect, onInput, onSend, canChat }: { agents: AgentSummary[]; selected: AgentName; selectedData?: AgentSummary; messages: Array<{ id: string; role: string; content: string; agent_name: AgentName | null }>; input: string; open: boolean; onClose: () => void; onSelect: (name: AgentName) => void; onInput: (value: string) => void; onSend: () => void; canChat: boolean }) {
  const { t } = useTranslation();
  const Icon = agentIcons[selected];
  const relevantMessages = messages.filter((message) => message.agent_name === selected);
  return (
    <aside className={`${styles.inspector} ${open ? styles.mobileOpen : ""}`}>
      <div className={styles.panelHeader}>
        <span>{t("workbench.agents")}</span>
        <button className={styles.mobileClose} type="button" onClick={onClose} title={t("common.close")} aria-label={t("common.close")}><X size={15} /></button>
      </div>
      <div className={styles.agentRoster}>
        {agents.map((agent) => {
          const AgentIcon = agentIcons[agent.agent_name];
          return (
            <button key={agent.agent_name} type="button" data-agent={agent.agent_name} className={selected === agent.agent_name ? styles.selectedAgent : ""} onClick={() => onSelect(agent.agent_name)}>
              <span><AgentIcon size={16} /></span><strong>{agent.display_name}</strong><i className={`${styles.agentDot} ${styles[`agent_${agent.status}`]}`} />
            </button>
          );
        })}
      </div>
      <section className={styles.agentDetail} data-agent={selected}>
        <div className={styles.agentIdentity}>
          <span><Icon size={21} /></span>
          <div><h2>{agentLabels[selected]}</h2><p>{selectedData?.description}</p></div>
          <StatusBadge status={selectedData?.status ?? "pending"} />
        </div>
        <div className={styles.configLine}><span>Model</span><strong>{selectedData?.configuration.provider_id}/{selectedData?.configuration.model}</strong></div>
        <div className={styles.configLine}><span>Mode</span><strong className={selectedData?.configuration.call_mode === "live" ? styles.liveText : styles.simulatedText}>{selectedData?.configuration.call_mode === "live" ? t("common.live") : t("common.simulated")}</strong></div>
        <div className={styles.objectiveBox}>
          <span>Latest output</span>
          <p>{selectedData?.last_summary ?? "Waiting for this agent to receive a handoff."}</p>
        </div>
      </section>
      <section className={styles.chatPanel}>
        <div className={styles.chatHeader}><span>{t("workbench.chat")}</span><small>{agentLabels[selected]}</small></div>
        <div className={styles.messages}>
          {relevantMessages.map((message) => <div key={message.id} className={message.role === "user" ? styles.userMessage : styles.agentMessage}><small>{message.role}</small><p>{message.content}</p></div>)}
          {relevantMessages.length === 0 && <p className={styles.chatEmpty}>Send context or a question to this agent.</p>}
        </div>
        {canChat && <div className={styles.composer}>
          <textarea rows={2} value={input} onChange={(event) => onInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSend(); } }} placeholder={`Message ${agentLabels[selected]}...`} />
          <button type="button" onClick={onSend} disabled={!input.trim()} title={t("workbench.send")} aria-label={t("workbench.send")}><Send size={16} /></button>
        </div>}
      </section>
    </aside>
  );
}

function EventConsole({ trace, paused, onToggle, onRefresh }: { trace?: Trace; paused: boolean; onToggle: () => void; onRefresh: () => void }) {
  const { t } = useTranslation();
  return (
    <section className={styles.console}>
      <header>
        <span><TerminalSquare size={14} />{t("workbench.eventStream")}</span>
        <div><span className={styles.liveIndicator}><i />{paused ? "Paused" : "Live"}</span><button type="button" onClick={onRefresh} title={t("common.refresh")} aria-label={t("common.refresh")}><RefreshCw size={13} /></button><button type="button" onClick={onToggle} title={paused ? "Resume" : "Pause"} aria-label={paused ? "Resume" : "Pause"}>{paused ? <Play size={13} /> : <Pause size={13} />}</button></div>
      </header>
      <div className={styles.consoleRows}>
        {trace?.events.toReversed().slice(0, 40).map((event) => (
          <div key={event.id}><time>{formatTime(event.created_at)}</time><strong data-agent={event.actor}>{event.actor}</strong><span>{event.event_type}</span><code>{compactPayload(event.payload)}</code></div>
        ))}
        {!trace?.events.length && <p>No task events yet.</p>}
      </div>
    </section>
  );
}

function EmptyWorkspace({ loading, onNew }: { loading: boolean; onNew?: () => void }) {
  const { t } = useTranslation();
  return <div className={styles.emptyWorkspace}><span><TerminalSquare size={26} /></span><h1>{loading ? "Loading..." : t("workbench.selectTask")}</h1><p>{t("settings.providerExecutionHelp")}</p>{onNew && <button type="button" onClick={onNew}><Plus size={16} />{t("workbench.newTask")}</button>}</div>;
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const translated = t(`task.${status}`, { defaultValue: status.replaceAll("_", " ") });
  return <span className={`${styles.statusBadge} ${styles[`badge_${status}`]}`}><i />{translated}</span>;
}

function nextAction(task: TaskRecord): string {
  if (task.status === "completed") return task.pr_url ? "Review draft PR" : "Inspect artifacts";
  if (task.status === "failed") return "Review failure and rerun";
  if (task.status === "input_required") return "Provide requested changes";
  return task.current_step.replaceAll("_", " ");
}

function formatRelative(value: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date(value));
}

function compactPayload(payload: Record<string, unknown>): string {
  const value = Object.entries(payload).slice(0, 3).map(([key, item]) => `${key}=${typeof item === "object" ? JSON.stringify(item) : item}`).join(" · ");
  return value.length > 150 ? `${value.slice(0, 147)}...` : value;
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
