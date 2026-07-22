import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Bot, CornerDownLeft, FolderGit2, History, LayoutGrid, ListTodo, Search } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { fuzzyScore } from "../lib/fuzzy";
import { safeStorage } from "../lib/storage";
import { navItems } from "../layout/navItems";
import styles from "./CommandPalette.module.css";

const RECENT_KEY = "agentsystem-palette-recent";
const MAX_RECENT = 6;

interface PaletteItem {
  id: string;
  kind: "page" | "task" | "project" | "agent";
  label: string;
  hint?: string;
  status?: string;
  to: string;
  group: string;
}

interface RecentEntry {
  kind: PaletteItem["kind"];
  id: string;
  label: string;
  hint?: string;
  to: string;
}

function loadRecent(): RecentEntry[] {
  try {
    const raw = safeStorage.get(RECENT_KEY);
    return raw ? (JSON.parse(raw) as RecentEntry[]) : [];
  } catch {
    return [];
  }
}

function saveRecent(entries: RecentEntry[]): void {
  safeStorage.set(RECENT_KEY, JSON.stringify(entries.slice(0, MAX_RECENT)));
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const { can } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setDebouncedQuery("");
      setSelectedIndex(0);
      const timer = window.setTimeout(() => inputRef.current?.focus(), 20);
      return () => window.clearTimeout(timer);
    }
  }, [open]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), 200);
    return () => window.clearTimeout(timer);
  }, [query]);

  const { data: taskPage } = useQuery({
    queryKey: ["palette-tasks", debouncedQuery],
    queryFn: () => api.tasks({ q: debouncedQuery || undefined, limit: 8 }),
    enabled: open && can("task:read"),
    placeholderData: (previous) => previous,
  });
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: api.projects, enabled: open });
  const { data: agents = [] } = useQuery({ queryKey: ["palette-agents"], queryFn: () => api.agents(), enabled: open && can("agent:read") });

  const groups = useMemo(() => {
    const result: Array<{ label: string; items: PaletteItem[] }> = [];
    const q = debouncedQuery.trim();

    if (!q) {
      const recent = loadRecent();
      if (recent.length > 0) {
        result.push({
          label: t("palette.recent"),
          items: recent.map((entry) => ({
            id: `${entry.kind}:${entry.id}`,
            kind: entry.kind,
            label: entry.label,
            hint: entry.hint,
            to: entry.to,
            group: t("palette.recent"),
          })),
        });
      }
    }

    const pageItems: PaletteItem[] = navItems
      .filter((item) => !item.permission || can(item.permission))
      .map((item) => ({
        id: `page:${item.key}`,
        kind: "page" as const,
        label: t(`nav.${item.key}`),
        hint: item.to,
        to: item.to,
        group: t("palette.pages"),
      }))
      .filter((item) => !q || fuzzyScore(q, `${item.label} ${item.hint ?? ""}`) !== null);
    if (pageItems.length > 0) result.push({ label: t("palette.pages"), items: pageItems });

    if (can("task:read")) {
      const tasks = taskPage?.items ?? [];
      const taskItems: PaletteItem[] = tasks
        .map((task) => ({
          id: `task:${task.id}`,
          kind: "task" as const,
          label: task.prompt,
          hint: task.id.slice(-10),
          status: task.status,
          to: `/tasks/${task.id}`,
          group: t("palette.tasks"),
        }))
        .filter((item) => !q || fuzzyScore(q, `${item.label} ${item.hint ?? ""}`) !== null)
        .slice(0, 6);
      if (taskItems.length > 0) result.push({ label: t("palette.tasks"), items: taskItems });
    }

    if (can("project:read")) {
      const projectItems: PaletteItem[] = projects
        .map((project) => ({
          id: `project:${project.id}`,
          kind: "project" as const,
          label: project.name,
          hint: project.path,
          to: "/projects",
          group: t("palette.projects"),
        }))
        .filter((item) => !q || fuzzyScore(q, `${item.label} ${item.hint ?? ""}`) !== null)
        .slice(0, 5);
      if (projectItems.length > 0) result.push({ label: t("palette.projects"), items: projectItems });
    }

    if (can("agent:read")) {
      const agentItems: PaletteItem[] = agents
        .map((agent) => ({
          id: `agent:${agent.agent_name}`,
          kind: "agent" as const,
          label: agent.display_name,
          hint: agent.description,
          to: "/agents",
          group: t("palette.agents"),
        }))
        .filter((item) => !q || fuzzyScore(q, `${item.label} ${item.hint ?? ""}`) !== null)
        .slice(0, 5);
      if (agentItems.length > 0) result.push({ label: t("palette.agents"), items: agentItems });
    }

    return result;
  }, [debouncedQuery, taskPage, projects, agents, can, t]);

  const flatItems = useMemo(() => groups.flatMap((group) => group.items), [groups]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [debouncedQuery]);

  if (!open) return null;

  const selectItem = (item: PaletteItem) => {
    const entry: RecentEntry = { kind: item.kind, id: item.id.split(":").slice(1).join(":"), label: item.label, hint: item.hint, to: item.to };
    const recent = [entry, ...loadRecent().filter((existing) => !(existing.kind === entry.kind && existing.id === entry.id))];
    saveRecent(recent);
    onClose();
    navigate(item.to);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelectedIndex((index) => (flatItems.length === 0 ? 0 : (index + 1) % flatItems.length));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelectedIndex((index) => (flatItems.length === 0 ? 0 : (index - 1 + flatItems.length) % flatItems.length));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const item = flatItems[selectedIndex];
      if (item) selectItem(item);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  };

  let flatIndex = -1;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-label={t("palette.open")}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className={styles.inputRow}>
          <Search size={16} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("palette.placeholder")}
            aria-label={t("palette.placeholder")}
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-results"
          />
          <kbd>esc</kbd>
        </div>

        <div className={styles.results} id="palette-results" role="listbox" ref={listRef} aria-label={t("palette.open")}>
          {flatItems.length === 0 && <div className={styles.noResults}>{t("palette.noResults")}</div>}
          {groups.map((group) => (
            <div key={group.label}>
              <div className={styles.groupLabel}>{group.label}</div>
              {group.items.map((item) => {
                flatIndex += 1;
                const isSelected = flatIndex === selectedIndex;
                const Icon = kindIcon(item.kind);
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    className={styles.item}
                    data-selected={isSelected}
                    onMouseEnter={() => setSelectedIndex(flatIndex)}
                    onClick={() => selectItem(item)}
                  >
                    <Icon size={15} />
                    <span className={styles.itemBody}>
                      <span className={styles.itemLabel}>{item.label}</span>
                      {item.hint && <span className={styles.itemHint}>{item.hint}</span>}
                    </span>
                    {item.status && <span className={styles.itemStatus}>{item.status.replace(/_/g, " ")}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className={styles.footer}>
          <span><kbd>↑</kbd><kbd>↓</kbd>{t("palette.navigate")}</span>
          <span><kbd><CornerDownLeft size={9} /></kbd>{t("palette.select")}</span>
          <span><kbd>esc</kbd>{t("palette.dismiss")}</span>
        </div>
      </div>
    </div>
  );
}

function kindIcon(kind: PaletteItem["kind"]) {
  switch (kind) {
    case "page":
      return LayoutGrid;
    case "task":
      return ListTodo;
    case "project":
      return FolderGit2;
    case "agent":
      return Bot;
    default:
      return History;
  }
}
