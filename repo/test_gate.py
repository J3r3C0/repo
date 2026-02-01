import requests

def test_security_gate():
    url = "http://127.0.0.1:8005/api/reset"
    try:
        resp = requests.post(url)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.json()}")
        if resp.status_code == 403:
            print("Security Gate Blocked Reset (Correct)")
        else:
            print("Security Gate Failed or Reset was enabled (Unexpected if SHERATAN_ENABLE_RESET=0)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_security_gate()
