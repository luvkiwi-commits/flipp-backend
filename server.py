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

STORE_IDS = {
    "publix": "7751",
    "kroger": "6772",
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
            cur = float(str(item["current_price"]).replace("$",""))
            orig = float(str(item["original_price"]).replace("$",""))
            if orig > cur:
                return "SALE"
        except:
            pass
    return "SALE"

def savings_pct(item):
    try:
        cur = float(str(item.get("current_price","0")).replace("$",""))
        orig = float(str(item.get("original_price","0")).replace("$",""))
        if orig > 0 and cur < orig:
            return round((orig - cur) / orig * 100)
    except:
        pass
    return 0


@app.route("/circular")
def circular():
    store = request.args.get("store", "publix").lower()
    zip_code = request.args.get("zip", "30301")

    try:
        # Step 1: find flyers for this store/zip
        flyer_url = "https://backflipp.wishabi.com/flipp/flyers"
        params = {"locale": "en-us", "postal_code": zip_code}
        res = requests.get(flyer_url, params=params, headers=HEADERS, timeout=10)
        flyers = res.json() if res.status_code == 200 else []

        # Normalize flyer list
        flyer_list = flyers if isinstance(flyers, list) else flyers.get("flyers", [])

        # Debug: return all merchant names if store not found
        all_merchants = []
        flyer_id = None
        for f in flyer_list:
            merchant = (f.get("merchant_name") or f.get("name") or "").lower()
            all_merchants.append(merchant)
            # Fuzzy match — check if any word in store name appears in merchant name
            if any(word in merchant for word in store.split()):
                flyer_id = f.get("id") or f.get("flyer_id")
                break

        if not flyer_id:
            return jsonify({
                "error": f"No flyer found for {store}",
                "available_stores": all_merchants[:30],
                "items": []
            })

        # Step 2: get flyer items
        items_url = f"https://backflipp.wishabi.com/flipp/flyers/{flyer_id}/flyer_items"
        res2 = requests.get(items_url, headers=HEADERS, timeout=10)
        raw_items = res2.json() if res2.status_code == 200 else []
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("flyer_items", raw_items.get("items", []))

        deals = []
        for item in raw_items:
            name = item.get("name") or item.get("description") or ""
            if not name:
                continue

            price = (item.get("current_price") or item.get("sale_price") or
                     item.get("price") or item.get("display_price"))
            orig  = item.get("original_price") or item.get("regular_price")
            sale_story = item.get("sale_story") or item.get("description") or ""
            category = item.get("category") or ""
            organic = is_organic(name)
            dtype = deal_type(item)
            pct = savings_pct(item)

            deals.append({
                "name": name,
                "price": f"${float(str(price).replace('$','')):.2f}" if price else None,
                "original_price": f"${float(str(orig).replace('$','')):.2f}" if orig else None,
                "sale_story": sale_story,
                "category": category,
                "organic": organic,
                "deal_type": dtype,
                "savings_pct": pct,
                "image_url": item.get("large_image_url") or item.get("image_url"),
            })

        # Sort: organic BOGOs first, then organic sales, then by savings %
        deals.sort(key=lambda x: (
            0 if (x["organic"] and x["deal_type"] == "BOGO") else
            1 if (x["organic"] and x["deal_type"] in ("PCT","SALE")) else
            2 if x["deal_type"] == "BOGO" else
            3,
            -x["savings_pct"]
        ))

        return jsonify({"store": store, "flyer_id": flyer_id, "items": deals})

    except Exception as e:
        return jsonify({"error": str(e), "items": []})


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
            headers=HEADERS, timeout=10,
        )
        if res.status_code != 200:
            return jsonify({"found": False})

        data = res.json()
        items = data if isinstance(data, list) else next(
            (data[k] for k in ("items","results","data","flyer_items") if isinstance(data.get(k), list)), []
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
                    price_f = float(str(price).replace("$",""))
                    savings = None
                    if orig:
                        orig_f = float(str(orig).replace("$",""))
                        if orig_f > price_f:
                            savings = f"Save ${orig_f - price_f:.2f}"
                    return jsonify({"found": True, "store": store,
                                    "price": f"${price_f:.2f}", "savings": savings, "product": name})
                except:
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
