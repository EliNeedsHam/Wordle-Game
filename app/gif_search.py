import json
import re
import urllib.parse
import urllib.request


DUCKDUCKGO_HOME = "https://duckduckgo.com/"
DUCKDUCKGO_IMAGES = "https://duckduckgo.com/i.js"
USER_AGENT = "Mozilla/5.0 WordForge/1.0"


def find_gif_url(term, timeout=4):
    clean_term = (term or "").strip().lower()
    if not clean_term:
        return None

    try:
        vqd = _duckduckgo_token(clean_term, timeout)
        if not vqd:
            return None
        return _first_duckduckgo_gif(clean_term, vqd, timeout)
    except Exception:
        return None


def _request(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _duckduckgo_token(term, timeout):
    query = urllib.parse.urlencode({"q": f"{term} gif"})
    html = _request(f"{DUCKDUCKGO_HOME}?{query}", timeout)
    match = re.search(r"vqd=['\"]?([^'\"&]+)", html)
    return match.group(1) if match else None


def _first_duckduckgo_gif(term, vqd, timeout):
    params = urllib.parse.urlencode(
        {
            "l": "us-en",
            "o": "json",
            "q": f"{term} gif",
            "vqd": vqd,
            "f": "type:gif",
            "p": "1",
        }
    )
    payload = json.loads(_request(f"{DUCKDUCKGO_IMAGES}?{params}", timeout))
    for result in payload.get("results", []):
        image = result.get("image") or result.get("thumbnail")
        if image:
            return image
    return None
