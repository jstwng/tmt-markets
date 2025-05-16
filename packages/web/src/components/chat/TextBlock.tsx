interface TextBlockProps {
  text: string;
}

export default function TextBlock({ text }: TextBlockProps) {
  // Split on double-newlines for paragraphs; render code blocks for ```...```
  const segments = text.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-2">
      {segments.map((segment, i) => {
        if (segment.startsWith("```") && segment.endsWith("```")) {
          const inner = segment.slice(3, -3).replace(/^\w+\n/, ""); // strip language hint
          return (
            <pre
              key={i}
              className="bg-muted rounded px-3 py-2 text-xs overflow-x-auto font-mono leading-relaxed"
            >
              {inner.trim()}
            </pre>
          );
        }

        // Regular text — split into paragraphs and apply basic inline formatting
        const paragraphs = segment.split(/\n\n+/).filter(Boolean);
        return paragraphs.map((para, j) => (
          <p key={`${i}-${j}`} className="text-sm leading-relaxed whitespace-pre-wrap">
            {para}
          </p>
        ));
      })}
    </div>
  );
}
