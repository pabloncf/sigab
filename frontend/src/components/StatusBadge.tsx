import type { ItemSummary } from "../api/types";

export function StatusBadge({ item }: { item: ItemSummary }) {
  const tone = item.condition === "unfit" ? "danger" : item.availability === "available" ? "success" : "warning";
  return <span className={`status-badge ${tone}`}>{item.availability_label} · {item.condition_label}</span>;
}
