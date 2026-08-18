import { useEffect, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import {
  ApiError,
  explainScreen,
  getHealth,
  getPlans,
  getPortfolio,
  runScreen,
  savePortfolio,
  searchSymbols,
} from "./lib/api";
import { translations } from "./lib/i18n";

const DEFAULT_SETTINGS = {
  horizon: "1y",
  risk: "medium",
  strategy: "momentum",
  universe: "mega_caps",
  selectedSymbols: [],
  plannedVolumeUsd: 5000,
  portfolioSize: 8,
  diversification: "balanced",
};

const TW_STOCK_ENABLED = import.meta.env.VITE_TW_STOCK_ENABLED === "true";

const STRIPE_LEVEL1_URL =
  import.meta.env.VITE_STRIPE_LEVEL1_CHECKOUT_URL ||
  "https://buy.stripe.com/dRm6oH2zxduG2Yc8Drds400";
const STRIPE_LEVEL2_URL =
  import.meta.env.VITE_STRIPE_LEVEL2_CHECKOUT_URL ||
  "https://buy.stripe.com/bJe9AT1vt62ebuI8Drds401";

function formatMoney(value) {
  if (!Number.isFinite(value)) return "-";
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function filterSymbolsForEnabledMarkets(symbols) {
  if (TW_STOCK_ENABLED) return symbols;
  return symbols.filter((symbol) => !symbol.toUpperCase().endsWith(".TW") && !symbol.toUpperCase().endsWith(".TWO"));
}

// ── SVG Icons ─────────────────────────────────────────────────────────────────
function GlobeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg viewBox="0 0 24 24">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg viewBox="0 0 24 24">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <line x1="10" y1="9" x2="8" y2="9" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

// ── Toast notification system ─────────────────────────────────────────────────
function useToasts() {
  const [toasts, setToasts] = useState([]);
  const toastSeq = useRef(0);
  const addToast = (message, type = "success") => {
    toastSeq.current += 1;
    const id = `${Date.now()}-${toastSeq.current}`;
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  };
  return { toasts, addToast };
}

function ToastContainer({ toasts }) {
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type}`} role="alert">
          <div className="toast-dot" />
          {t.message}
        </div>
      ))}
    </div>
  );
}

// ── Skeleton loader ───────────────────────────────────────────────────────────
function SkeletonResults() {
  return (
    <div className="skeleton-rows" aria-label="Loading results…">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="skeleton-row">
          <div className="skeleton-cell" style={{ width: "60px" }} />
          <div className="skeleton-cell" style={{ width: "40px" }} />
          <div className="skeleton-cell" style={{ width: "65px" }} />
          <div className="skeleton-cell" style={{ width: "60px" }} />
          <div className="skeleton-cell" style={{ width: "50px" }} />
          <div className="skeleton-cell" style={{ width: "50px" }} />
          <div className="skeleton-cell" />
        </div>
      ))}
    </div>
  );
}

// ── Quota progress bar ────────────────────────────────────────────────────────
function QuotaBar({ quota }) {
  if (!quota || quota.exempt) return null;
  const pct = Math.max(0, Math.min(100, ((quota.remaining ?? quota.limit) / quota.limit) * 100));
  const danger = quota.remaining <= 1;
  return (
    <div className="quota-bar-wrap">
      <div className="quota-bar-track">
        <div
          className={`quota-bar-fill${danger ? " danger" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Auth-gated app entry ──────────────────────────────────────────────────────
function AuthenticatedApp() {
  const {
    error,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    user,
  } = useAuth0();

  const auth = {
    enabled: true,
    error,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    user,
  };

  return <StockPickerApp auth={auth} />;
}

// ── Main app ──────────────────────────────────────────────────────────────────
function StockPickerApp({ auth }) {
  // Theme state: 'light' or 'dark'
  const [theme, setTheme] = useState(() => {
    const saved = window.localStorage.getItem("be5g_theme");
    if (saved === "dark" || saved === "light") return saved;
    return "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("be5g_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  };

  // Language state: 'en' or 'zh-TW' (Big5 Taiwan compatible)
  const [lang, setLang] = useState(() => {
    const saved = window.localStorage.getItem("be5g_lang");
    if (saved === "en" || saved === "zh-TW") return saved;
    // Auto-detect browser locale
    if (typeof navigator !== "undefined" && navigator.language?.toLowerCase().includes("zh")) {
      return "zh-TW";
    }
    return "en";
  });

  useEffect(() => {
    window.localStorage.setItem("be5g_lang", lang);
    document.documentElement.setAttribute("lang", lang === "zh-TW" ? "zh-TW" : "en");
  }, [lang]);

  const toggleLang = () => {
    setLang((current) => (current === "en" ? "zh-TW" : "en"));
  };

  const t = translations[lang] || translations.en;

  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [health, setHealth] = useState(null);
  const [quota, setQuota] = useState(null);
  const [billingPortalUrl, setBillingPortalUrl] = useState(
    import.meta.env.VITE_STRIPE_BILLING_PORTAL_URL || ""
  );
  const [results, setResults] = useState([]);
  const [symbolQuery, setSymbolQuery] = useState("");
  const [symbolMarket, setSymbolMarket] = useState(TW_STOCK_ENABLED ? "US,TW" : "US");
  const [symbolResults, setSymbolResults] = useState([]);
  const [symbolMeta, setSymbolMeta] = useState(null);
  const [portfolioSaving, setPortfolioSaving] = useState(false);
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { toasts, addToast } = useToasts();

  // Fetch health + plans on mount
  useEffect(() => {
    getHealth()
      .then((payload) => {
        setHealth(payload);
        setQuota(payload.guestQuota || null);
      })
      .catch((err) => setError(err.message));

    getPlans()
      .then((payload) => {
        if (payload.billingPortalUrl) setBillingPortalUrl(payload.billingPortalUrl);
      })
      .catch(() => { });
  }, []);

  // Restore portfolio from local storage then API
  useEffect(() => {
    const stored = window.localStorage.getItem("stockPickerPortfolio");
    if (stored) {
      try {
        const symbols = JSON.parse(stored);
        if (Array.isArray(symbols))
          setSettings((current) => ({ ...current, selectedSymbols: filterSymbolsForEnabledMarkets(symbols) }));
      } catch {
        window.localStorage.removeItem("stockPickerPortfolio");
      }
    }

    getPortfolio()
      .then((payload) => {
        const symbols = filterSymbolsForEnabledMarkets(payload.symbols || []);
        if (symbols.length) {
          window.localStorage.setItem(
            "stockPickerPortfolio",
            JSON.stringify(symbols)
          );
          setSettings((current) => ({ ...current, selectedSymbols: symbols }));
        }
      })
      .catch(() => { });
  }, []);

  // Debounced symbol search
  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      searchSymbols({ query: symbolQuery, market: symbolMarket, limit: 60 })
        .then((payload) => {
          if (!cancelled) {
            setSymbolResults(payload.symbols || []);
            setSymbolMeta(payload.meta || null);
          }
        })
        .catch(() => {
          if (!cancelled) setSymbolResults([]);
        });
    }, 180);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [symbolQuery, symbolMarket]);

  function updateSetting(key, value) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  function updateUniverse(value) {
    setSettings((current) => ({ ...current, universe: value }));
    if (value === "tw_popular") {
      setSymbolMarket("TW");
    } else if (value === "us_most_traded" || value === "mega_caps" || value === "nasdaq100_like" || value === "sp500_like") {
      setSymbolMarket("US");
    }
  }

  function updateSymbolMarket(value) {
    setSymbolMarket(value);
    if (value === "TW") {
      setSettings((current) => ({ ...current, universe: "tw_popular" }));
    } else if (value === "US") {
      setSettings((current) => (
        current.universe === "tw_popular"
          ? { ...current, universe: "us_most_traded" }
          : current
      ));
    }
  }

  function selectedSet() {
    return new Set(settings.selectedSymbols || []);
  }

  async function persistSelected(symbols) {
    window.localStorage.setItem("stockPickerPortfolio", JSON.stringify(symbols));
    setPortfolioSaving(true);
    try {
      const accessToken = auth?.isAuthenticated
        ? await auth.getAccessTokenSilently()
        : null;
      await savePortfolio(symbols, accessToken);
      addToast(t.toast.portfolioSaved, "success");
    } catch {
      // Local storage keeps working set even if API is unavailable
    } finally {
      setPortfolioSaving(false);
    }
  }

  function addSymbol(symbol) {
    const next = Array.from(
      new Set([...(settings.selectedSymbols || []), symbol])
    ).slice(0, 100);
    setSettings((current) => ({
      ...current,
      selectedSymbols: next,
      universe: "mixed_portfolio",
    }));
    persistSelected(next);
  }

  function removeSymbol(symbol) {
    const next = (settings.selectedSymbols || []).filter((item) => item !== symbol);
    setSettings((current) => ({ ...current, selectedSymbols: next }));
    persistSelected(next);
  }

  async function handleRunScreen() {
    setLoading(true);
    setError("");
    setResults([]);
    setSummary("");
    setNotes([]);

    try {
      const screenSettings = {
        ...settings,
        selectedSymbols: [...(settings.selectedSymbols || [])],
      };
      if (screenSettings.universe === "mixed_portfolio" && screenSettings.selectedSymbols.length === 0) {
        throw new Error(t.controls.emptyPortfolioError);
      }

      const accessToken = auth?.isAuthenticated
        ? await auth.getAccessTokenSilently()
        : null;
      const screen = await runScreen(screenSettings, accessToken);
      setResults(screen.candidates || []);
      setNotes(screen.notes || []);
      setQuota(screen.settings?.guestQuota || quota);

      const explanation = await explainScreen(
        screen.settings,
        screen.candidates || [],
        accessToken
      );
      setSummary(explanation.summary || "");
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setQuota(err.detail?.quota || quota);
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSignup() {
    auth?.loginWithRedirect?.({ authorizationParams: { screen_hint: "signup" } });
  }
  function handleLogin() { auth?.loginWithRedirect?.(); }
  function handleLogout() {
    auth?.logout?.({ logoutParams: { returnTo: window.location.origin } });
  }

  const showUpgradeBanner =
    quota && !quota.exempt && quota.remaining !== null && quota.remaining <= 1;

  const heroCopy = TW_STOCK_ENABLED ? t.hero.copy : t.hero.copyUsOnly;

  const strategyPlans = [
    {
      id: "free",
      name: t.tiers.items.free.name,
      tagline: t.tiers.items.free.tagline,
      price: t.tiers.items.free.price,
      period: t.tiers.items.free.period,
      highlight: false,
      features: t.tiers.items.free.features,
      checkoutUrl: null,
    },
    {
      id: "level_1",
      name: t.tiers.items.level_1.name,
      tagline: t.tiers.items.level_1.tagline,
      price: t.tiers.items.level_1.price,
      period: t.tiers.items.level_1.period,
      highlight: true,
      features: t.tiers.items.level_1.features,
      checkoutUrl: STRIPE_LEVEL1_URL,
    },
    {
      id: "level_2",
      name: t.tiers.items.level_2.name,
      tagline: t.tiers.items.level_2.tagline,
      price: t.tiers.items.level_2.price,
      period: t.tiers.items.level_2.period,
      highlight: false,
      features: TW_STOCK_ENABLED
        ? t.tiers.items.level_2.features
        : t.tiers.items.level_2.featuresUsOnly,
      checkoutUrl: STRIPE_LEVEL2_URL,
    },
  ];

  return (
    <div className="app-shell">
      {/* ── Top Navigation Bar ─────────────────────────────────────────────── */}
      <nav className="top-nav" aria-label="Main Navigation">
        <a href="/" className="brand-badge">
          <span className="brand-dot" />
          <span className="brand-name">be5g.com</span>
          <span className="brand-tag">{t.nav.brandTag}</span>
        </a>
        <div className="nav-actions">
          {/* Language Switcher */}
          <button
            type="button"
            className="theme-toggle-btn"
            onClick={toggleLang}
            title={t.nav.langTitle}
            aria-label="Toggle Language"
          >
            <span className="theme-icon"><GlobeIcon /></span>
            <span>{t.nav.langSwitch}</span>
          </button>

          {/* Theme Switcher */}
          <button
            type="button"
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={theme === "light" ? t.nav.switchThemeToDark : t.nav.switchThemeToLight}
            aria-label="Toggle Theme"
          >
            <span className="theme-icon">{theme === "light" ? <MoonIcon /> : <SunIcon />}</span>
            <span>{theme === "light" ? t.nav.themeDark : t.nav.themeLight}</span>
          </button>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <header className="hero">
        <div className="hero-main">
          <div>
            <p className="eyebrow">{t.hero.eyebrow}</p>
            <h1>{t.hero.title}</h1>
          </div>
          <p className="hero-copy">{heroCopy}</p>
          <div className="hero-cta-row">
            <button
              id="run-screen-btn"
              className="primary-button"
              onClick={handleRunScreen}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  {t.hero.running}
                </>
              ) : (
                t.hero.runCta
              )}
            </button>
            <span className="hero-badge">{t.hero.badge}</span>
          </div>
        </div>

        {/* ── Status sidebar ────────────────────────────────────────────────── */}
        <div className="status-panel">
          {/* Account */}
          <div className="account-card">
            <h2>{t.status.account}</h2>
            {!auth?.enabled ? (
              <>
                <p className="usage-count">{t.status.guestMode}</p>
                <p className="upgrade-copy">{t.status.guestModeDesc}</p>
              </>
            ) : auth.isLoading ? (
              <p className="usage-count">{t.status.checkingSession}</p>
            ) : auth.isAuthenticated ? (
              <>
                <p className="usage-count">{auth.user?.email || auth.user?.name || t.status.activeSession}</p>
                <div className="button-row">
                  {billingPortalUrl && (
                    <a className="secondary-link" href={billingPortalUrl}>
                      {t.status.billing}
                    </a>
                  )}
                  <button className="text-button" type="button" onClick={handleLogout}>
                    {t.status.logout}
                  </button>
                </div>
              </>
            ) : (
              <>
                {auth.error && (
                  <p className="error-text">{auth.error.message}</p>
                )}
                <div className="button-row">
                  <button
                    className="primary-button compact"
                    type="button"
                    id="signup-btn"
                    onClick={handleSignup}
                  >
                    {t.status.signup}
                  </button>
                  <button className="text-button" type="button" id="login-btn" onClick={handleLogin}>
                    {t.status.login}
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Guest quota */}
          <div className="usage-card">
            <h2>{t.status.quotaTitle}</h2>
            {quota?.exempt ? (
              <p className="usage-count">{t.status.unlimitedAccess}</p>
            ) : (
              <>
                <p className="usage-count">
                  {quota
                    ? t.status.quotaLeft(quota.remaining, quota.limit)
                    : t.status.checkingQuota}
                </p>
                <QuotaBar quota={quota} />
                {quota && !quota.exempt && quota.remaining === 0 ? (
                  <p className="upgrade-copy">{t.status.quotaReached}</p>
                ) : (
                  <p className="upgrade-copy">
                    {t.status.guestNotice(quota?.limit ?? "3")}
                  </p>
                )}
              </>
            )}
          </div>

          {/* Market Engine Health */}
          <div className="api-card">
            <h2>{t.status.engineTitle}</h2>
            {health ? (
              <ul>
                <li>{t.status.engineTitle}: {health.ok ? t.status.engineOperational : t.status.engineDegraded}</li>
                <li>{t.status.dataFeedActive}</li>
                <li>{health.mode === "paper" ? t.status.execPaper : t.status.execLive}</li>
                <li>{t.status.feedLabel(health.feed?.toUpperCase() || "IEX")}</li>
              </ul>
            ) : (
              <p className="usage-count" style={{ color: "var(--text-muted)" }}>
                {t.status.connectingEngine}
              </p>
            )}
          </div>
        </div>
      </header>

      <main className="layout">
        {/* ── Controls ──────────────────────────────────────────────────────── */}
        <section className="panel controls" aria-label="Screen configuration">
          <h2>{t.controls.title}</h2>

          <label htmlFor="setting-horizon">
            {t.controls.horizon}
            <select
              id="setting-horizon"
              value={settings.horizon}
              onChange={(e) => updateSetting("horizon", e.target.value)}
            >
              <option value="daytrade">{t.controls.horizons.daytrade}</option>
              <option value="weekly">{t.controls.horizons.weekly}</option>
              <option value="monthly">{t.controls.horizons.monthly}</option>
              <option value="3m">{t.controls.horizons["3m"]}</option>
              <option value="1y">{t.controls.horizons["1y"]}</option>
              <option value="5y">{t.controls.horizons["5y"]}</option>
            </select>
          </label>

          <label htmlFor="setting-risk">
            {t.controls.risk}
            <select
              id="setting-risk"
              value={settings.risk}
              onChange={(e) => updateSetting("risk", e.target.value)}
            >
              <option value="low">{t.controls.risks.low}</option>
              <option value="medium">{t.controls.risks.medium}</option>
              <option value="high">{t.controls.risks.high}</option>
            </select>
          </label>

          <label htmlFor="setting-strategy">
            {t.controls.strategy}
            <select
              id="setting-strategy"
              value={settings.strategy}
              onChange={(e) => updateSetting("strategy", e.target.value)}
            >
              <option value="quality_value">{t.controls.strategies.quality_value}</option>
              <option value="momentum">{t.controls.strategies.momentum}</option>
              <option value="low_vol">{t.controls.strategies.low_vol}</option>
              <option value="dividend">{t.controls.strategies.dividend}</option>
              <option value="mean_reversion">{t.controls.strategies.mean_reversion}</option>
            </select>
          </label>

          <label htmlFor="setting-universe">
            {t.controls.universe}
            <select
              id="setting-universe"
              value={settings.universe}
              onChange={(e) => updateUniverse(e.target.value)}
            >
              <option value="mega_caps">{t.controls.universes.mega_caps}</option>
              <option value="nasdaq100_like">{t.controls.universes.nasdaq100_like}</option>
              <option value="sp500_like">{t.controls.universes.sp500_like}</option>
              <option value="us_most_traded">{t.controls.universes.us_most_traded}</option>
              {TW_STOCK_ENABLED && (
                <option value="tw_popular">{t.controls.universes.tw_popular}</option>
              )}
              <option value="mixed_portfolio">{t.controls.universes.mixed_portfolio}</option>
            </select>
          </label>

          {/* Portfolio builder */}
          <div className="portfolio-builder">
            <div className="builder-heading">
              <h3>{t.controls.portfolioTitle}</h3>
              <span>{portfolioSaving ? t.controls.saving : t.controls.savedCount(settings.selectedSymbols.length)}</span>
            </div>

            <div className="symbol-filters">
              <input
                type="search"
                id="symbol-search"
                placeholder={TW_STOCK_ENABLED ? t.controls.searchPlaceholder : t.controls.searchPlaceholderUsOnly}
                value={symbolQuery}
                onChange={(e) => setSymbolQuery(e.target.value)}
              />
              <select
                id="symbol-market"
                aria-label="Market"
                value={symbolMarket}
                onChange={(e) => updateSymbolMarket(e.target.value)}
              >
                {TW_STOCK_ENABLED && (
                  <option value="US,TW">{t.controls.marketOptions.all}</option>
                )}
                <option value="US">{t.controls.marketOptions.us}</option>
                {TW_STOCK_ENABLED && (
                  <option value="TW">{t.controls.marketOptions.tw}</option>
                )}
              </select>
            </div>

            {symbolMeta && (
              <p className="catalog-meta">
                {TW_STOCK_ENABLED
                  ? t.controls.catalogMeta(symbolMeta.counts?.US || 0, symbolMeta.counts?.TW || 0)
                  : t.controls.catalogMetaUsOnly(symbolMeta.counts?.US || 0)}
              </p>
            )}

            {settings.selectedSymbols.length > 0 && (
              <div className="selected-symbols">
                {settings.selectedSymbols.map((symbol) => (
                  <button
                    type="button"
                    key={symbol}
                    onClick={() => removeSymbol(symbol)}
                    title={`Remove ${symbol}`}
                  >
                    {symbol} ×
                  </button>
                ))}
              </div>
            )}

            <div className="symbol-results">
              {symbolResults.slice(0, 8).map((item) => {
                const id = item.providerSymbol || item.symbol;
                const alreadySelected = selectedSet().has(id);
                return (
                  <button
                    type="button"
                    className="symbol-option"
                    key={`${item.market}:${item.symbol}`}
                    onClick={() => addSymbol(id)}
                    disabled={alreadySelected}
                  >
                    <strong>{item.symbol}</strong>
                    <span>{item.market} · {item.name || item.exchange}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <label htmlFor="setting-volume">
            {t.controls.volumePerPosition}
            <input
              type="number"
              id="setting-volume"
              min="0"
              step="100"
              value={settings.plannedVolumeUsd}
              onChange={(e) =>
                updateSetting("plannedVolumeUsd", Number(e.target.value || 0))
              }
            />
          </label>

          <label htmlFor="setting-size">
            {t.controls.portfolioSize}
            <input
              type="number"
              id="setting-size"
              min="1"
              max="30"
              value={settings.portfolioSize}
              onChange={(e) =>
                updateSetting("portfolioSize", Number(e.target.value || 1))
              }
            />
          </label>

          <label htmlFor="setting-diversification">
            {t.controls.diversification}
            <select
              id="setting-diversification"
              value={settings.diversification}
              onChange={(e) => updateSetting("diversification", e.target.value)}
            >
              <option value="balanced">{t.controls.diversifications.balanced}</option>
              <option value="concentrated">{t.controls.diversifications.concentrated}</option>
            </select>
          </label>

          <button
            id="run-screen-sidebar-btn"
            className="primary-button"
            onClick={handleRunScreen}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" />
                {t.hero.running}
              </>
            ) : (
              t.controls.runSidebarCta
            )}
          </button>

          <p className="fine-print">
            {t.controls.disclaimer}
          </p>
        </section>

        {/* ── Results ───────────────────────────────────────────────────────── */}
        <section className="panel results" aria-label="Screening results">
          <div className="section-heading">
            <h2>{t.results.title}</h2>
            {error && <p className="error-text" role="alert">{error}</p>}
          </div>

          {/* Upgrade nudge banner */}
          {showUpgradeBanner && (
            <div className="upgrade-banner" role="status">
              <span className="upgrade-icon">⚡</span>
              <p>{t.results.upgradeNudge}</p>
              <a
                className="primary-link"
                href={STRIPE_LEVEL1_URL || "#pricing-heading"}
                style={{ fontSize: "0.84rem", padding: "8px 16px", whiteSpace: "nowrap" }}
              >
                {t.results.upgradeNudgeCta}
              </a>
            </div>
          )}

          {summary && <div className="summary-card">{summary}</div>}

          {notes.length > 0 && (
            <div className="notes-card">
              <h3>{t.results.notesTitle}</h3>
              <ul>
                {notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          )}

          {loading ? (
            <SkeletonResults />
          ) : results.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state-icon">📊</span>
              {t.results.emptyState}
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t.results.headers.ticker}</th>
                    <th>{t.results.headers.score}</th>
                    <th>{t.results.headers.price}</th>
                    <th>{t.results.headers.adv}</th>
                    <th>{t.results.headers.vol}</th>
                    <th>{t.results.headers.drawdown}</th>
                    <th>{t.results.headers.rationale}</th>
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
                        <td className="ticker-col">
                          <strong>{candidate.ticker}</strong>
                        </td>
                        <td className={`score-col ${scoreClass}`}>
                          <span className="score-badge">{score}</span>
                        </td>
                        <td className="price-col">${candidate.price.toFixed(2)}</td>
                        <td className="metric-col">{formatMoney(candidate.advUsd)}</td>
                        <td className="metric-col">
                          {(candidate.vol30 * 100).toFixed(0)}%
                        </td>
                        <td className="metric-col">
                          {(candidate.drawdown1y * 100).toFixed(0)}%
                        </td>
                        <td className="rationale-col">{candidate.rationale}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* ── Strategy Tiers Section ────────────────────────────────────────── */}
        <section className="panel pricing-section" aria-labelledby="pricing-heading">
          <div className="section-heading">
            <h2 id="pricing-heading">{t.tiers.title}</h2>
            <p className="fine-print">{t.tiers.subtitle}</p>
          </div>

          <div className="pricing-grid">
            {strategyPlans.map((plan) => (
              <article
                className={`plan-card ${plan.highlight ? "featured-plan" : ""}`}
                key={plan.id}
              >
                {plan.highlight && (
                  <div className="featured-badge">{t.tiers.mostPopular}</div>
                )}
                <div className="plan-card-header">
                  <h3>{plan.name}</h3>
                  {plan.tagline && <p className="plan-tagline">{plan.tagline}</p>}
                  <p className="plan-price">
                    {plan.price}
                    <span> / {plan.period}</span>
                  </p>
                </div>
                <ul>
                  {(plan.features || []).map((feature) => (
                    <li key={feature}>
                      <CheckIcon />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                {plan.checkoutUrl ? (
                  <a className="primary-link" href={plan.checkoutUrl}>
                    {auth?.isAuthenticated ? t.tiers.subscribe(plan.name) : t.tiers.getPlan(plan.name)}
                  </a>
                ) : (
                  <button
                    className="text-button"
                    type="button"
                    id={`start-free-btn-${plan.id}`}
                    onClick={auth?.enabled ? handleSignup : undefined}
                    disabled={!auth?.enabled}
                  >
                    {t.tiers.startFree}
                  </button>
                )}
              </article>
            ))}
          </div>
        </section>

        {/* ── FAQ ───────────────────────────────────────────────────────────── */}
        <section className="panel faq-section" itemScope itemType="https://schema.org/FAQPage">
          <h2>{t.faq.title}</h2>
          <div className="faq-grid">
            {t.faq.items.map((item, idx) => (
              <div className="faq-item" key={idx} itemScope itemProp="mainEntity" itemType="https://schema.org/Question">
                <h3 itemProp="name">{item.q}</h3>
                <div itemScope itemProp="acceptedAnswer" itemType="https://schema.org/Answer">
                  <p itemProp="text" style={{ whiteSpace: "pre-line" }}>{item.a}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="site-footer">
        <div className="footer-content">
          <div className="footer-links">
            <a href="https://x.com/be5g_com" className="footer-link-item" target="_blank" rel="noopener noreferrer">
              <XIcon />
              <span>{t.footer.xTwitter}</span>
            </a>
            <a href="https://www.facebook.com/people/Be5g/61551348224525/" className="footer-link-item" target="_blank" rel="noopener noreferrer">
              <FacebookIcon />
              <span>{t.footer.facebook}</span>
            </a>
            <a href="https://bun2too.com/terms" className="footer-link-item" target="_blank" rel="noopener noreferrer">
              <DocumentIcon />
              <span>{t.footer.terms}</span>
            </a>
            <a href="https://bun2too.com/cookies" className="footer-link-item" target="_blank" rel="noopener noreferrer">
              <ShieldIcon />
              <span>{t.footer.cookies}</span>
            </a>
          </div>
          <div className="footer-disclaimer">
            <p>{t.footer.disclaimer}</p>
          </div>
        </div>
      </footer>

      {/* ── Toast notifications ──────────────────────────────────────────────── */}
      <ToastContainer toasts={toasts} />
    </div>
  );
}

export default function App({ authEnabled = false }) {
  if (authEnabled) {
    return <AuthenticatedApp />;
  }

  return (
    <StockPickerApp
      auth={{
        enabled: false,
        isAuthenticated: false,
        isLoading: false,
      }}
    />
  );
}
