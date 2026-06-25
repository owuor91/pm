import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card, Priority } from "@/lib/kanban";

const PRIORITY_STYLES: Record<Priority, { badge: string; label: string }> = {
  low: { badge: "bg-emerald-100 text-emerald-700", label: "Low" },
  medium: { badge: "bg-amber-100 text-amber-700", label: "Medium" },
  high: { badge: "bg-orange-100 text-orange-700", label: "High" },
  critical: { badge: "bg-red-100 text-red-700", label: "Critical" },
};

type CardEdits = {
  title: string;
  details: string;
  dueDate?: string;
  labels?: string[];
  priority?: Priority;
};

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEdit: (cardId: string, edits: CardEdits) => void;
};

export const KanbanCard = ({ card, onDelete, onEdit }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState({
    title: card.title,
    details: card.details,
    dueDate: card.dueDate ?? "",
    labels: card.labels?.join(", ") ?? "",
    priority: card.priority ?? ("" as Priority | ""),
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const startEditing = () => {
    setDraft({
      title: card.title,
      details: card.details,
      dueDate: card.dueDate ?? "",
      labels: card.labels?.join(", ") ?? "",
      priority: card.priority ?? "",
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    if (!draft.title.trim()) return;
    const labels = draft.labels
      .split(",")
      .map((label) => label.trim())
      .filter(Boolean);
    onEdit(card.id, {
      title: draft.title.trim(),
      details: draft.details.trim() || "No details yet.",
      dueDate: draft.dueDate || undefined,
      labels: labels.length > 0 ? labels : undefined,
      priority: draft.priority || undefined,
    });
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <article
        ref={setNodeRef}
        style={style}
        className="relative space-y-2 rounded-2xl border border-[var(--primary-blue)]/40 bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]"
        data-testid={`card-${card.id}`}
      >
        <input
          value={draft.title}
          onChange={(event) => setDraft((prev) => ({ ...prev, title: event.target.value }))}
          aria-label="Edit card title"
          className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-semibold text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <textarea
          value={draft.details}
          onChange={(event) => setDraft((prev) => ({ ...prev, details: event.target.value }))}
          aria-label="Edit card details"
          rows={3}
          className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none focus:border-[var(--primary-blue)]"
        />
        <input
          type="date"
          value={draft.dueDate}
          onChange={(event) => setDraft((prev) => ({ ...prev, dueDate: event.target.value }))}
          aria-label="Edit due date"
          className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <input
          value={draft.labels}
          onChange={(event) => setDraft((prev) => ({ ...prev, labels: event.target.value }))}
          aria-label="Edit labels"
          placeholder="Labels (comma separated)"
          className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <select
          value={draft.priority}
          onChange={(event) => setDraft((prev) => ({ ...prev, priority: event.target.value as Priority | "" }))}
          aria-label="Edit priority"
          className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        >
          <option value="">No priority</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSave}
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
          >
            Cancel
          </button>
        </div>
      </article>
    );
  }

  const priorityStyle = card.priority ? PRIORITY_STYLES[card.priority] : null;

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="absolute right-3 top-3 flex items-center gap-1 opacity-0 transition focus-within:opacity-100 group-hover:opacity-100">
        <button
          type="button"
          onClick={startEditing}
          className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--primary-blue)]"
          aria-label={`Edit ${card.title}`}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M4 20h4l11-11-4-4L4 16v4Z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-red-500"
          aria-label={`Delete ${card.title}`}
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
      </div>
      <div className="flex items-start gap-2 pr-14">
        {priorityStyle ? (
          <span
            className={clsx(
              "mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              priorityStyle.badge
            )}
            data-testid={`priority-${card.id}`}
          >
            {priorityStyle.label}
          </span>
        ) : null}
        <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
          {card.title}
        </h4>
      </div>
      <p className="mt-2 pr-7 text-sm leading-6 text-[var(--gray-text)]">{card.details}</p>
      {card.labels && card.labels.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {card.labels.map((label) => (
            <span
              key={label}
              className="rounded-full bg-[var(--primary-blue)]/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--primary-blue)]"
            >
              {label}
            </span>
          ))}
        </div>
      ) : null}
      {card.dueDate ? (
        <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
          Due {card.dueDate}
        </p>
      ) : null}
    </article>
  );
};
