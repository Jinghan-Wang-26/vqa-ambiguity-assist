"use client";

import { useEffect, useMemo, useState } from "react";

export default function Uploader({
  file,
  setFile,
}: {
  file: File | null;
  setFile: (f: File | null) => void;
}) {
  const [previewUrl, setPreviewUrl] = useState<string>("");

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const fileLabel = useMemo(() => (file ? file.name : "No file selected"), [file]);

  return (
    <div className="uploader">
      <label className="label" htmlFor="img">
        Upload an image
      </label>

      <div className="uploadRow">
        <input
          id="img"
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-describedby="upload-help"
        />
        <span className="fileName" aria-label="Selected file">
          {fileLabel}
        </span>
      </div>

      {previewUrl && (
        <figure className="preview">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Preview of the uploaded image"
            className="previewImg"
          />
        </figure>
      )}
    </div>
  );
}
