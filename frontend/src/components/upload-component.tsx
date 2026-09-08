"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadComponentProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

export function UploadComponent({ onFileSelect, disabled }: UploadComponentProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File | null) => {
    if (!f) return;
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
      alert("يُرجى رفع ملف بصيغة PDF أو DOCX فقط.");
      return;
    }
    setFile(f);
    onFileSelect(f);
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files?.[0] ?? null);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-colors",
          dragOver ? "border-primary bg-accent" : "border-border bg-muted/30",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          disabled={disabled}
        />
        {file ? (
          <>
            <FileText className="h-10 w-10 text-primary" />
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">{file.name}</p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </>
        ) : (
          <>
            <Upload className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="text-sm font-semibold">اسحب الملف هنا أو اضغط للاختيار</p>
              <p className="text-xs text-muted-foreground mt-1">ملفات PDF أو DOCX حتى 15 ميجابايت</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
