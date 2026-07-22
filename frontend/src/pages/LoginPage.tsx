import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Boxes, KeyRound, LockKeyhole, UserRound } from "lucide-react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import type { AuthSession } from "../types";
import styles from "./LoginPage.module.css";

export function LoginPage({ onSignedIn }: { onSignedIn: (session: AuthSession) => void }) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const signIn = useMutation({
    mutationFn: () => api.login(username.trim(), password),
    onSuccess: (session) => onSignedIn(session),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (username.trim() && password) signIn.mutate();
  };

  return (
    <main className={styles.page}>
      <section className={styles.loginPanel} aria-labelledby="login-title">
        <header>
          <span className={styles.brandMark}><Boxes size={22} /></span>
          <div><strong>AGENT<span>SYSTEM</span></strong><small>{t("auth.privateWorkspace")}</small></div>
        </header>
        <div className={styles.heading}>
          <span><LockKeyhole size={16} />{t("auth.secureSession")}</span>
          <h1 id="login-title">{t("auth.signIn")}</h1>
          <p>{t("auth.signInHelp")}</p>
        </div>
        <form onSubmit={submit}>
          <label>
            <span>{t("auth.username")}</span>
            <span className={styles.inputWrap}><UserRound size={16} /><input autoFocus autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></span>
          </label>
          <label>
            <span>{t("auth.password")}</span>
            <span className={styles.inputWrap}><KeyRound size={16} /><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></span>
          </label>
          {signIn.error && <p className={styles.error} role="alert">{(signIn.error as Error).message}</p>}
          <button type="submit" disabled={!username.trim() || password.length < 8 || signIn.isPending}>
            <LockKeyhole size={16} />{signIn.isPending ? t("auth.signingIn") : t("auth.signIn")}
          </button>
        </form>
        <footer>{t("auth.cookieNotice")}</footer>
      </section>
    </main>
  );
}
