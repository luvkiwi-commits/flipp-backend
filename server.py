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
        # Use the items search API with store name as query to find store-specific deals
        # This is more reliable than the flyers endpoint
        search_url = "https://backflipp.wishabi.com/flipp/flyers/search"
        params = {"q": store, "locale": "en-us", "postal_code": zip_code}
        res = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        print(f"Flyer search status: {res.status_code}")
        print(f"Flyer search response: {res.text[:500]}")

        flyer_id = None
        if res.status_code == 200:
            data = res.json()
            flyer_list = data if isinstance(data, list) else data.get("flyers", data.get("results", []))
            for f in flyer_list:
                merchant = (f.get("merchant_name") or f.get("name") or "").lower()
                if store in merchant or merchant in store:
                    flyer_id = f.get("id") or f.get("flyer_id")
                    break

        # Fallback: try the items search endpoint directly for this store
        if not flyer_id:
            items_search_url = "https://backflipp.wishabi.com/flipp/items/search"
            params2 = {"q": store, "postal_code": zip_code, "locale": "en-us"}
            res2 = requests.get(items_search_url, params=params2, headers=HEADERS, timeout=10)
            print(f"Items search status: {res2.status_code}")
            print(f"Items search response: {res2.text[:500]}")

            if res2.status_code == 200:
                raw = res2.json()
                raw_items = raw if isinstance(raw, list) else next(
                    (raw[k] for k in ("items","results","data","flyer_items") if isinstance(raw.get(k), list)), []
                )
                # Filter to items from this store
                store_items = [i for i in raw_items if store in (i.get("merchant_name") or "").lower()]
                if not store_items:
                    store_items = raw_items  # fallback: use all

                deals = []
                for item in store_items:
                    name = item.get("name") or item.get("description") or ""
                    if not name:
                        continue
                    price = (item.get("current_price") or item.get("sale_price") or
                             item.get("price") or item.get("display_price"))
                    orig  = item.get("original_price") or item.get("regular_price")
                    sale_story = item.get("sale_story") or ""
                    organic = is_organic(name)
                    dtype = deal_type(item)
                    pct = savings_pct(item)
                    deals.append({
                        "name": name,
                        "price": f"${float(str(price).replace('


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
,'')):.2f}" if price else None,
                        "original_price": f"${float(str(orig).replace('


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
,'')):.2f}" if orig else None,
                        "sale_story": sale_story,
                        "category": item.get("category") or "",
                        "organic": organic,
                        "deal_type": dtype,
                        "savings_pct": pct,
                        "merchant": item.get("merchant_name") or store,
                    })

                deals.sort(key=lambda x: (
                    0 if (x["organic"] and x["deal_type"] == "BOGO") else
                    1 if (x["organic"] and x["deal_type"] in ("PCT","SALE")) else
                    2 if x["deal_type"] == "BOGO" else 3,
                    -x["savings_pct"]
                ))
                return jsonify({"store": store, "source": "items_search", "items": deals})

            return jsonify({"error": f"Could not find deals for {store}", "items": []})

        # If we found a flyer_id, fetch its items
        items_url = f"https://backflipp.wishabi.com/flipp/flyers/{flyer_id}/flyer_items"
        res3 = requests.get(items_url, headers=HEADERS, timeout=10)
        raw_items = res3.json() if res3.status_code == 200 else []
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
            sale_story = item.get("sale_story") or ""
            organic = is_organic(name)
            dtype = deal_type(item)
            pct = savings_pct(item)
            deals.append({
                "name": name,
                "price": f"${float(str(price).replace('


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
,'')):.2f}" if price else None,
                "original_price": f"${float(str(orig).replace('


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
,'')):.2f}" if orig else None,
                "sale_story": sale_story,
                "category": item.get("category") or "",
                "organic": organic,
                "deal_type": dtype,
                "savings_pct": pct,
            })

        deals.sort(key=lambda x: (
            0 if (x["organic"] and x["deal_type"] == "BOGO") else
            1 if (x["organic"] and x["deal_type"] in ("PCT","SALE")) else
            2 if x["deal_type"] == "BOGO" else 3,
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
