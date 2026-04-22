import { type ReactNode } from "react";

interface Props {
  value: string;
  onChange?: (value: string) => void;
  placeholder: string;
  editable: boolean;
  isLoading?: boolean;
  charCount?: number;
  maxChars?: number;
  footer?: ReactNode;
}

export function TranslationPanel({
  value,
  onChange,
  placeholder,
  editable,
  isLoading = false,
  charCount,
  maxChars,
  footer,
}: Props) {
  return (
    <div className="flex-1 flex flex-col relative">
      {isLoading && (
        <div className="absolute inset-0 bg-white/60 z-10 flex items-center justify-center">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-dlv-accent rounded-full animate-bounce [animation-delay:-0.3s]" />
            <div className="w-2 h-2 bg-dlv-accent rounded-full animate-bounce [animation-delay:-0.15s]" />
            <div className="w-2 h-2 bg-dlv-accent rounded-full animate-bounce" />
          </div>
        </div>
      )}
      <textarea
        className="flex-1 p-4 text-lg leading-relaxed focus:outline-none bg-transparent min-h-[250px] placeholder:text-gray-300"
        value={value}
        onChange={editable && onChange ? (e) => onChange(e.target.value) : undefined}
        readOnly={!editable}
        placeholder={placeholder}
      />
      <div className="flex items-center justify-between px-4 py-2 text-xs text-gray-400 border-t border-gray-100">
        <div>
          {charCount !== undefined && maxChars !== undefined && (
            <span className={charCount > maxChars ? "text-red-500 font-medium" : ""}>
              {charCount.toLocaleString()} / {maxChars.toLocaleString()}
            </span>
          )}
        </div>
        <div>{footer}</div>
      </div>
    </div>
  );
}
