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

@app.route("/deals")
def deals():
    item = request.args.get("item", "")
    zip_code = request.args.get("zip", "30301")
    if not item:
        return jsonify({"error": "item param required"}), 400

    try:
        # Step 1: Search for items
        search_url = "https://backflipp.wishabi.com/flipp/items/search"
        params = {
            "q": item,
            "postal_code": zip_code,
            "locale": "en-us",
        }
        print(f"Searching Flipp for: {item} near {zip_code}")
        res = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        print(f"Status code: {res.status_code}")
        print(f"Response preview: {res.text[:500]}")

        if res.status_code != 200:
            return jsonify({"found": False, "error": f"Flipp returned {res.status_code}"})

        data = res.json()

        # Handle different possible response shapes
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common keys
            for key in ("items", "results", "data", "flyer_items"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break

        print(f"Found {len(items)} items in response")
        if items:
            print(f"First item keys: {list(items[0].keys()) if items else 'none'}")
            print(f"First item: {items[0]}")

        if not items:
            return jsonify({"found": False, "debug": f"Response keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"})

        # Try to extract price and store from first item
        for candidate in items[:5]:
            # Try different price field names
            price = (
                candidate.get("current_price") or
                candidate.get("sale_price") or
                candidate.get("price") or
                candidate.get("display_price")
            )
            orig = (
                candidate.get("original_price") or
                candidate.get("regular_price") or
                candidate.get("was_price")
            )
            store = (
                candidate.get("merchant_name") or
                candidate.get("store_name") or
                candidate.get("retailer_name") or
                candidate.get("name")
            )
            name = candidate.get("name") or candidate.get("description") or item

            if price:
                savings = None
                try:
                    if orig and float(str(orig).replace("$","")) > float(str(price).replace("$","")):
                        savings = f"Save ${float(str(orig).replace('$','')) - float(str(price).replace('$','')):.2f}"
                except:
                    pass

                return jsonify({
                    "found": True,
                    "store": store,
                    "price": f"${float(str(price).replace('$','')):.2f}",
                    "savings": savings,
                    "product": name,
                })

        # Return first item raw for debugging if no price found
        return jsonify({
            "found": False,
            "debug": f"No price found. First item: {items[0] if items else 'none'}"
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"found": False, "error": str(e)})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Flipp backend running at http://localhost:5001")
    app.run(port=5001, debug=True)
