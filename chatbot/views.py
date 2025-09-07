from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt
from .models import Product, QuotationRequest
import os, yaml, re, json
from difflib import get_close_matches
from twilio.twiml.messaging_response import MessagingResponse


# ---- Load intents.yml ----
intents_path = os.path.join(os.path.dirname(__file__), "intents/intents.yml")
with open(intents_path, "r", encoding="utf-8") as f:
    yaml_data = yaml.safe_load(f)
    INTENTS = yaml_data["intents"]
    CATEGORY_SYNONYMS = yaml_data.get("categories", {})


# --- Detect intent ---
def detect_intent(user_msg):
    user_msg = user_msg.lower()
    
     # custom rules
    if "under" in user_msg or "below" in user_msg:
        return "price_filter"
    if "price for" in user_msg or "cost of" in user_msg:
        return "bulk_orders"
    if "interested" in user_msg:
        return "inquiry"

    # 1. Exact match first
    for intent, phrases in INTENTS.items():
        if user_msg in [p.lower() for p in phrases]:
            return intent

    # 2. Substring match
    for intent, phrases in INTENTS.items():
        sorted_phrases = sorted(phrases, key=len, reverse=True)
        for phrase in sorted_phrases:
            if phrase.lower() in user_msg:
                return intent
    
   

    # 3. Fuzzy match
    for intent, phrases in INTENTS.items():
        if get_close_matches(user_msg, [p.lower() for p in phrases], cutoff=0.75):
            return intent

    return "fallback"


# --- Helpers for category matching ---
def build_category_query(user_msg):
    user_msg = user_msg.lower()
    for key, category in CATEGORY_SYNONYMS.items():
        if key.lower() in user_msg:
            return Q(category__iexact=category)
    return None


def format_products_list(products, header="🔎 Matching items:"):
    reply = header + "<br>"
    for p in products:
        price_txt = f"₹{p.price}" if p.price else "Price NA"
        reply += f"- {p.name} ({price_txt})<br>"
    reply += "<br>💬 Type 'add <product>' to add to cart, or 'I'm interested' to request a callback."
    return reply


# --- Common reply function (for WhatsApp + Web) ---
def chatbot_reply(user_msg, request):
    fake_request = request
    fake_request.GET = {"msg": user_msg}

    json_response = chatbot_response(fake_request)
    response_dict = json.loads(json_response.content.decode("utf-8"))

    return response_dict.get("reply", "❌ Sorry, I didn’t understand.")


# --- WhatsApp Webhook (Twilio) ---
@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "POST":
        user_msg = request.POST.get("Body", "").strip()  # WhatsApp msg
        bot_reply = chatbot_reply(user_msg, request)

        resp = MessagingResponse()
        resp.message(bot_reply)

        return HttpResponse(str(resp), content_type="application/xml")

    return HttpResponse("WhatsApp bot running ✅")


# --- Web chatbot home ---
def chatbot_home(request):
    if "cart" not in request.session:
        request.session["cart"] = []
    if "chat_state" not in request.session:
        request.session["chat_state"] = {}
    return render(request, "chatbot/chatbot.html")


