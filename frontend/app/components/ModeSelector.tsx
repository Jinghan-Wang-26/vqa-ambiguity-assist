"use client";

export type Mode = "onepass" | "iter";

export default function ModeSelector({
  mode, setMode,
}: { mode: Mode; setMode: (m: Mode) => void }) {
  return (
    <fieldset>
      <legend>Interaction mode</legend>
      <label>
        <input
          type="radio"
          name="mode"
          checked={mode === "onepass"}
          onChange={() => setMode("onepass")}
        />
        Respond in One Pass
      </label>
      <label style={{ marginLeft: 12 }}>
        <input
          type="radio"
          name="mode"
          checked={mode === "iter"}
          onChange={() => setMode("iter")}
        />
        Clarify Iteratively
      </label>
    </fieldset>
  );
}
