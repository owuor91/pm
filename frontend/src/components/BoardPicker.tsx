"use client";

import { useState, type FormEvent } from "react";
import type { BoardSummary } from "@/lib/api";

type BoardPickerProps = {
  boards: BoardSummary[];
  selectedBoardId: number | null;
  onSelect: (boardId: number) => void;
  onCreate: (name: string) => void;
  onRename: (boardId: number, name: string) => void;
  onDelete: (boardId: number) => void;
};

export const BoardPicker = ({
  boards,
  selectedBoardId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: BoardPickerProps) => {
  const [isCreating, setIsCreating] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [draftName, setDraftName] = useState("");

  const selectedBoard = boards.find((board) => board.id === selectedBoardId) ?? null;

  const handleCreateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draftName.trim()) return;
    onCreate(draftName.trim());
    setDraftName("");
    setIsCreating(false);
  };

  const handleRenameSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedBoard || !draftName.trim()) return;
    onRename(selectedBoard.id, draftName.trim());
    setDraftName("");
    setIsRenaming(false);
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="sr-only" htmlFor="board-select">
        Select board
      </label>
      <select
        id="board-select"
        value={selectedBoardId ?? ""}
        onChange={(event) => onSelect(Number(event.target.value))}
        className="rounded-2xl border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
      >
        {boards.map((board) => (
          <option key={board.id} value={board.id}>
            {board.name}
          </option>
        ))}
      </select>

      {isCreating ? (
        <form onSubmit={handleCreateSubmit} className="flex items-center gap-2">
          <input
            autoFocus
            value={draftName}
            onChange={(event) => setDraftName(event.target.value)}
            placeholder="Board name"
            aria-label="New board name"
            className="rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
          />
          <button
            type="submit"
            className="rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white"
          >
            Create
          </button>
          <button
            type="button"
            onClick={() => {
              setIsCreating(false);
              setDraftName("");
            }}
            className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]"
          >
            Cancel
          </button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsCreating(true)}
          className="rounded-full border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
        >
          New board
        </button>
      )}

      {selectedBoard ? (
        isRenaming ? (
          <form onSubmit={handleRenameSubmit} className="flex items-center gap-2">
            <input
              autoFocus
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              placeholder="New name"
              aria-label="Rename board"
              className="rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
            />
            <button
              type="submit"
              className="rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => setIsRenaming(false)}
              className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]"
            >
              Cancel
            </button>
          </form>
        ) : (
          <>
            <button
              type="button"
              onClick={() => {
                setDraftName(selectedBoard.name);
                setIsRenaming(true);
              }}
              className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
            >
              Rename
            </button>
            {selectedBoard.role === "owner" && boards.length > 1 ? (
              <button
                type="button"
                onClick={() => onDelete(selectedBoard.id)}
                className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-red-600 transition hover:bg-red-50"
              >
                Delete
              </button>
            ) : null}
          </>
        )
      ) : null}
    </div>
  );
};
