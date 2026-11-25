import httpx
urls = [
    ("wikipedia-api", "https://en.wikipedia.org/w/api.php", {"action":"query","list":"search","srsearch":"artificial intelligence","format":"json","srlimit":3}),
    ("ddg-lite", "https://lite.duckduckgo.com/lite/", {"q":"artificial intelligence"}),
    ("bing", "https://www.bing.com/search", {"q":"artificial intelligence"}),
]
for name, url, params in urls:
    try:
        r = httpx.get(url, params=params, timeout=15, headers={"User-Agent":"Mozilla/5.0 IAM-Research/1.0"})
        print(name, r.status_code, len(r.text), r.text[:120].replace("\n"," "))
    except Exception as e:
        print(name, "ERR", str(e)[:100])
