import logging
import os
import sys
import threading
from typing import Iterable, List, Optional


# Define a custom TRACE level below DEBUG
TRACE_LEVEL_NUM = 5
if not hasattr(logging, "TRACE"):
    logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


def _trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws)


if not hasattr(logging.Logger, "trace"):
    logging.Logger.trace = _trace  # type: ignore[attr-defined]


def _level_from_str(level: Optional[str]) -> int:
    s = (level or "INFO").strip().upper()
    if s == "TRACE":
        return TRACE_LEVEL_NUM
    return getattr(logging, s, logging.INFO)


def _normalize_prefixes(prefixes: Optional[Iterable[str]]) -> List[str]:
    if not prefixes:
        return []
    out = []
    for p in prefixes:
        p = (p or "").strip()
        if not p:
            continue
        # Support file system style (e.g., services/) by converting to module prefix
        if p.endswith("/"):
            p = p[:-1]
        if not p.endswith('.'):
            p = p + '.'
        out.append(p)
    return out


def _normalize_contains(items: Optional[Iterable[str]], default: Optional[List[str]] = None) -> List[str]:
    if items is None:
        return list(default or [])
    out: List[str] = []
    for it in items:
        s = (it or "").strip()
        if s:
            out.append(s)
    return out if out else list(default or [])


def setup_logging(level: Optional[str] = None, *, force: bool = True) -> int:
    """Initialize root logging with a consistent format.

    Returns the effective numeric level configured.
    """
    lvl = _level_from_str(level)
    fmt = (
        "%(asctime)s %(levelname)-5s %(name)s.%(funcName)s:%(lineno)d - %(message)s"
    )
    logging.basicConfig(level=lvl, format=fmt, force=force)
    # Reduce noise from third-party libraries at TRACE/DEBUG
    for noisy in ("httpx", "uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"):
        logging.getLogger(noisy).setLevel(max(logging.INFO, lvl))
    # Explicitly suppress chatty libraries regardless of global level
    for quiet in ("fontTools", "fontTools.subset", "fpdf"):
        logging.getLogger(quiet).setLevel(logging.ERROR)
    return lvl


def enable_call_tracing(
    module_prefixes: Iterable[str],
    path_contains: Optional[Iterable[str]] = None,
    *,
    concise: bool = False,
) -> None:
    """Install a lightweight function call tracer using sys.setprofile.

    Logs CALL/RETURN events at TRACE level for functions whose module name
    starts with any of the provided prefixes. Intended for ad-hoc deep
    diagnostics; expect significant verbosity.
    """
    prefixes = _normalize_prefixes(module_prefixes)
    paths = _normalize_contains(path_contains, default=["services/"])
    trace_logger = logging.getLogger("trace.calls")
    # If concise mode, attach a dedicated minimal handler and stop propagation
    if concise:
        handler = logging.StreamHandler()
        handler.setLevel(TRACE_LEVEL_NUM)
        handler.setFormatter(logging.Formatter("%(message)s"))
        # Avoid duplicating via root handlers
        trace_logger.handlers.clear()
        trace_logger.addHandler(handler)
        trace_logger.setLevel(TRACE_LEVEL_NUM)
        trace_logger.propagate = False
    tls = threading.local()

    def _profile(frame, event, arg):
        if event not in ("call", "return"):
            return
        # Avoid recursion/overhead while logging
        if getattr(tls, "busy", False):
            return
        mod = frame.f_globals.get("__name__", "")
        filename = frame.f_code.co_filename or ""
        match_module = any(mod.startswith(p) for p in prefixes) if prefixes else False
        match_path = any(s in filename for s in paths) if paths else False
        if not (match_module or match_path):
            return
        # Skip logging internals and stdlib logging itself
        if mod.startswith("logging") or mod.startswith(__name__):
            return
        code = frame.f_code
        func = code.co_name
        # Skip trivial internal frames
        if func in ("<module>", "_profile"):
            return
        try:
            tls.busy = True
            if event == "call":
                if concise:
                    trace_logger.log(TRACE_LEVEL_NUM, "CALL %s.%s", mod, func)
                else:
                    trace_logger.log(
                        TRACE_LEVEL_NUM,
                        "CALL %s.%s (%s:%s)",
                        mod,
                        func,
                        code.co_filename,
                        code.co_firstlineno,
                    )
            elif event == "return":
                trace_logger.log(TRACE_LEVEL_NUM, "RET  %s.%s", mod, func)
        finally:
            tls.busy = False

    sys.setprofile(_profile)


def setup_from_env() -> None:
    """Configure logging/tracing using environment variables.

    - LOG_LEVEL: standard levels or TRACE
    - TRACE_CALLS: truthy to force call tracing
    - TRACE_MODULE_PREFIXES: comma-separated module prefixes (default: services.)
    """
    lvl = setup_logging(os.getenv("LOG_LEVEL"))
    want_trace = os.getenv("TRACE_CALLS", "").strip().lower() in {"1", "true", "yes", "y"}
    prefixes_env = os.getenv("TRACE_MODULE_PREFIXES", "")
    paths_env = os.getenv("TRACE_FILE_PATH_CONTAINS", "services/")
    concise = os.getenv("TRACE_CONCISE", "").strip().lower() in {"1", "true", "yes", "y"}
    if want_trace or lvl <= TRACE_LEVEL_NUM:
        prefixes = [p.strip() for p in prefixes_env.split(",") if p.strip()]
        paths = [p.strip() for p in paths_env.split(",") if p.strip()]
        enable_call_tracing(prefixes, paths, concise=concise)


def setup_from_settings(settings_obj) -> None:
    """Configure logging/tracing using a Settings-like object.

    The object should expose: log_level, trace_calls, trace_module_prefixes
    """
    lvl = setup_logging(getattr(settings_obj, "log_level", None))
    trace_calls = bool(getattr(settings_obj, "trace_calls", False)) or lvl <= TRACE_LEVEL_NUM
    prefixes_raw = getattr(settings_obj, "trace_module_prefixes", "")
    paths_raw = getattr(settings_obj, "trace_file_path_contains", "services/")
    concise = bool(getattr(settings_obj, "trace_concise", False))
    if trace_calls:
        prefixes = [p.strip() for p in str(prefixes_raw).split(",") if p.strip()]
        paths = [p.strip() for p in str(paths_raw).split(",") if p.strip()]
        enable_call_tracing(prefixes, paths, concise=concise)
