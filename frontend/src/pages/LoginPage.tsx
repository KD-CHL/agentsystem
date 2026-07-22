import { useEffect, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Boxes, Github, KeyRound, LockKeyhole, TriangleAlert, UserRound } from "lucide-react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import type { AuthSession } from "../types";
import styles from "./LoginPage.module.css";

export function LoginPage({ onSignedIn, backendUnreachable = false }: { onSignedIn: (session: AuthSession) => void; backendUnreachable?: boolean }) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [githubClientId, setGithubClientId] = useState<string | null>(null);
  const signIn = useMutation({
    mutationFn: () => api.login(username.trim(), password),
    onSuccess: (session) => onSignedIn(session),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (username.trim() && password) signIn.mutate();
  };

  useEffect(() => {
    let active = true;
    api.githubConfig()
      .then((config) => {
        if (active && config.enabled && config.client_id) setGithubClientId(config.client_id);
      })
      .catch(() => {
        // GitHub OAuth not configured on this backend — button stays hidden.
      });
    return () => {
      active = false;
    };
  }, []);

  const startGithubLogin = () => {
    if (!githubClientId) return;
    const redirectUri = `${location.origin}/github-callback.html`;
    const url =
      "https://github.com/login/oauth/authorize" +
      `?client_id=${encodeURIComponent(githubClientId)}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      "&scope=read:user";
    location.href = url;
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
        {backendUnreachable && (
          <div className={styles.backendDown} role="status">
            <TriangleAlert size={14} />
            <p>{t("auth.backendDown")}</p>
          </div>
        )}
        <form onSubmit={submit}>
          <label>
            <span>{t("auth.username")}</span>
            <span className={styles.inputWrap}><UserRound size={16} /><input autoFocus autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} disabled={backendUnreachable} /></span>
          </label>
          <label>
            <span>{t("auth.password")}</span>
            <span className={styles.inputWrap}><KeyRound size={16} /><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} disabled={backendUnreachable} /></span>
          </label>
          {signIn.error && <p className={styles.error} role="alert">{(signIn.error as Error).message}</p>}
          <button type="submit" disabled={backendUnreachable || !username.trim() || password.length < 8 || signIn.isPending}>
            <LockKeyhole size={16} />{signIn.isPending ? t("auth.signingIn") : t("auth.signIn")}
          </button>
          {githubClientId && !backendUnreachable && (
            <>
              <span className={styles.divider}><span>{t("auth.or")}</span></span>
              <button type="button" className={styles.githubButton} onClick={startGithubLogin}>
                <Github size={16} />{t("auth.githubSignIn")}
              </button>
            </>
          )}
        </form>
        <footer>{t("auth.cookieNotice")}</footer>
      </section>
    </main>
  );
}
