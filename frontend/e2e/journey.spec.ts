import { expect, test } from "@playwright/test";
import { E2E_ADMIN } from "./env";

test("administrator lists a vehicle and a new buyer purchases the last unit", async ({
  page
}) => {
  const runId = Date.now();
  // Unique per run so the search below matches only this car.
  const make = `E2E Motors ${runId}`;
  const model = "Roadster";
  const carName = `${make} ${model}`;

  // Administrator signs in and lists one unit.
  await page.goto("/login");
  await page.getByLabel("Email").fill(E2E_ADMIN.email);
  await page.getByLabel("Password").fill(E2E_ADMIN.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Administrator", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Add vehicle" }).click();
  const dialog = page.getByRole("dialog", { name: "Add vehicle" });
  await dialog.getByLabel("Make").fill(make);
  await dialog.getByLabel("Model").fill(model);
  await dialog.getByLabel("Category").selectOption("SUV");
  await dialog.getByLabel("Price (₹)").fill("1250000");
  await dialog.getByLabel("Quantity").fill("1");
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(dialog).toBeHidden();
  const adminCard = page.getByRole("article", { name: carName });
  await expect(adminCard).toBeVisible();
  await expect(adminCard.getByText("1 in stock")).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  // A new buyer registers and is signed in straight away.
  const buyerEmail = `buyer-${runId}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(buyerEmail);
  await page.getByLabel("Password").fill("buyer-password-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText(buyerEmail)).toBeVisible();
  await expect(page.getByRole("button", { name: "Add vehicle" })).toHaveCount(
    0
  );

  // The buyer finds the car by make and buys it.
  const search = page.getByRole("search");
  await search.getByLabel("Make").fill(make);
  await search.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/make=/);
  const card = page.getByRole("article", { name: carName });
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(card).toBeVisible();

  await card.getByRole("button", { name: "Purchase" }).click();
  await expect(page.getByRole("status")).toHaveText(`Purchased ${carName}`);
  await expect(card.getByText("Out of stock")).toBeVisible();
  await expect(card.getByRole("button", { name: "Purchase" })).toBeDisabled();
});
