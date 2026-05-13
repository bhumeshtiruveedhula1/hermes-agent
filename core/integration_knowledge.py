# core/integration_knowledge.py — Phase 16: Auto-Integration Builder
# Pre-built knowledge for all integrations Hermes already knows.
# When user says "add spotify", Hermes uses this instead of researching
# from scratch — faster, more accurate, matches existing capability patterns.
#
# JSON spec format mirrors plugins/active/*.json (executor.action_map structure).
# Python class pattern mirrors core/integrations/slack.py + spotify.py.

KNOWN_INTEGRATIONS = {
    # ── Already deployed integrations ──────────────────────────────────
    "spotify": {
        "pip_packages": ["spotipy"],
        "env_vars": {
            "SPOTIFY_CLIENT_ID": {
                "description": "Your Spotify app Client ID",
                "where": "developer.spotify.com/dashboard → your app → Settings",
                "example": "6cb0f15430b544d39b49a5acbac1ee14"
            },
            "SPOTIFY_CLIENT_SECRET": {
                "description": "Your Spotify app Client Secret",
                "where": "Settings → View client secret",
                "example": "9e65165c3ac64569a244cebaa28399e1"
            },
            "SPOTIFY_REDIRECT_URI": {
                "description": "OAuth callback URL — use exactly this value",
                "where": "Add this to your Spotify app's Redirect URIs in the dashboard",
                "example": "http://127.0.0.1:8888/callback",
                "fixed_value": "http://127.0.0.1:8888/callback"
            }
        },
        "oauth_required": True,
        "oauth_note": "First run opens a browser — login to Spotify and authorize. Token cached in .spotify_cache forever after.",
        "zero_cred": False,
        "approval_tools": [],
        "tools": ["spotify_current", "spotify_search", "spotify_play",
                  "spotify_pause", "spotify_next", "spotify_playlists"],
        "test_action": "current",
        "test_tool":   "spotify_current",
        "test_description": "what's playing on spotify",
        "already_deployed": True
    },

    "whatsapp": {
        "pip_packages": ["requests"],
        "env_vars": {
            "TWILIO_ACCOUNT_SID": {
                "description": "Twilio Account SID",
                "where": "console.twilio.com → Account Info"
            },
            "TWILIO_AUTH_TOKEN": {
                "description": "Twilio Auth Token",
                "where": "console.twilio.com → Account Info → click to reveal"
            },
            "TWILIO_WHATSAPP_FROM": {
                "description": "Twilio WhatsApp sandbox number",
                "where": "Messaging → Try WhatsApp → Sandbox number",
                "fixed_value": "whatsapp:+14155238886"
            },
            "TWILIO_WHATSAPP_TO": {
                "description": "Your WhatsApp number with country code prefix",
                "where": "Your phone number, e.g. whatsapp:+91XXXXXXXXXX"
            }
        },
        "sandbox_note": "Send 'join <keyword>' to +14155238886 on WhatsApp before testing",
        "zero_cred": False,
        "approval_tools": ["whatsapp_send"],
        "tools": ["whatsapp_send", "whatsapp_status"],
        "test_action": "status",
        "test_tool":   "whatsapp_status",
        "test_description": "whatsapp status",
        "already_deployed": True
    },

    "notion": {
        "pip_packages": ["requests"],
        "env_vars": {
            "NOTION_TOKEN": {
                "description": "Notion Internal Integration Token",
                "where": "notion.so/my-integrations → New Integration → copy token",
                "note": "Also share each Notion page with your integration (Share button → Connections)"
            }
        },
        "zero_cred": False,
        "approval_tools": ["notion_create", "notion_append"],
        "tools": ["notion_list", "notion_read", "notion_create", "notion_append"],
        "test_action": "list_pages",
        "test_tool":   "notion_list",
        "test_description": "list my notion pages",
        "already_deployed": True
    },

    "slack": {
        "pip_packages": ["slack-sdk"],
        "env_vars": {
            "SLACK_BOT_TOKEN": {
                "description": "Slack Bot User OAuth Token (xoxb-...)",
                "where": "api.slack.com/apps → your app → OAuth & Permissions → Bot Token",
                "note": "Required scopes: channels:read, channels:history, chat:write, groups:read, groups:history"
            }
        },
        "zero_cred": False,
        "approval_tools": ["slack_send"],
        "tools": ["slack_channels", "slack_send", "slack_read"],
        "test_action": "list_channels",
        "test_tool":   "slack_channels",
        "test_description": "list my slack channels",
        "already_deployed": True
    },

    "github": {
        "pip_packages": ["requests"],
        "env_vars": {
            "GITHUB_TOKEN": {
                "description": "GitHub Personal Access Token",
                "where": "github.com/settings/tokens → Generate new token (classic)",
                "note": "Select scopes: repo, read:user"
            }
        },
        "zero_cred": False,
        "approval_tools": ["github_create_issue"],
        "tools": ["github_repos", "github_issues", "github_prs", "github_commits"],
        "test_action": "list_repos",
        "test_tool":   "github_repos",
        "test_description": "list my github repos",
        "already_deployed": True
    },

    "telegram": {
        "pip_packages": ["requests"],
        "env_vars": {
            "TELEGRAM_TOKEN": {
                "description": "Telegram Bot Token from BotFather",
                "where": "Telegram → search @BotFather → /newbot → copy token"
            },
            "TELEGRAM_CHAT_ID": {
                "description": "Your Telegram chat ID",
                "where": "Send a message to your bot → visit api.telegram.org/bot<TOKEN>/getUpdates → find chat.id"
            }
        },
        "zero_cred": False,
        "approval_tools": ["telegram_send"],
        "tools": ["telegram_send", "telegram_read"],
        "test_action": "read",
        "test_tool":   "telegram_read",
        "test_description": "list recent telegram messages",
        "already_deployed": True
    },

    "openweather": {
        "pip_packages": ["requests"],
        "env_vars": {
            "OPENWEATHER_API_KEY": {
                "description": "OpenWeatherMap API key",
                "where": "openweathermap.org/api → Sign up free → My API Keys"
            }
        },
        "zero_cred": False,
        "approval_tools": [],
        "tools": ["weather_current", "weather_forecast"],
        "test_action": "current",
        "test_tool":   "weather_current",
        "test_description": "weather in bangalore",
        "already_deployed": True
    },

    # ── Zero-credential integrations — activate immediately ─────────────
    "jokes": {
        "pip_packages": ["requests"],
        "env_vars": {},
        "zero_cred": True,
        "approval_tools": [],
        "tools": ["joke_tell"],
        "test_action": "random",
        "test_tool":   "joke_tell",
        "test_description": "tell me a joke",
        "already_deployed": False
    },

    "crypto": {
        "pip_packages": ["requests"],
        "env_vars": {},
        "zero_cred": True,
        "approval_tools": [],
        "tools": ["crypto_price", "crypto_top"],
        "test_action": "price",
        "test_tool":   "crypto_price",
        "test_description": "bitcoin price",
        "already_deployed": False
    },

    "trivia": {
        "pip_packages": ["requests"],
        "env_vars": {},
        "zero_cred": True,
        "approval_tools": [],
        "tools": ["trivia_fact"],
        "test_action": "random",
        "test_tool":   "trivia_fact",
        "test_description": "give me a trivia fact",
        "already_deployed": False
    },

    "exchange_rates": {
        "pip_packages": ["requests"],
        "env_vars": {},
        "zero_cred": True,
        "approval_tools": [],
        "tools": ["exchange_rate", "currency_convert"],
        "test_action": "rate",
        "test_tool":   "exchange_rate",
        "test_description": "USD to EUR exchange rate",
        "already_deployed": False
    },
}


