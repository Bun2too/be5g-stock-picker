import { useEffect, useState } from "react";
import { ApiError, explainScreen, getHealth, runScreen } from "./lib/api";

const DEFAULT_SETTINGS = {
  horizon: "1y",
  risk: "medium",
  strategy: "momentum",
  universe: "mega_caps",
  plannedVolumeUsd: 5000,
  portfolioSize: 8,
  diversification: "balanced",
};

function formatMoney(value) {
  if (!Number.isFinite(value)) return "-";
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

export default function App() {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [health, setHealth] = useState(null);
  const [quota, setQuota] = useState(null);
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getHealth()
      .then((payload) => {
        setHealth(payload);
        setQuota(payload.guestQuota || null);
      })
      .catch((err) => setError(err.message));
  }, []);

  function updateSetting(key, value) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function handleRunScreen() {
    setLoading(true);
    setError("");

    try {
      const screen = await runScreen(settings);
      setResults(screen.candidates || []);
      setNotes(screen.notes || []);
      setQuota(screen.settings?.guestQuota || quota);

      const explanation = await explainScreen(screen.settings, screen.candidates || []);
      setSummary(explanation.summary || "");
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setQuota(err.detail?.quota || quota);
      }
      setError(err.message);
      setResults([]);
      setSummary("");
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Investor Screening Workbench</p>
          <h1>Trainable screening product foundation for traders and investors</h1>
          <p className="hero-copy">
            This workspace starts as an explainable screener and can evolve into a
            subscription product with saved models, portfolio workflows, and broker integrations.
          </p>
        </div>
        <div className="status-panel">
          <div className="usage-card">
            <h2>Guest access</h2>
            {quota?.exempt ? (
              <p className="usage-count">Unlimited access enabled</p>
            ) : (
              <p className="usage-count">
                {quota ? `${quota.remaining} of ${quota.limit} free screens left` : "Checking free usage..."}
              </p>
            )}
            {quota && !quota.exempt && quota.remaining === 0 ? (
              <p className="upgrade-copy">Upgrade to a paid subscription for more screens, saved workflows, and higher usage limits.</p>
            ) : (
              <p className="upgrade-copy">Free guests can run a limited number of screens before upgrading.</p>
            )}
          </div>

          <div className="api-card">
            <h2>API status</h2>
            {health ? (
              <ul>
                <li>Healthy: {health.ok ? "yes" : "no"}</li>
                <li>Alpaca configured: {health.alpacaConfigured ? "yes" : "no"}</li>
                {health.missingAlpacaFields?.length > 0 ? (
                  <li>Missing Alpaca fields: {health.missingAlpacaFields.join(", ")}</li>
                ) : null}
                <li>Mode: {health.mode}</li>
                <li>Feed: {health.feed}</li>
              </ul>
            ) : (
              <p>Checking backend health...</p>
            )}
          </div>
        </div>
      </header>

      <main className="layout">
        <section className="panel controls">
          <h2>Screen setup</h2>

          <label>
            Horizon
            <select value={settings.horizon} onChange={(event) => updateSetting("horizon", event.target.value)}>
              <option value="daytrade">Day trade</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="3m">3 months</option>
              <option value="1y">1 year</option>
              <option value="5y">5 years</option>
            </select>
          </label>

          <label>
            Risk profile
            <select value={settings.risk} onChange={(event) => updateSetting("risk", event.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>

          <label>
            Strategy
            <select value={settings.strategy} onChange={(event) => updateSetting("strategy", event.target.value)}>
              <option value="quality_value">Quality + value</option>
              <option value="momentum">Momentum</option>
              <option value="low_vol">Low volatility</option>
              <option value="dividend">Dividend</option>
              <option value="mean_reversion">Mean reversion</option>
            </select>
          </label>

          <label>
            Universe
            <select value={settings.universe} onChange={(event) => updateSetting("universe", event.target.value)}>
              <option value="mega_caps">Mega caps</option>
              <option value="nasdaq100_like">Nasdaq 100-like</option>
              <option value="sp500_like">S&amp;P 500-like</option>
            </select>
          </label>

          <label>
            Planned volume per position
            <input
              type="number"
              min="0"
              step="100"
              value={settings.plannedVolumeUsd}
              onChange={(event) => updateSetting("plannedVolumeUsd", Number(event.target.value || 0))}
            />
          </label>

          <label>
            Portfolio size
            <input
              type="number"
              min="1"
              max="30"
              value={settings.portfolioSize}
              onChange={(event) => updateSetting("portfolioSize", Number(event.target.value || 1))}
            />
          </label>

          <label>
            Diversification
            <select
              value={settings.diversification}
              onChange={(event) => updateSetting("diversification", event.target.value)}
            >
              <option value="balanced">Balanced</option>
              <option value="concentrated">Concentrated</option>
            </select>
          </label>

          <button className="primary-button" onClick={handleRunScreen} disabled={loading}>
            {loading ? "Running screen..." : "Run live screen"}
          </button>

          <p className="fine-print">
            This tool is a research assistant and screening workflow. It is not investment advice.
          </p>
        </section>

        <section className="panel results">
          <div className="section-heading">
            <h2>Results</h2>
            {error ? <p className="error-text">{error}</p> : null}
          </div>

          {summary ? <div className="summary-card">{summary}</div> : null}

          {notes.length > 0 ? (
            <div className="notes-card">
              <h3>Screen notes</h3>
              <ul>
                {notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {results.length === 0 ? (
            <div className="empty-state">
              Configure your screen settings above and click "Run live screen" to see ranked candidates here.
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Score</th>
                    <th>Price</th>
                    <th>ADV$</th>
                    <th>Vol 30d</th>
                    <th>1Y DD</th>
                    <th>Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((candidate) => {
                    const score = Math.round((candidate.score || 0) * 100);
                    let scoreClass = "score-neutral";
                    if (score >= 75) scoreClass = "score-high";
                    else if (score < 40) scoreClass = "score-low";

                    return (
                      <tr key={candidate.ticker}>
                        <td className="ticker-col"><strong>{candidate.ticker}</strong></td>
                        <td className={`score-col ${scoreClass}`}>{score}</td>
                        <td className="price-col">${candidate.price.toFixed(2)}</td>
                        <td className="metric-col">{formatMoney(candidate.advUsd)}</td>
                        <td className="metric-col">{(candidate.vol30 * 100).toFixed(0)}%</td>
                        <td className="metric-col">{(candidate.drawdown1y * 100).toFixed(0)}%</td>
                        <td className="rationale-col">{candidate.rationale}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel faq-section" itemScope itemType="https://schema.org/FAQPage">
          <h2>Frequently Asked Questions</h2>
          <div className="faq-item" itemScope itemProp="mainEntity" itemType="https://schema.org/Question">
            <h3 itemProp="name">What is the be5g.com Stock Screener?</h3>
            <div itemScope itemProp="acceptedAnswer" itemType="https://schema.org/Answer">
              <p itemProp="text">
                The be5g.com Stock Screener is an advanced tool for quantitative traders and investors. It calculates complex strategies (like momentum, value, and low volatility) and evaluates stock candidates against specific risk profiles to streamline your research process.
              </p>
            </div>
          </div>
          <div className="faq-item" itemScope itemProp="mainEntity" itemType="https://schema.org/Question">
            <h3 itemProp="name">How does the stock screening algorithm work?</h3>
            <div itemScope itemProp="acceptedAnswer" itemType="https://schema.org/Answer">
              <div itemProp="text">
                <p>Our calculation engine uses a multi-factor model:</p>
                <ul>
                  <li><strong>Universe Selection:</strong> Filters based on market cap and liquidity (e.g., ADV).</li>
                  <li><strong>Strategy Scoring:</strong> Ranks assets based on specific technical and fundamental signals.</li>
                  <li><strong>Risk Management:</strong> Adjusts position sizing depending on your risk profile and diversification settings.</li>
                </ul>
              </div>
            </div>
          </div>
          <div className="faq-item" itemScope itemProp="mainEntity" itemType="https://schema.org/Question">
            <h3 itemProp="name">Does be5g.com provide financial advice?</h3>
            <div itemScope itemProp="acceptedAnswer" itemType="https://schema.org/Answer">
              <p itemProp="text">
                No. be5g.com and Bun2too, inc only provide quantitative tools to calculate data. We do not provide financial, investment, or strategy advice. Users must evaluate decisions with a licensed broker.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-content">
          <div className="footer-links">
            <a href="https://bun2too.com/terms">Terms of Condition</a>
            <a href="https://bun2too.com/cookies">Cookie Selection</a>
            <a href="https://x.com/be5g_com">X (Twitter)</a>
            <a href="https://www.facebook.com/people/Be5g/61551348224525/">Facebook</a>
          </div>
          <div className="footer-disclaimer">
            <p>
              be5g.com and Bun2too, inc provides only tools to support user access and calculate but it doesn't provide any financial, investment or strategy advice, neither does the site provide educational or responsible for any win, loss or money account related profit or loss. The site tool also doesn't guarranty any SLA for any consistent, real time, near realtime, no delay connection to reflect the market status. Users and visitors have the full responsibility to check with their own licensed stock broker for any in market updates and be accountible for their own decisions.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
