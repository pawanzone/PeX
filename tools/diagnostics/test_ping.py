import urllib.request
try:
    with urllib.request.urlopen("http://localhost:8000/docs", timeout=2) as response:
        print("Server is RUNNING. Status code:", response.status)
except Exception as e:
    print("Server is not currently running on port 8000:", e)
