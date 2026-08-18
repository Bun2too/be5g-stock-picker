import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

const { runScreenMock, searchSymbolsMock } = vi.hoisted(() => ({
  runScreenMock: vi.fn(() => Promise.resolve({ candidates: [], notes: [] })),
  searchSymbolsMock: vi.fn(() => Promise.resolve({
    symbols: [
      { symbol: "NVDA", providerSymbol: "NVDA", market: "US", exchange: "NASDAQ", name: "NVIDIA Corporation" },
      { symbol: "AAPL", providerSymbol: "AAPL", market: "US", exchange: "NASDAQ", name: "Apple Inc." },
    ],
    meta: { counts: { US: 2, TW: 0 } },
  })),
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
  searchSymbols: (...args) => searchSymbolsMock(...args),
  runScreen: (...args) => runScreenMock(...args),
  explainScreen: () => Promise.resolve({ summary: "" }),
}));

beforeEach(() => {
  runScreenMock.mockClear();
  searchSymbolsMock.mockClear();
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

test("runs saved portfolio with only the currently selected symbols", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: /Smart screens for serious investors/i });

  fireEvent.click(await screen.findByRole("button", { name: /NVDA/i }));
  fireEvent.click(await screen.findByRole("button", { name: /AAPL/i }));
  fireEvent.click(screen.getByRole("button", { name: /NVDA ×/i }));
  await waitFor(() => expect(screen.queryByRole("button", { name: /NVDA ×/i })).not.toBeInTheDocument());
  fireEvent.change(document.getElementById("setting-strategy"), { target: { value: "low_vol" } });
  fireEvent.click(screen.getAllByRole("button", { name: /Run live screen/i })[0]);

  await waitFor(() => expect(runScreenMock).toHaveBeenCalled());
  expect(runScreenMock.mock.calls[0][0]).toMatchObject({
    universe: "mixed_portfolio",
    strategy: "low_vol",
    selectedSymbols: ["AAPL"],
  });
});
