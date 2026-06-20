import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginGate } from "@/components/LoginGate";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("LoginGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getBoard).mockResolvedValue({ columns: [], cards: {} });
    vi.mocked(api.saveBoard).mockResolvedValue({ state: "" });
  });

  it("shows the login form initially", () => {
    render(<LoginGate />);

    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("calls authUser on form submit", async () => {
    vi.mocked(api.authUser).mockResolvedValue({ user_id: 1, username: "user" });

    render(<LoginGate />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "user");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(api.authUser).toHaveBeenCalledWith("user", "password");
  });

  it("authenticates and shows the board on valid credentials", async () => {
    vi.mocked(api.authUser).mockResolvedValue({ user_id: 1, username: "user" });

    render(<LoginGate />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "user");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
    });
  });

  it("shows error on invalid credentials", async () => {
    vi.mocked(api.authUser).mockRejectedValue(new Error("Authentication failed"));

    render(<LoginGate />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "bad");
    await user.type(screen.getByLabelText(/password/i), "creds");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid username or password/i)).toBeInTheDocument();
    });
  });
});
