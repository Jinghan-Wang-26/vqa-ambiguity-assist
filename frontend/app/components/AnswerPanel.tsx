"use client";

export default function AnswerPanel({ text }: { text: string }) {
  return (
    <section style={{ marginTop: 18 }}>
      <h2>Output</h2>
      <pre
        tabIndex={0}
        aria-label="Model output"
        style={{
          whiteSpace: "pre-wrap",
          padding: 12,
          border: "1px solid #ddd",
          borderRadius: 10,
          minHeight: 160,
        }}
      >
        {text || "No output yet."}
      </pre>
    </section>
  );
}
