import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight, File, FileCode2, Folder, FolderOpen, HardDrive, RefreshCw } from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import type { ProjectFile } from "../types";
import styles from "./StandardPage.module.css";

export function ProjectsPage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const { data: projects = [], isLoading } = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [selectedProjectId, setSelectedProjectId] = useState<string>();
  const [directory, setDirectory] = useState("");
  const [selectedFile, setSelectedFile] = useState<string>();

  useEffect(() => {
    if (!selectedProjectId && projects[0]) setSelectedProjectId(projects[0].id);
  }, [projects, selectedProjectId]);

  const filesQuery = useQuery({
    queryKey: ["project-files", selectedProjectId, directory],
    queryFn: () => api.projectFiles(selectedProjectId!, directory),
    enabled: Boolean(selectedProjectId),
  });
  const fileQuery = useQuery({
    queryKey: ["project-file", selectedProjectId, selectedFile],
    queryFn: () => api.projectFile(selectedProjectId!, selectedFile!),
    enabled: Boolean(selectedProjectId && selectedFile),
  });
  const pickProject = useMutation({
    mutationFn: api.pickProject,
    onSuccess: async (result) => {
      if ("id" in result) {
        await queryClient.invalidateQueries({ queryKey: ["projects"] });
        setSelectedProjectId(result.id);
        setDirectory("");
        setSelectedFile(undefined);
      }
    },
  });
  const project = projects.find((item) => item.id === selectedProjectId);
  const crumbs = directory ? directory.split("/") : [];

  const openItem = (item: ProjectFile) => {
    if (item.kind === "directory") {
      setDirectory(item.path);
      setSelectedFile(undefined);
    } else {
      setSelectedFile(item.path);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div><span className={styles.eyebrow}>Workspace / Projects</span><h1>{t("projects.title")}</h1><p>{t("drawer.projectHint")}</p></div>
        {can("project:write") && (
          <button type="button" className={styles.primaryButton} onClick={() => pickProject.mutate()} disabled={pickProject.isPending}>
            <FolderOpen size={16} />{t("projects.add")}
          </button>
        )}
      </header>

      <div className={styles.projectLayout}>
        <aside className={styles.listPanel}>
          <div className={styles.panelTitle}><span>Projects</span><small>{projects.length}</small></div>
          <div className={styles.projectRows}>
            {projects.map((item) => (
              <button key={item.id} type="button" className={item.id === selectedProjectId ? styles.selectedRow : ""} onClick={() => { setSelectedProjectId(item.id); setDirectory(""); setSelectedFile(undefined); }}>
                <span className={styles.projectIcon}><HardDrive size={17} /></span>
                <span><strong>{item.name}</strong><small>{item.path}</small></span>
                <em>{item.file_count}</em>
              </button>
            ))}
            {!projects.length && !isLoading && <div className={styles.inlineEmpty}>{t("projects.empty")}</div>}
          </div>
        </aside>

        <section className={styles.filePanel}>
          <div className={styles.panelTitle}>
            <div className={styles.breadcrumbs}>
              <button type="button" onClick={() => { setDirectory(""); setSelectedFile(undefined); }}>{project?.name ?? t("projects.files")}</button>
              {crumbs.map((crumb, index) => (
                <span key={`${crumb}-${index}`}><ChevronRight size={11} /><button type="button" onClick={() => { setDirectory(crumbs.slice(0, index + 1).join("/")); setSelectedFile(undefined); }}>{crumb}</button></span>
              ))}
            </div>
            <button type="button" className={styles.iconButton} onClick={() => filesQuery.refetch()} title={t("common.refresh")} aria-label={t("common.refresh")}><RefreshCw size={14} /></button>
          </div>
          {directory && (
            <button type="button" className={styles.parentRow} onClick={() => { setDirectory(crumbs.slice(0, -1).join("/")); setSelectedFile(undefined); }}><ChevronLeft size={14} />Parent directory</button>
          )}
          <div className={styles.fileRows}>
            {filesQuery.data?.map((item) => (
              <button key={item.path} type="button" className={item.path === selectedFile ? styles.selectedFile : ""} onClick={() => openItem(item)}>
                {item.kind === "directory" ? <Folder size={16} /> : <File size={16} />}
                <span>{item.name}</span>
                <small>{item.size_bytes == null ? "" : formatBytes(item.size_bytes)}</small>
                {item.kind === "directory" && <ChevronRight size={13} />}
              </button>
            ))}
          </div>
        </section>

        <section className={styles.previewPanel}>
          <div className={styles.panelTitle}><span>{t("projects.preview")}</span>{fileQuery.data && <small>{fileQuery.data.truncated ? "truncated" : "complete"}</small>}</div>
          {fileQuery.data ? (
            <><div className={styles.previewPath}><FileCode2 size={14} />{fileQuery.data.path}</div><pre>{fileQuery.data.content}</pre></>
          ) : (
            <div className={styles.previewEmpty}><FileCode2 size={24} /><span>Select a text or code file</span></div>
          )}
        </section>
      </div>
      {pickProject.error && <div className={styles.toastError}>{(pickProject.error as Error).message}</div>}
    </div>
  );
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
