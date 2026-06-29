import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginGate } from "@/components/LoginGate";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("LoginGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.me).mockRejectedValue(new Error("not authenticated"));
    vi.mocked(api.listBoards).mockResolvedValue([]);
  });

  it("shows the login form initially", async () => {
    render(<LoginGate />);

    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("calls login on form submit", async () => {
    vi.mocked(api.login).mockResolvedValue({ user_id: 1, username: "user" });

    render(<LoginGate />);
    await screen.findByRole("heading", { name: /sign in/i });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "user");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(api.login).toHaveBeenCalledWith("user", "password");
  });

  it("authenticates and shows the board on valid credentials", async () => {
    vi.mocked(api.login).mockResolvedValue({ user_id: 1, username: "user" });

    render(<LoginGate />);
    await screen.findByRole("heading", { name: /sign in/i });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "user");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
    });
  });

  it("shows error on invalid credentials", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("Invalid credentials"));

    render(<LoginGate />);
    await screen.findByRole("heading", { name: /sign in/i });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "bad");
    await user.type(screen.getByLabelText(/password/i), "creds");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid username or password/i)).toBeInTheDocument();
    });
  });

  it("shows the lockout message verbatim instead of a generic error", async () => {
    vi.mocked(api.login).mockRejectedValue(
      new Error("Too many failed login attempts. Try again later.")
    );

    render(<LoginGate />);
    await screen.findByRole("heading", { name: /sign in/i });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "alice");
    await user.type(screen.getByLabelText(/password/i), "whatever");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/too many failed login attempts/i)).toBeInTheDocument();
  });

  it("toggles to signup mode and calls signup", async () => {
    vi.mocked(api.signup).mockResolvedValue({ user_id: 2, username: "newperson" });

    render(<LoginGate />);
    await screen.findByRole("heading", { name: /sign in/i });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /need an account/i }));
    expect(screen.getByRole("heading", { name: /create an account/i })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/username/i), "newperson");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign up/i }));

    expect(api.signup).toHaveBeenCalledWith("newperson", "password");
  });

  it("returns to login mode (not signup) after logging out", async () => {
    vi.mocked(api.signup).mockResolvedValue({ user_id: 2, username: "newperson" });
    vi.mocked(api.logout).mockResolvedValue(undefined);

    render(<LoginGate />);
    await screen.findByRole("heading", { name: /sign in/i });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /need an account/i }));
    await user.type(screen.getByLabelText(/username/i), "newperson");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign up/i }));

    const logoutButton = await screen.findByRole("button", { name: /logout/i });
    await user.click(logoutButton);

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
