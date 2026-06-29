import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { BoardPicker } from "@/components/BoardPicker";
import type { BoardSummary } from "@/lib/api";

const boards: BoardSummary[] = [
  { id: 1, name: "Board One", role: "owner", updated_at: "" },
  { id: 2, name: "Board Two", role: "editor", updated_at: "" },
];

describe("BoardPicker", () => {
  it("lists all boards in the select", () => {
    render(
      <BoardPicker
        boards={boards}
        selectedBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.getByRole("option", { name: "Board One" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Board Two" })).toBeInTheDocument();
  });

  it("calls onSelect when switching boards", async () => {
    const onSelect = vi.fn();
    render(
      <BoardPicker
        boards={boards}
        selectedBoardId={1}
        onSelect={onSelect}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText(/select board/i), "2");
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("creates a board with the entered name", async () => {
    const onCreate = vi.fn();
    render(
      <BoardPicker
        boards={boards}
        selectedBoardId={1}
        onSelect={vi.fn()}
        onCreate={onCreate}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /new board/i }));
    await userEvent.type(screen.getByLabelText(/new board name/i), "Marketing");
    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(onCreate).toHaveBeenCalledWith("Marketing");
  });

  it("only shows delete for the owner when more than one board exists", () => {
    render(
      <BoardPicker
        boards={boards}
        selectedBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("hides delete for an editor", () => {
    render(
      <BoardPicker
        boards={boards}
        selectedBoardId={2}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
  });
});
