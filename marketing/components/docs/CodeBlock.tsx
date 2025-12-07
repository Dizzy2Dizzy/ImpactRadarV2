'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  language: string;
  children: string;
  filename?: string;
}

export function CodeBlock({ language, children, filename }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      {filename && (
        <div className="bg-white/5 border-b border-white/10 px-4 py-2 text-xs text-[--muted] font-mono rounded-t-lg">
          {filename}
        </div>
      )}
      <div className="relative">
        <pre className={`bg-[--panel] border border-white/10 text-[--text] p-4 ${filename ? 'rounded-b-lg' : 'rounded-lg'} overflow-x-auto`}>
          <code className={`language-${language} text-sm font-mono`}>{children}</code>
        </pre>
        <button
          onClick={copyToClipboard}
          className="absolute top-2 right-2 p-2 bg-white/10 hover:bg-white/20 text-[--text] rounded transition-all opacity-0 group-hover:opacity-100"
          aria-label="Copy code"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-400" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
