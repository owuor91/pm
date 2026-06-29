"use client";

import { useMemo, useRef, useState, type FormEvent, useEffect } from "react";
import clsx from "clsx";
import { aiChat, type ChatMessage } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type ChatSidebarProps = {
  boardId: number;
  onBoardUpdate: (board: BoardData) => void;
  onBeforeSend?: () => Promise<void>;
  className?: string;
};

export const ChatSidebar = ({
  boardId,
  onBoardUpdate,
  onBeforeSend,
  className,
}: ChatSidebarProps) => {
  const introMessage: ChatMessage = {
    role: "assistant",
    content:
      "Tell me what you want to change on your board. I can create, move, edit, or delete cards.",
  };

  const [messages, setMessages] = useState<ChatMessage[]>([
    introMessage,
  ]);
  const [prompt, setPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement | null>(null);

  const conversation = useMemo(() => messages.slice(1), [messages]);

  useEffect(() => {
    const node = scrollAnchorRef.current;
    if (!node) return;
    if (typeof node.scrollIntoView !== "function") return;
    node.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const nextPrompt = prompt.trim();
    if (!nextPrompt || isSending) return;

    setError(null);
    setIsSending(true);
    setPrompt("");

    setMessages((prev) => [...prev, { role: "user", content: nextPrompt }]);

    try {
      if (onBeforeSend) {
        await onBeforeSend();
      }

      const result = await aiChat(boardId, nextPrompt, conversation);
      onBoardUpdate(result.board as BoardData);
      setMessages((prev) => [...prev, { role: "assistant", content: result.message }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach the AI service.");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I couldn’t complete that request. Try again in a moment.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside
      className={clsx(
        "flex max-h-[calc(100vh-6rem)] flex-col rounded-[32px] border border-[var(--stroke)] bg-white/80 shadow-[var(--shadow)] backdrop-blur",
        className
      )}
    >
      <div className="border-b border-[var(--stroke)] px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
          AI Assistant
        </p>
        <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
          Board copilot
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
          Ask for changes like “move card X to Review” or “create three tasks for launch”.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="flex flex-col gap-4">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={clsx(
                "max-w-[92%] rounded-3xl border px-4 py-3 text-sm leading-6 shadow-sm",
                message.role === "user"
                  ? "ml-auto border-[var(--primary-blue)]/20 bg-[var(--primary-blue)]/10 text-[var(--navy-dark)]"
                  : "mr-auto border-[var(--stroke)] bg-[var(--surface)] text-[var(--navy-dark)]"
              )}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                {message.role === "user" ? "You" : "AI"}
              </p>
              <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
            </div>
          ))}

          {isSending ? (
            <div className="mr-auto max-w-[92%] rounded-3xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--gray-text)] shadow-sm">
              Thinking…
            </div>
          ) : null}
          <div ref={scrollAnchorRef} />
        </div>
      </div>

      <div className="border-t border-[var(--stroke)] px-6 py-5">
        {error ? (
          <p className="mb-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        ) : null}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="sr-only" htmlFor="ai-prompt">
            Message the AI
          </label>
          <textarea
            id="ai-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={isSending}
            rows={3}
            placeholder="Try: Create a card 'Prep demo' in Backlog"
            className="w-full resize-none rounded-3xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isSending || !prompt.trim()}
            className="rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-white transition hover:brightness-110 disabled:opacity-50"
          >
            {isSending ? "Sending…" : "Send"}
          </button>
        </form>
      </div>
    </aside>
  );
};
