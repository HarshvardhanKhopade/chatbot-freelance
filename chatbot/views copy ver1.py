from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Product, QuotationRequest
import re


def chatbot_home(request):
    # Ensure cart exists in session
    if "cart" not in request.session:
        request.session["cart"] = []
    return render(request, "chatbot/chatbot.html")


# ---------- Helpers ----------
def parse_budget(text: str) -> int | None:
    """
    Extract a budget number from user text.
    Supports: 2000, 2,000, ₹2,000, 2k, 2.5k
    Returns an integer rupee amount or None.
    """
    t = text.lower()
    # Remove rupee symbol and "/-" etc.
    t = t.replace("₹", "").replace("/-", " ").replace(",", " ").strip()

    # Match number + optional 'k'
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k\b)?", t)
    if not m:
        return None

    num = float(m.group(1))
    if m.group(2):  # had 'k'
        num *= 1000.0
    return int(num)


CATEGORY_KEYWORDS = {
    # canonical : list of query terms to match
    "ring": ["ring", "rings"],
    "necklace": ["necklace", "necklaces"],
    "bangle": ["bangle", "bangles", "kada", "kadas"],
    "earring": ["earring", "earrings", "tops", "jhumka", "jhumkas"],
    "anklet": ["anklet", "anklets", "payal", "payals"],
    "chain": ["chain", "chains", "neck chain", "neck chains"],
}

def build_category_query(user_msg: str) -> Q:
    """
    Build a Q filter that matches products by category keywords OR name keywords.
    """
    q = Q()
    for canon, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in user_msg:
                q |= Q(name__icontains=w) | Q(category__icontains=w) | Q(category__icontains=canon)
    return q


def format_products_list(products, prefix: str) -> str:
    if not products:
        return "❌ No items found."
    reply = prefix + "<br>"
    for p in products:
        price_txt = f"₹{p.price}" if getattr(p, "price", None) is not None else "Price NA"
        reply += f"- {p.name} ({price_txt})<br>"
    reply += "<br>💬 Type 'add <product name>' to add to cart, or 'I'm interested' to request a callback."
    return reply


