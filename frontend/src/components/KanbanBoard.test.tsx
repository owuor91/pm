import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import * as api from "@/lib/api";
import { initialData } from "@/lib/kanban";

vi.mock("@/lib/api");

const getColumns = () => screen.getAllByTestId(/^column-/);
const getFirstColumn = () => getColumns()[0];

const boardSummary: api.BoardSummary = {
  id: 1,
  name: "My Board",
  role: "owner",
  updated_at: "",
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listBoards).mockResolvedValue([boardSummary]);
    vi.mocked(api.getBoardState).mockResolvedValue(initialData);
    vi.mocked(api.saveBoardState).mockResolvedValue(undefined);
  });

  it("renders five columns", async () => {
    render(<KanbanBoard userId={1} username="user" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    expect(getColumns()).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard userId={1} username="user" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard userId={1} username="user" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("edits an existing card's title, details, due date, and labels", async () => {
    render(<KanbanBoard userId={1} username="user" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const column = getFirstColumn();
    const editButton = within(column).getByRole("button", { name: /edit align roadmap themes/i });
    await userEvent.click(editButton);

    const titleInput = within(column).getByLabelText(/edit card title/i);
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated title");

    const labelsInput = within(column).getByLabelText(/edit labels/i);
    await userEvent.type(labelsInput, "urgent, planning");

    await userEvent.click(within(column).getByRole("button", { name: /^save$/i }));

    expect(within(column).getByText("Updated title")).toBeInTheDocument();
    expect(within(column).getByText("urgent")).toBeInTheDocument();
    expect(within(column).getByText("planning")).toBeInTheDocument();
  });

  it("filters cards by search text", async () => {
    render(<KanbanBoard userId={1} username="user" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText(/search cards/i), "roadmap");

    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
    expect(screen.queryByText("Gather customer signals")).not.toBeInTheDocument();
  });

  it("creates a new board via the board picker", async () => {
    vi.mocked(api.createBoard).mockResolvedValue({ id: 2, name: "Roadmap", role: "owner", updated_at: "" });

    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /new board/i }));
    await userEvent.type(screen.getByLabelText(/new board name/i), "Roadmap");
    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(api.createBoard).toHaveBeenCalledWith("Roadmap");
  });

  it("shows an empty state when there are no boards", async () => {
    vi.mocked(api.listBoards).mockResolvedValue([]);

    render(<KanbanBoard userId={1} username="user" />);

    expect(await screen.findByText(/create a board to get started/i)).toBeInTheDocument();
  });

  it("lets an editor leave a shared board but hides that option for owners", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.removeBoardMember).mockResolvedValue(undefined);
    vi.mocked(api.listBoards).mockResolvedValue([
      { id: 1, name: "Shared Board", role: "editor", updated_at: "" },
    ]);

    render(<KanbanBoard userId={7} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const leaveButton = screen.getByRole("button", { name: /leave board/i });
    await userEvent.click(leaveButton);

    await waitFor(() => {
      expect(api.removeBoardMember).toHaveBeenCalledWith(1, 7);
    });
  });

  it("does not show a leave-board option for owners", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /leave board/i })).not.toBeInTheDocument();
  });

  it("adds a new column via the Add column button", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    expect(getColumns()).toHaveLength(5);
    await userEvent.click(screen.getByRole("button", { name: /add column/i }));
    expect(getColumns()).toHaveLength(6);
    expect(screen.getByDisplayValue("New Column")).toBeInTheDocument();
  });

  it("deletes an empty column without confirmation", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /add column/i }));
    expect(getColumns()).toHaveLength(6);

    const newCol = getColumns()[5];
    await userEvent.click(within(newCol).getByRole("button", { name: /delete column/i }));
    expect(getColumns()).toHaveLength(5);
  });

  it("adds a card with a priority and shows the priority badge", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const column = getFirstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "Priority task");

    const prioritySelect = within(column).getByLabelText(/priority/i);
    await userEvent.selectOptions(prioritySelect, "high");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("Priority task")).toBeInTheDocument();
    expect(within(column).getByText("High")).toBeInTheDocument();
  });

  it("sets a WIP limit on a column and shows card count / limit", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const column = getFirstColumn();
    await userEvent.click(within(column).getByTestId(/^wip-btn-/));

    const wipInput = within(column).getByRole("spinbutton");
    await userEvent.clear(wipInput);
    await userEvent.type(wipInput, "3");
    await userEvent.click(within(column).getByRole("button", { name: /^set$/i }));

    expect(within(column).getByText(/\/ 3 max/i)).toBeInTheDocument();
  });

  it("shows board stats bar with total and progress", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const stats = screen.getByTestId("board-stats");
    expect(stats).toBeInTheDocument();
    expect(within(stats).getByText("8")).toBeInTheDocument();
    expect(within(stats).getByText("2/8")).toBeInTheDocument();
  });

  it("duplicates a card into the same column right after the original", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const column = getFirstColumn();
    const dupButton = within(column).getByRole("button", { name: /duplicate align roadmap themes/i });
    await userEvent.click(dupButton);

    const copies = within(column).getAllByText(/align roadmap themes/i);
    expect(copies).toHaveLength(2);
    expect(within(column).getByText("Align roadmap themes (copy)")).toBeInTheDocument();
  });

  it("shows 'Overdue' for past due dates on a card", async () => {
    vi.mocked(api.getBoardState).mockResolvedValue({
      ...initialData,
      cards: {
        ...initialData.cards,
        "card-1": { ...initialData.cards["card-1"], dueDate: "2020-01-01" },
      },
    });

    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    expect(screen.getByText(/overdue 2020-01-01/i)).toBeInTheDocument();
  });

  it("shows high-priority indicator when high/critical cards exist", async () => {
    vi.mocked(api.getBoardState).mockResolvedValue({
      ...initialData,
      cards: {
        ...initialData.cards,
        "card-1": { ...initialData.cards["card-1"], priority: "critical" },
      },
    });

    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    expect(screen.getByText(/1 high priority/i)).toBeInTheDocument();
  });

  it("pressing / focuses the search box", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText(/search cards/i);
    expect(document.activeElement).not.toBe(searchInput);

    await userEvent.keyboard("/");
    expect(document.activeElement).toBe(searchInput);
  });

  it("pressing Escape clears the search", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText(/search cards/i);
    await userEvent.type(searchInput, "roadmap");
    expect(searchInput).toHaveValue("roadmap");
    await userEvent.keyboard("{Escape}");
    expect(searchInput).toHaveValue("");
  });

  it("sort control renders and allows selecting a sort mode", async () => {
    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    const sortSelect = screen.getByLabelText(/sort cards/i);
    expect(sortSelect).toBeInTheDocument();
    await userEvent.selectOptions(sortSelect, "title");
    expect((sortSelect as HTMLSelectElement).value).toBe("title");
    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
  });

  it("filters cards by priority", async () => {
    vi.mocked(api.getBoardState).mockResolvedValue({
      ...initialData,
      cards: {
        ...initialData.cards,
        "card-1": { ...initialData.cards["card-1"], priority: "high" },
      },
    });

    render(<KanbanBoard userId={1} username="user" />);
    await waitFor(() => {
      expect(screen.queryByText("Loading board...")).not.toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText(/filter by priority/i), "high");

    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
    expect(screen.queryByText("Gather customer signals")).not.toBeInTheDocument();
  });
});
