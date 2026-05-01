from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Allow the local HTML file to call this server

FLIPP_SEARCH = "https://backflipp.wishabi.com/flipp/items/search"
FLIPP_ITEM   = "https://backflipp.wishabi.com/flipp/items/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://flipp.com/",
}

def fetch_deal(query, postal_code):
    try:
        res = requests.get(
            FLIPP_SEARCH,
            params={"q": query, "postal_code": postal_code, "locale": "en-us"},
            headers=HEADERS,
            timeout=8,
        )
        data = res.json()
        items = data.get("items", [])
        if not items:
            return {"found": False}

        # Grab the first result that has a price
        for item in items[:5]:
            item_id = item.get("flyer_item_id")
            if not item_id:
                continue
            detail = requests.get(
                f"{FLIPP_ITEM}{item_id}",
                headers=HEADERS,
                timeout=8,
            ).json()

            price = detail.get("current_price") or detail.get("sale_price")
            orig  = detail.get("original_price")
            store = detail.get("merchant_name") or detail.get("flyer", {}).get("merchant_name")
            name  = detail.get("name", query)

            if price:
                savings = None
                if orig and float(orig) > float(price):
                    savings = f"Save ${float(orig) - float(price):.2f}"
                return {
                    "found": True,
                    "store": store,
                    "price": f"${float(price):.2f}",
                    "savings": savings,
                    "name": name,
                }

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
