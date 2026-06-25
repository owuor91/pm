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
import { BoardPicker } from "@/components/BoardPicker";
import { BoardMembersDialog } from "@/components/BoardMembersDialog";
import { ActivityDialog } from "@/components/ActivityDialog";
import { ChangePasswordDialog } from "@/components/ChangePasswordDialog";
import { createId, moveCard, type BoardData, type Column, type Priority } from "@/lib/kanban";
import {
  createBoard,
  deleteBoard,
  getBoardState,
  listBoards,
  removeBoardMember,
  renameBoard,
  saveBoardState,
  type BoardSummary,
} from "@/lib/api";

type KanbanBoardProps = {
  userId: number;
  username: string;
  onLogout?: () => void;
};

const EMPTY_BOARD: BoardData = { columns: [], cards: {} };

// Equal-width columns sit close enough together that closestCorners can pick
// the wrong column; checking literal pointer containment first is reliable,
// falling back to rect overlap only when the pointer briefly leaves every column.
const collisionDetection: CollisionDetection = (args) => {
  const pointerCollisions = pointerWithin(args);
  return pointerCollisions.length > 0 ? pointerCollisions : rectIntersection(args);
};

export const KanbanBoard = ({ userId, username, onLogout }: KanbanBoardProps) => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [boardsLoaded, setBoardsLoaded] = useState(false);
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [board, setBoard] = useState<BoardData>(EMPTY_BOARD);
  const [loadedBoardId, setLoadedBoardId] = useState<number | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [labelFilter, setLabelFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<Priority | "">("");
  const [showMembers, setShowMembers] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const isLoading = !boardsLoaded || (selectedBoardId !== null && loadedBoardId !== selectedBoardId);

  useEffect(() => {
    let cancelled = false;
    listBoards().then((result) => {
      if (cancelled) return;
      setBoards(result);
      setSelectedBoardId(result.length > 0 ? result[0].id : null);
      setBoardsLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedBoardId === null) return;
    let cancelled = false;
    getBoardState(selectedBoardId).then((data) => {
      if (cancelled) return;
      setBoard(data);
      setLoadedBoardId(selectedBoardId);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedBoardId]);

  useEffect(() => {
    if (isLoading || selectedBoardId === null) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await saveBoardState(selectedBoardId, board);
      } catch (error) {
        console.error("Failed to save board:", error);
      }
    }, 500);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [board, selectedBoardId, isLoading]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);

  const boardStats = useMemo(() => {
    const total = Object.keys(board.cards).length;
    const lastColumn = board.columns[board.columns.length - 1];
    const done = lastColumn ? lastColumn.cardIds.filter((id) => board.cards[id]).length : 0;
    const highPriority = Object.values(board.cards).filter(
      (c) => c.priority === "high" || c.priority === "critical"
    ).length;
    const overdue = Object.values(board.cards).filter((c) => {
      if (!c.dueDate) return false;
      return new Date(c.dueDate) < new Date(new Date().toDateString());
    }).length;
    return { total, done, highPriority, overdue };
  }, [board.cards, board.columns]);

  const allLabels = useMemo(() => {
    const labels = new Set<string>();
    Object.values(board.cards).forEach((card) => {
      card.labels?.forEach((label) => labels.add(label));
    });
    return Array.from(labels).sort();
  }, [board.cards]);

  const visibleColumns: Column[] = useMemo(() => {
    if (!search.trim() && !labelFilter && !priorityFilter) return board.columns;
    const query = search.trim().toLowerCase();
    return board.columns.map((column) => ({
      ...column,
      cardIds: column.cardIds.filter((cardId) => {
        const card = board.cards[cardId];
        if (!card) return false;
        const matchesQuery =
          !query ||
          card.title.toLowerCase().includes(query) ||
          card.details.toLowerCase().includes(query);
        const matchesLabel = !labelFilter || card.labels?.includes(labelFilter);
        const matchesPriority = !priorityFilter || card.priority === priorityFilter;
        return matchesQuery && matchesLabel && matchesPriority;
      }),
    }));
  }, [board.columns, board.cards, search, labelFilter, priorityFilter]);

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

  const handleAddCard = (
    columnId: string,
    title: string,
    details: string,
    dueDate?: string,
    labels?: string[],
    priority?: Priority
  ) => {
    const id = createId("card");
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet.", dueDate, labels, priority },
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

  const handleEditCard = (
    cardId: string,
    edits: { title: string; details: string; dueDate?: string; labels?: string[]; priority?: Priority }
  ) => {
    setBoard((prev) => {
      const existing = prev.cards[cardId];
      if (!existing) return prev;
      return {
        ...prev,
        cards: {
          ...prev.cards,
          [cardId]: { ...existing, ...edits },
        },
      };
    });
  };

  const handleSetWipLimit = (columnId: string, limit: number | undefined) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((c) =>
        c.id === columnId ? { ...c, wipLimit: limit } : c
      ),
    }));
  };

  const handleAddColumn = () => {
    const id = createId("col");
    setBoard((prev) => ({
      ...prev,
      columns: [...prev.columns, { id, title: "New Column", cardIds: [] }],
    }));
  };

  const handleDeleteColumn = (columnId: string) => {
    setBoard((prev) => {
      const column = prev.columns.find((c) => c.id === columnId);
      if (!column) return prev;
      if (column.cardIds.length > 0) {
        if (!window.confirm(`Delete "${column.title}"? This will also delete its ${column.cardIds.length} card(s).`)) {
          return prev;
        }
      }
      const deletedCardIds = new Set(column.cardIds);
      return {
        columns: prev.columns.filter((c) => c.id !== columnId),
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => !deletedCardIds.has(id))
        ),
      };
    });
  };

  const flushSave = useCallback(async () => {
    if (isLoading || selectedBoardId === null) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }

    await saveBoardState(selectedBoardId, board);
  }, [board, selectedBoardId, isLoading]);

  const handleSelectBoard = async (boardId: number) => {
    await flushSave();
    setSelectedBoardId(boardId);
  };

  const handleCreateBoard = async (name: string) => {
    await flushSave();
    const created = await createBoard(name);
    setBoards((prev) => [...prev, { id: created.id, name: created.name, role: "owner", updated_at: "" }]);
    setSelectedBoardId(created.id);
  };

  const handleRenameBoard = async (boardId: number, name: string) => {
    await renameBoard(boardId, name);
    setBoards((prev) => prev.map((b) => (b.id === boardId ? { ...b, name } : b)));
  };

  const handleDeleteBoard = async (boardId: number) => {
    await deleteBoard(boardId);
    const remaining = boards.filter((b) => b.id !== boardId);
    setBoards(remaining);
    if (selectedBoardId === boardId) {
      setSelectedBoardId(remaining.length > 0 ? remaining[0].id : null);
    }
  };

  const handleLeaveBoard = async () => {
    if (!selectedBoard) return;
    if (!window.confirm(`Leave "${selectedBoard.name}"? You will lose access unless an owner adds you back.`)) {
      return;
    }
    await removeBoardMember(selectedBoard.id, userId);
    const remaining = boards.filter((b) => b.id !== selectedBoard.id);
    setBoards(remaining);
    setSelectedBoardId(remaining.length > 0 ? remaining[0].id : null);
  };

  const selectedBoard = boards.find((b) => b.id === selectedBoardId) ?? null;

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
              Signed in as {username}
            </p>
            <h1 className="mt-3 font-display text-2xl font-semibold text-[var(--navy-dark)] sm:text-3xl lg:text-4xl">
              Kanban Studio
            </h1>
            <div className="mt-4">
              <BoardPicker
                boards={boards}
                selectedBoardId={selectedBoardId}
                onSelect={handleSelectBoard}
                onCreate={handleCreateBoard}
                onRename={handleRenameBoard}
                onDelete={handleDeleteBoard}
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setShowMembers(true)}
              disabled={!selectedBoard}
              className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)] disabled:opacity-50"
            >
              Members
            </button>
            <button
              type="button"
              onClick={() => setShowActivity(true)}
              disabled={!selectedBoard}
              className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)] disabled:opacity-50"
            >
              Activity
            </button>
            {selectedBoard?.role === "editor" ? (
              <button
                type="button"
                onClick={handleLeaveBoard}
                className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-red-600 transition hover:bg-red-50"
              >
                Leave board
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setShowChangePassword(true)}
              className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
            >
              Change password
            </button>
            {onLogout ? (
              <button
                type="button"
                onClick={onLogout}
                className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
              >
                Logout
              </button>
            ) : null}
          </div>
        </header>

        {selectedBoard && boardStats.total > 0 ? (
          <div
            className="flex flex-wrap items-center gap-6 rounded-2xl border border-[var(--stroke)] bg-white/80 px-5 py-3 shadow-[var(--shadow)] sm:rounded-3xl"
            data-testid="board-stats"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Total
              </span>
              <span className="font-display text-lg font-semibold text-[var(--navy-dark)]">
                {boardStats.total}
              </span>
            </div>
            <div className="flex-1">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  Progress
                </span>
                <span className="text-xs font-semibold text-[var(--gray-text)]">
                  {boardStats.done}/{boardStats.total}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--stroke)]">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                  style={{ width: `${(boardStats.done / boardStats.total) * 100}%` }}
                  data-testid="progress-bar"
                />
              </div>
            </div>
            {boardStats.highPriority > 0 ? (
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-red-500" />
                <span className="text-xs font-semibold text-red-600">
                  {boardStats.highPriority} high priority
                </span>
              </div>
            ) : null}
            {boardStats.overdue > 0 ? (
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                <span className="text-xs font-semibold text-amber-700">
                  {boardStats.overdue} overdue
                </span>
              </div>
            ) : null}
          </div>
        ) : null}

        {selectedBoard ? (
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--stroke)] bg-white/80 p-4 shadow-[var(--shadow)] sm:rounded-3xl">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search cards"
              aria-label="Search cards"
              className="min-w-[180px] flex-1 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
            />
            <select
              value={labelFilter}
              onChange={(event) => setLabelFilter(event.target.value)}
              aria-label="Filter by label"
              className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
            >
              <option value="">All labels</option>
              {allLabels.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
            <select
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value as Priority | "")}
              aria-label="Filter by priority"
              className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
            >
              <option value="">All priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <button
              type="button"
              onClick={handleAddColumn}
              className="rounded-full border border-dashed border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
              aria-label="Add column"
            >
              + Add column
            </button>
          </div>
        ) : null}

        {selectedBoard ? (
          <DndContext
            sensors={sensors}
            collisionDetection={collisionDetection}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="board-scroll -mx-3 flex flex-1 gap-3 overflow-x-auto px-3 pb-3 sm:-mx-5 sm:gap-5 sm:px-5 lg:-mx-6 lg:px-6">
              {visibleColumns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId]).filter(Boolean)}
                  onRename={handleRenameColumn}
                  onSetWipLimit={handleSetWipLimit}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onEditCard={handleEditCard}
                  onDeleteColumn={handleDeleteColumn}
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
        ) : (
          <p className="text-sm text-[var(--gray-text)]">Create a board to get started.</p>
        )}

        {selectedBoard ? (
          <CopilotDialog
            boardId={selectedBoard.id}
            onBeforeSend={flushSave}
            onBoardUpdate={(nextBoard) => setBoard(nextBoard)}
          />
        ) : null}

        {showMembers && selectedBoard ? (
          <BoardMembersDialog
            boardId={selectedBoard.id}
            role={selectedBoard.role}
            onClose={() => setShowMembers(false)}
          />
        ) : null}

        {showActivity && selectedBoard ? (
          <ActivityDialog boardId={selectedBoard.id} onClose={() => setShowActivity(false)} />
        ) : null}

        {showChangePassword ? (
          <ChangePasswordDialog onClose={() => setShowChangePassword(false)} />
        ) : null}
      </main>
    </div>
  );
};
