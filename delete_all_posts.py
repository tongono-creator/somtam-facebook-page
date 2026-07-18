import time
#!/usr/bin/env python3
"""delete_all_posts.py -- remove all posts from page 554501167740603 (Prik 10 Med)
Run once via GitHub Actions: .github/workflows/delete_posts.yml
"""
import requests, os, time, sys

PAGE_ID = "554501167740603"
TOKEN = os.environ.get("SOMTAM_PAGE_ACCESS_TOKEN", "")

if not TOKEN:
    raise SystemExit("ERROR: SOMTAM_PAGE_ACCESS_TOKEN env var not set")

print(f"Starting cleanup for page {PAGE_ID}...")
removed = 0
after = None

while True:
    params = {"fields": "id,created_time", "limit": 100, "access_token": TOKEN}
    if after:
        params["after"] = after

    resp = requests.get(
        f"https://graph.facebook.com/v21.0/{PAGE_ID}/posts",
        params=params, timeout=30
    )
    data = resp.json()

    if "error" in data:
        print(f"API Error: {data['error']}")
        sys.exit(1)

    posts = data.get("data", [])
    if not posts:
        print(f"No more posts. Total removed: {removed}")
        break

    print(f"Batch: {len(posts)} posts...")
    for post in posts:
        post_id = post["id"]
        r = requests.delete(
            f"https://graph.facebook.com/v21.0/{post_id}",
            params={"access_token": TOKEN}, timeout=30
        )
        result = r.json()
        if result.get("success"):
            print(f"  OK: {post_id}")
            removed += 1
        else:
            print(f"  FAIL {post_id}: {result}")
        time.sleep(0.3)

    paging = data.get("paging", {})
    after = paging.get("cursors", {}).get("after")
    if not after or not paging.get("next"):
        break

print(f"Finished. {removed} posts removed.")
