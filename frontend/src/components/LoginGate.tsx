"use client";

import { useEffect, useState, type FormEvent } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { login, logout, me, signup } from "@/lib/api";

export const LoginGate = () => {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [session, setSession] = useState<{ userId: number; username: string } | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    me()
      .then((result) => setSession({ userId: result.user_id, username: result.username }))
      .catch(() => setSession(null))
      .finally(() => setIsBootstrapping(false));
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const result = mode === "login" ? await login(username, password) : await signup(username, password);
      setSession({ userId: result.user_id, username: result.username });
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (mode === "login") {
        // Surface lockout messages verbatim; keep other login failures generic so we
        // don't hint at whether a username exists.
        setError(message.toLowerCase().includes("too many") ? message : "Invalid username or password.");
      } else {
        setError(message || "Could not create account.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout().catch(() => undefined);
    setSession(null);
    setUsername("");
    setPassword("");
    setError("");
    setMode("login");
  };

  if (isBootstrapping) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-lg font-semibold text-[var(--navy-dark)]">Loading...</p>
      </div>
    );
  }

  if (session) {
    return <KanbanBoard userId={session.userId} username={session.username} onLogout={handleLogout} />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
      <div className="w-full max-w-md rounded-[32px] border border-[var(--stroke)] bg-white p-10 shadow-[var(--shadow)]">
        <h1 className="text-3xl font-semibold text-[var(--navy-dark)]">
          {mode === "login" ? "Sign in" : "Create an account"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
          {mode === "login"
            ? "Enter your credentials to access your boards."
            : "Choose a username and password to get started."}
        </p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <label className="block text-sm font-semibold text-[var(--navy-dark)]">
            Username
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={isLoading}
              className="mt-2 w-full rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm outline-none transition focus:border-[var(--primary-blue)] disabled:opacity-50"
              autoComplete="username"
            />
          </label>
          <label className="block text-sm font-semibold text-[var(--navy-dark)]">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isLoading}
              className="mt-2 w-full rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm outline-none transition focus:border-[var(--primary-blue)] disabled:opacity-50"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>
          {error ? (
            <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110 disabled:opacity-50"
          >
            {isLoading ? "Please wait..." : mode === "login" ? "Sign in" : "Sign up"}
          </button>
        </form>
        <button
          type="button"
          onClick={() => {
            setMode((current) => (current === "login" ? "signup" : "login"));
            setError("");
          }}
          className="mt-6 w-full text-center text-sm font-semibold text-[var(--primary-blue)] hover:underline"
        >
          {mode === "login" ? "Need an account? Sign up" : "Already have an account? Sign in"}
        </button>
      </div>
    </main>
  );
};
