import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { BarChart3, Table2 } from "lucide-react";

import styles from "./ChartCard.module.css";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  chart: ReactNode;
  table: ReactNode;
}

/**
 * Dashboard card that renders a chart with an accessible fallback table view.
 * The toggle lets users switch between the visual and a plain data table.
 */
export function ChartCard({ title, subtitle, chart, table }: ChartCardProps) {
  const { t } = useTranslation();
  const [view, setView] = useState<"chart" | "table">("chart");

  return (
    <section className={styles.card}>
      <header className={styles.cardHeader}>
        <div>
          <strong>{title}</strong>
          {subtitle && <small>{subtitle}</small>}
        </div>
        <div className={styles.viewToggle} role="group" aria-label={title}>
          <button type="button" data-active={view === "chart"} aria-pressed={view === "chart"} onClick={() => setView("chart")}>
            <BarChart3 size={12} />
            {t("operations.chartView")}
          </button>
          <button type="button" data-active={view === "table"} aria-pressed={view === "table"} onClick={() => setView("table")}>
            <Table2 size={12} />
            {t("operations.tableView")}
          </button>
        </div>
      </header>
      <div className={styles.cardBody}>
        {view === "chart" ? chart : <div className={styles.tableWrap}>{table}</div>}
      </div>
    </section>
  );
}
