import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { TableBlock as TableBlockType } from "@/api/chat-types";

interface TableBlockProps {
  block: TableBlockType;
}

export default function TableBlock({ block }: TableBlockProps) {
  return (
    <div className="rounded border border-border overflow-hidden text-sm">
      <Table>
        <TableHeader>
          <TableRow>
            {block.headers.map((h) => (
              <TableHead key={h} className="h-8 text-xs uppercase tracking-wide text-muted-foreground">
                {h}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {block.rows.map((row, i) => (
            <TableRow key={i}>
              {row.map((cell, j) => (
                <TableCell key={j} className="py-1.5 tabular-nums">
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
