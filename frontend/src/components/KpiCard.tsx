type Props = {
  label: string;
  value: string;
  delta?: string;
};

export function KpiCard({ label, value, delta }: Props) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {delta ? <div className="delta">{delta}</div> : null}
    </div>
  );
}
