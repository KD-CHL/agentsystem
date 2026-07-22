import { useTranslation } from "react-i18next";

import styles from "./StatusBadge.module.css";

/**
 * Shared status pill that pairs a colored dot with a translated label so status
 * is never conveyed by color alone. Falls back to a humanized key when a
 * specific translation is missing.
 */
export function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const label = t(`task.${status}`, { defaultValue: status.replaceAll("_", " ") });
  const toneClass = styles[status] ?? "";
  return (
    <span className={`${styles.badge} ${toneClass}`}>
      <i aria-hidden="true" />
      {label}
    </span>
  );
}
