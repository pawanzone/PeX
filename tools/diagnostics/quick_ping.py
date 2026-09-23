import urllib.request
with urllib.request.urlopen("http://localhost:8000/api/cases", timeout=2) as r:
    print("API Live. Status code:", r.status)
