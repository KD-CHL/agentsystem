import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Activity,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  KeyRound,
  Languages,
  Laptop,
  LockKeyhole,
  LogOut,
  Moon,
  Palette,
  ServerCog,
  ShieldCheck,
  Sun,
  UserRound,
  UsersRound,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LANGUAGE_KEY } from "../i18n";
import { api } from "../lib/api";
import { safeStorage } from "../lib/storage";
import { getThemePreference, setThemePreference, type ThemePreference } from "../lib/theme";
import styles from "./SettingsPage.module.css";

type SavedPreference = "theme" | "language" | null;

const themeOptions = [
  ["dark", Moon, "dark"],
  ["light", Sun, "light"],
  ["system", Laptop, "system"],
] as const;

const languageOptions = [
  ["zh", "中文", "简体中文"],
  ["en", "English", "English (US)"],
] as const;

export function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { session, can, logout } = useAuth();
  const systemQuery = useQuery({ queryKey: ["system"], queryFn: api.system, refetchInterval: 5_000 });
  const [theme, setTheme] = useState<ThemePreference>(getThemePreference());
  const [language, setLanguage] = useState<"zh" | "en">(i18n.language.startsWith("en") ? "en" : "zh");
  const [savedPreference, setSavedPreference] = useState<SavedPreference>(null);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);

  const system = systemQuery.data;
  const executionMode = system?.execution_mode;
  const totalAgents = system ? system.live_agent_count + system.simulated_agent_count : null;

  const changeTheme = (value: ThemePreference) => {
    setTheme(value);
    setThemePreference(value);
    setSavedPreference("theme");
  };

  const changeLanguage = (value: "zh" | "en") => {
    setLanguage(value);
    safeStorage.set(LANGUAGE_KEY, value);
    void i18n.changeLanguage(value);
    document.documentElement.lang = value === "zh" ? "zh-CN" : "en";
    setSavedPreference("language");
  };

  const signOut = async () => {
    setSigningOut(true);
    setSignOutError(null);
    try {
      await logout();
    } catch (error) {
      setSignOutError(error instanceof Error ? error.message : t("settings.signOutFailed"));
      setSigningOut(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <span className={styles.eyebrow}>System / Preferences</span>
          <h1>{t("settings.title")}</h1>
          <p>{t("settings.subtitle")}</p>
        </div>
        <div className={styles.headerStatus}>
          <span className={styles.autoSave}><CheckCircle2 size={14} />{t("settings.autoSave")}</span>
          <span className={styles.executionBadge} data-mode={executionMode ?? "loading"}>
            <i />
            {executionMode ? t(`common.${executionMode}`) : t("settings.loadingStatus")}
          </span>
        </div>
      </header>

      <div className={styles.settingsFrame}>
        <aside className={styles.settingsNav}>
          <span className={styles.navTitle}>{t("settings.sections")}</span>
          <nav aria-label={t("settings.sections")}>
            <a href="#interface"><Palette size={17} /><span><strong>{t("settings.interface")}</strong><small>{t("settings.interfaceNavHelp")}</small></span></a>
            <a href="#runtime"><ShieldCheck size={17} /><span><strong>{t("settings.runtimeSecurity")}</strong><small>{t("settings.runtimeNavHelp")}</small></span></a>
            <a href="#account"><UserRound size={17} /><span><strong>{t("settings.account")}</strong><small>{t("settings.accountNavHelp")}</small></span></a>
          </nav>
          <div className={styles.localNotice}>
            <LockKeyhole size={16} />
            <span><strong>{t("settings.localFirst")}</strong><small>{t("settings.localFirstHelp")}</small></span>
          </div>
        </aside>

        <main className={styles.settingsContent}>
          <section id="interface" className={styles.settingsSection} aria-labelledby="interface-heading">
            <header className={styles.sectionHeader}>
              <span className={styles.sectionIcon}><Palette size={18} /></span>
              <div><h2 id="interface-heading">{t("settings.interface")}</h2><p>{t("settings.interfaceHelp")}</p></div>
            </header>

            <div className={styles.preferenceRow}>
              <div className={styles.rowCopy}><h3>{t("settings.theme")}</h3><p>{t("settings.themeHelp")}</p></div>
              <div className={`${styles.choiceGrid} ${styles.themeGrid}`} role="radiogroup" aria-label={t("settings.theme")}>
                {themeOptions.map(([value, Icon, key]) => (
                  <button key={value} type="button" role="radio" aria-checked={theme === value} className={theme === value ? styles.choiceActive : ""} onClick={() => changeTheme(value)}>
                    <Icon size={17} />
                    <span><strong>{t(`settings.${key}`)}</strong><small>{t(`settings.${key}Help`)}</small></span>
                    {theme === value && <Check size={14} />}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.preferenceRow}>
              <div className={styles.rowCopy}><h3>{t("settings.language")}</h3><p>{t("settings.languageHelp")}</p></div>
              <div className={`${styles.choiceGrid} ${styles.languageGrid}`} role="radiogroup" aria-label={t("settings.language")}>
                {languageOptions.map(([value, label, detail]) => (
                  <button key={value} type="button" role="radio" aria-checked={language === value} className={language === value ? styles.choiceActive : ""} onClick={() => changeLanguage(value)}>
                    <Languages size={17} />
                    <span><strong>{label}</strong><small>{detail}</small></span>
                    {language === value && <Check size={14} />}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.feedbackSlot} aria-live="polite">
              {savedPreference && <span><CheckCircle2 size={14} />{t("settings.savedLocally")}</span>}
            </div>
          </section>

          <section id="runtime" className={styles.settingsSection} aria-labelledby="runtime-heading">
            <header className={styles.sectionHeader}>
              <span className={styles.sectionIcon}><ServerCog size={18} /></span>
              <div><h2 id="runtime-heading">{t("settings.runtimeSecurity")}</h2><p>{t("settings.runtimeSecurityHelp")}</p></div>
            </header>

            <div className={styles.runtimeSummary} aria-label={t("settings.runtimeSummary")}>
              <div><span>{t("settings.executionMode")}</span><strong>{executionMode ? t(`common.${executionMode}`) : "—"}</strong><small>{systemQuery.error ? t("settings.statusUnavailable") : t("settings.executionModeHelp")}</small></div>
              <div><span>{t("settings.agentRouting")}</span><strong>{totalAgents ?? "—"}</strong><small>{system ? t("settings.agentRoutingValue", { live: system.live_agent_count, simulated: system.simulated_agent_count }) : t("settings.loadingStatus")}</small></div>
              <div><span>{t("settings.workflowWorker")}</span><strong>{system ? t(system.worker_running ? "common.running" : "common.idle") : "—"}</strong><small>{system ? t(system.worker_running ? "settings.workerRunningHelp" : "settings.workerIdleHelp") : t("settings.loadingStatus")}</small></div>
            </div>

            <div className={styles.settingRows}>
              <div className={styles.settingRow}>
                <span className={styles.rowIcon}><Bot size={17} /></span>
                <div className={styles.rowCopy}><h3>{t("settings.providerExecution")}</h3><p>{t("settings.providerExecutionHelp")}</p></div>
                {can("agent:manage") ? <Link className={styles.rowAction} to="/agents">{t("settings.openAgentStudio")}<ChevronRight size={15} /></Link> : <span className={styles.statusPill}>{t("settings.readOnly")}</span>}
              </div>
              <div className={styles.settingRow}>
                <span className={styles.rowIcon}><ShieldCheck size={17} /></span>
                <div className={styles.rowCopy}><h3>{t("settings.workspaceIsolation")}</h3><p>{t("settings.workspaceIsolationHelp")}</p></div>
                <span className={styles.statusPill} data-tone="success"><Check size={13} />{t("settings.enforced")}</span>
              </div>
              <div className={styles.settingRow}>
                <span className={styles.rowIcon}><KeyRound size={17} /></span>
                <div className={styles.rowCopy}><h3>{t("settings.credentialSecurity")}</h3><p>{t("settings.credentialSecurityHelp")}</p></div>
                <span className={styles.statusPill} data-tone="success"><LockKeyhole size={13} />{t("settings.keychain")}</span>
              </div>
            </div>
          </section>

          <section id="account" className={styles.settingsSection} aria-labelledby="account-heading">
            <header className={styles.sectionHeader}>
              <span className={styles.sectionIcon}><UserRound size={18} /></span>
              <div><h2 id="account-heading">{t("settings.account")}</h2><p>{t("settings.identityHelp")}</p></div>
            </header>

            <div className={styles.accountProfile}>
              <span className={styles.avatar}>{initials(session.user.display_name)}</span>
              <span><strong>{session.user.display_name}</strong><small>@{session.user.username}</small></span>
              <span className={styles.statusPill} data-tone="success"><CheckCircle2 size={13} />{session.user.status}</span>
            </div>

            <dl className={styles.sessionGrid}>
              <div><dt>{t("settings.tenant")}</dt><dd>{session.user.tenant_id}</dd></div>
              <div><dt>{t("settings.role")}</dt><dd>{session.user.role}</dd></div>
              <div><dt>{t("settings.authMode")}</dt><dd>{session.auth_mode}</dd></div>
              <div><dt>{t("settings.version")}</dt><dd>{system?.version ?? "—"}</dd></div>
            </dl>

            <div className={styles.accountActions}>
              <span><ShieldCheck size={16} /><span><strong>{t("settings.sessionProtected")}</strong><small>{t("settings.sessionProtectedHelp")}</small></span></span>
              <div>
                {can("user:manage") && <Link className={styles.secondaryAction} to="/users"><UsersRound size={15} />{t("settings.manageUsers")}</Link>}
                <button className={styles.signOutButton} type="button" onClick={() => void signOut()} disabled={signingOut}><LogOut size={15} />{t(signingOut ? "settings.signingOut" : "auth.signOut")}</button>
              </div>
            </div>
            {signOutError && <p className={styles.errorMessage} role="alert">{signOutError}</p>}
          </section>
        </main>
      </div>
    </div>
  );
}

function initials(value: string): string {
  return value.split(/\s+/).filter(Boolean).slice(0, 2).map((item) => item[0]).join("").toUpperCase() || "U";
}