# --- Web chatbot response ---
def chatbot_response(request):
    user_msg = request.GET.get("msg", "").lower()
    state = request.session.get("chat_state", {})

    # Ensure cart exists
    if "cart" not in request.session:
        request.session["cart"] = []

    # If already in inquiry flow, override intent
    if state.get("awaiting") in ["name", "contact"]:
        intent = "inquiry"
    else:
        intent = detect_intent(user_msg)

    response = {"reply": "❌ Sorry, I didn’t understand. Try: rings, necklaces, bangles, earrings, anklets, chains."}

    # --- Greeting ---
    if intent == "greeting":
        response = {"reply": "Hi 👋 I’m SilverBot! Ask me about rings, bangles, necklaces, earrings, chains, anklets."}

    # --- Price filter ---
    elif intent == "price_filter":
        price_match = re.search(r"(\d+)", user_msg)
        if price_match:
            price_limit = int(price_match.group(1))
            products = Product.objects.filter(price__lte=price_limit)[:5]
            if products:
                response = {"reply": format_products_list(products, f"💎 Items under ₹{price_limit}:")}
            else:
                response = {"reply": f"❌ No items found under ₹{price_limit}."}

    # --- Bulk Orders ---
    elif intent == "bulk_orders":
        qty_match = re.search(r"(\d+)", user_msg)
        product_q = build_category_query(user_msg)

        if qty_match and product_q:
            qty = int(qty_match.group(1))
            product = Product.objects.filter(product_q).first()
            if product:
                total_price = product.price * qty
                img_url = product.image.url if getattr(product, "image", None) else ""
                reply = (
                    f"📦 Bulk order quotation:<br>"
                    f"{qty} x {product.name} = ₹{total_price}<br>"
                    f"💬 Type 'I'm interested' to request a callback."
                )
                response = {"reply": reply, "img": img_url}
            else:
                response = {"reply": "❌ Couldn’t find the product for bulk order."}
        else:
            response = {"reply": "ℹ️ Please mention quantity and product, e.g. 'price for 20 rings'."}

    # --- Recommendations ---
    elif intent == "best_sellers":
        popular = (Product.objects
                   .annotate(req_count=Count("quotationrequest"))
                   .order_by("-req_count")[:5])
        if popular:
            response = {"reply": format_products_list(popular, "🔥 Our best selling items:")}
        else:
            response = {"reply": "🤔 Not enough data yet for best sellers."}

    # --- Cart management ---
    elif intent == "cart_management":
        if "add" in user_msg:
            parts = user_msg.split(maxsplit=1)
            if len(parts) > 1:
                product_code = parts[1]
                all_products = list(Product.objects.values_list("name", flat=True))
                match = get_close_matches(product_code.lower(), [p.lower() for p in all_products], n=1, cutoff=0.6)
                prod = Product.objects.filter(name__iexact=match[0]).first() if match else None

                if prod:
                    request.session["cart"].append(prod.name)
                    request.session.modified = True
                    response = {"reply": f"✅ {prod.name} added to your cart!"}
                else:
                    response = {"reply": f"❌ Couldn’t find {product_code} in catalog."}

        elif "show" in user_msg or "view" in user_msg:
            cart = request.session.get("cart", [])
            if cart:
                response = {"reply": "🛒 Your cart: " + ", ".join(cart)}
            else:
                response = {"reply": "🛒 Your cart is empty."}

    # --- Inquiry (Lead capture) ---
       
        elif intent == "inquiry":
            from .models import Lead  

            # force start if fresh
            if not state.get("awaiting"):
                last_cart = request.session.get("cart", [])
                product_interest = last_cart[-1] if last_cart else "General"
                state["product_interest"] = product_interest
                state["awaiting"] = "name"
                response = {"reply": "🙋 Sure! Please tell me your name."}

            elif state.get("awaiting") == "name":
                state["customer_name"] = user_msg
                state["awaiting"] = "contact"
                response = {"reply": "📞 Great! Please share your contact number."}

            elif state.get("awaiting") == "contact":
                if re.match(r"^\d{7,15}$", user_msg):  # phone validate
                    state["contact"] = user_msg
                    state["awaiting"] = "email"
                    response = {"reply": "📧 Thanks! Please share your email address."}
                else:
                    response = {"reply": "⚠️ Please enter a valid phone number (digits only)."}

            elif state.get("awaiting") == "email":
                if re.match(r"^[^@]+@[^@]+\.[^@]+$", user_msg):
                    state["email"] = user_msg
                    product_name = state.get("product_interest", "General Inquiry")
                    product = Product.objects.filter(name__icontains=product_name).first()

                    # Save Lead
                    Lead.objects.create(
                        name=state.get("customer_name"),
                        phone=state.get("contact"),
                        email=state.get("email"),
                        message=f"Inquiry about {product.name if product else 'General'}"
                    )

                    # Save Quotation Request
                    QuotationRequest.objects.create(
                        customer_name=state.get("customer_name"),
                        contact=state.get("contact"),
                        product=product if product else None,
                        quantity=1,
                        message="Lead generated from chatbot"
                    )

                    response = {"reply": "✅ Thank you! Our team will contact you soon."}
                    state.clear()
                else:
                    response = {"reply": "⚠️ Please enter a valid email address."}


    # --- Business Info ---
    elif intent == "business_info":
        if "store" in user_msg or "located" in user_msg:
            response = {"reply": "🏬 Our store is located at: Mumbai, India. We also deliver PAN-India 🌍"}
        elif "catalog" in user_msg:
            response = {"reply": "📖 You can view our full catalog on our website or ask me for specific categories."}
        elif "customize" in user_msg:
            response = {"reply": "🎨 Yes, we do customize silver jewelry on request."}
        elif "gold" in user_msg:
            response = {"reply": "✨ We specialize in silver jewelry only, not gold."}
        else:
            response = {"reply": "ℹ️ We are a silver jewelry manufacturer. Ask me about store, catalog, or customization."}

    # --- Fallback (search products with fuzzy match) ---
    else:
        q = build_category_query(user_msg)
        products = Product.objects.filter(q).order_by("price")[:5] if q else []
        if products:
            response = {"reply": format_products_list(products, "🔎 Matching items:")}
            state["product_interest"] = products[0].name
        else:
            all_products = list(Product.objects.values_list("name", flat=True))
            match = get_close_matches(user_msg, [p.lower() for p in all_products], n=1, cutoff=0.6)
            prod = Product.objects.filter(name__iexact=match[0]).first() if match else None

            if prod:
                price_txt = f"₹{prod.price}" if prod.price else "Price NA"
                img_url = prod.image.url if getattr(prod, "image", None) else ""
                reply = (
                    f"Our {prod.name} is available. "
                    f"Price: {price_txt}. "
                    f"Description: {prod.description or 'No details'}<br>"
                    f"💬 Type 'add {prod.name.lower()}' to add to cart, or 'I'm interested' for a callback."
                )
                response = {"reply": reply, "img": img_url}
                state["product_interest"] = prod.name
            else:
                response = {"reply": "❌ I couldn't find a match. Try a category like 'rings', 'bangles', 'chains', or say 'best selling items' / 'under 2000'."}

    # --- Reset ---
    if user_msg in ["end", "reset", "restart", "bye"]:
        request.session["chat_state"] = {}
        request.session["cart"] = []
        response = {"reply": "🔄 Conversation ended. You can start a new chat now."}
        return JsonResponse(response)

    request.session["chat_state"] = state
    return JsonResponse(response)
