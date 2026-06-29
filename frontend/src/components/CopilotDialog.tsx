"use client";

import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { ChatSidebar } from "@/components/ChatSidebar";
import type { BoardData } from "@/lib/kanban";

type CopilotDialogProps = {
  boardId: number;
  onBoardUpdate: (board: BoardData) => void;
  onBeforeSend?: () => Promise<void>;
};

export const CopilotDialog = ({ boardId, onBoardUpdate, onBeforeSend }: CopilotDialogProps) => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const buttonLabel = useMemo(() => (isOpen ? "Close board copilot" : "Open board copilot"), [isOpen]);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-label={buttonLabel}
        className={clsx(
          "fixed bottom-6 left-6 z-40 flex h-12 w-12 items-center justify-center rounded-full border border-[var(--stroke)] bg-white/90 shadow-[var(--shadow)] transition hover:bg-[var(--surface)]",
          isOpen && "ring-2 ring-[var(--accent-yellow)]"
        )}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M7.5 18.5L4 20l1.5-3.5V6.75C5.5 5.23 6.73 4 8.25 4h9.5C19.27 4 20.5 5.23 20.5 6.75v7.5c0 1.52-1.23 2.75-2.75 2.75H7.5Z"
            stroke="var(--navy-dark)"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M9 9.5h8M9 12h6"
            stroke="var(--primary-blue)"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </button>

      {isOpen ? (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-[rgba(3,33,71,0.32)]"
            aria-label="Close board copilot dialog"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute bottom-6 left-6 w-[380px] max-w-[calc(100vw-3rem)]">
            <div className="relative">
              <ChatSidebar
                boardId={boardId}
                onBoardUpdate={onBoardUpdate}
                onBeforeSend={onBeforeSend}
                className="max-h-[70vh] w-full"
              />
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="absolute right-4 top-4 rounded-full border border-[var(--stroke)] bg-white/90 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};

