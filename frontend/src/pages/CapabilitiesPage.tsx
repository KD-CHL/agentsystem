import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Bot,
  Cable,
  Check,
  CheckCircle2,
  CircleAlert,
  FileCode2,
  FolderOpen,
  KeyRound,
  Network,
  Plus,
  RefreshCw,
  Save,
  ServerCog,
  ShieldCheck,
  TerminalSquare,
  Trash2,
  Wrench,
} from "lucide-react";

import { agentIcons, agentLabels } from "../components/agentVisuals";
import { api } from "../lib/api";
import type {
  AgentCapabilitySet,
  AgentName,
  CapabilityStatus,
  McpServer,
  McpTransport,
  Skill,
} from "../types";
import pageStyles from "./StandardPage.module.css";
import styles from "./CapabilitiesPage.module.css";

const agentNames: AgentName[] = [
  "orchestrator",
  "repo_context",
  "planning",
  "coding",
  "test",
  "security",
  "review",
  "pr",
];

type RegistryTab = "mcp" | "skills";
type Notice = { text: string; ok: boolean } | null;

type McpDraft = {
  name: string;
  description: string;
  transport: McpTransport;
  url: string;
  command: string;
  argsText: string;
  credential_ref: string;
  credential_header: string;
  credential_scheme: string;
  credential_env: string;
  toolAllowlistText: string;
  approval_policy: "always" | "never";
  enabled: boolean;
  timeout_seconds: number;
};

const emptyDraft: McpDraft = {
  name: "",
  description: "",
  transport: "streamable_http",
  url: "http://127.0.0.1:3001/mcp",
  command: "",
  argsText: "",
  credential_ref: "",
  credential_header: "Authorization",
  credential_scheme: "Bearer",
  credential_env: "",
  toolAllowlistText: "",
  approval_policy: "always",
  enabled: false,
  timeout_seconds: 15,
};

