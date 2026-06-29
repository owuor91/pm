"use client";

import type { ReactNode } from "react";

type ModalShellProps = {
  title: string;
  closeLabel: string;
  onClose: () => void;
  children: ReactNode;
};

export const ModalShell = ({ title, closeLabel, onClose, children }: ModalShellProps) => {
  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 cursor-default bg-[rgba(3,33,71,0.32)]"
        aria-label={closeLabel}
        onClick={onClose}
      />
      <div className="absolute left-1/2 top-1/2 w-[420px] max-w-[calc(100vw-3rem)] -translate-x-1/2 -translate-y-1/2 rounded-[28px] border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)]">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[var(--stroke)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.25em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
          >
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};
