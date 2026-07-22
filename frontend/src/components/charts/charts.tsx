import { useTranslation } from "react-i18next";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { agentLabels } from "../agentVisuals";
import type { AgentName } from "../../types";
import type { AgentStat, SuccessBreakdown, TokenTrendPoint, TrendPoint } from "./derive";
import { useChartColors, type ChartColors } from "./useChartColors";

function tooltipStyle(colors: ChartColors) {
  return {
    background: colors.panel,
    border: `1px solid ${colors.grid}`,
    borderRadius: 8,
    fontSize: 10,
    color: colors.text,
  } as const;
}

function agentLabel(name: AgentStat["agent"]): string {
  return agentLabels[name as AgentName] ?? String(name);
}

export function TaskTrendChart({ data }: { data: TrendPoint[] }) {
  const { t } = useTranslation();
  const colors = useChartColors();
  return (
    <ResponsiveContainer width="100%" height={210}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="trendCreated" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.chart1} stopOpacity={0.32} />
            <stop offset="100%" stopColor={colors.chart1} stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="trendCompleted" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.chart3} stopOpacity={0.3} />
            <stop offset="100%" stopColor={colors.chart3} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={{ stroke: colors.grid }} interval="preserveStartEnd" />
        <YAxis tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle(colors)} labelStyle={{ color: colors.text, fontSize: 10 }} />
        <Area type="monotone" dataKey="created" name={t("operations.trendCreated")} stroke={colors.chart1} strokeWidth={2} fill="url(#trendCreated)" />
        <Area type="monotone" dataKey="completed" name={t("operations.trendCompleted")} stroke={colors.chart3} strokeWidth={2} fill="url(#trendCompleted)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function SuccessRing({ data }: { data: SuccessBreakdown }) {
  const { t } = useTranslation();
  const colors = useChartColors();
  const rate = data.rate ?? 0;
  const pct = `${Math.round(rate * 100)}%`;
  return (
    <div style={{ position: "relative", height: 210 }}>
      <ResponsiveContainer width="100%" height={210}>
        <RadialBarChart innerRadius="72%" outerRadius="100%" data={[{ name: "rate", value: rate }]} startAngle={90} endAngle={-270}>
          <PolarAngleAxis type="number" domain={[0, 1]} tick={false} />
          <RadialBar dataKey="value" cornerRadius={10} fill={colors.chart3} background={{ fill: colors.grid }} isAnimationActive={false} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeContent: "center", justifyItems: "center", pointerEvents: "none" }}>
        <strong style={{ fontSize: 26, fontVariantNumeric: "tabular-nums" }}>{data.rate === null ? "–" : pct}</strong>
        <small style={{ color: colors.axis, fontSize: 9 }}>{t("operations.successRate")}</small>
      </div>
    </div>
  );
}

export function AgentCostChart({ data }: { data: AgentStat[] }) {
  const { t } = useTranslation();
  const colors = useChartColors();
  const palette = [colors.chart1, colors.chart2, colors.chart3, colors.chart4, colors.chart5, colors.chart6];
  const rows = data.map((item) => ({ agent: agentLabel(item.agent), cost: item.cost }));
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={rows} margin={{ top: 8, right: 12, left: -14, bottom: 0 }}>
        <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="agent" tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={{ stroke: colors.grid }} interval={0} />
        <YAxis tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tooltipStyle(colors)} labelStyle={{ color: colors.text, fontSize: 10 }} cursor={{ fill: colors.grid, opacity: 0.35 }} />
        <Bar dataKey="cost" name={t("operations.cost")} radius={[4, 4, 0, 0]}>
          {rows.map((_, index) => (
            <Cell key={index} fill={palette[index % palette.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AgentDurationChart({ data }: { data: AgentStat[] }) {
  const { t } = useTranslation();
  const colors = useChartColors();
  const rows = data
    .filter((item) => item.avgLatencyMs != null)
    .map((item) => ({ agent: agentLabel(item.agent), ms: item.avgLatencyMs ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 18, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="agent" width={78} tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={{ stroke: colors.grid }} />
        <Tooltip contentStyle={tooltipStyle(colors)} labelStyle={{ color: colors.text, fontSize: 10 }} cursor={{ fill: colors.grid, opacity: 0.35 }} formatter={(value) => [`${value} ms`, t("operations.avgDuration")]} />
        <Bar dataKey="ms" name={t("operations.avgDuration")} fill={colors.chart2} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TokenTrendChart({ data }: { data: TokenTrendPoint[] }) {
  const { t } = useTranslation();
  const colors = useChartColors();
  return (
    <ResponsiveContainer width="100%" height={210}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: -14, bottom: 0 }}>
        <defs>
          <linearGradient id="tokenFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.chart4} stopOpacity={0.32} />
            <stop offset="100%" stopColor={colors.chart4} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={{ stroke: colors.grid }} interval="preserveStartEnd" />
        <YAxis tick={{ fill: colors.axis, fontSize: 9 }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tooltipStyle(colors)} labelStyle={{ color: colors.text, fontSize: 10 }} />
        <Area type="monotone" dataKey="tokens" name={t("operations.tokens")} stroke={colors.chart4} strokeWidth={2} fill="url(#tokenFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface DataTableProps {
  headers: string[];
  rows: Array<Array<string | number>>;
}

/** Accessible plain-table fallback rendered when a card switches to table view. */
export function DataTable({ headers, rows }: DataTableProps) {
  return (
    <table>
      <thead>
        <tr>{headers.map((header) => <th key={header} scope="col">{header}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}
