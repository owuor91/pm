import { expect, test, type Page } from "@playwright/test";

const uniqueUsername = (label: string) => `${label}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;

const signUp = async (page: Page, username: string, password = "password123") => {
  await page.goto("/");
  await page.getByRole("button", { name: /need an account/i }).click();
  await page.getByLabel(/username/i).fill(username);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign up/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

test("signs up and loads the kanban board", async ({ page }) => {
  await signUp(page, uniqueUsername("loads"));
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("rejects signup with a too-short password", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /need an account/i }).click();
  await page.getByLabel(/username/i).fill(uniqueUsername("shortpw"));
  await page.getByLabel(/password/i).fill("short1");
  await page.getByRole("button", { name: /sign up/i }).click();

  await expect(page.getByText(/at least 8 characters/i)).toBeVisible();
});

test("locks out login after repeated failed attempts", async ({ page }) => {
  const username = uniqueUsername("lockout");
  await signUp(page, username, "password123");
  await page.getByRole("button", { name: /logout/i }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

  for (let i = 0; i < 5; i += 1) {
    await page.getByLabel(/username/i).fill(username);
    await page.getByLabel(/password/i).fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/invalid username or password/i)).toBeVisible();
  }

  await page.getByLabel(/username/i).fill(username);
  await page.getByLabel(/password/i).fill("password123");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/too many failed login attempts/i)).toBeVisible();
});

test("changes password and can log back in with the new one", async ({ page }) => {
  const username = uniqueUsername("changepw");
  await signUp(page, username, "password123");

  await page.getByRole("button", { name: /change password/i }).click();
  await page.getByLabel(/current password/i).fill("password123");
  await page.getByLabel(/new password/i).fill("newpassword456");
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByText(/password changed/i)).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("button", { name: /logout/i }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel(/username/i).fill(username);
  await page.getByLabel(/password/i).fill("password123");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/invalid username or password/i)).toBeVisible();

  await page.getByLabel(/password/i).fill("newpassword456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("adds a card to a column", async ({ page }) => {
  await signUp(page, uniqueUsername("addcard"));
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await signUp(page, uniqueUsername("movecard"));
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const targetColumn = page.getByTestId("column-col-review");

  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Movable card");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = page.locator('[data-testid^="card-"]', { hasText: "Movable card" });
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(columnBox.x + columnBox.width / 2, columnBox.y + 120, { steps: 12 });
  await page.mouse.up();

  await expect(targetColumn.getByText("Movable card")).toBeVisible();
});

test("edits an existing card's title, due date, and labels", async ({ page }) => {
  await signUp(page, uniqueUsername("editcard"));
  const firstColumn = page.locator('[data-testid^="column-"]').first();

  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Original title");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Original title")).toBeVisible();

  await firstColumn.locator('button[aria-label="Edit Original title"]').click();
  const titleInput = firstColumn.getByLabel(/edit card title/i);
  await titleInput.fill("Edited title");
  await firstColumn.getByLabel(/edit labels/i).fill("urgent");
  await firstColumn.getByRole("button", { name: /^save$/i }).click();

  await expect(firstColumn.getByText("Edited title")).toBeVisible();
  await expect(firstColumn.getByText("urgent")).toBeVisible();
});

test("creates a second board and keeps cards isolated per board", async ({ page }) => {
  await signUp(page, uniqueUsername("multiboard"));

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Board A card");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(page.getByText("Board A card")).toBeVisible();

  await page.getByRole("button", { name: /new board/i }).click();
  await page.getByLabel(/new board name/i).fill("Second Board");
  await page.getByRole("button", { name: /^create$/i }).click();

  await expect(page.getByText("Board A card")).not.toBeVisible();

  await page.getByLabel(/select board/i).selectOption({ label: "My Board" });
  await expect(page.getByText("Board A card")).toBeVisible();
});

test("shares a board with another user and records activity", async ({ page, browser }) => {
  const ownerUsername = uniqueUsername("owner");
  const memberUsername = uniqueUsername("member");

  await signUp(page, ownerUsername);
  await page.getByRole("button", { name: /^members$/i }).click();
  await page.getByLabel(/username to add/i).fill(memberUsername);

  const memberContext = await browser.newContext();
  const memberPage = await memberContext.newPage();
  await signUp(memberPage, memberUsername);

  await page.getByRole("button", { name: /^add$/i }).click();
  await expect(page.getByText(memberUsername)).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("button", { name: /^activity$/i }).click();
  await expect(page.getByText(/added a member/i)).toBeVisible();

  await memberContext.close();
});

test("lets a shared member leave a board", async ({ page, browser }) => {
  const ownerUsername = uniqueUsername("owner2");
  const memberUsername = uniqueUsername("member2");

  await signUp(page, ownerUsername);
  const ownerBoardName = "Owner Shared Board";
  await page.getByRole("button", { name: /^rename$/i }).click();
  await page.getByLabel(/rename board/i).fill(ownerBoardName);
  await page.getByRole("button", { name: /^save$/i }).click();

  const memberContext = await browser.newContext();
  const memberPage = await memberContext.newPage();
  await signUp(memberPage, memberUsername);

  await page.getByRole("button", { name: /^members$/i }).click();
  await page.getByLabel(/username to add/i).fill(memberUsername);
  await page.getByRole("button", { name: /^add$/i }).click();
  await expect(page.getByText(memberUsername)).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await memberPage.reload();
  await memberPage.getByLabel(/select board/i).selectOption({ label: ownerBoardName });
  await expect(memberPage.getByRole("button", { name: /leave board/i })).toBeVisible();

  memberPage.once("dialog", (dialog) => dialog.accept());
  await memberPage.getByRole("button", { name: /leave board/i }).click();

  await expect(memberPage.getByText(ownerBoardName)).not.toBeVisible();

  await memberContext.close();
});
