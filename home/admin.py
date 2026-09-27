# pyrefly: ignore-errors
# type: ignore
from decimal import Decimal
from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django.db.models import Sum
from django.forms import TextInput
from django.utils.html import format_html
from .models import (
    Category,
    SubCategory,
    Product,
    Order,
    OrderItem,
    Review,
    CustomerProfile,
    Wishlist,
)


def normalize_price_string(value: Any) -> str | None:
    if value is None:
        return None

    val_str = str(value).strip().replace(' ', '')
    if not val_str:
        return ''

    has_comma = ',' in val_str
    has_dot = '.' in val_str

    if has_comma and has_dot:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif has_comma:
        parts = val_str.split(',')
        if len(parts) > 1 and len(parts[-1]) == 3:
            val_str = ''.join(parts)
        else:
            val_str = val_str.replace(',', '.')

    return val_str


def format_price_for_display(value: Any) -> str:
    if value is None or value == '':
        return ''

    try:
        amount = Decimal(str(value))
    except Exception:
        return str(value)

    return format(amount, ',.2f')


class ProductAdminForm(forms.ModelForm):
    price = forms.CharField(widget=TextInput(attrs={'class': 'vTextField'}))

    class Meta:
        model = Product
        fields = '__all__'

    class Media:
        js = (
            'home/js/admin_price_format.js',
            'home/js/admin_subcategory.js',
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        price = self.initial.get('price')

        if price is None and self.instance and self.instance.pk:
            price = self.instance.price

        if price is not None:
            self.fields['price'].initial = format_price_for_display(price)

        category_id: int | None = None
        if self.data and self.data.get('category'):
            try:
                category_id = int(self.data.get('category'))
            except (ValueError, TypeError):
                pass
        elif self.initial.get('category'):
            cat_val = self.initial.get('category')
            if isinstance(cat_val, int):
                category_id = cat_val
            elif isinstance(cat_val, Category):
                category_id = cat_val.id
            elif isinstance(cat_val, str) and cat_val.isdigit():
                category_id = int(cat_val)
        elif self.instance and getattr(self.instance, 'category_id', None):
            category_id = self.instance.category_id

        if 'subcategory' in self.fields:
            if category_id is not None:
                self.fields['subcategory'].queryset = SubCategory.objects.filter(category_id=category_id)
            else:
                self.fields['subcategory'].queryset = SubCategory.objects.all()

    def clean_price(self) -> Decimal | None:
        price = self.cleaned_data.get('price')

        if isinstance(price, str):
            normalized = normalize_price_string(price)
            if normalized == '':
                return None
            try:
                return Decimal(normalized)
            except Exception:
                raise forms.ValidationError('Enter a valid price.')

        return price


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display: Any = ("id", "name")
    inlines: Any = [SubCategoryInline]


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display: Any = ("id", "name", "category")
    list_filter: Any = ("category",)
    search_fields: Any = ("name", "category__name")
    list_editable: Any = ("category",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    formfield_overrides: Any = {
        models.DecimalField: {
            'widget': TextInput(attrs={'class': 'vTextField'})
        },
    }

    list_display: Any = (
        "id",
        "name",
        "category",
        "subcategory",
        "price",
        "stock",
        "featured",
    )

    list_editable: Any = ("category", "subcategory", "stock")

    list_filter: Any = (
        "category",
        "subcategory",
        "featured",
    )

    search_fields: Any = (
        "name",
        "description",
    )

    list_per_page = 15
    ordering: Any = ("-id",)

    fieldsets: Any = (
        ("Product Details", {
            "fields": ("name", "category", "subcategory", "description", "image", "price", "stock", "featured")
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display: Any = (
        "id",
        "user",
        "total_price",
        "status",
        "created_at",
    )
    list_editable: Any = ("status",)
    list_filter: Any = ("status", "created_at")
    ordering: Any = ("-created_at",)
    readonly_fields: Any = ("created_at",)

    def changelist_view(self, request: Any, extra_context: Any = None) -> Any:
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            total_sales = Order.objects.aggregate(total=Sum("total_price"))["total"] or 0
            order_count = Order.objects.count()
            latest_order = Order.objects.order_by("-created_at").first()
            if hasattr(response, 'context_data') and response.context_data is not None:
                response.context_data["summary"] = {
                    "total_sales": total_sales,
                    "order_count": order_count,
                    "latest_order": latest_order,
                }
        except Exception:
            pass
        return response


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display: Any = (
        "order",
        "product",
        "quantity",
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display: Any = (
        "product",
        "user",
        "rating",
        "created_at",
    )

    list_filter: Any = (
        "rating",
    )


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = "Customer Profile & Contact Info"
    fk_name = "user"


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines: Any = (CustomerProfileInline,)
    list_display: Any = (
        "id",
        "username",
        "email",
        "get_phone_number",
        "get_order_count",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
        "last_login",
    )
    list_filter: Any = ("is_staff", "is_superuser", "is_active", "date_joined")
    search_fields: Any = ("username", "email", "profile__phone_number")
    ordering: Any = ("-id",)

    def get_phone_number(self, obj: Any) -> str:
        if hasattr(obj, "profile") and obj.profile and obj.profile.phone_number:
            return obj.profile.phone_number
        return "-"
    get_phone_number.short_description = "Mobile / Phone"

    def get_order_count(self, obj: Any) -> Any:
        count = obj.order_set.count()
        if count > 0:
            return format_html('<span class="badge badge-info">{} Orders</span>', count)
        return format_html('<span class="badge badge-secondary">{} Orders</span>', count)
    get_order_count.short_description = "Total Orders"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display: Any = (
        "id",
        "user",
        "get_email",
        "phone_number",
        "get_date_joined",
        "get_order_count",
    )
    search_fields: Any = ("user__username", "user__email", "phone_number")
    list_filter: Any = ("user__is_active", "user__date_joined")

    def get_email(self, obj: Any) -> str:
        return obj.user.email
    get_email.short_description = "Email Address"

    def get_date_joined(self, obj: Any) -> str:
        return obj.user.date_joined.strftime("%Y-%m-%d %H:%M") if obj.user.date_joined else "-"
    get_date_joined.short_description = "Date Joined"

    def get_order_count(self, obj: Any) -> str:
        count = obj.user.order_set.count()
        return f"{count} order(s)"
    get_order_count.short_description = "Orders"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display: Any = ("id", "user", "product", "created_at")
    list_filter: Any = ("created_at",)
    search_fields: Any = ("user__username", "product__name")