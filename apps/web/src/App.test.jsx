import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

const { runScreenMock } = vi.hoisted(() => ({
  runScreenMock: vi.fn(() => Promise.resolve({ candidates: [], notes: [] })),
}));

vi.mock("./lib/api", () => ({
  getHealth: () =>
    Promise.resolve({
      ok: true,
      alpacaConfigured: true,
      auth0Configured: true,
      stripeConfigured: true,
      mode: "paper",
      feed: "iex",
    }),
  getPlans: () => Promise.resolve({ plans: [] }),
  getPortfolio: () => Promise.resolve({ symbols: [] }),
  savePortfolio: () => Promise.resolve({ symbols: [] }),
  searchSymbols: () => Promise.resolve({ symbols: [], meta: { counts: { US: 0, TW: 0 } } }),
  runScreen: (...args) => runScreenMock(...args),
  explainScreen: () => Promise.resolve({ summary: "" }),
}));

beforeEach(() => {
  runScreenMock.mockClear();
  window.localStorage.clear();
});

test("renders main product heading, theme toggle, and language switcher", async () => {
  render(<App />);
  expect(await screen.findByRole("heading", { name: /Smart screens for serious investors/i })).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: /Run live screen/i })[0]).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Toggle Theme/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Toggle Language/i })).toBeInTheDocument();
});

test("switches between English and Traditional Chinese (Taiwan)", async () => {
  render(<App />);
  const langBtn = screen.getByRole("button", { name: /Toggle Language/i });
  expect(langBtn).toHaveTextContent(/繁體中文/i);

  // Switch to Traditional Chinese
  fireEvent.click(langBtn);
  expect(await screen.findByRole("heading", { name: /專為專業投資人打造的量化選股引擎/i })).toBeInTheDocument();
  expect(langBtn).toHaveTextContent(/English/i);

  // Switch back to English
  fireEvent.click(langBtn);
  expect(await screen.findByRole("heading", { name: /Smart screens for serious investors/i })).toBeInTheDocument();
});

test("hides Taiwan stock controls when the feature flag is disabled", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: /Smart screens for serious investors/i });

  expect(screen.getByLabelText(/^Universe/i)).not.toHaveTextContent(/Taiwan/i);
  expect(screen.getByLabelText(/Market/i)).not.toHaveTextContent(/Taiwan/i);
  expect(screen.getByLabelText(/Market/i)).not.toHaveTextContent(/US \+ TW/i);
});

test("runs a US universe when Taiwan stocks are disabled", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: /Smart screens for serious investors/i });

  fireEvent.click(screen.getAllByRole("button", { name: /Run live screen/i })[0]);

  await waitFor(() => expect(runScreenMock).toHaveBeenCalled());
  expect(runScreenMock.mock.calls[0][0].universe).toBe("mega_caps");
});
