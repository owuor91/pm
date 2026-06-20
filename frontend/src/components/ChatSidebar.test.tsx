import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChatSidebar } from "@/components/ChatSidebar";
import * as api from "@/lib/api";
import { initialData } from "@/lib/kanban";

vi.mock("@/lib/api");

describe("ChatSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends a prompt and applies the returned board state", async () => {
    const onBoardUpdate = vi.fn();
    const onBeforeSend = vi.fn().mockResolvedValue(undefined);

    vi.mocked(api.aiChat).mockResolvedValue({
      message: "Done.",
      applied: true,
      confidence: 0.9,
      board: initialData,
    });

    render(<ChatSidebar userId={1} onBoardUpdate={onBoardUpdate} onBeforeSend={onBeforeSend} />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/message the ai/i), "Add a card");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(api.aiChat).toHaveBeenCalled();
    });

    expect(onBeforeSend).toHaveBeenCalled();
    expect(onBoardUpdate).toHaveBeenCalledWith(initialData);
    expect(await screen.findByText("Done.")).toBeInTheDocument();
  });
});

