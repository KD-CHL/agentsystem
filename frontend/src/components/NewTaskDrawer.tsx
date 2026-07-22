import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { ArrowLeft, ArrowRight, Check, FolderOpen, ShieldCheck, X } from "lucide-react";
import { z } from "zod";

import { api, ApiError } from "../lib/api";
import styles from "./NewTaskDrawer.module.css";

const schema = z.object({
  projectId: z.string().min(1),
  prompt: z.string().min(5).max(8_000),
  baseBranch: z.string().min(1).max(120),
  approvalPolicy: z.enum(["manual_plan", "manual_all", "auto"]),
  priority: z.enum(["low", "normal", "high"]),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (taskId: string) => void;
}

export function NewTaskDrawer({ open, onClose, onCreated }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: api.projects, enabled: open });
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      projectId: "",
      prompt: "",
      baseBranch: "main",
      approvalPolicy: "manual_plan",
      priority: "normal",
    },
  });
  const selectedProject = useMemo(
    () => projects.find((project) => project.id === form.watch("projectId")),
    [projects, form.watch("projectId")],
  );

  useEffect(() => {
    if (!open) return;
    setStep(0);
    setPickerError(null);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (!form.getValues("projectId") && projects[0]) {
      form.setValue("projectId", projects[0].id, { shouldValidate: true });
    }
  }, [projects, form]);

  const pickProject = useMutation({
    mutationFn: api.pickProject,
    onSuccess: async (result) => {
      if ("id" in result) {
        await queryClient.invalidateQueries({ queryKey: ["projects"] });
        form.setValue("projectId", result.id, { shouldValidate: true });
        setPickerError(null);
      }
    },
    onError: (error: ApiError) => setPickerError(error.message),
  });

  const createTask = useMutation({
    mutationFn: (values: FormValues) => {
      const project = projects.find((item) => item.id === values.projectId);
      if (!project) throw new ApiError("Project is required", "PROJECT_REQUIRED");
      return api.createTask({
        repo_id: `local/${project.name}`,
        base_branch: values.baseBranch,
        prompt: values.prompt,
        workspace_path: project.path,
        approval_policy: values.approvalPolicy,
        priority: values.priority,
      });
    },
    onSuccess: async (view) => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      form.reset();
      onCreated(view.task.id);
    },
  });

  if (!open) return null;

  const next = async () => {
    const valid = step === 0 ? await form.trigger("projectId") : await form.trigger("prompt");
    if (valid) setStep((value) => Math.min(2, value + 1));
  };

  return (
    <div className={styles.backdrop} role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="new-task-title">
        <header className={styles.header}>
          <div>
            <span className={styles.eyebrow}>{t("agents.providerConfigured")}</span>
            <h2 id="new-task-title">{t("drawer.title")}</h2>
          </div>
          <button type="button" className={styles.iconButton} onClick={onClose} aria-label={t("common.close")} title={t("common.close")}>
            <X size={18} />
          </button>
        </header>

        <ol className={styles.steps} aria-label="Task creation progress">
          {["project", "requirement", "policy"].map((key, index) => (
            <li key={key} className={index <= step ? styles.stepActive : ""} aria-current={index === step ? "step" : undefined}>
              <span>{index < step ? <Check size={13} /> : index + 1}</span>
              {t(`drawer.${key}`)}
            </li>
          ))}
        </ol>

        <form className={styles.form} onSubmit={form.handleSubmit((values) => createTask.mutate(values))}>
          {step === 0 && (
            <div className={styles.section}>
              <div className={styles.sectionHeading}>
                <FolderOpen size={18} />
                <div>
                  <h3>{t("drawer.project")}</h3>
                  <p>{t("drawer.projectHint")}</p>
                </div>
              </div>
              <div className={styles.projectList} role="radiogroup">
                {projects.map((project) => (
                  <label key={project.id} className={`${styles.projectOption} ${form.watch("projectId") === project.id ? styles.selected : ""}`}>
                    <input type="radio" value={project.id} {...form.register("projectId")} />
                    <FolderOpen size={18} />
                    <span>
                      <strong>{project.name}</strong>
                      <small>{project.path}</small>
                    </span>
                    <em>{project.file_count}</em>
                  </label>
                ))}
              </div>
              <button className={styles.secondaryButton} type="button" onClick={() => pickProject.mutate()} disabled={pickProject.isPending}>
                <FolderOpen size={16} />
                {t("projects.add")}
              </button>
              {form.formState.errors.projectId && <p className={styles.error}>请选择一个项目。</p>}
              {pickerError && <p className={styles.error}>{pickerError}</p>}
            </div>
          )}

          {step === 1 && (
            <div className={styles.section}>
              <label className={styles.field}>
                <span>{t("drawer.promptLabel")}</span>
                <textarea autoFocus rows={10} placeholder={t("drawer.promptPlaceholder")} {...form.register("prompt")} />
                <small>{form.watch("prompt").length} / 8000</small>
              </label>
              {form.formState.errors.prompt && <p className={styles.error}>{form.formState.errors.prompt.message}</p>}
            </div>
          )}

          {step === 2 && (
            <div className={styles.section}>
              <div className={styles.summaryStrip}>
                <ShieldCheck size={19} />
                <span><strong>{selectedProject?.name}</strong><small>{t("settings.providerExecutionHelp")}</small></span>
              </div>
              <label className={styles.field}>
                <span>{t("drawer.approval")}</span>
                <select {...form.register("approvalPolicy")}>
                  <option value="manual_plan">{t("drawer.manualPlan")}</option>
                  <option value="manual_all">{t("drawer.manualAll")}</option>
                  <option value="auto">{t("drawer.auto")}</option>
                </select>
              </label>
              <div className={styles.fieldGrid}>
                <label className={styles.field}>
                  <span>Base branch</span>
                  <input {...form.register("baseBranch")} />
                </label>
                <label className={styles.field}>
                  <span>{t("drawer.priority")}</span>
                  <select {...form.register("priority")}>
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                  </select>
                </label>
              </div>
              <div className={styles.requirementPreview}>
                <span>Requirement</span>
                <p>{form.getValues("prompt")}</p>
              </div>
              {createTask.error && <p className={styles.error}>{(createTask.error as Error).message}</p>}
            </div>
          )}

          <footer className={styles.footer}>
            <button type="button" className={styles.secondaryButton} onClick={step === 0 ? onClose : () => setStep((value) => value - 1)}>
              {step > 0 && <ArrowLeft size={16} />}
              {step === 0 ? t("common.cancel") : t("drawer.back")}
            </button>
            {step < 2 ? (
              <button type="button" className={styles.primaryButton} onClick={next}>
                {t("drawer.next")}<ArrowRight size={16} />
              </button>
            ) : (
              <button type="submit" className={styles.primaryButton} disabled={createTask.isPending}>
                <Check size={16} />{t("drawer.create")}
              </button>
            )}
          </footer>
        </form>
      </section>
    </div>
  );
}
