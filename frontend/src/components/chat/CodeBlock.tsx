import React, { useState } from 'react';
import { Check, Copy, Code } from 'lucide-react';

interface CodeBlockProps {
  language?: string;
  code: string;
  title?: string;
  showLineNumbers?: boolean;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  language = 'text',
  code,
  title,
  showLineNumbers = false,
}) => {
  const [copied, setCopied] = useState(false);

  const cleanCode = code.replace(/\n$/, '');
  const lines = cleanCode.split('\n');
  const displayLang = language.toLowerCase();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API fails
      const textarea = document.createElement('textarea');
      textarea.value = cleanCode;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="my-3.5 rounded-xl overflow-hidden border border-zinc-800 bg-[#141416] shadow-sm text-left font-mono text-[12.5px] leading-relaxed">
      {/* Code Block Header */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-[#1c1c20] border-b border-zinc-800 text-zinc-400 text-[11px]">
        <div className="flex items-center gap-2">
          <Code className="w-3.5 h-3.5 text-[var(--color-action)]" />
          <span className="font-semibold uppercase tracking-wider text-zinc-300">
            {title || displayLang}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 hover:text-white transition-colors cursor-pointer text-[11px]"
          title="Copy code to clipboard"
          aria-label="Copy code to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Area */}
      <div className="p-3.5 overflow-x-auto text-[#f4f4f5]">
        {showLineNumbers ? (
          <table className="border-collapse w-full">
            <tbody>
              {lines.map((line, idx) => (
                <tr key={idx} className="hover:bg-white/5">
                  <td className="pr-4 select-none text-zinc-600 text-right w-8 text-[11px]">
                    {idx + 1}
                  </td>
                  <td className="whitespace-pre">
                    {line || ' '}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <pre className="m-0 p-0 font-mono text-[12.5px] whitespace-pre overflow-x-auto text-[#e4e4e7]">
            <code>{cleanCode}</code>
          </pre>
        )}
      </div>
    </div>
  );
};

export default CodeBlock;

