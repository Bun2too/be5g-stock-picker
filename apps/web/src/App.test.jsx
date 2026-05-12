import { render, screen } from "@testing-library/react";
import App from "./App";

vi.mock("./lib/api", () => ({
  getHealth: () =>
    Promise.resolve({
      ok: true,
      alpacaConfigured: false,
      mode: "paper",
      feed: "iex",
    }),
  runScreen: () => Promise.resolve({ candidates: [], notes: [] }),
  explainScreen: () => Promise.resolve({ summary: "" }),
}));

test("renders main product heading", async () => {
  render(<App />);
  expect(await screen.findByText(/Investor Screening Workbench/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Run live screen/i })).toBeInTheDocument();
});