def chatbot_response(request):
    user_msg = (request.GET.get("msg", "") or "").lower().strip()
    response = {
        "reply": "❌ Sorry, I didn’t understand. Try: rings, necklaces, bangles, earrings, anklets, chains."
    }

    # --- Session state for lead capture ---
    if "chat_state" not in request.session:
        request.session["chat_state"] = {}
    state = request.session["chat_state"]

    # ----------------------------------------------------
    # 1) Lead Capture Workflow (highest priority)
    # ----------------------------------------------------
    if state.get("awaiting") == "name":
        state["customer_name"] = user_msg
        state["awaiting"] = "contact"
        response = {"reply": "📞 Great! Please share your contact number."}

  

    elif state.get("awaiting") == "contact":
        # check if input looks like a phone number
        if re.match(r"^\d{7,15}$", user_msg):  # allow 7–15 digits
            state["contact"] = user_msg
            product_name = state.get("product_interest", "General Inquiry")
            product = Product.objects.filter(name__icontains=product_name).first()
            QuotationRequest.objects.create(
                customer_name=state.get("customer_name"),
                contact=state.get("contact"),
                product=product if product else None,
                quantity=1,
                message="Lead generated from chatbot"
            )
            response = {"reply": "✅ Thank you! Our team will contact you soon."}
            state.clear()  # reset after saving
        else:
            response = {"reply": "⚠️ Please enter a valid phone number (digits only)."}


    elif any(kw in user_msg for kw in ["interested", "contact me", "buy"]):
        # Try to infer current interest from last cart item or last matched product
        last_cart = request.session.get("cart", [])
        product_interest = state.get("product_interest") or (last_cart[-1] if last_cart else "General")
        state["product_interest"] = product_interest
        state["awaiting"] = "name"
        response = {"reply": "🙋 Sure! Please tell me your name."}

    # ----------------------------------------------------
    # 2) Greeting
    # ----------------------------------------------------
    elif re.search(r"\b(hi|hello)\b", user_msg):
        response = {
            "reply": "Hi 👋 I’m SilverBot! I help you explore our wholesale silver jewelry. "
                     "You can ask for rings, necklaces, bangles, earrings, anklets, or chains."
        }

    # ----------------------------------------------------
    # 3) Price Filter (e.g., 'under 2000', 'below 2k')
    # ----------------------------------------------------
    elif "under" in user_msg or "below" in user_msg:
        price_match = re.search(r"(\d+)", user_msg)
        if price_match:
            price_limit = int(price_match.group(1))

            # Ensure we only check products that have a price
            products = Product.objects.filter(price__isnull=False, price__lte=price_limit)[:5]

            if products.exists():
                reply = f"💎 Here are items under ₹{price_limit}:<br>"
                for p in products:
                    reply += f"- {p.name} (₹{p.price})<br>"
                response = {"reply": reply}
            else:
                if not Product.objects.filter(price__isnull=False).exists():
                    response = {"reply": "❌ I couldn't find any products with prices set yet."}
                else:
                    response = {"reply": f"❌ No items found under ₹{price_limit}."}


    # ----------------------------------------------------
    # 4) Recommendations (best-selling via QuotationRequest stats)
    # ----------------------------------------------------
    elif any(kw in user_msg for kw in ["best", "popular", "recommend"]):
        # Robust approach: aggregate directly from QuotationRequest
        top = (
            QuotationRequest.objects.values("product")
            .annotate(req_count=Count("id"))
            .order_by("-req_count")[:5]
        )
        prod_ids = [row["product"] for row in top if row["product"]]
        id_to_product = {p.id: p for p in Product.objects.filter(id__in=prod_ids)}
        ordered_products = [id_to_product[i] for i in prod_ids if i in id_to_product]

        if ordered_products:
            response = {"reply": format_products_list(ordered_products, "🔥 Our best-selling items:")}
        else:
            # Fallback: show top 5 cheapest as a starting point
            fallback = Product.objects.filter(price__isnull=False).order_by("price")[:5]
            if fallback:
                response = {
                    "reply": "🤔 Not enough sales data yet.<br>"
                             + format_products_list(fallback, "Here are some popular picks:")
                }
            else:
                response = {"reply": "🤔 Not enough data yet, and I couldn't find priced products."}

    # ----------------------------------------------------
    # 5) Category / Product Search
    # ----------------------------------------------------
    else:
        # Try category-style search first (e.g., "rings", "bangles")
        q = build_category_query(user_msg)
        products = Product.objects.filter(q).order_by("price")[:5] if q else []

        if products:
            response = {"reply": format_products_list(products, "🔎 Matching items:")}
            # Store last interest for lead capture convenience
            state["product_interest"] = products[0].name

        else:
            # Fallback: direct name substring match over all products
            matched = None
            for product in Product.objects.all():
                if product.name and product.name.lower() in user_msg:
                    matched = product
                    break

            if matched:
                img_url = matched.image.url if getattr(matched, "image", None) else ""
                price_txt = f"₹{matched.price}" if getattr(matched, "price", None) is not None else "Price NA"
                reply = (
                    f"Our {matched.name} is available. "
                    f"Price: {price_txt}. "
                    f"Description: {matched.description or 'No details'}<br>"
                    f"💬 Type 'add {matched.name.lower()}' to add to cart, or 'I'm interested' for a callback."
                )
                response = {"reply": reply, "img": img_url}
                state["product_interest"] = matched.name
            else:
                # Still nothing
                response = {
                    "reply": "❌ I couldn't find a match. Try a category like 'rings', 'bangles', 'chains', "
                             "or say 'best selling items' / 'under 2000'."
                }

    # ----------------------------------------------------
    # 6) Cart Handling (runs after main intent so quick adds still work)
    # ----------------------------------------------------
    if user_msg.startswith("add"):
        # Support multi-word product names: "add silver ring"
        m = re.search(r"add\s+(.+)$", user_msg)
        product_query = m.group(1).strip() if m else None

        if product_query:
            prod = Product.objects.filter(name__icontains=product_query).first()
        else:
            # Legacy: try second word
            parts = user_msg.split()
            prod = Product.objects.filter(name__icontains=parts[1]).first() if len(parts) > 1 else None

        if prod:
            request.session["cart"].append(prod.name)
            request.session.modified = True
            response = {
                "reply": f"✅ {prod.name} added to your cart!<br>"
                         "💬 Type 'I'm interested' if you’d like us to contact you."
            }
            state["product_interest"] = prod.name
        else:
            response = {"reply": "❌ I couldn't find that product. Try 'rings', 'bangles', etc."}

    elif "cart" in user_msg:
        cart_items = request.session.get("cart", [])
        if cart_items:
            response = {
                "reply": f"🛒 Your Cart: {', '.join(cart_items)}<br>"
                         "💬 Type 'I'm interested' if you’d like us to contact you."
            }
            state["product_interest"] = cart_items[-1]
        else:
            response = {"reply": "🛒 Your cart is empty."}
    
    # --- Reset conversation ---
    if user_msg in ["end", "reset", "restart", "bye"]:
        request.session["chat_state"] = {}
        request.session["cart"] = []
        response = {"reply": "🔄 Conversation ended. You can start a new chat now."}
        return JsonResponse(response)


    # Save updated state back to session
    request.session["chat_state"] = state
    return JsonResponse(response)
