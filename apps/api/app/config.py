from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path
import ipaddress

API_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = API_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # Internal API key — callers must send this in X-API-Key header.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    api_key: Optional[str] = None

    alpaca_api_key: Optional[str] = None
    alpaca_api_secret: Optional[str] = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets/v2"
    alpaca_paper: bool = True
    paper_trading_enabled: bool = False

    # Market data feed: "iex" (free/basic) or "sip" (full market; usually subscription/entitlement)
    alpaca_data_feed: str = "iex"

    # Auth0 / authorization planning. These can be enforced once the API adds JWT validation.
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    auth0_issuer: Optional[str] = None
    auth0_algorithms: str = "RS256"

    # Stripe subscription plumbing. Checkout URLs can be temporary Stripe Payment
    # Links for launch, then replaced by backend-created Checkout Sessions.
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_level1_checkout_url: Optional[str] = None
    stripe_level2_checkout_url: Optional[str] = None
    stripe_billing_portal_url: Optional[str] = None

    # Public launch guest quota.
    guest_screen_limit: int = 3
    guest_quota_ttl_seconds: int = 60 * 60 * 24
    guest_session_cookie_name: str = "stock_picker_guest"
    guest_session_cookie_secure: bool = True
    guest_session_cookie_samesite: str = "lax"
    whitelisted_ips: str = ""
    bypass_cookie_name: str = "stock_picker_access"
    bypass_cookie_value: Optional[str] = None

    # CORS
    allowed_origins: str = "http://localhost:5173"

    snapshot_cache_ttl_seconds: int = 60 * 10  # 10 minutes

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def alpaca_configured(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_api_secret)

    @property
    def auth0_configured(self) -> bool:
        return bool(self.auth0_domain and self.auth0_audience)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_webhook_secret)

    @property
    def missing_alpaca_fields(self) -> List[str]:
        missing = []
        if not self.alpaca_api_key:
            missing.append("ALPACA_API_KEY")
        if not self.alpaca_api_secret:
            missing.append("ALPACA_API_SECRET")
        return missing

    @property
    def whitelisted_ip_entries(self) -> List[str]:
        return [entry.strip() for entry in self.whitelisted_ips.split(",") if entry.strip()]

    def is_whitelisted_ip(self, ip: str) -> bool:
        if not ip:
            return False

        try:
            candidate = ipaddress.ip_address(ip)
        except ValueError:
            return False

        for entry in self.whitelisted_ip_entries:
            try:
                if "/" in entry:
                    if candidate in ipaddress.ip_network(entry, strict=False):
                        return True
                elif candidate == ipaddress.ip_address(entry):
                    return True
            except ValueError:
                continue

        return False

settings = Settings()
