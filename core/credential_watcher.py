# core/credential_watcher.py — Phase 16: Auto-Integration Builder
# Monitors .env for new credentials using a daemon thread + polling.
# When all required vars for an integration appear → triggers activation.
# Completely non-blocking — never touches the FastAPI event loop directly.

import threading
import time
from pathlib import Path

ENV_FILE      = Path(".env")
POLL_INTERVAL = 15  # seconds between checks


def _read_env_vars() -> dict:
    """
    Parse .env file and return {KEY: VALUE} dict.
    Handles quoted values, blank lines, and comment lines (#).
    Does NOT rely on os.environ — reads the file directly so the daemon thread
    always sees the current on-disk state without needing a process restart.
    Also calls load_dotenv(override=True) so os.environ is updated for any
    library that reads credentials from os.environ rather than from our dict.
    """
    # Refresh os.environ so libraries (spotipy, slack_sdk, etc.) see new creds
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        pass  # python-dotenv not installed — file-read below is still correct

    result = {}
    if not ENV_FILE.exists():
        return result
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            # Strip surrounding quotes from value
            value = value.strip().strip('"').strip("'")
            result[key.strip()] = value
    except Exception:
        pass
    return result



def _check_vars(required_vars: list) -> tuple[bool, list]:
    """
    Check whether all required_vars are set in .env.
    Returns (all_present: bool, missing: list[str]).
    """
    env = _read_env_vars()
    missing = [v for v in required_vars if not env.get(v, "").strip()]
    return (len(missing) == 0), missing


class CredentialWatcher:
    """
    Thread-safe watcher. Each watched integration runs its own daemon thread
    that polls .env every POLL_INTERVAL seconds.
    On all vars detected → calls the activation_callback(integration_name).
    """

    def __init__(self):
        self._active: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start_watching(
        self,
        integration_name: str,
        required_vars:    list,
        activation_callback,   # sync callable(integration_name: str)
        broadcast_fn = None    # async broadcast — stored for reference, not called here
    ) -> bool:
        """
        Start credential polling for integration_name.
        Returns True if started, False if no vars required (zero-cred).
        """
        if not required_vars:
            print(f"[WATCHER] {integration_name}: zero-cred — skip watching")
            return False

        with self._lock:
            if integration_name in self._active:
                print(f"[WATCHER] Already watching: {integration_name}")
                return True

            self._active[integration_name] = {
                "required_vars": required_vars,
                "callback":      activation_callback,
                "started_at":    time.time(),
                "checks":        0
            }

        thread = threading.Thread(
            target=self._poll_loop,
            args=(integration_name,),
            daemon=True,                            # dies when main process dies
            name=f"cred-watcher-{integration_name}"
        )
        thread.start()
        print(
            f"[WATCHER] Started watching '{integration_name}' "
            f"for vars: {required_vars}"
        )
        return True

    def _poll_loop(self, integration_name: str):
        """Daemon thread body — polls until creds appear or watcher cancelled."""
        while True:
            with self._lock:
                if integration_name not in self._active:
                    print(f"[WATCHER] Cancelled: {integration_name}")
                    return
                watcher = self._active[integration_name]

            watcher["checks"] += 1
            all_present, missing = _check_vars(watcher["required_vars"])

            status = "✓ all vars present" if all_present else f"missing: {missing}"
            print(
                f"[WATCHER] {integration_name} check "
                f"#{watcher['checks']}: {status}"
            )

            if all_present:
                print(
                    f"[WATCHER] Credentials detected for '{integration_name}'! "
                    f"Triggering activation..."
                )
                # Remove from active before callback to prevent duplicate triggers
                with self._lock:
                    self._active.pop(integration_name, None)

                try:
                    watcher["callback"](integration_name)
                except Exception as e:
                    print(f"[WATCHER] Activation callback error for '{integration_name}': {e}")
                return  # thread exits after successful activation

            time.sleep(POLL_INTERVAL)

    def stop_watching(self, integration_name: str):
        """Cancel an active watcher. Thread will exit on its next iteration."""
        with self._lock:
            removed = self._active.pop(integration_name, None)
        if removed:
            print(f"[WATCHER] Cancelled watcher for: {integration_name}")
        else:
            print(f"[WATCHER] No active watcher for: {integration_name}")

    def get_watching(self) -> list:
        """
        Return status of all currently-watched integrations.
        Safe to call from any thread.
        """
        with self._lock:
            return [
                {
                    "name":            name,
                    "required_vars":   w["required_vars"],
                    "checks":          w["checks"],
                    "waiting_seconds": int(time.time() - w["started_at"]),
                }
                for name, w in self._active.items()
            ]

    def is_watching(self, name: str) -> bool:
        """Returns True if this integration is currently being watched."""
        with self._lock:
            return name in self._active


# ── Module-level singleton ─────────────────────────────────────────────────────
# api.py imports get_watcher() so it always gets the same instance.

_watcher: CredentialWatcher | None = None
_watcher_lock = threading.Lock()


def get_watcher() -> CredentialWatcher:
    """Return the global CredentialWatcher singleton (thread-safe)."""
    global _watcher
    if _watcher is None:
        with _watcher_lock:
            if _watcher is None:
                _watcher = CredentialWatcher()
    return _watcher
