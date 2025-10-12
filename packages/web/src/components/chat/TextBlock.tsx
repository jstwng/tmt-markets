import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface TextBlockProps {
  text: string;
}

const components: Components = {
  p({ children }) {
    return <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>;
  },
  strong({ children }) {
    return <strong className="font-semibold text-foreground">{children}</strong>;
  },
  em({ children }) {
    return <em className="italic">{children}</em>;
  },
  pre({ children }) {
    return (
      <pre className="bg-muted rounded px-3 py-2 text-xs overflow-x-auto font-mono leading-relaxed my-2">
        {children}
      </pre>
    );
  },
  code({ children, className }) {
    // Labelled fenced block (className = "language-xxx"): pre handles outer styling
    if (className) {
      return <code>{children}</code>;
    }
    // Unlabelled fenced block: react-markdown passes content with trailing newline
    const text = typeof children === "string" ? children : "";
    if (text.includes("\n")) {
      return <code>{children}</code>;
    }
    // Inline code
    return (
      <code className="bg-muted border border-border rounded px-1 py-0.5 text-xs font-mono text-blue-300">
        {children}
      </code>
    );
  },
  ul({ children }) {
    return <ul className="list-disc pl-5 space-y-1 my-2 text-sm">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal pl-5 space-y-1 my-2 text-sm">{children}</ol>;
  },
  li({ children }) {
    return <li className="leading-relaxed">{children}</li>;
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-2">
        <table className="w-full border-collapse text-xs">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="border-b border-border">{children}</thead>;
  },
  tbody({ children }) {
    return <tbody>{children}</tbody>;
  },
  tr({ children }) {
    return <tr className="border-b border-border/50 last:border-0">{children}</tr>;
  },
  th({ children }) {
    return (
      <th className="text-left px-3 py-1.5 text-muted-foreground font-medium">
        {children}
      </th>
    );
  },
  td({ children }) {
    return <td className="px-3 py-1.5">{children}</td>;
  },
};

export default function TextBlock({ text }: TextBlockProps) {
  return (
    <div className="space-y-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
