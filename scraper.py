import json
import os
import requests

SERPAPI_KEY = os.environ["SERPAPI_KEY"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

results_for_app = []

for item in watchlist:
    query = item["name"]
    target = item.get("target_price")
    region = item.get("region", "nz")

    params = {
        "engine": "google_shopping",
        "q": query,
        "google_domain": "google.co.nz" if region == "nz" else "google.com",
        "gl": "nz" if region == "nz" else "us",
        "hl": "en",
        "on_sale": "1",  # Only return items actively on sale
        "api_key": SERPAPI_KEY
    }

    res = requests.get("https://serpapi.com/search.json", params=params).json()
    shopping_results = res.get("shopping_results", [])

    stores_on_sale = []
    product_image = ""

    for offer in shopping_results[:5]:  # Check top 5 live store offers
        if not product_image and offer.get("thumbnail"):
            product_image = offer.get("thumbnail")

        price = offer.get("extracted_price")
        store_name = offer.get("source")
        link = offer.get("link") or offer.get("product_link")

        if price and store_name and link:
            # If target price is set, only include if at or below target
            if target is None or price <= float(target):
                stores_on_sale.append({
                    "name": store_name,
                    "price": float(price),
                    "link": link
                })

    results_for_app.append({
        "name": query,
        "region": region,
        "targetPrice": target,
        "image": product_image,
        "storesOnSale": stores_on_sale
    })

    # Send push notification to your phone if a real sale is found
    if stores_on_sale:
        best = min(stores_on_sale, key=lambda x: x["price"])
        msg = f"{query} is ON SALE for ${best['price']:.2f} at {best['name']}!"
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=msg.encode("utf-8"),
            headers={
                "Title": "NZ Sale Watch Alert!",
                "Click": best["link"],
                "Tags": "shopping_bags,tag"
            }
        )

# Save real results for your web app UI to read
with open("deals.json", "w") as f:
    json.dump(results_for_app, f, indent=2)
