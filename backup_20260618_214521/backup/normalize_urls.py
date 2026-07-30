from pathlib import Path

def normalize_url(url):
    for p in ["https://www.","http://www.","https://","http://"]:
        if url.startswith(p): url = url[len(p):]; break
    return url.split("/")[0].replace("-", " ")

if __name__ == "__main__":
    p = Path("urls.txt")
    if not p.exists(): print("Error: urls.txt not found."); exit()
    u = sorted({normalize_url(l.strip()) for l in p.read_text().splitlines() if l.strip()})
    p.write_text("\n".join(u) + "\n")
    print(f"Normalized. Saved {len(u)} unique results.")
