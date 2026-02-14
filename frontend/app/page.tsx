"use client";

import { useMemo, useState } from "react";
import LiveRegion from "./components/LiveRegion";
import VoiceControls from "./components/VoiceControls";
import ModeSelector, { Mode } from "./components/ModeSelector";
import Uploader from "./components/Uploader";
import AnswerPanel from "./components/AnswerPanel";
import OptionsPicker from "./components/OptionsPicker";
import { postForm, postJson } from "./lib/api";
import type { OnePassResponse, IterStartResponse, IterChooseResponse } from "./lib/types";
import { speak } from "./lib/speech";

type Status = "idle" | "loading" | "success" | "error";

export default function Page() {
  const [mode, setMode] = useState<Mode>("onepass");
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("What is on the table?");
  const [output, setOutput] = useState("");
  const [liveText, setLiveText] = useState("");

  const [sessionId, setSessionId] = useState("");
  const [options, setOptions] = useState<string[]>([]);
  const [selected, setSelected] = useState("");

  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [status, setStatus] = useState<Status>("idle");
  const [statusMsg, setStatusMsg] = useState("Ready");

  function announce(text: string, doSpeak = true) {
    setLiveText(text);
    setStatusMsg(text);
    if (ttsEnabled && doSpeak) speak(text);
  }

  const canRun = useMemo(() => !!file && !!question.trim() && status !== "loading", [file, question, status]);

  async function run() {
    try {
      if (!file) {
        setStatus("error");
        announce("Please upload an image first.");
        return;
      }
      if (!question.trim()) {
        setStatus("error");
        announce("Please enter a question.");
        return;
      }

      setStatus("loading");
      setOutput("");
      setOptions([]);
      setSelected("");
      setSessionId("");
      announce("Processing. Please wait.", false);

      const form = new FormData();
      form.append("image", file);
      form.append("question", question);

      if (mode === "onepass") {
        const data = await postForm<OnePassResponse>("/v1/onepass", form);
        setOutput(data.answer);
        setStatus("success");
        announce("Answer ready.");
        if (ttsEnabled) speak(data.answer);
      } else {
        const data = await postForm<IterStartResponse>("/v1/iter/start", form);
        setSessionId(data.session_id);
        setOptions(data.options ?? []);
        setOutput(`${data.inventory_brief}\n\n${data.clarification_question}`);
        setStatus("success");
        announce(data.clarification_question);
      }
    } catch (e: any) {
      setStatus("error");
      announce("Request failed.");
      setOutput(String(e?.message ?? e));
    }
  }

  async function confirmChoice() {
    try {
      if (!sessionId || !selected) {
        setStatus("error");
        announce("Please choose an option first.");
        return;
      }
      setStatus("loading");
      announce("Getting focused description.", false);

      const data = await postJson<IterChooseResponse>("/v1/iter/choose", {
        session_id: sessionId,
        chosen: selected,
      });

      setOutput(data.focused_answer);
      setStatus("success");
      announce("Focused answer ready.");
      if (ttsEnabled) speak(data.focused_answer);
    } catch (e: any) {
      setStatus("error");
      announce("Request failed.");
      setOutput(String(e?.message ?? e));
    }
  }

  function clearAll() {
    setOutput("");
    setOptions([]);
    setSelected("");
    setSessionId("");
    setStatus("idle");
    setStatusMsg("Ready");
    announce("Cleared.", false);
  }

  return (
    <main className="page">
      <LiveRegion text={liveText} />

      <header className="header">
        <div>
          <h1 className="title">Ambiguity-Aware VQA for Accessibility</h1>
          <p className="subtitle">
            Upload an image and ask a question. Choose a single comprehensive response or an iterative clarification
            flow designed for screen-reader users.
          </p>
        </div>

        <div className={`status status--${status}`} aria-label="System status">
          <strong>Status:</strong>
          <span>{statusMsg}</span>
        </div>
      </header>

      <section className="grid">
        {/* Inputs */}
        <div className="card">
          <h2>Inputs</h2>

          <div className="block">
            <ModeSelector mode={mode} setMode={setMode} />
          </div>

          <div className="block">
            <Uploader file={file} setFile={setFile} />
          </div>

          <div className="block">
            <label className="label" htmlFor="q">
              Your question
            </label>
            <input
              id="q"
              className="input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder='e.g., "What is on the table?"'
            />
            <p className="hint">Tip: Ask about objects, counts, locations, or visible text.</p>
          </div>

          <div className="actions">
            <button className="btn btn--primary" onClick={run} disabled={!canRun} aria-label="Run">
              {status === "loading" ? "Running…" : "Run"}
            </button>

            <button className="btn btn--ghost" onClick={clearAll} aria-label="Clear">
              Clear
            </button>

            <label className="checkbox">
              <input type="checkbox" checked={ttsEnabled} onChange={(e) => setTtsEnabled(e.target.checked)} />
              Voice output
            </label>
          </div>

          <div className="voiceBox">
            <div className="voiceTitle">Voice controls</div>
            <VoiceControls
              onTranscript={(t) => setQuestion(t)}
              onAnnounce={(t) => setLiveText(t)}
              enabledSpeak={ttsEnabled}
            />
            <p className="hint">Voice input works best in Chrome/Edge on localhost.</p>
          </div>

          {mode === "iter" && options.length > 0 && (
            <div className="block">
              <h3>Disambiguation</h3>
              <p className="hint">Multiple plausible targets were detected. Choose one for a focused answer.</p>
              <OptionsPicker
                options={options}
                selected={selected}
                onSelect={(v) => setSelected(v)}
                onConfirm={confirmChoice}
              />
            </div>
          )}
        </div>

        {/* Output */}
        <div className="card">
          <AnswerPanel text={output} />

          <div className="badges" aria-label="Accessibility features">
            <span className="badge">Screen-reader friendly</span>
            <span className="badge">Keyboard navigation</span>
            <span className="badge">Voice input/output</span>
          </div>
        </div>
      </section>
    </main>
  );
}
