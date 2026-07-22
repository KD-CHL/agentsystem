import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Activity,
  Boxes,
  LogOut,
  Moon,
  Plus,
  Search,
  Sun,
} from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { CommandPalette } from "../components/CommandPalette";
import { NewTaskDrawer } from "../components/NewTaskDrawer";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { applyTheme, getThemePreference, setThemePreference, THEME_CHANGE_EVENT, type ThemePreference } from "../lib/theme";
import { navItems } from "./navItems";
import styles from "./AppShell.module.css";

export function AppShell() {
  const { t } = useTranslation();
  const { session, can, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [theme, setTheme] = useState(getThemePreference());
  const [accountOpen, setAccountOpen] = useState(false);
  const { data: system } = useQuery({ queryKey: ["system"], queryFn: api.system, refetchInterval: 5_000 });
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const executionMode = system?.execution_mode ?? "simulated";

  useEffect(() => setAccountOpen(false), [location.pathname]);
  useEffect(() => {
    const syncTheme = (event: Event) => setTheme((event as CustomEvent<ThemePreference>).detail);
    window.addEventListener(THEME_CHANGE_EVENT, syncTheme);
    return () => window.removeEventListener(THEME_CHANGE_EVENT, syncTheme);
  }, []);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const toggleTheme = () => {
    const currentDark = document.documentElement.dataset.theme === "dark";
    const next = currentDark ? "light" : "dark";
    setTheme(next);
    setThemePreference(next);
    applyTheme(next);
  };

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true"><Boxes size={19} /></span>
          <span className={styles.brandText}>AGENT<span>SYSTEM</span></span>
        </div>
        <div className={styles.headerContext}>
          <span className={styles.contextLabel}>Workspace</span>
          <strong>{projects[0]?.name ?? "Local"}</strong>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.modeBadge} data-mode={executionMode}>
            <span className={styles.modeDot} />
            {t(`common.${executionMode}`)}
          </span>
          <span className={styles.workerState} title={system?.worker_running ? t("common.running") : t("common.idle")}>
            <Activity size={14} />
            {system?.worker_running ? t("common.running") : t("common.idle")}
          </span>
          <button className={styles.searchButton} type="button" onClick={() => setPaletteOpen(true)} aria-label={t("palette.open")} title={t("palette.open")}>
            <Search size={15} />
            <span className={styles.searchLabel}>{t("palette.search")}</span>
            <kbd>⌘K</kbd>
          </button>
          <button className={styles.iconButton} type="button" onClick={toggleTheme} title={document.documentElement.dataset.theme === "dark" ? t("settings.light") : t("settings.dark")} aria-label={t("settings.theme")} data-preference={theme}>
            {document.documentElement.dataset.theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>
          {can("task:write") && (
            <button className={styles.primaryAction} type="button" onClick={() => setDrawerOpen(true)} aria-label={t("workbench.newTask")} title={t("workbench.newTask")}>
              <Plus size={16} />
              <span>{t("workbench.newTask")}</span>
            </button>
          )}
          <div className={styles.accountWrap}>
            <button className={styles.avatar} type="button" onClick={() => setAccountOpen((value) => !value)} onKeyDown={(event) => event.key === "Escape" && setAccountOpen(false)} aria-haspopup="menu" aria-expanded={accountOpen} aria-label={t("auth.accountMenu")}>{initials(session.user.display_name)}</button>
            {accountOpen && (
              <div className={styles.accountMenu} role="menu">
                <div><strong>{session.user.display_name}</strong><small>@{session.user.username} · {session.user.role}</small></div>
                <button type="button" role="menuitem" onClick={() => void logout()}><LogOut size={14} />{t("auth.signOut")}</button>
              </div>
            )}
          </div>
        </div>
      </header>

      <nav className={styles.rail} aria-label="Primary">
        <div className={styles.railItems}>
          {navItems.filter((item) => !item.permission || can(item.permission)).map((item) => {
            const { to, icon: Icon, key, end = false } = item;
            return (
            <NavLink
              key={key}
              to={to}
              end={end}
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ""}`}
              title={t(`nav.${key}`)}
              aria-label={t(`nav.${key}`)}
            >
              <Icon size={20} strokeWidth={1.8} />
              <span>{t(`nav.${key}`)}</span>
            </NavLink>
            );
          })}
        </div>
      </nav>

      <main className={styles.main}>
        <Outlet context={{ openTaskDrawer: () => setDrawerOpen(true) }} />
      </main>

      <NewTaskDrawer
        open={drawerOpen && can("task:write")}
        onClose={() => setDrawerOpen(false)}
        onCreated={(taskId) => {
          setDrawerOpen(false);
          navigate(`/tasks/${taskId}`);
        }}
      />

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

function initials(value: string): string {
  return value.split(/\s+/).filter(Boolean).slice(0, 2).map((item) => item[0]).join("").toUpperCase() || "U";
}
