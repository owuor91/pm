import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ActivityDialog } from "@/components/ActivityDialog";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("ActivityDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows activity entries", async () => {
    vi.mocked(api.getActivity).mockResolvedValue([
      {
        id: 1,
        board_id: 1,
        user_id: 1,
        username: "alice",
        action: "board_state_saved",
        details: null,
        created_at: "2026-06-25 12:00:00",
      },
    ]);

    render(<ActivityDialog boardId={1} onClose={vi.fn()} />);

    expect(await screen.findByText(/alice/)).toBeInTheDocument();
    expect(screen.getByText(/updated the board/)).toBeInTheDocument();
  });

  it("shows an empty state when there is no activity", async () => {
    vi.mocked(api.getActivity).mockResolvedValue([]);

    render(<ActivityDialog boardId={1} onClose={vi.fn()} />);

    expect(await screen.findByText(/no activity yet/i)).toBeInTheDocument();
  });
});