export function CapabilitiesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: servers = [], isLoading: serversLoading } = useQuery({ queryKey: ["mcp-servers"], queryFn: api.mcpServers });
  const { data: skills = [], isLoading: skillsLoading } = useQuery({ queryKey: ["skills"], queryFn: api.skills });
  const { data: policy } = useQuery({ queryKey: ["capability-policy"], queryFn: api.capabilityPolicy });
  const { data: credentials = [] } = useQuery({ queryKey: ["credentials"], queryFn: api.credentials });
  const capabilityQueries = useQueries({
    queries: agentNames.map((name) => ({
      queryKey: ["agent-capabilities", name],
      queryFn: () => api.agentCapabilities(name),
    })),
  });
  const [tab, setTab] = useState<RegistryTab>("mcp");
  const [selectedMcpId, setSelectedMcpId] = useState<string | null>(null);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [creatingServer, setCreatingServer] = useState(false);
  const [draft, setDraft] = useState<McpDraft>(emptyDraft);
  const [notice, setNotice] = useState<Notice>(null);

  const selectedServer = servers.find((item) => item.id === selectedMcpId) ?? null;
  const selectedSkill = skills.find((item) => item.id === selectedSkillId) ?? null;
  const selectedCapability = tab === "mcp" ? selectedServer : selectedSkill;

  useEffect(() => {
    if (!creatingServer && !selectedMcpId && servers.length) setSelectedMcpId(servers[0].id);
  }, [creatingServer, selectedMcpId, servers]);

  useEffect(() => {
    if (!selectedSkillId && skills.length) setSelectedSkillId(skills[0].id);
  }, [selectedSkillId, skills]);

  useEffect(() => {
    if (selectedServer && !creatingServer) setDraft(serverToDraft(selectedServer));
  }, [creatingServer, selectedServer]);

  const refreshRegistry = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] }),
      queryClient.invalidateQueries({ queryKey: ["skills"] }),
      queryClient.invalidateQueries({ queryKey: ["agents"] }),
    ]);
  };

  const createServer = useMutation({
    mutationFn: () => api.createMcpServer(mcpPayload(draft)),
    onSuccess: async (server) => {
      setCreatingServer(false);
      setSelectedMcpId(server.id);
      setNotice({ text: t("capabilities.serverCreated"), ok: true });
      await refreshRegistry();
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const saveServer = useMutation({
    mutationFn: () => api.updateMcpServer(selectedMcpId ?? "", mcpPayload(draft)),
    onSuccess: async (server) => {
      setDraft(serverToDraft(server));
      setNotice({ text: t("capabilities.serverSaved"), ok: true });
      await refreshRegistry();
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const validateServer = useMutation({
    mutationFn: (id: string) => api.validateMcpServer(id),
    onSuccess: async (result) => {
      setNotice({
        text: result.valid ? t("capabilities.validationPassed", { count: result.tools.length }) : result.message,
        ok: result.valid,
      });
      await refreshRegistry();
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const deleteServer = useMutation({
    mutationFn: api.deleteMcpServer,
    onSuccess: async () => {
      setSelectedMcpId(null);
      setNotice({ text: t("capabilities.serverDeleted"), ok: true });
      await refreshRegistry();
      await queryClient.invalidateQueries({ queryKey: ["agent-capabilities"] });
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const importSkill = useMutation({
    mutationFn: api.pickSkill,
    onSuccess: async (result) => {
      if ("id" in result) {
        setTab("skills");
        setSelectedSkillId(result.id);
        setNotice({ text: t("capabilities.skillImported"), ok: true });
        await refreshRegistry();
      } else {
        setNotice({ text: t("capabilities.folderCanceled"), ok: true });
      }
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const refreshSkill = useMutation({
    mutationFn: api.refreshSkill,
    onSuccess: async () => {
      setNotice({ text: t("capabilities.skillRefreshed"), ok: true });
      await refreshRegistry();
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const updateSkill = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.updateSkill(id, enabled),
    onSuccess: refreshRegistry,
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const deleteSkill = useMutation({
    mutationFn: api.deleteSkill,
    onSuccess: async () => {
      setSelectedSkillId(null);
      setNotice({ text: t("capabilities.skillDeleted"), ok: true });
      await refreshRegistry();
      await queryClient.invalidateQueries({ queryKey: ["agent-capabilities"] });
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const bindingMutation = useMutation({
    mutationFn: ({ agentName, checked }: { agentName: AgentName; checked: boolean }) => {
      const index = agentNames.indexOf(agentName);
      const current = capabilityQueries[index].data;
      if (!current || !selectedCapability) throw new Error(t("capabilities.selectItem"));
      const mcpIds = new Set(current.mcp_servers.map((item) => item.id));
      const skillIds = new Set(current.skills.map((item) => item.id));
      const target = tab === "mcp" ? mcpIds : skillIds;
      if (checked) target.add(selectedCapability.id);
      else target.delete(selectedCapability.id);
      return api.updateAgentCapabilities(agentName, {
        mcp_server_ids: [...mcpIds],
        skill_ids: [...skillIds],
      });
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(["agent-capabilities", result.agent_name], result);
      setNotice({ text: t("capabilities.bindingSaved"), ok: true });
      await queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (error: Error) => setNotice({ text: error.message, ok: false }),
  });

  const bindingStates = useMemo(() => agentNames.map((name, index) => {
    const data = capabilityQueries[index].data;
    const bound = selectedCapability
      ? (tab === "mcp" ? data?.mcp_servers : data?.skills)?.some((item) => item.id === selectedCapability.id) ?? false
      : false;
    return { name, bound, loading: capabilityQueries[index].isLoading };
  }), [capabilityQueries, selectedCapability, tab]);
  const boundCount = bindingStates.filter((item) => item.bound).length;
  const serverBusy = createServer.isPending || saveServer.isPending || validateServer.isPending || deleteServer.isPending;

  const startServer = () => {
    setTab("mcp");
    setCreatingServer(true);
    setSelectedMcpId(null);
    setDraft(emptyDraft);
    setNotice(null);
  };

  return (
    <div className={pageStyles.page}>
      <header className={pageStyles.pageHeader}>
        <div>
          <span className={pageStyles.eyebrow}>Configuration / Capabilities</span>
          <h1>{t("capabilities.title")}</h1>
          <p>{t("capabilities.subtitle")}</p>
        </div>
        <span className={pageStyles.safetyBadge}><ShieldCheck size={15} />{t("capabilities.safeRegistry")}</span>
      </header>

      <div className={styles.layout}>
        <aside className={styles.registryPanel}>
          <div className={styles.tabs} role="tablist" aria-label={t("capabilities.title")}>
            <button type="button" role="tab" aria-selected={tab === "mcp"} className={tab === "mcp" ? styles.activeTab : ""} onClick={() => setTab("mcp")}><Cable size={15} />{t("capabilities.mcp")}</button>
            <button type="button" role="tab" aria-selected={tab === "skills"} className={tab === "skills" ? styles.activeTab : ""} onClick={() => setTab("skills")}><FileCode2 size={15} />{t("capabilities.skills")}</button>
          </div>
          <div className={styles.registryAction}>
            {tab === "mcp" ? (
              <button type="button" onClick={startServer}><Plus size={14} />{t("capabilities.addServer")}</button>
            ) : (
              <button type="button" onClick={() => importSkill.mutate()} disabled={importSkill.isPending}><FolderOpen size={14} />{t("capabilities.importSkill")}</button>
            )}
          </div>
          <div className={styles.registryList}>
            {tab === "mcp" && servers.map((server) => (
              <button key={server.id} type="button" className={server.id === selectedMcpId && !creatingServer ? styles.selectedRow : ""} onClick={() => { setCreatingServer(false); setSelectedMcpId(server.id); }}>
                <span className={styles.itemIcon}><ServerCog size={17} /></span>
                <span><strong>{server.name}</strong><small>{server.transport === "streamable_http" ? hostLabel(server.url) : server.command}</small></span>
                <StatusDot status={server.status} />
              </button>
            ))}
            {tab === "skills" && skills.map((skill) => (
              <button key={skill.id} type="button" className={skill.id === selectedSkillId ? styles.selectedRow : ""} onClick={() => setSelectedSkillId(skill.id)}>
                <span className={styles.itemIcon} data-kind="skill"><FileCode2 size={17} /></span>
                <span><strong>{skill.name}</strong><small>{skill.version ? `v${skill.version}` : skill.content_hash.slice(0, 8)}</small></span>
                <StatusDot status={skill.status} />
              </button>
            ))}
            {tab === "mcp" && !serversLoading && !servers.length && !creatingServer && <EmptyState icon={Cable} text={t("capabilities.noMcp")} />}
            {tab === "skills" && !skillsLoading && !skills.length && <EmptyState icon={FileCode2} text={t("capabilities.noSkills")} />}
          </div>
          <section className={styles.policyBlock} aria-label={t("capabilities.policy")}>
            <div><Network size={13} /><span>{policy?.network_enabled ? t("capabilities.networkAllowed") : t("capabilities.networkBlocked")}</span></div>
            <small>{t("capabilities.allowedHosts")}: {policy?.allowed_hosts.join(", ") ?? "..."}</small>
            <div><TerminalSquare size={13} /><span>{policy?.stdio_enabled ? t("capabilities.stdioAllowed") : t("capabilities.stdioBlocked")}</span></div>
          </section>
        </aside>

        <main className={styles.detailPanel}>
          {tab === "mcp" && (selectedServer || creatingServer) && (
            <McpEditor
              draft={draft}
              setDraft={setDraft}
              server={selectedServer}
              creating={creatingServer}
              credentials={credentials}
              busy={serverBusy}
              onSave={() => creatingServer ? createServer.mutate() : saveServer.mutate()}
              onValidate={() => selectedServer && validateServer.mutate(selectedServer.id)}
              onDelete={() => selectedServer && window.confirm(t("capabilities.deleteServerConfirm", { name: selectedServer.name })) && deleteServer.mutate(selectedServer.id)}
            />
          )}
          {tab === "skills" && selectedSkill && (
            <SkillDetail
              skill={selectedSkill}
              busy={refreshSkill.isPending || updateSkill.isPending || deleteSkill.isPending}
              onToggle={(enabled) => updateSkill.mutate({ id: selectedSkill.id, enabled })}
              onRefresh={() => refreshSkill.mutate(selectedSkill.id)}
              onDelete={() => window.confirm(t("capabilities.deleteSkillConfirm", { name: selectedSkill.name })) && deleteSkill.mutate(selectedSkill.id)}
            />
          )}
          {!selectedCapability && !creatingServer && <EmptyState icon={Wrench} text={t("capabilities.selectItem")} large />}
        </main>

        <aside className={styles.bindingPanel}>
          <div className={styles.panelHeading}>
            <span><Bot size={14} />{t("capabilities.agentBindings")}</span>
            <small>{selectedCapability ? t("capabilities.boundCount", { count: boundCount }) : "-"}</small>
          </div>
          <p className={styles.bindingHelp}>{t("capabilities.bindingsHelp")}</p>
          <div className={styles.bindingRows}>
            {bindingStates.map(({ name, bound, loading }) => {
              const Icon = agentIcons[name];
              return (
                <label key={name} className={bound ? styles.boundAgent : ""}>
                  <span className={styles.agentIcon}><Icon size={16} /></span>
                  <span><strong>{agentLabels[name]}</strong><small>{name}</small></span>
                  <input
                    type="checkbox"
                    checked={bound}
                    disabled={!selectedCapability || loading || bindingMutation.isPending}
                    onChange={(event) => bindingMutation.mutate({ agentName: name, checked: event.target.checked })}
                  />
                  <span className={styles.checkboxVisual} aria-hidden="true">{bound && <Check size={12} />}</span>
                </label>
              );
            })}
          </div>
          <div className={styles.credentialNote}><KeyRound size={14} /><span>{t("capabilities.localCredentialHelp")}</span></div>
        </aside>
      </div>

      {notice && <div className={`${styles.notice} ${notice.ok ? styles.noticeSuccess : styles.noticeError}`} role="status">{notice.ok ? <CheckCircle2 size={15} /> : <CircleAlert size={15} />}<span>{notice.text}</span><button type="button" onClick={() => setNotice(null)} aria-label={t("common.close")}>×</button></div>}
    </div>
  );
}

function McpEditor({
  draft,
  setDraft,
  server,
  creating,
  credentials,
  busy,
  onSave,
  onValidate,
  onDelete,
}: {
  draft: McpDraft;
  setDraft: (value: McpDraft) => void;
  server: McpServer | null;
  creating: boolean;
  credentials: Array<{ id: string; name: string; fingerprint: string }>;
  busy: boolean;
  onSave: () => void;
  onValidate: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className={styles.detailScroll}>
      <div className={styles.panelHeading}>
        <span><ServerCog size={14} />{creating ? t("capabilities.newServer") : t("capabilities.serverConfiguration")}</span>
        {server && <StatusBadge status={server.status} />}
      </div>
      <form className={styles.editorForm} onSubmit={(event) => { event.preventDefault(); onSave(); }}>
        <div className={styles.formGrid}>
          <label><span>{t("capabilities.name")}</span><input required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
          <label><span>{t("capabilities.transport")}</span><select value={draft.transport} onChange={(event) => setDraft({ ...draft, transport: event.target.value as McpTransport })}><option value="streamable_http">Streamable HTTP</option><option value="stdio">stdio</option></select></label>
          <label className={styles.fullField}><span>{t("capabilities.description")}</span><input value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
          {draft.transport === "streamable_http" ? (
            <>
              <label className={styles.fullField}><span>{t("capabilities.endpoint")}</span><input required type="url" value={draft.url} onChange={(event) => setDraft({ ...draft, url: event.target.value })} placeholder="http://127.0.0.1:3001/mcp" /></label>
              <label><span>{t("capabilities.credentialHeader")}</span><input value={draft.credential_header} onChange={(event) => setDraft({ ...draft, credential_header: event.target.value })} /></label>
              <label><span>{t("capabilities.credentialScheme")}</span><input value={draft.credential_scheme} onChange={(event) => setDraft({ ...draft, credential_scheme: event.target.value })} /></label>
            </>
          ) : (
            <>
              <label><span>{t("capabilities.command")}</span><input required value={draft.command} onChange={(event) => setDraft({ ...draft, command: event.target.value })} placeholder="npx" /></label>
              <label><span>{t("capabilities.credentialEnv")}</span><input value={draft.credential_env} onChange={(event) => setDraft({ ...draft, credential_env: event.target.value })} placeholder="MCP_SERVER_TOKEN" /></label>
              <label className={styles.fullField}><span>{t("capabilities.arguments")}</span><textarea value={draft.argsText} onChange={(event) => setDraft({ ...draft, argsText: event.target.value })} rows={3} /><small>{t("capabilities.argumentsHelp")}</small></label>
            </>
          )}
          <label><span>{t("capabilities.credential")}</span><select value={draft.credential_ref} onChange={(event) => setDraft({ ...draft, credential_ref: event.target.value })}><option value="">{t("capabilities.noCredential")}</option>{credentials.map((credential) => <option key={credential.id} value={credential.id}>{credential.name} · {credential.fingerprint}</option>)}</select></label>
          <label><span>{t("capabilities.timeout")}</span><input type="number" min={2} max={120} value={draft.timeout_seconds} onChange={(event) => setDraft({ ...draft, timeout_seconds: Number(event.target.value) })} /></label>
          <label><span>{t("capabilities.approvalPolicy")}</span><select value={draft.approval_policy} onChange={(event) => setDraft({ ...draft, approval_policy: event.target.value as McpDraft["approval_policy"] })}><option value="always">{t("capabilities.alwaysApprove")}</option><option value="never">{t("capabilities.directInvoke")}</option></select></label>
          <label className={styles.toggleField}><span><strong>{t("capabilities.enabled")}</strong><small>{t("capabilities.enabledHelp")}</small></span><input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} /><i aria-hidden="true" /></label>
          <label className={styles.fullField}><span>{t("capabilities.toolAllowlist")}</span><textarea value={draft.toolAllowlistText} onChange={(event) => setDraft({ ...draft, toolAllowlistText: event.target.value })} rows={3} /><small>{t("capabilities.toolAllowlistHelp")}</small></label>
        </div>
        <div className={styles.formActions}>
          {!creating && <button type="button" className={styles.dangerButton} onClick={onDelete} disabled={busy}><Trash2 size={14} />{t("capabilities.deleteServer")}</button>}
          <span />
          {!creating && <button type="button" className={styles.secondaryButton} onClick={onValidate} disabled={busy}><Network size={14} />{t("capabilities.validateServer")}</button>}
          <button type="submit" className={styles.primaryButton} disabled={busy || !draft.name.trim()}><Save size={14} />{creating ? t("capabilities.createServer") : t("common.save")}</button>
        </div>
      </form>
      {!creating && server && (
        <section className={styles.toolSection}>
          <div className={styles.sectionTitle}><span><Wrench size={13} />{t("capabilities.tools")}</span><small>{server.tools.length}</small></div>
          {server.tools.length ? <div className={styles.toolRows}>{server.tools.map((tool) => <div key={tool.name}><code>{tool.name}</code><span>{tool.description || "-"}</span></div>)}</div> : <p className={styles.inlineEmpty}>{t("capabilities.noTools")}</p>}
          {server.last_error && <p className={styles.inlineError}><CircleAlert size={13} />{server.last_error}</p>}
        </section>
      )}
    </div>
  );
}

function SkillDetail({ skill, busy, onToggle, onRefresh, onDelete }: { skill: Skill; busy: boolean; onToggle: (enabled: boolean) => void; onRefresh: () => void; onDelete: () => void }) {
  const { t } = useTranslation();
  return (
    <div className={styles.detailScroll}>
      <div className={styles.panelHeading}><span><FileCode2 size={14} />{t("capabilities.skillDetails")}</span><StatusBadge status={skill.status} /></div>
      <div className={styles.skillSummary}>
        <div className={styles.skillTitle}><span className={styles.largeSkillIcon}><FileCode2 size={22} /></span><span><h2>{skill.name}</h2><p>{skill.description || "-"}</p></span></div>
        <label className={styles.toggleField}><span><strong>{t("capabilities.enabled")}</strong><small>{t("capabilities.enabledHelp")}</small></span><input type="checkbox" checked={skill.enabled} disabled={busy} onChange={(event) => onToggle(event.target.checked)} /><i aria-hidden="true" /></label>
        <dl className={styles.metadata}>
          <div><dt>{t("capabilities.source")}</dt><dd title={skill.source_path}>{skill.source_path}</dd></div>
          <div><dt>{t("capabilities.hash")}</dt><dd><code>{skill.content_hash}</code></dd></div>
          <div><dt>{t("capabilities.version")}</dt><dd>{skill.version ?? "-"}</dd></div>
        </dl>
        <section className={styles.instructions}>
          <div className={styles.sectionTitle}><span><FileCode2 size={13} />{t("capabilities.instructions")}</span></div>
          <pre tabIndex={0}>{skill.instructions}</pre>
        </section>
        {skill.last_error && <p className={styles.inlineError}><CircleAlert size={13} />{skill.last_error}</p>}
        <div className={styles.skillActions}>
          <button type="button" className={styles.dangerButton} onClick={onDelete} disabled={busy}><Trash2 size={14} />{t("capabilities.deleteSkill")}</button>
          <button type="button" className={styles.secondaryButton} onClick={onRefresh} disabled={busy}><RefreshCw size={14} />{t("capabilities.refreshSkill")}</button>
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: CapabilityStatus }) {
  return <i className={styles.statusDot} data-status={status} title={status} />;
}

function StatusBadge({ status }: { status: CapabilityStatus }) {
  const { t } = useTranslation();
  return <span className={styles.statusBadge} data-status={status}><StatusDot status={status} />{t(`capabilities.status.${status}`)}</span>;
}

function EmptyState({ icon: Icon, text, large = false }: { icon: typeof Cable; text: string; large?: boolean }) {
  return <div className={`${styles.emptyState} ${large ? styles.largeEmpty : ""}`}><Icon size={large ? 26 : 20} /><span>{text}</span></div>;
}

function serverToDraft(server: McpServer): McpDraft {
  return {
    name: server.name,
    description: server.description,
    transport: server.transport,
    url: server.url ?? "",
    command: server.command ?? "",
    argsText: server.args.join("\n"),
    credential_ref: server.credential_ref ?? "",
    credential_header: server.credential_header,
    credential_scheme: server.credential_scheme,
    credential_env: server.credential_env ?? "",
    toolAllowlistText: server.tool_allowlist.join("\n"),
    approval_policy: server.approval_policy,
    enabled: server.enabled,
    timeout_seconds: server.timeout_seconds,
  };
}

function mcpPayload(draft: McpDraft): Record<string, unknown> {
  return {
    name: draft.name.trim(),
    description: draft.description.trim(),
    transport: draft.transport,
    url: draft.transport === "streamable_http" ? draft.url.trim() : null,
    command: draft.transport === "stdio" ? draft.command.trim() : null,
    args: draft.transport === "stdio" ? lines(draft.argsText) : [],
    credential_ref: draft.credential_ref || null,
    credential_header: draft.credential_header.trim(),
    credential_scheme: draft.credential_scheme.trim(),
    credential_env: draft.transport === "stdio" ? draft.credential_env.trim() || null : null,
    tool_allowlist: lines(draft.toolAllowlistText),
    approval_policy: draft.approval_policy,
    enabled: draft.enabled,
    timeout_seconds: draft.timeout_seconds,
  };
}

function lines(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function hostLabel(url: string | null): string {
  if (!url) return "Streamable HTTP";
  try { return new URL(url).host; } catch { return url; }
}
