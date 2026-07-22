import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  CheckCircle2,
  CircleAlert,
  Eye,
  EyeOff,
  FlaskConical,
  KeyRound,
  RefreshCw,
  Save,
  ShieldCheck,
  TerminalSquare,
  Trash2,
  Wifi,
  X,
} from "lucide-react";

import { agentIcons, agentLabels } from "../components/agentVisuals";
import { api } from "../lib/api";
import type { AgentConfiguration, AgentName, ApiFormat } from "../types";
import styles from "./StandardPage.module.css";

type ActivityEntry = { time: string; text: string; ok: boolean };

export function AgentStudioPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: () => api.agents() });
  const { data: providers = [] } = useQuery({ queryKey: ["model-providers"], queryFn: api.modelProviders });
  const { data: credentials = [] } = useQuery({ queryKey: ["credentials"], queryFn: api.credentials });
  const [selected, setSelected] = useState<AgentName>("orchestrator");
  const selectedAgent = agents.find((agent) => agent.agent_name === selected);
  const [form, setForm] = useState<AgentConfiguration | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [credentialFormOpen, setCredentialFormOpen] = useState(false);
  const [credentialName, setCredentialName] = useState("");
  const [credentialSecret, setCredentialSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);

  useEffect(() => {
    if (selectedAgent) {
      setForm(selectedAgent.configuration);
      setDiscoveredModels([]);
    }
  }, [selectedAgent]);

  const selectedProvider = providers.find((provider) => provider.id === form?.provider_id);
  const modelSuggestions = useMemo(
    () => [...new Set([...(selectedProvider?.models ?? []), ...discoveredModels])],
    [selectedProvider, discoveredModels],
  );

  const addActivity = (text: string, ok = true) => {
    setActivity((items) => [{ time: now(), text, ok }, ...items].slice(0, 60));
  };

  const save = useMutation({
    mutationFn: (configuration: AgentConfiguration) => api.updateAgent(selected, configurationPayload(configuration)),
    onSuccess: async (configuration) => {
      setForm(configuration);
      addActivity(`${agentLabels[selected]}: ${t("agents.saved")}`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agents"] }),
        queryClient.invalidateQueries({ queryKey: ["system"] }),
      ]);
    },
    onError: (error: Error) => addActivity(`${agentLabels[selected]}: ${error.message}`, false),
  });

  const validate = useMutation({
    mutationFn: async (configuration: AgentConfiguration) => {
      await api.updateAgent(selected, configurationPayload(configuration));
      return api.validateAgent(selected);
    },
    onSuccess: async (result) => {
      if (result.models.length) setDiscoveredModels(result.models);
      addActivity(`${agentLabels[selected]}: ${result.message}`, result.valid);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agents"] }),
        queryClient.invalidateQueries({ queryKey: ["system"] }),
      ]);
    },
    onError: (error: Error) => addActivity(`${agentLabels[selected]}: ${error.message}`, false),
  });

  const discover = useMutation({
    mutationFn: async (configuration: AgentConfiguration) => {
      await api.updateAgent(selected, configurationPayload(configuration));
      return api.discoverAgentModels(selected);
    },
    onSuccess: async (result) => {
      setDiscoveredModels(result.models);
      addActivity(t("agents.modelsFound", { count: result.models.length }), result.models.length > 0);
      await queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (error: Error) => addActivity(`${t("agents.modelDiscovery")}: ${error.message}`, false),
  });

  const createCredential = useMutation({
    mutationFn: () => api.createCredential({ name: credentialName.trim(), secret: credentialSecret }),
    onSuccess: async (credential) => {
      setForm((current) => current ? { ...current, credential_ref: credential.id, credential_available: true } : current);
      setCredentialName("");
      setCredentialSecret("");
      setShowSecret(false);
      setCredentialFormOpen(false);
      addActivity(t("agents.credentialStored", { name: credential.name }));
      await queryClient.invalidateQueries({ queryKey: ["credentials"] });
    },
    onError: (error: Error) => addActivity(`${t("agents.credential")}: ${error.message}`, false),
  });

  const deleteCredential = useMutation({
    mutationFn: api.deleteCredential,
    onSuccess: async (credential) => {
      setForm((current) => current?.credential_ref === credential.id
        ? { ...current, credential_ref: null, credential_available: false }
        : current);
      addActivity(t("agents.credentialDeleted", { name: credential.name }));
      await queryClient.invalidateQueries({ queryKey: ["credentials"] });
    },
    onError: (error: Error) => addActivity(`${t("agents.credential")}: ${error.message}`, false),
  });

  const changeProvider = (providerId: string) => {
    if (!form) return;
    const provider = providers.find((item) => item.id === providerId);
    if (!provider) return;
    setDiscoveredModels([]);
    setForm({
      ...form,
      provider_id: provider.id,
      model: provider.default_model,
      base_url: provider.default_base_url,
      api_format: provider.default_api_format,
      call_mode: provider.id === "simulated" ? "simulated" : "live",
      credential_ref: provider.requires_credential ? form.credential_ref : null,
    });
  };

  const busy = save.isPending || validate.isPending || discover.isPending;

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div><span className={styles.eyebrow}>Configuration / Agents</span><h1>{t("agents.title")}</h1><p>{t("agents.subtitle")}</p></div>
        <span className={styles.safetyBadge}><ShieldCheck size={15} />{t("agents.providerConfigured")}</span>
      </header>

      <div className={styles.studioLayout}>
        <aside className={styles.agentListPanel}>
          <div className={styles.panelTitle}><span>Agent roster</span><small>{agents.length}</small></div>
          <div className={styles.studioAgentRows}>
            {agents.map((agent) => {
              const Icon = agentIcons[agent.agent_name];
              return (
                <button key={agent.agent_name} type="button" className={agent.agent_name === selected ? styles.selectedRow : ""} onClick={() => setSelected(agent.agent_name)}>
                  <span className={styles.agentIcon}><Icon size={18} /></span>
                  <span><strong>{agent.display_name}</strong><small>{agent.configuration.provider_id}/{agent.configuration.model}</small></span>
                  <i className={agent.configuration.call_mode === "live" ? styles.liveDot : styles.readyDot} />
                </button>
              );
            })}
          </div>
        </aside>

        <section className={styles.configurationPanel}>
          <div className={styles.panelTitle}><span>{agentLabels[selected]} configuration</span><small>v{form?.version ?? 1}</small></div>
          {form && (
            <div className={styles.configForm}>
              <div className={`${styles.formNotice} ${form.call_mode === "live" ? styles.liveNotice : ""}`}>
                {form.call_mode === "live" ? <Wifi size={17} /> : <FlaskConical size={17} />}
                <span>
                  <strong>{form.call_mode === "live" ? t("common.live") : t("common.simulated")}</strong>
                  <small>{selectedProvider?.description ?? t("agents.customProviderHelp")}</small>
                </span>
              </div>

              <div className={styles.formGrid}>
                <label>
                  <span>{t("agents.provider")}</span>
                  <select value={form.provider_id} onChange={(event) => changeProvider(event.target.value)}>
                    {!providers.some((provider) => provider.id === form.provider_id) && <option value={form.provider_id}>{form.provider_id} (custom)</option>}
                    {providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.display_name}</option>)}
                  </select>
                </label>
                <label>
                  <span>{t("agents.mode")}</span>
                  <select value={form.call_mode} onChange={(event) => setForm({ ...form, call_mode: event.target.value as AgentConfiguration["call_mode"] })} disabled={form.provider_id === "simulated"}>
                    <option value="live">{t("common.live")}</option>
                    <option value="simulated">{t("common.simulated")}</option>
                  </select>
                </label>
                <label>
                  <span>{t("agents.model")}</span>
                  <input list={`models-${selected}`} value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} autoComplete="off" />
                  <datalist id={`models-${selected}`}>{modelSuggestions.map((model) => <option key={model} value={model} />)}</datalist>
                </label>
                <label>
                  <span>{t("agents.apiFormat")}</span>
                  <select value={form.api_format} onChange={(event) => setForm({ ...form, api_format: event.target.value as ApiFormat })}>
                    {(selectedProvider?.supported_api_formats ?? ["responses", "chat_completions"]).map((format) => (
                      <option key={format} value={format}>{format === "responses" ? "Responses API" : "Chat Completions"}</option>
                    ))}
                  </select>
                </label>
                <label className={styles.fullField}>
                  <span>{t("agents.endpoint")}</span>
                  <input value={form.base_url ?? ""} onChange={(event) => setForm({ ...form, base_url: event.target.value || null })} placeholder="https://gateway.internal/v1" />
                </label>
                <label>
                  <span>{t("agents.credential")}</span>
                  <select value={form.credential_ref ?? ""} onChange={(event) => setForm({ ...form, credential_ref: event.target.value || null })}>
                    <option value="">{selectedProvider?.requires_credential ? t("agents.selectCredential") : t("agents.noCredential")}</option>
                    {credentials.map((credential) => <option key={credential.id} value={credential.id}>{credential.name} · {credential.fingerprint}</option>)}
                  </select>
                </label>
                <label>
                  <span>{t("agents.apiKeyEnv")}</span>
                  <input value={form.api_key_env ?? ""} onChange={(event) => setForm({ ...form, api_key_env: event.target.value || null })} placeholder="CODING_AGENT_API_KEY" autoCapitalize="none" />
                </label>
                <label>
                  <span>{t("agents.timeout")}</span>
                  <input type="number" min={5} max={600} value={form.timeout_seconds} onChange={(event) => setForm({ ...form, timeout_seconds: Number(event.target.value) })} />
                </label>
                <label>
                  <span>{t("agents.maxOutputTokens")}</span>
                  <input type="number" min={64} max={131072} step={64} value={form.max_output_tokens} onChange={(event) => setForm({ ...form, max_output_tokens: Number(event.target.value) })} />
                </label>
                <label>
                  <span>{t("agents.budget")}</span>
                  <input type="number" min={0} step="0.1" value={form.budget_limit ?? ""} onChange={(event) => setForm({ ...form, budget_limit: event.target.value ? Number(event.target.value) : null })} />
                </label>
              </div>

              <section className={styles.credentialSection} aria-labelledby="credential-heading">
                <div className={styles.credentialHeader}>
                  <span><KeyRound size={15} /><span><strong id="credential-heading">{t("agents.credentialVault")}</strong><small>{t("agents.credentialHelp")}</small></span></span>
                  <button type="button" className={styles.secondaryButton} onClick={() => setCredentialFormOpen((open) => !open)}>
                    {credentialFormOpen ? <X size={14} /> : <KeyRound size={14} />}
                    {credentialFormOpen ? t("common.cancel") : t("agents.addCredential")}
                  </button>
                </div>
                {credentialFormOpen && (
                  <div className={styles.credentialForm}>
                    <label><span>{t("agents.credentialName")}</span><input value={credentialName} onChange={(event) => setCredentialName(event.target.value)} placeholder="OpenAI production" /></label>
                    <label><span>{t("agents.apiKey")}</span><span className={styles.secretInput}><input type={showSecret ? "text" : "password"} value={credentialSecret} onChange={(event) => setCredentialSecret(event.target.value)} autoComplete="new-password" /><button type="button" onClick={() => setShowSecret((value) => !value)} title={showSecret ? t("agents.hideKey") : t("agents.showKey")} aria-label={showSecret ? t("agents.hideKey") : t("agents.showKey")}>{showSecret ? <EyeOff size={14} /> : <Eye size={14} />}</button></span></label>
                    <button type="button" className={styles.primaryButton} onClick={() => createCredential.mutate()} disabled={credentialName.trim().length < 1 || credentialSecret.length < 8 || createCredential.isPending}><Save size={14} />{t("agents.storeCredential")}</button>
                  </div>
                )}
                {credentials.length > 0 && (
                  <div className={styles.credentialRows}>
                    {credentials.map((credential) => (
                      <div key={credential.id} className={styles.credentialRow}>
                        <KeyRound size={13} />
                        <span><strong>{credential.name}</strong><small>{credential.fingerprint} · {credential.backend}</small></span>
                        <i title={credential.available ? t("agents.credentialAvailable") : t("agents.credentialMissing")}>{credential.available ? <CheckCircle2 size={13} /> : <CircleAlert size={13} />}</i>
                        <button type="button" onClick={() => window.confirm(t("agents.deleteCredentialConfirm", { name: credential.name })) && deleteCredential.mutate(credential.id)} title={t("agents.deleteCredential")} aria-label={t("agents.deleteCredential")}><Trash2 size={13} /></button>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <div className={styles.formActions}>
                {selectedProvider?.supports_model_discovery && form.call_mode === "live" && (
                  <button type="button" className={styles.secondaryButton} onClick={() => discover.mutate(form)} disabled={busy}><RefreshCw size={15} />{t("agents.modelDiscovery")}</button>
                )}
                <button type="button" className={styles.secondaryButton} onClick={() => validate.mutate(form)} disabled={busy}><FlaskConical size={15} />{t("common.validate")}</button>
                <button type="button" className={styles.primaryButton} onClick={() => save.mutate(form)} disabled={busy}><Save size={15} />{t("common.save")}</button>
              </div>
              {(save.error || validate.error || discover.error || createCredential.error || deleteCredential.error) && <p className={styles.formError}>{((save.error ?? validate.error ?? discover.error ?? createCredential.error ?? deleteCredential.error) as Error).message}</p>}
            </div>
          )}
        </section>

        <section className={styles.activityPanel}>
          <div className={styles.panelTitle}><span><TerminalSquare size={13} /> Configuration console</span><small>{t("agents.localConsole")}</small></div>
          <div className={styles.activityRows}>
            {activity.map((item, index) => <div className={item.ok ? "" : styles.activityError} key={`${item.time}-${index}`}><time>{item.time}</time>{item.ok ? <CheckCircle2 size={13} /> : <CircleAlert size={13} />}<span>{item.text}</span></div>)}
            {!activity.length && <p>{t("agents.consoleEmpty")}</p>}
          </div>
        </section>
      </div>
    </div>
  );
}

function configurationPayload(configuration: AgentConfiguration) {
  return {
    provider_id: configuration.provider_id,
    model: configuration.model,
    credential_ref: configuration.credential_ref,
    api_key_env: configuration.api_key_env,
    base_url: configuration.base_url,
    api_format: configuration.api_format,
    call_mode: configuration.call_mode,
    timeout_seconds: configuration.timeout_seconds,
    max_output_tokens: configuration.max_output_tokens,
    budget_limit: configuration.budget_limit,
  };
}

function now(): string {
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date());
}
