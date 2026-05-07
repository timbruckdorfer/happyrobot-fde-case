import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DistributionItem, TimeseriesPoint } from "../lib/api";

const COLORS = ["#7c5cff", "#22d3ee", "#22c55e", "#f59e0b", "#ef4444", "#94a3b8", "#a78bfa"];

const tooltipStyle: React.CSSProperties = {
  background: "#131a33",
  border: "1px solid #243056",
  borderRadius: 8,
  color: "#e8ecf7",
  fontSize: 12,
};

export function CallsTimeseries({ data }: { data: TimeseriesPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 5, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#243056" />
        <XAxis dataKey="date" stroke="#93a0c8" fontSize={11} />
        <YAxis stroke="#93a0c8" fontSize={11} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12, color: "#93a0c8" }} />
        <Line type="monotone" dataKey="calls" stroke="#22d3ee" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="booked" stroke="#22c55e" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DistributionPie({ data }: { data: DistributionItem[] }) {
  if (!data.length) {
    return <div className="empty">No data yet</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="label"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={(entry) => entry.label}
          labelLine={false}
          fontSize={11}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function DistributionBar({ data }: { data: DistributionItem[] }) {
  if (!data.length) {
    return <div className="empty">No data yet</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 5, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#243056" />
        <XAxis dataKey="label" stroke="#93a0c8" fontSize={11} interval={0} angle={-12} dy={6} />
        <YAxis stroke="#93a0c8" fontSize={11} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
