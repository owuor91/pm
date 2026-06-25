"use client";

import { useCallback, useMemo, useState, useEffect, useRef } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  rectIntersection,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { CopilotDialog } from "@/components/CopilotDialog";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";
import { getBoard, saveBoard } from "@/lib/api";

type KanbanBoardProps = {
  userId: number;
  onLogout?: () => void;
};

// Equal-width columns sit close enough together that closestCorners can pick
// the wrong column; checking literal pointer containment first is reliable,
// falling back to rect overlap only when the pointer briefly leaves every column.
const collisionDetection: CollisionDetection = (args) => {
  const pointerCollisions = pointerWithin(args);
  return pointerCollisions.length > 0 ? pointerCollisions : rectIntersection(args);
};

export const KanbanBoard = ({ userId, onLogout }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData>(initialData);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const loadBoard = async () => {
      try {
        const boardData = await getBoard(userId);
        setBoard(boardData);
      } catch (error) {
        console.error("Failed to load board:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadBoard();
  }, [userId]);

  useEffect(() => {
    if (isLoading) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await saveBoard(userId, board);
      } catch (error) {
        console.error("Failed to save board:", error);
      }
    }, 500);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [board, userId, isLoading]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    setBoard((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setBoard((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  const flushSave = useCallback(async () => {
    if (isLoading) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }

    await saveBoard(userId, board);
  }, [board, userId, isLoading]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-lg font-semibold text-[var(--navy-dark)]">Loading board...</p>
      </div>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col gap-5 px-3 pb-8 pt-5 sm:gap-6 sm:px-5 sm:pb-10 sm:pt-8 lg:gap-8 lg:px-6 lg:pt-10">
        <header className="flex flex-wrap items-center gap-4 rounded-2xl border border-[var(--stroke)] bg-white/80 p-5 shadow-[var(--shadow)] backdrop-blur sm:gap-6 sm:rounded-[32px] sm:p-8">
          <div className="min-w-0 flex-1 basis-full sm:basis-auto">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
              Single Board Kanban
            </p>
            <h1 className="mt-3 font-display text-2xl font-semibold text-[var(--navy-dark)] sm:text-3xl lg:text-4xl">
              Kanban Studio
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
              Keep momentum visible. Rename columns, drag cards between stages,
              and capture quick notes without getting buried in settings.
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 sm:px-5 sm:py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
              Focus
            </p>
            <p className="mt-2 text-base font-semibold text-[var(--primary-blue)] sm:text-lg">
              One board. Five columns. Zero clutter.
            </p>
          </div>
          {onLogout ? (
            <button
              type="button"
              onClick={onLogout}
              className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
            >
              Logout
            </button>
          ) : null}
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="board-scroll -mx-3 flex flex-1 gap-3 overflow-x-auto px-3 pb-3 sm:-mx-5 sm:gap-5 sm:px-5 lg:-mx-6 lg:px-6">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
                className="min-w-[260px] flex-1 basis-[260px] sm:min-w-[280px] sm:basis-[280px]"
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        <CopilotDialog
          userId={userId}
          onBeforeSend={flushSave}
          onBoardUpdate={(nextBoard) => setBoard(nextBoard)}
        />
      </main>
    </div>
  );
};