# ── Public API ────────────────────────────────────────────────────────────────

def get_known(name: str) -> dict | None:
    """Returns integration config dict or None if not known."""
    name = name.lower().strip()

    # Exact match
    if name in KNOWN_INTEGRATIONS:
        return KNOWN_INTEGRATIONS[name]

    # Alias lookup — common synonyms / short names
    _ALIASES: dict[str, str] = {
        # Crypto
        "bitcoin": "crypto", "cryptocurrency": "crypto",
        "coinbase": "crypto", "binance": "crypto",
        # Jokes
        "joke": "jokes", "random joke": "jokes",
        # Trivia
        "fun facts": "trivia", "fact": "trivia",
        # Weather
        "weather": "openweather", "openweathermap": "openweather",
        "open weather": "openweather",
        # WhatsApp
        "wa": "whatsapp",
        # Telegram
        "tg": "telegram", "telegram bot": "telegram",
        # Exchange rates
        "currency": "exchange_rates", "forex": "exchange_rates",
        "exchange rate": "exchange_rates",
    }
    alias = _ALIASES.get(name)
    if alias:
        return KNOWN_INTEGRATIONS.get(alias)

    return None


def is_zero_cred(name: str) -> bool:
    """Returns True if integration needs no credentials."""
    config = get_known(name)
    return config.get("zero_cred", False) if config else False


def is_already_deployed(name: str) -> bool:
    """Returns True if the integration files already exist (Phase 14+)."""
    config = get_known(name)
    return config.get("already_deployed", False) if config else False


def get_all_known_names() -> list[str]:
    """Returns sorted list of all known integration names."""
    return sorted(KNOWN_INTEGRATIONS.keys())


def get_required_env_vars(name: str) -> list[str]:
    """Returns list of required env var keys for an integration."""
    config = get_known(name)
    if not config:
        return []
    return list(config.get("env_vars", {}).keys())
