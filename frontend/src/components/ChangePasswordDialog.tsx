"use client";

import { useState, type FormEvent } from "react";
import { ModalShell } from "@/components/ModalShell";
import { changePassword } from "@/lib/api";

type ChangePasswordDialogProps = {
  onClose: () => void;
};

export const ChangePasswordDialog = ({ onClose }: ChangePasswordDialogProps) => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ModalShell title="Change password" closeLabel="Close change password dialog" onClose={onClose}>
      {success ? (
        <p className="mt-4 rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          Password changed. Other sessions have been signed out.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <label className="block text-sm font-semibold text-[var(--navy-dark)]">
            Current password
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              disabled={isSubmitting}
              autoComplete="current-password"
              className="mt-2 w-full rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)] disabled:opacity-50"
            />
          </label>
          <label className="block text-sm font-semibold text-[var(--navy-dark)]">
            New password
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              disabled={isSubmitting}
              autoComplete="new-password"
              className="mt-2 w-full rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)] disabled:opacity-50"
            />
          </label>
          {error ? (
            <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110 disabled:opacity-50"
          >
            {isSubmitting ? "Saving..." : "Save"}
          </button>
        </form>
      )}
    </ModalShell>
  );
};
