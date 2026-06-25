import { useState } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column, Priority } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onSetWipLimit: (columnId: string, limit: number | undefined) => void;
  onAddCard: (columnId: string, title: string, details: string, dueDate?: string, labels?: string[], priority?: Priority) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onEditCard: (
    cardId: string,
    edits: { title: string; details: string; dueDate?: string; labels?: string[]; priority?: Priority }
  ) => void;
  onDuplicateCard: (columnId: string, cardId: string) => void;
  onDeleteColumn?: (columnId: string) => void;
  className?: string;
};

export const KanbanColumn = ({
  column,
  cards,
  onRename,
  onSetWipLimit,
  onAddCard,
  onDeleteCard,
  onEditCard,
  onDuplicateCard,
  onDeleteColumn,
  className,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const [editingWip, setEditingWip] = useState(false);
  const [wipDraft, setWipDraft] = useState(String(column.wipLimit ?? ""));

  const isOverLimit = column.wipLimit !== undefined && cards.length > column.wipLimit;
  const isAtLimit = column.wipLimit !== undefined && cards.length === column.wipLimit;

  const commitWip = () => {
    const parsed = parseInt(wipDraft, 10);
    if (wipDraft.trim() === "" || isNaN(parsed) || parsed <= 0) {
      onSetWipLimit(column.id, undefined);
    } else {
      onSetWipLimit(column.id, parsed);
    }
    setEditingWip(false);
  };

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[420px] flex-col rounded-2xl border bg-[var(--surface-strong)] p-3 shadow-[var(--shadow)] transition sm:min-h-[520px] sm:rounded-3xl sm:p-4",
        isOverLimit
          ? "border-red-300 ring-2 ring-red-200"
          : isAtLimit
          ? "border-amber-300"
          : "border-[var(--stroke)]",
        isOver && !isOverLimit && "ring-2 ring-[var(--accent-yellow)]",
        className
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-3">
            <div
              className={clsx(
                "h-2 w-10 rounded-full",
                isOverLimit ? "bg-red-400" : isAtLimit ? "bg-amber-400" : "bg-[var(--accent-yellow)]"
              )}
            />
            <span
              className={clsx(
                "text-xs font-semibold uppercase tracking-[0.2em]",
                isOverLimit ? "text-red-600" : "text-[var(--gray-text)]"
              )}
            >
              {cards.length} cards
              {column.wipLimit !== undefined ? (
                <span className="ml-1 opacity-70">/ {column.wipLimit} max</span>
              ) : null}
            </span>
          </div>
          <input
            value={column.title}
            onChange={(event) => onRename(column.id, event.target.value)}
            className="mt-3 w-full bg-transparent font-display text-lg font-semibold text-[var(--navy-dark)] outline-none"
            aria-label="Column title"
          />
        </div>
        <div className="mt-1 flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={() => {
              setWipDraft(String(column.wipLimit ?? ""));
              setEditingWip(true);
            }}
            className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--primary-blue)]"
            aria-label={`Set WIP limit for ${column.title}`}
            data-testid={`wip-btn-${column.id}`}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
              <path d="M12 8v4m0 4h.01" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
          {onDeleteColumn ? (
            <button
              type="button"
              onClick={() => onDeleteColumn(column.id)}
              className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-red-500"
              aria-label={`Delete column ${column.title}`}
              data-testid={`delete-column-${column.id}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M5 7h14M10 7V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2m-7 0 1 13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-13M10 11v6m4-6v6"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          ) : null}
        </div>
      </div>

      {editingWip ? (
        <div className="mt-2 flex items-center gap-2">
          <input
            type="number"
            min="1"
            value={wipDraft}
            onChange={(e) => setWipDraft(e.target.value)}
            placeholder="No limit"
            aria-label={`WIP limit for ${column.title}`}
            className="w-24 rounded-xl border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <button
            type="button"
            onClick={commitWip}
            className="rounded-full bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white"
          >
            Set
          </button>
          <button
            type="button"
            onClick={() => setEditingWip(false)}
            className="rounded-full border border-[var(--stroke)] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]"
          >
            Cancel
          </button>
        </div>
      ) : null}

      <div className="mt-4 flex flex-1 flex-col gap-3">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onEdit={onEditCard}
              onDuplicate={(cardId) => onDuplicateCard(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details, dueDate, labels, priority) =>
          onAddCard(column.id, title, details, dueDate, labels, priority)
        }
      />
    </section>
  );
};
