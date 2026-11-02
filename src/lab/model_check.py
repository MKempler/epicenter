"""Is the live lab's model still answering? One tiny request, one line of output.

    docker exec investigator python -m src.lab.model_check

The hackathon's Baseten key carries a fixed credit with no balance to look up,
so the only way to know it still works is to use it. This sends a one-word
prompt to the provider the lab investigates with and prints a JSON line: when,
which model, whether it answered, and the error if not. It exits non-zero on
failure. deploy/setup.sh runs it daily from cron, appending to
/var/log/epicenter-model-check.log.
"""

import json
import sys
import time
from datetime import datetime, timezone

from src.config import DEFAULT
from src.llm import PROVIDERS, api_key


def check(provider: str) -> dict:
    from openai import OpenAI
    p = PROVIDERS[provider]
    started = time.time()
    line = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "provider": provider, "model": p.model}
    try:
        c = OpenAI(base_url=api_key(p.url_name) if p.url_name else p.base_url, api_key=api_key(p.key_name),
                   max_retries=1, timeout=60)
        c.chat.completions.create(model=p.model, messages=[{"role": "user", "content": "Reply with: ok"}], max_tokens=32)
        line.update(ok=True)
    except Exception as error:
        line.update(ok=False, error=f"{type(error).__name__}: {str(error)[:300]}")
    line["seconds"] = round(time.time() - started, 1)
    return line


if __name__ == "__main__":
    result = check(DEFAULT.live.provider)
    print(json.dumps(result), flush=True)
    sys.exit(0 if result["ok"] else 1)
