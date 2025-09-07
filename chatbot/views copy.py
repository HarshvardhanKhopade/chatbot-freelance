from django.shortcuts import render
from django.http import JsonResponse

# Sample products (later DB se bhi laa sakte ho)
products = {
    "rings": {
        "name": "Silver Ring",
        "price": "₹500 - ₹1200 (depends on weight)",
        "img": "/static/images/ring.jpg"
    },
    "necklaces": {
        "name": "Silver Necklace",
        "price": "₹2500 - ₹6000",
        "img": "/static/images/necklace.jpg"
    },
    "bangles": {
        "name": "Silver Bangles",
        "price": "₹1500 - ₹4000",
        "img": "/static/images/bangles.jpg"
    },
}


def chatbot_home(request):
    # Ensure cart exists in session
    if "cart" not in request.session:
        request.session["cart"] = []
    return render(request, "chatbot/chatbot.html")


def chatbot_response(request):
    user_msg = request.GET.get("msg", "").lower()
    response = {"reply": "Sorry, I didn’t understand. Type: rings, necklaces, bangles."}

    if "ring" in user_msg:
        response = {
            "reply": f"Our {products['rings']['name']} starts at {products['rings']['price']}",
            "img": products['rings']['img']
        }
    elif "necklace" in user_msg:
        response = {
            "reply": f"Our {products['necklaces']['name']} price: {products['necklaces']['price']}",
            "img": products['necklaces']['img']
        }
    elif "bangle" in user_msg:
        response = {
            "reply": f"Our {products['bangles']['name']} price: {products['bangles']['price']}",
            "img": products['bangles']['img']
        }
    elif "hi" in user_msg or "hello" in user_msg:
        response = {
            "reply": "Hi 👋 I’m SilverBot! I help you explore our wholesale silver jewelry. "
                     "You can ask for rings, necklaces, or bangles."
        }

    # Cart handling
    elif "add" in user_msg:
        # Example: "add ring"
        parts = user_msg.split()
        if len(parts) > 1:
            product_code = parts[1]  # ring, necklace, bangle
            request.session["cart"].append(product_code)
            request.session.modified = True
            response = {"reply": f"✅ {product_code} added to your cart!"}

    elif "cart" in user_msg:
        cart_items = request.session.get("cart", [])
        if cart_items:
            response = {"reply": f"🛒 Your Cart: {', '.join(cart_items)}"}
        else:
            response = {"reply": "🛒 Your cart is empty."}

    return JsonResponse(response)
