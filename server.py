from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://flipp.com/",
    "Origin": "https://flipp.com",
}

def fetch_deal(item, zip_code):
    try:
        res = requests.get(
            "https://backflipp.wishabi.com/flipp/items/search",
            params={"q": item, "postal_code": zip_code, "locale": "en-us"},
            headers=HEADERS,
            timeout=10,
        )
        if res.status_code != 200:
            return {"found": False}

        data = res.json()
        items = data if isinstance(data, list) else next(
            (data[k] for k in ("items", "results", "data", "flyer_items") if isinstance(data.get(k), list)), []
        )

        for candidate in items[:5]:
            price = (candidate.get("current_price") or candidate.get("sale_price") or
                     candidate.get("price") or candidate.get("display_price"))
            orig  = (candidate.get("original_price") or candidate.get("regular_price") or
                     candidate.get("was_price"))
            store = (candidate.get("merchant_name") or candidate.get("store_name") or
                     candidate.get("retailer_name"))
            name  = candidate.get("name") or candidate.get("description") or item

            if price:
                try:
                    price_f = float(str(price).replace("$", ""))
                    savings = None
                    if orig:
                        orig_f = float(str(orig).replace("$", ""))
                        if orig_f > price_f:
                            savings = f"Save ${orig_f - price_f:.2f}"
                    return {"found": True, "store": store, "price": f"${price_f:.2f}",
                            "savings": savings, "product": name}
                except Exception:
                    continue

        return {"found": False}
    except Exception as e:
        return {"found": False, "error": str(e)}


@app.route("/deals")
def deals():
    item = request.args.get("item", "")
    zip_code = request.args.get("zip", "30301")
    if not item:
        return jsonify({"error": "item param required"}), 400
    return jsonify(fetch_deal(item, zip_code))


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Flipp backend running at http://localhost:5001")
    app.run(port=5001, debug=False)
