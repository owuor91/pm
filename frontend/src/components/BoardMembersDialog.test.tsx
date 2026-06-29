import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { BoardMembersDialog } from "@/components/BoardMembersDialog";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("BoardMembersDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listBoardMembers).mockResolvedValue([
      { user_id: 1, username: "alice", role: "owner" },
    ]);
  });

  it("lists members", async () => {
    render(<BoardMembersDialog boardId={1} role="owner" onClose={vi.fn()} />);

    expect(await screen.findByText("alice")).toBeInTheDocument();
  });

  it("adds a member as owner", async () => {
    vi.mocked(api.addBoardMember).mockResolvedValue({ user_id: 2, username: "bob", role: "editor" });

    render(<BoardMembersDialog boardId={1} role="owner" onClose={vi.fn()} />);
    await screen.findByText("alice");

    await userEvent.type(screen.getByLabelText(/username to add/i), "bob");
    await userEvent.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => {
      expect(api.addBoardMember).toHaveBeenCalledWith(1, "bob", "editor");
    });
  });

  it("does not show the add-member form for editors", async () => {
    render(<BoardMembersDialog boardId={1} role="editor" onClose={vi.fn()} />);
    await screen.findByText("alice");

    expect(screen.queryByLabelText(/username to add/i)).not.toBeInTheDocument();
  });

  it("removes a member", async () => {
    vi.mocked(api.listBoardMembers).mockResolvedValue([
      { user_id: 1, username: "alice", role: "owner" },
      { user_id: 2, username: "bob", role: "editor" },
    ]);
    vi.mocked(api.removeBoardMember).mockResolvedValue(undefined);

    render(<BoardMembersDialog boardId={1} role="owner" onClose={vi.fn()} />);
    await screen.findByText("bob");

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));

    await waitFor(() => {
      expect(api.removeBoardMember).toHaveBeenCalledWith(1, 2);
    });
  });

  it("hides the remove button for the sole owner", async () => {
    render(<BoardMembersDialog boardId={1} role="owner" onClose={vi.fn()} />);
    await screen.findByText("alice");

    expect(screen.queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
  });

  it("shows the remove button for an owner when there is more than one owner", async () => {
    vi.mocked(api.listBoardMembers).mockResolvedValue([
      { user_id: 1, username: "alice", role: "owner" },
      { user_id: 2, username: "bob", role: "owner" },
    ]);

    render(<BoardMembersDialog boardId={1} role="owner" onClose={vi.fn()} />);
    await screen.findByText("bob");

    expect(screen.getAllByRole("button", { name: /remove/i })).toHaveLength(2);
  });

  it("shows an error when the backend rejects removing the last owner", async () => {
    vi.mocked(api.listBoardMembers).mockResolvedValue([
      { user_id: 1, username: "alice", role: "owner" },
      { user_id: 2, username: "bob", role: "owner" },
    ]);
    vi.mocked(api.removeBoardMember).mockRejectedValue(new Error("Cannot remove the last owner of a board"));

    render(<BoardMembersDialog boardId={1} role="owner" onClose={vi.fn()} />);
    await screen.findByText("bob");

    await userEvent.click(screen.getAllByRole("button", { name: /remove/i })[0]);

    expect(await screen.findByText(/cannot remove the last owner/i)).toBeInTheDocument();
  });
});
