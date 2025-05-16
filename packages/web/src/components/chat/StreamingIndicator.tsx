export default function StreamingIndicator() {
  return (
    <span className="inline-flex items-center gap-0.5 h-4">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="inline-block w-1 h-1 rounded-full bg-foreground/50 animate-bounce"
          style={{ animationDelay: `${delay}ms`, animationDuration: "900ms" }}
        />
      ))}
    </span>
  );
}
