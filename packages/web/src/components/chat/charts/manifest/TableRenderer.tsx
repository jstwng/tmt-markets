import type { RendererProps, TableData } from "./types";

function formatCell(value: unknown, format?: string): string {
  if (value == null) return "—";
  if (format === "percent" && typeof value === "number") return `${(value * 100).toFixed(2)}%`;
  if (format === "currency" && typeof value === "number") return `$${value.toLocaleString()}`;
  if (format === "number" && typeof value === "number") return value.toLocaleString();
  return String(value);
}

export default function TableRenderer({ data }: RendererProps<TableData>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border">
            {data.columns.map((col) => (
              <th key={col.key} className="text-left py-2 px-3 font-medium text-muted-foreground">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i} className="border-b border-border/50">
              {data.columns.map((col) => (
                <td key={col.key} className="py-2 px-3">
                  {formatCell(row[col.key], col.format)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
