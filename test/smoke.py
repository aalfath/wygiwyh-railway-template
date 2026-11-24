"""Smoke test for a WYGIWYH deploy: login through the CSRF-protected form,
create a currency, account and transaction over the API (session auth),
upload an attachment and download it again, then optionally verify data from
an earlier run.

usage: python smoke.py BASE_URL EMAIL PASSWORD [create|verify]
"""
import re
import sys

import requests

base, email, password = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else "create"
s = requests.Session()
s.headers["Referer"] = base + "/login/"

r = s.get(base + "/login/", timeout=30)
assert r.status_code == 200, r.status_code
tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)
bad = requests.post(base + "/login/", data={"csrfmiddlewaretoken": tok, "username": email, "password": "wrong"},
                    cookies=r.cookies, headers={"Referer": base + "/login/"}, timeout=30, allow_redirects=False)
assert bad.status_code == 200, f"wrong password should not log in ({bad.status_code})"
r = s.post(base + "/login/", data={"csrfmiddlewaretoken": tok, "username": email, "password": password},
           timeout=30, allow_redirects=False)
assert r.status_code == 302, f"login failed {r.status_code}"
print("login ok ->", r.headers.get("Location"))
anon = requests.get(base + "/api/transactions/", timeout=30)
assert anon.status_code in (401, 403), f"anonymous API should be refused ({anon.status_code})"
print("anonymous API refused:", anon.status_code)
for p in ("/auth/signup/", "/signup/"):
    print("signup page", p, requests.get(base + p, timeout=30, allow_redirects=False).status_code)

csrf = s.cookies.get("csrftoken")
h = {"X-CSRFToken": csrf, "Referer": base + "/"}

if mode == "create":
    c = s.post(base + "/api/currencies/", json={"code": "TST", "name": "Smoke Dollar", "decimal_places": 2, "prefix": "T$ "}, headers=h, timeout=30)
    assert c.status_code == 201, c.text[:300]
    a = s.post(base + "/api/accounts/", json={"name": "Smoke Account", "currency_id": c.json()["id"]}, headers=h, timeout=30)
    if a.status_code != 201:
        a = s.post(base + "/api/accounts/", json={"name": "Smoke Account", "currency": c.json()["id"]}, headers=h, timeout=30)
    assert a.status_code == 201, a.text[:300]
    t = s.post(base + "/api/transactions/", json={"account": a.json()["id"], "type": "EX", "is_paid": True, "date": "2026-11-24",
                                                    "reference_date": "2026-11", "amount": "12.34", "description": "smoke coffee"},
               headers=h, timeout=30)
    assert t.status_code == 201, t.text[:300]
    tid = t.json()["id"]
    up = s.post(f"{base}/transaction/{tid}/attachments/", files={"attachments": ("receipt.txt", b"smoke receipt 42\n", "text/plain")},
                data={"csrfmiddlewaretoken": csrf}, headers={**h, "HX-Request": "true"}, timeout=60)
    assert up.status_code == 200, up.status_code
    m = re.search(r"/transaction/attachments/([0-9a-f-]{36})/download/", up.text)
    assert m, "attachment link not found"
    print("transaction", tid, "attachment", m.group(1))

lst = s.get(base + "/api/transactions/?description=smoke%20coffee", headers=h, timeout=30).json()
items = lst.get("results", lst)
smoke = [x for x in items if x.get("description") == "smoke coffee"]
assert smoke, "smoke transaction missing"
tid = smoke[0]["id"]
page = s.get(f"{base}/transaction/{tid}/attachments/list/", headers={**h, "HX-Request": "true"}, timeout=30)
m = re.search(r"/transaction/attachments/([0-9a-f-]{36})/download/", page.text)
assert m, "attachment missing after " + mode
d = s.get(f"{base}/transaction/attachments/{m.group(1)}/download/", timeout=30)
assert d.status_code == 200 and d.content == b"smoke receipt 42\n", (d.status_code, d.content[:80])
print(f"{mode}: transaction {tid} and its attachment are there; download matches")
print("SMOKE OK")
