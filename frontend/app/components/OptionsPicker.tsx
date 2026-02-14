"use client";

export default function OptionsPicker({
  options,
  selected,
  onSelect,
  onConfirm,
}: {
  options: string[];
  selected: string;
  onSelect: (v: string) => void;
  onConfirm: () => void;
}) {
  return (
    <fieldset style={{ marginTop: 12 }}>
      <legend>Choose what you meant</legend>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {options.map((o) => (
          <button
            key={o}
            type="button"
            onClick={() => onSelect(o)}
            aria-pressed={selected === o}
            style={{
              border: "1px solid #ccc",
              padding: "8px 10px",
              borderRadius: 8,
              background: selected === o ? "#eee" : "white",
            }}
          >
            {o}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 10 }}>
        <button
          type="button"
          onClick={onConfirm}
          disabled={!selected}
          aria-label="Confirm selection"
        >
          Describe selected option
        </button>
      </div>
    </fieldset>
  );
}
