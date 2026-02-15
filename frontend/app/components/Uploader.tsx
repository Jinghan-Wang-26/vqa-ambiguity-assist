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
  const isVideo = !!file && file.type.startsWith("video/");
  const isImage = !!file && file.type.startsWith("image/");

  return (
    <div className="uploader">
      <label className="label" htmlFor="img">
        Upload an image or video
      </label>

      <div className="uploadRow">
        <input
          id="img"
          type="file"
          accept="image/*,video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-describedby="upload-help"
        />
        <span className="fileName" aria-label="Selected file">
          {fileLabel}
        </span>
      </div>

      <p className="hint" id="upload-help">
        Images work with one-pass and iterative modes. Videos are supported in one-pass only.
      </p>

      {previewUrl && (
        <figure className="preview">
          {isImage && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={previewUrl}
              alt="Preview of the uploaded image"
              className="previewImg"
            />
          )}

          {isVideo && (
            <video className="previewVideo" src={previewUrl} controls preload="metadata" />
          )}
        </figure>
      )}
    </div>
  );
}
