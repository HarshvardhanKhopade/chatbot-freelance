from django.contrib import admin
from .models import Product, QuotationRequest, Lead

# --- Product Admin ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "best_seller")  # columns jo dikhenge
    list_filter = ("category", "best_seller")  # sidebar filter
    search_fields = ("name", "description", "category")  # search option
    list_editable = ("price", "best_seller")  # direct edit from list view
    ordering = ("id",)  # Default ordering
    list_per_page = 20  # Pagination

# --- Quotation Request Admin ---
@admin.register(QuotationRequest)
class QuotationRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "contact", "product", "quantity", "created_at")
    list_filter = ("created_at", "product")
    search_fields = ("customer_name", "contact", "message")
    ordering = ("-created_at",)
    list_per_page = 20

# --- Lead Admin ---
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email")
    list_filter = ("created_at",)
