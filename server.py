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

SEARCH_TERMS = {
    "publix": [
        "publix chicken", "publix produce", "publix beef",
        "publix organic", "publix dairy", "publix bogo", "publix seafood"
    ],
    "kroger": [
        "kroger chicken", "kroger produce", "kroger beef",
        "kroger organic", "kroger dairy", "kroger sale", "kroger seafood"
    ],
}

def is_organic(name):
    return "organic" in (name or "").lower()

def deal_type(item):
    sale = (item.get("sale_story") or "").lower()
    if "bogo" in sale or "buy one" in sale or "buy 1" in sale:
        return "BOGO"
    if "%" in sale:
        return "PCT"
    if item.get("current_price") and item.get("original_price"):
        try:
            cur = float(str(item["current_price"]).replace("$", ""))
            orig = float(str(item["original_price"]).replace("$", ""))
            if orig > cur:
                return "SALE"
        except Exception:
            pass
    return "SALE"

def savings_pct(item):
    try:
        cur = float(str(item.get("current_price", "0")).replace("$", ""))
        orig = float(str(item.get("original_price", "0")).replace("$", ""))
        if orig > 0 and cur < orig:
            return round((orig - cur) / orig * 100)
    except Exception:
        pass
    return 0

def parse_items(data):
    if isinstance(data, list):
        return data
    for k in ("items", "results", "data", "flyer_items"):
        if isinstance(data.get(k), list):
            return data[k]
    return []

def make_deal(item, fallback_store):
    name = item.get("name") or item.get("description") or ""
    if not name:
        return None
    price = (item.get("current_price") or item.get("sale_price") or
             item.get("price") or item.get("display_price"))
    orig = item.get("original_price") or item.get("regular_price")
    try:
        price_str = "$%.2f" % float(str(price).replace("$", "")) if price else None
    except Exception:
        price_str = None
    try:
        orig_str = "$%.2f" % float(str(orig).replace("$", "")) if orig else None
    except Exception:
        orig_str = None
    return {
        "name": name,
        "price": price_str,
        "original_price": orig_str,
        "sale_story": item.get("sale_story") or "",
        "category": item.get("category") or "",
        "organic": is_organic(name),
        "deal_type": deal_type(item),
        "savings_pct": savings_pct(item),
        "merchant": (item.get("merchant_name") or fallback_store).lower(),
    }

def sort_deals(deals):
    deals.sort(key=lambda x: (
        0 if (x["organic"] and x["deal_type"] == "BOGO") else
        1 if (x["organic"] and x["deal_type"] in ("PCT", "SALE")) else
        2 if x["deal_type"] == "BOGO" else 3,
        -x["savings_pct"]
    ))
    return deals


@app.route("/circular")
def circular():
    store = request.args.get("store", "publix").lower()
    zip_code = request.args.get("zip", "30301")
    terms = SEARCH_TERMS.get(store, [store + " sale", store + " organic", store + " produce"])

    seen = set()
    deals = []

    for term in terms:
        try:
            res = requests.get(
                "https://backflipp.wishabi.com/flipp/items/search",
                params={"q": term, "postal_code": zip_code, "locale": "en-us"},
                headers=HEADERS,
                timeout=10,
            )
            if res.status_code != 200:
                continue
            items = parse_items(res.json())
            for item in items:
                name = item.get("name") or item.get("description") or ""
                if not name or name in seen:
                    continue
                merchant = (item.get("merchant_name") or "").lower()
                if merchant and store not in merchant:
                    continue
                seen.add(name)
                deal = make_deal(item, store)
                if deal:
                    deals.append(deal)
        except Exception:
            continue

    # Fallback: if store filtering removed everything, retry without merchant filter
    if not deals:
        for term in terms[:3]:
            try:
                res = requests.get(
                    "https://backflipp.wishabi.com/flipp/items/search",
                    params={"q": term, "postal_code": zip_code, "locale": "en-us"},
                    headers=HEADERS,
                    timeout=10,
                )
                if res.status_code != 200:
                    continue
                items = parse_items(res.json())
                for item in items:
                    name = item.get("name") or item.get("description") or ""
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    deal = make_deal(item, store)
                    if deal:
                        deals.append(deal)
            except Exception:
                continue

    return jsonify({"store": store, "count": len(deals), "items": sort_deals(deals)})


@app.route("/deals")
def deals():
    item = request.args.get("item", "")
    zip_code = request.args.get("zip", "30301")
    if not item:
        return jsonify({"error": "item param required"}), 400
    try:
        res = requests.get(
            "https://backflipp.wishabi.com/flipp/items/search",
            params={"q": item, "postal_code": zip_code, "locale": "en-us"},
            headers=HEADERS,
            timeout=10,
        )
        if res.status_code != 200:
            return jsonify({"found": False})
        items = parse_items(res.json())
        for candidate in items[:5]:
            price = (candidate.get("current_price") or candidate.get("sale_price") or
                     candidate.get("price") or candidate.get("display_price"))
            orig = (candidate.get("original_price") or candidate.get("regular_price") or
                    candidate.get("was_price"))
            store = (candidate.get("merchant_name") or candidate.get("store_name") or
                     candidate.get("retailer_name"))
            name = candidate.get("name") or candidate.get("description") or item
            if price:
                try:
                    price_f = float(str(price).replace("$", ""))
                    savings = None
                    if orig:
                        orig_f = float(str(orig).replace("$", ""))
                        if orig_f > price_f:
                            savings = "Save $%.2f" % (orig_f - price_f)
                    return jsonify({"found": True, "store": store,
                                    "price": "$%.2f" % price_f,
                                    "savings": savings, "product": name})
                except Exception:
                    continue
        return jsonify({"found": False})
    except Exception as e:
        return jsonify({"found": False, "error": str(e)})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Flipp backend running at http://localhost:5001")
    app.run(port=5001, debug=False)
