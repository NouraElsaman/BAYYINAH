import React from "react";

/**
 * Splits text into blocks: code, table, list, header, paragraph.
 * Then renders each block as standard JSX with beautiful Tailwind styling.
 */
export function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null;

  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    // 1. Fenced Code Blocks
    if (line.trim().startsWith("```")) {
      const lang = line.trim().slice(3).trim();
      const codeLines: string[] = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index++;
      }
      index++; // skip closing ```
      const codeString = codeLines.join("\n");
      elements.push(
        <div key={`code-${index}`} className="my-4 overflow-hidden rounded-lg border border-border bg-slate-950 dark:bg-slate-900 text-slate-100 font-mono text-xs direction-ltr text-left">
          <div className="flex items-center justify-between px-4 py-1.5 bg-slate-900 dark:bg-slate-800 border-b border-slate-800 text-slate-400 select-none">
            <span>{lang || "code"}</span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(codeString);
              }}
              className="px-2 py-0.5 rounded text-[10px] hover:bg-slate-800 hover:text-white transition-colors"
              title="نسخ الكود"
            >
              نسخ
            </button>
          </div>
          <pre className="p-4 overflow-x-auto">
            <code>{codeString}</code>
          </pre>
        </div>
      );
      continue;
    }

    // 2. Markdown Tables
    if (line.trim().startsWith("|") && index + 1 < lines.length && lines[index + 1].trim().includes("-|-")) {
      const headerLine = line;
      const separatorLine = lines[index + 1];
      const dataLines: string[] = [];
      index += 2;

      while (index < lines.length && lines[index].trim().startsWith("|")) {
        dataLines.push(lines[index]);
        index++;
      }

      const parseTableRow = (rowStr: string) => {
        return rowStr
          .split("|")
          .map((cell) => cell.trim())
          .filter((_, i, arr) => i > 0 && i < arr.length - 1); // remove outer empty values from start/end |
      };

      const headers = parseTableRow(headerLine);
      const rows = dataLines.map(parseTableRow);

      elements.push(
        <div key={`table-${index}`} className="my-4 overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm text-right border-collapse">
            <thead className="bg-muted/70 text-foreground font-semibold border-b border-border">
              <tr>
                {headers.map((h, i) => (
                  <th key={i} className="px-4 py-2.5 text-right border-l border-border/60 last:border-l-0">
                    {parseInlineMarkdown(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 bg-card">
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-muted/30 transition-colors odd:bg-muted/10">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-4 py-2.5 text-right border-l border-border/60 last:border-l-0 text-foreground/90">
                      {parseInlineMarkdown(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // 3. Headers
    if (line.trim().startsWith("#")) {
      const match = line.match(/^(#{1,6})\s+(.*)$/);
      if (match) {
        const level = match[1].length;
        const headingText = match[2];
        const headingClasses = [
          "",
          "text-2xl font-extrabold my-4 border-b border-border/40 pb-1.5",
          "text-xl font-bold my-3",
          "text-lg font-bold my-2.5",
          "text-base font-semibold my-2",
          "text-sm font-semibold my-2",
          "text-xs font-semibold my-2",
        ][level];

        const Tag = `h${level}` as keyof JSX.IntrinsicElements;
        elements.push(
          <Tag key={`h-${index}`} className={headingClasses}>
            {parseInlineMarkdown(headingText)}
          </Tag>
        );
        index++;
        continue;
      }
    }

    // 4. Blockquotes
    if (line.trim().startsWith(">")) {
      const quoteText = line.slice(1).trim();
      elements.push(
        <blockquote key={`quote-${index}`} className="my-3 border-r-4 border-accent bg-accent/5 px-4 py-2 rounded-l-md italic text-muted-foreground">
          {parseInlineMarkdown(quoteText)}
        </blockquote>
      );
      index++;
      continue;
    }

    // 5. Lists (unordered)
    if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
      const listItems: string[] = [];
      while (
        index < lines.length &&
        (lines[index].trim().startsWith("- ") || lines[index].trim().startsWith("* "))
      ) {
        listItems.push(lines[index].trim().slice(2).trim());
        index++;
      }
      elements.push(
        <ul key={`ul-${index}`} className="list-disc list-inside mr-5 my-3 space-y-1.5 text-foreground/95">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx} className="leading-relaxed">
              {parseInlineMarkdown(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 6. Lists (ordered)
    if (/^\d+\.\s+/.test(line.trim())) {
      const listItems: string[] = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        const itemLine = lines[index].trim();
        const firstSpace = itemLine.indexOf(" ");
        listItems.push(itemLine.slice(firstSpace + 1).trim());
        index++;
      }
      elements.push(
        <ol key={`ol-${index}`} className="list-decimal list-inside mr-5 my-3 space-y-1.5 text-foreground/95">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx} className="leading-relaxed">
              {parseInlineMarkdown(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 7. Regular Paragraphs
    if (line.trim() !== "") {
      elements.push(
        <p key={`p-${index}`} className="leading-relaxed text-foreground/90 my-2 safe-text">
          {parseInlineMarkdown(line)}
        </p>
      );
    }
    index++;
  }

  return <>{elements}</>;
}

/**
 * Parses inline elements like bold (**text**), italics (*text* or _text_), and inline code (`code`).
 */
function parseInlineMarkdown(text: string): React.ReactNode[] {
  // Regex to split on bold, italic, and inline code markers
  const tokenRegex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={idx} className="font-bold text-foreground">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={idx} className="italic text-foreground/90">{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={idx} className="px-1.5 py-0.5 rounded bg-muted-foreground/10 text-accent font-mono text-xs break-all mx-0.5">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}
