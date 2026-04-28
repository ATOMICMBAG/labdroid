from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str = ""


def _check_python_version() -> CheckResult:
    ok = sys.version_info >= (3, 11)
    return CheckResult(
        name="Python >= 3.11",
        ok=ok,
        detail=f"Gefunden: {sys.version.split()[0]}",
        hint="Bitte Python 3.11+ installieren." if not ok else "",
    )


def _check_imports() -> CheckResult:
    missing: list[str] = []
    for module in ("fastapi", "uvicorn", "numpy", "httpx", "pydantic"):
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(module)

    if missing:
        return CheckResult(
            name="Backend-Module",
            ok=False,
            detail=f"Fehlend: {', '.join(missing)}",
            hint="Im Ordner labdroid/backend: `uv sync` ausführen.",
        )

    return CheckResult(name="Backend-Module", ok=True, detail="Alle Kernmodule importierbar")


def _http_get_json(url: str, timeout_s: float = 2.5) -> tuple[bool, dict | None, str]:
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(body), "ok"
    except URLError as exc:
        return False, None, f"{exc}"
    except Exception as exc:  # noqa: BLE001
        return False, None, f"{exc}"


def _check_ollama_binary() -> CheckResult:
    path = shutil.which("ollama")
    if not path:
        return CheckResult(
            name="Ollama CLI",
            ok=False,
            detail="`ollama` nicht im PATH gefunden",
            hint="Ollama installieren: https://ollama.com/download",
        )
    return CheckResult(name="Ollama CLI", ok=True, detail=f"Gefunden: {path}")


def _check_ollama_server(base_url: str) -> CheckResult:
    ok, payload, msg = _http_get_json(f"{base_url.rstrip('/')}/api/tags")
    if not ok:
        return CheckResult(
            name="Ollama Server",
            ok=False,
            detail=f"Nicht erreichbar: {msg}",
            hint="Ollama starten (z. B. App öffnen oder `ollama serve`).",
        )

    count = len((payload or {}).get("models", []))
    return CheckResult(name="Ollama Server", ok=True, detail=f"Erreichbar, Modelle: {count}")


def _check_ollama_model(base_url: str, model: str) -> CheckResult:
    ok, payload, msg = _http_get_json(f"{base_url.rstrip('/')}/api/tags")
    if not ok:
        return CheckResult(
            name=f"Ollama Modell `{model}`",
            ok=False,
            detail=f"Nicht prüfbar: {msg}",
            hint=f"Nach Server-Start prüfen oder `ollama pull {model}` ausführen.",
        )

    names = [str(m.get("name", "")) for m in (payload or {}).get("models", [])]
    found = any(name == model or name.startswith(f"{model}:") for name in names)
    if found:
        return CheckResult(name=f"Ollama Modell `{model}`", ok=True, detail="Modell vorhanden")

    return CheckResult(
        name=f"Ollama Modell `{model}`",
        ok=False,
        detail="Modell nicht gefunden",
        hint=f"`ollama pull {model}` ausführen.",
    )


def _check_openrouter_key(explicit_key: str | None) -> CheckResult:
    key = explicit_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        return CheckResult(
            name="OpenRouter API Key",
            ok=False,
            detail="OPENROUTER_API_KEY fehlt",
            hint="Im Environment oder in .env-Datei setzen.",
        )
    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "gesetzt"
    return CheckResult(name="OpenRouter API Key", ok=True, detail=f"Vorhanden ({masked})")


def _render(results: list[CheckResult]) -> int:
    print("\n=== Labdroid Setup Companion · Status ===\n")
    for item in results:
        marker = "[OK]" if item.ok else "[FAIL]"
        print(f"{marker} {item.name}: {item.detail}")
        if item.hint:
            print(f"   -> Hinweis: {item.hint}")

    failed = [r for r in results if not r.ok]
    print("\n----------------------------------------")
    if failed:
        print(f"Ergebnis: {len(failed)} Problem(e) gefunden")
        return 1
    print("Ergebnis: Setup ist bereit")
    return 0


def _env_template_local(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            "# Labdroid Setup-Companion (local profile)",
            "LABDROID_DEFAULT_PROVIDER=ollama",
            "LABDROID_PROVIDER_ALLOWLIST=litert,ollama,openrouter",
            f"LABDROID_OLLAMA_BASE_URL={args.ollama_base_url.rstrip('/')}",
            f"LABDROID_OLLAMA_DEFAULT_MODEL={args.ollama_model}",
            "LABDROID_OPENROUTER_DEFAULT_MODEL=google/gemma-3-27b-it:free",
            "# OPENROUTER_API_KEY=",
            "",
        ]
    )


def _env_template_online(args: argparse.Namespace) -> str:
    key = args.openrouter_key or os.getenv("OPENROUTER_API_KEY") or ""
    return "\n".join(
        [
            "# Labdroid Setup-Companion (online profile)",
            "LABDROID_DEFAULT_PROVIDER=openrouter",
            "LABDROID_PROVIDER_ALLOWLIST=litert,ollama,openrouter",
            "LABDROID_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1",
            f"LABDROID_OPENROUTER_DEFAULT_MODEL={args.openrouter_model}",
            f"OPENROUTER_API_KEY={key}",
            f"LABDROID_OLLAMA_DEFAULT_MODEL={args.ollama_model}",
            "",
        ]
    )


def _write_env(profile: str, args: argparse.Namespace) -> Path:
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    content = _env_template_local(args) if profile == "local" else _env_template_online(args)
    output.write_text(content, encoding="utf-8")
    return output


def _print_next_steps(env_file: Path) -> None:
    backend_dir = Path(__file__).resolve().parent
    cmd = (
        "python -m uvicorn app.main:app "
        f"--app-dir \"{backend_dir}\" --host 0.0.0.0 --port 8000 "
        f"--env-file \"{env_file}\""
    )
    print("\nNächster Schritt:")
    print(cmd)


def _status_command(args: argparse.Namespace) -> int:
    results: list[CheckResult] = [_check_python_version(), _check_imports()]

    if args.profile in {"local", "auto"}:
        results.append(_check_ollama_binary())
        results.append(_check_ollama_server(args.ollama_base_url))
        results.append(_check_ollama_model(args.ollama_base_url, args.ollama_model))

    if args.profile in {"online", "auto"}:
        results.append(_check_openrouter_key(args.openrouter_key))

    return _render(results)


def _write_env_command(args: argparse.Namespace) -> int:
    env_file = _write_env(args.profile, args)
    print(f"\nEnv-Datei geschrieben: {env_file}")
    _print_next_steps(env_file)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Labdroid Setup-Companion: Preflight-Checks und env-Profile für lokal/online.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--ollama-base-url", default="http://localhost:11434")
        p.add_argument("--ollama-model", default="gemma4:e4b")
        p.add_argument("--openrouter-model", default="google/gemma-3-27b-it:free")
        p.add_argument("--openrouter-key", default=None)

    p_status = sub.add_parser("status", help="Prüft lokales Setup")
    p_status.add_argument("--profile", choices=["auto", "local", "online"], default="auto")
    add_common(p_status)
    p_status.set_defaults(func=_status_command)

    p_env = sub.add_parser("write-env", help="Schreibt env-Datei für local/online")
    p_env.add_argument("--profile", choices=["local", "online"], required=True)
    p_env.add_argument("--output", default=".env.generated")
    add_common(p_env)
    p_env.set_defaults(func=_write_env_command)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
