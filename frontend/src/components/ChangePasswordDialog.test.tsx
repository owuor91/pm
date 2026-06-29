import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChangePasswordDialog } from "@/components/ChangePasswordDialog";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("ChangePasswordDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits current and new password and shows a success message", async () => {
    vi.mocked(api.changePassword).mockResolvedValue(undefined);

    render(<ChangePasswordDialog onClose={vi.fn()} />);

    await userEvent.type(screen.getByLabelText(/current password/i), "oldpassword");
    await userEvent.type(screen.getByLabelText(/new password/i), "newpassword");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(api.changePassword).toHaveBeenCalledWith("oldpassword", "newpassword");
    });
    expect(await screen.findByText(/password changed/i)).toBeInTheDocument();
  });

  it("shows an error message when the backend rejects the change", async () => {
    vi.mocked(api.changePassword).mockRejectedValue(new Error("Current password is incorrect"));

    render(<ChangePasswordDialog onClose={vi.fn()} />);

    await userEvent.type(screen.getByLabelText(/current password/i), "wrong");
    await userEvent.type(screen.getByLabelText(/new password/i), "newpassword");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/current password is incorrect/i)).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const onClose = vi.fn();
    render(<ChangePasswordDialog onClose={onClose} />);

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalled();
  });
});
