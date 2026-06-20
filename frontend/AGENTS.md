# Frontend AGENTS.md

## Overview

This frontend is a Next.js app built with React 19 and Tailwind CSS. It renders a single-page Kanban board demo with drag-and-drop support using `@dnd-kit`.

## Key files

- `src/app/page.tsx`
  - Renders the main `KanbanBoard` component.

- `src/components/KanbanBoard.tsx`
  - Main client component for the Kanban board.
  - Uses local state to manage board data.
  - Supports drag-and-drop with `DndContext` from `@dnd-kit/core`.
  - Handles column renaming, adding cards, deleting cards, and moving cards between columns.

- `src/components/KanbanColumn.tsx`
  - Renders a single column with a title input, card list, and add-card form.
  - Uses `useDroppable` and `SortableContext` to enable dropping cards into the column.

- `src/components/KanbanCard.tsx`
  - Renders an individual card and delete button.
  - Uses `useSortable` from `@dnd-kit/sortable` for drag behavior.

- `src/components/KanbanCardPreview.tsx`
  - Renders the drag overlay preview shown while dragging a card.

- `src/components/NewCardForm.tsx`
  - Toggles between open/closed states for adding a card.
  - Validates the title and calls `onAdd` with title/details.

- `src/lib/kanban.ts`
  - Defines `Card`, `Column`, and `BoardData` types.
  - Provides static `initialData` for the demo board.
  - Implements `moveCard` logic for within-column and cross-column drag behavior.
  - Includes `createId` helper for new cards.

## Tests

- `src/components/KanbanBoard.test.tsx`
  - Unit tests cover rendering columns, renaming a column, and adding/removing a card.

## Notes

- The current frontend is fully client-side and does not call a backend.
- The app currently uses hardcoded initial board data from `src/lib/kanban.ts`.
- The plan indicates this frontend should later be integrated with a FastAPI backend and Docker.
