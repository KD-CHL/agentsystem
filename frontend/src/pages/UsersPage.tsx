import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, LockKeyhole, ShieldCheck, UserPlus, UsersRound } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { User, UserRole } from "../types";
import styles from "./StandardPage.module.css";

const roles: UserRole[] = ["admin", "operator", "reviewer", "viewer"];

export function UsersPage() {
  const { t } = useTranslation();
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: api.users });
  const createUser = useMutation({
    mutationFn: () => api.createUser({ username: username.trim(), display_name: displayName.trim(), password, role }),
    onSuccess: async () => {
      setUsername(""); setDisplayName(""); setPassword(""); setRole("viewer");
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
  const updateUser = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { role?: UserRole; status?: "active" | "disabled" } }) => api.updateUser(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (username.trim() && displayName.trim() && password.length >= 12) createUser.mutate();
  };
  const error = createUser.error ?? updateUser.error ?? usersQuery.error;

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div><span className={styles.eyebrow}>Security / Identity</span><h1>{t("users.title")}</h1><p>{t("users.subtitle")}</p></div>
        <span className={styles.safetyBadge}><ShieldCheck size={15} />{session.auth_mode}</span>
      </header>

      {session.auth_mode === "local" ? (
        <form className={styles.userCreateBand} onSubmit={submit}>
          <span className={styles.userCreateTitle}><UserPlus size={17} /><span><strong>{t("users.add")}</strong><small>{t("users.passwordRule")}</small></span></span>
          <label><span>{t("auth.username")}</span><input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" /></label>
          <label><span>{t("users.displayName")}</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <label><span>{t("auth.password")}</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /></label>
          <label><span>{t("users.role")}</span><select value={role} onChange={(event) => setRole(event.target.value as UserRole)}>{roles.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <button type="submit" className={styles.primaryButton} disabled={createUser.isPending || username.trim().length < 3 || !displayName.trim() || password.length < 12}><UserPlus size={15} />{t("users.create")}</button>
        </form>
      ) : (
        <div className={styles.infoBand}><LockKeyhole size={17} /><span><strong>{t("users.devIdentity")}</strong><small>{t("users.devIdentityHelp")}</small></span></div>
      )}

      <section className={styles.userTable}>
        <div className={styles.panelTitle}><span><UsersRound size={14} />{t("users.directory")}</span><small>{usersQuery.data?.length ?? 0}</small></div>
        <div className={styles.userHead}><span>{t("users.user")}</span><span>{t("users.role")}</span><span>{t("users.status")}</span><span>{t("users.lastLogin")}</span></div>
        {usersQuery.data?.map((user) => (
          <UserRow key={user.id} user={user} immutable={session.auth_mode === "dev" || user.id === session.user.id && user.role === "admin"} onUpdate={(payload) => updateUser.mutate({ id: user.id, payload })} />
        ))}
        {!usersQuery.data?.length && !usersQuery.isLoading && <div className={styles.inlineEmpty}>{t("common.noData")}</div>}
      </section>
      {error && <div className={styles.toastError} role="alert">{(error as Error).message}</div>}
    </div>
  );
}

function UserRow({ user, immutable, onUpdate }: { user: User; immutable: boolean; onUpdate: (payload: { role?: UserRole; status?: "active" | "disabled" }) => void }) {
  return (
    <div className={styles.userRow}>
      <span className={styles.userIdentity}><span>{initials(user.display_name)}</span><span><strong>{user.display_name}</strong><small>@{user.username}</small></span></span>
      <select aria-label={`Role for ${user.username}`} value={user.role} disabled={immutable} onChange={(event) => onUpdate({ role: event.target.value as UserRole })}>{roles.map((item) => <option key={item} value={item}>{item}</option>)}</select>
      <label className={styles.statusToggle}><input type="checkbox" checked={user.status === "active"} disabled={immutable} onChange={(event) => onUpdate({ status: event.target.checked ? "active" : "disabled" })} /><span>{user.status === "active" ? <CheckCircle2 size={13} /> : null}{user.status}</span></label>
      <time>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</time>
    </div>
  );
}

function initials(value: string): string {
  return value.split(/\s+/).filter(Boolean).slice(0, 2).map((item) => item[0]).join("").toUpperCase() || "U";
}
