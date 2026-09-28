import os
import random
import time
from decimal import Decimal
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings



from .models import Product, Category, SubCategory, Order, OrderItem, Review , Wishlist, CustomerProfile
from .forms import RegisterForm, ReviewForm, LoginForm, CheckoutForm, ContactForm



def index(request):
    return render(request, "index.html")


def home(request):

    categories = Category.objects.prefetch_related("subcategories").all()
    products = Product.objects.select_related("category", "subcategory").all()

    category_id = request.GET.get("category")
    subcategory_id = request.GET.get("subcategory")
    search = request.GET.get("search")

    selected_category = None
    selected_subcategory = None
    subcategories = []

    if category_id:
        try:
            cat_id = int(category_id)
            products = products.filter(category_id=cat_id)
            selected_category = categories.filter(id=cat_id).first()
            if selected_category:
                subcategories = list(selected_category.subcategories.all())
        except ValueError:
            pass

    if subcategory_id:
        try:
            subcat_id = int(subcategory_id)
            products = products.filter(subcategory_id=subcat_id)
            selected_subcategory = SubCategory.objects.filter(id=subcat_id).first()
            if selected_subcategory and not selected_category:
                selected_category = selected_subcategory.category
                subcategories = list(selected_category.subcategories.all())
        except ValueError:
            pass

    if search:
        products = products.filter(name__icontains=search)

    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        wishlist_product_ids = set()

    return render(
        request,
        "home.html",
        {
            "products": products,
            "categories": categories,
            "subcategories": subcategories,
            "selected_category": selected_category,
            "selected_subcategory": selected_subcategory,
            "search": search,
            "cart_count": cart_count,
            "wishlist_product_ids": wishlist_product_ids,
        },
    )


def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            CustomerProfile.objects.update_or_create(
                user=user,
                defaults={"phone_number": form.cleaned_data["phone_number"]},
            )

            login(request, user)

            return redirect("home")

    else:
        form = RegisterForm()

    return render(
        request,
        "register.html",
        {
            "form": form,
        },
    )


def user_login(request):

    if request.user.is_authenticated:
        return redirect("home")

    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST":

        if form.is_valid():

            login(request, form.get_user())

            return redirect("home")

    return render(
        request,
        "login.html",
        {
            "form": form,
        },
    )


def user_logout(request):

    logout(request)

    return redirect("home")


@login_required
def profile(request):

    categories = Category.objects.all()
    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    CustomerProfile.objects.get_or_create(user=request.user)
    total_orders = Order.objects.filter(user=request.user).count()
    recent_orders = Order.objects.filter(user=request.user).order_by("-created_at")[:3]
    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return render(
        request,
        "profile.html",
        {
            "categories": categories,
            "cart_count": cart_count,
            "customer": request.user,
            "total_orders": total_orders,
            "recent_orders": recent_orders,
            "wishlist_count": wishlist_count,
        },
    )


@login_required
def add_to_cart(request, product_id):

    cart = request.session.get("cart", {})

    cart[str(product_id)] = cart.get(str(product_id), 0) + 1

    request.session["cart"] = cart

    return redirect("cart")


@login_required
def order_now(request, product_id):

    product = get_object_or_404(Product, id=product_id)
    if product.stock <= 0:
        return redirect("product_detail", product_id=product.id)

    request.session["cart"] = {str(product_id): 1}

    return redirect("checkout")

def increase_quantity(request, product_id):

    cart = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id in cart:
        cart[product_id] += 1

    request.session["cart"] = cart

    return redirect("cart")

def decrease_quantity(request, product_id):

    cart = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id in cart:

        if cart[product_id] > 1:
            cart[product_id] -= 1
        else:
            del cart[product_id]

    request.session["cart"] = cart

    return redirect("cart")

def remove_from_cart(request, product_id):

    cart = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session["cart"] = cart

    return redirect("cart")


def cart(request):

    cart = request.session.get("cart", {})

    products = []
    total = 0

    for product_id, quantity in cart.items():

        product = get_object_or_404(Product, id=product_id)

        subtotal = product.price * quantity
        total += subtotal

        products.append(
            {
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )

    cart_count = sum(cart.values())

    # Order Summary
    shipping = 0
    discount = 0
    grand_total = total + shipping - discount

    return render(
        request,
        "cart.html",
        {
            "products": products,
            "total": total,
            "cart_count": cart_count,
            "shipping": shipping,
            "discount": discount,
            "grand_total": grand_total,
        },
    )


@login_required
def add_to_wishlist(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    # Toggle wishlist: if exists, remove; otherwise add.
    existing = Wishlist.objects.filter(user=request.user, product=product).first()

    if existing:
        existing.delete()
    else:
        Wishlist.objects.create(user=request.user, product=product)

    # Redirect back to product detail
    return redirect("product_detail", product_id=product.id)

def wishlist(request):

    wishlist_items = Wishlist.objects.filter(
        user=request.user
    )

    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    return render(
        request,
        "wishlist.html",
        {
            "wishlist_items": wishlist_items,
            "cart_count": cart_count,
        },
    )

@login_required
def orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())
    return render(request, "orders.html", {"orders": orders, "cart_count": cart_count})

@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart")

    products = []
    subtotal = Decimal("0")
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        line_total = product.price * quantity
        subtotal += line_total
        products.append({"product": product, "quantity": quantity, "subtotal": line_total})

    shipping = Decimal("0") if subtotal >= Decimal("2000") else Decimal("99")
    discount = Decimal("0")
    coupon_code = ""
    form = CheckoutForm()

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            coupon_code = form.cleaned_data["coupon_code"].strip().upper()
            if coupon_code == "SAVE10":
                discount = subtotal * Decimal("0.10")
            elif coupon_code == "WELCOME20":
                discount = Decimal("200")
            elif coupon_code:
                form.add_error("coupon_code", "Invalid coupon code")
            if not form.errors:
                grand_total = subtotal + shipping - discount
                order = Order.objects.create(user=request.user, total_price=grand_total)
                for item in products:
                    OrderItem.objects.create(order=order, product=item["product"], quantity=item["quantity"])
                request.session.pop("cart", None)
                return render(request, "order_success.html", {"order": order})

    if request.method == "GET" and request.GET.get("coupon"):
        coupon_code = request.GET["coupon"].strip().upper()
        if coupon_code == "SAVE10":
            discount = subtotal * Decimal("0.10")
        elif coupon_code == "WELCOME20":
            discount = Decimal("200")

    grand_total = subtotal + shipping - discount
    categories = Category.objects.all()
    cart_count = sum(cart.values())

    return render(
        request,
        "checkout.html",
        {
            "form": form,
            "products": products,
            "subtotal": subtotal,
            "shipping": shipping,
            "discount": discount,
            "grand_total": grand_total,
            #"coupon_code": coupon_code,
            "cart_count": cart_count,
            "categories": categories,
        },
    )


def product_detail(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    related_products = Product.objects.exclude(
        id=product.id
    )[:4]

    reviews = Review.objects.filter(product=product)

    form = ReviewForm()

    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        wishlist_product_ids = set()

    return render(
        request,
        "product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "reviews": reviews,
            "form": form,
            "cart_count": cart_count,
            "wishlist_product_ids": wishlist_product_ids,
        },
    )


def category_products(request, category_id):

    categories = Category.objects.prefetch_related("subcategories").all()
    selected_category = get_object_or_404(Category, id=category_id)
    subcategories = list(selected_category.subcategories.all())
    products = Product.objects.filter(category=selected_category).select_related("category", "subcategory")

    subcategory_id = request.GET.get("subcategory")
    selected_subcategory = None
    if subcategory_id:
        try:
            subcat_id = int(subcategory_id)
            products = products.filter(subcategory_id=subcat_id)
            selected_subcategory = SubCategory.objects.filter(id=subcat_id).first()
        except ValueError:
            pass

    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        wishlist_product_ids = set()

    return render(
        request,
        "products.html",
        {
            "products": products,
            "categories": categories,
            "subcategories": subcategories,
            "selected_category": selected_category,
            "selected_subcategory": selected_subcategory,
            "cart_count": cart_count,
            "search": "",
            "wishlist_product_ids": wishlist_product_ids,
            "is_category_page": True,
        },
    )


def subcategory_products(request, subcategory_id):

    categories = Category.objects.prefetch_related("subcategories").all()
    selected_subcategory = get_object_or_404(SubCategory.objects.select_related("category"), id=subcategory_id)
    selected_category = selected_subcategory.category
    subcategories = list(selected_category.subcategories.all())
    products = Product.objects.filter(subcategory=selected_subcategory).select_related("category", "subcategory")

    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        wishlist_product_ids = set()

    return render(
        request,
        "products.html",
        {
            "products": products,
            "categories": categories,
            "subcategories": subcategories,
            "selected_category": selected_category,
            "selected_subcategory": selected_subcategory,
            "cart_count": cart_count,
            "search": "",
            "wishlist_product_ids": wishlist_product_ids,
            "is_category_page": True,
        },
    )


def get_subcategories_api(request):

    category_id = request.GET.get("category_id")
    if category_id:
        subs = SubCategory.objects.filter(category_id=category_id).values("id", "name")
    else:
        subs = SubCategory.objects.values("id", "name", "category_id")
    return JsonResponse({"subcategories": list(subs)})


def about(request):

    categories = Category.objects.all()
    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())

    return render(
        request,
        "about.html",
        {
            "categories": categories,
            "cart_count": cart_count,
        },
    )


def contact(request):

    categories = Category.objects.all()
    cart = request.session.get("cart", {})
    cart_count = sum(cart.values())
    success_message = ""

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            success_message = "Thank you! Your message has been received. We will reply shortly."
            form = ContactForm()
    else:
        form = ContactForm()

    return render(
        request,
        "contact.html",
        {
            "categories": categories,
            "cart_count": cart_count,
            "form": form,
            "success_message": success_message,
        },
    )


def send_otp_api(request):
    """Generates a 6-digit OTP and emails it to the user's Gmail address."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        if not email:
            return JsonResponse({"success": False, "message": "Please enter a valid email address."})

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return JsonResponse({"success": False, "message": "No registered account found with this email address."})

        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))

        # Store in session with timestamp
        request.session["reset_otp"] = otp
        request.session["reset_email"] = email
        request.session["reset_otp_time"] = time.time()

        subject = "ARKAN'S Store — Password Reset OTP"
        message = (
            f"Hello {user.get_full_name() or user.username},\n\n"
            f"Your One-Time Password (OTP) to reset your password on ARKAN'S Store is:\n\n"
            f"  {otp}\n\n"
            f"This OTP is valid for 10 minutes. If you did not request a password reset, please ignore this email.\n\n"
            f"Best regards,\n"
            f"ARKAN'S Store Team"
        )

        # Dynamically ensure latest .env credentials are in settings (handles server running state)
        if load_dotenv:
            env_file = settings.BASE_DIR / '.env'
            if env_file.exists():
                load_dotenv(env_file, override=True)
                settings.EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', settings.EMAIL_HOST_USER)
                pwd = os.environ.get('EMAIL_HOST_PASSWORD', '').replace(' ', '')
                if pwd:
                    settings.EMAIL_HOST_PASSWORD = pwd
                settings.DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return JsonResponse({
                "success": True,
                "message": f"OTP sent successfully to {email}! Please check your Gmail inbox or spam folder."
            })
        except Exception as e:
            print(f"\n=======================================================")
            print(f"=== EMAIL OTP FOR {email}: {otp} ===")
            print(f"=== SMTP ERROR: {e} ===")
            print(f"=======================================================\n")

            error_str = str(e)
            if "BadCredentials" in error_str or "535" in error_str:
                err_msg = f"Failed to send email to {email}. Invalid Gmail App Password or Bad Credentials (535)."
            else:
                err_msg = f"Failed to send email to {email}. Error: {error_str}"

            return JsonResponse({
                "success": False,
                "message": err_msg
            })


    return JsonResponse({"success": False, "message": "Invalid request method."})


def verify_otp_and_reset_password_api(request):
    """Verifies the submitted OTP and resets the user password."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        otp_submitted = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        session_email = request.session.get("reset_email")
        session_otp = request.session.get("reset_otp")
        session_otp_time = request.session.get("reset_otp_time", 0)

        if not session_otp or not session_email or session_email.lower() != email.lower():
            return JsonResponse({"success": False, "message": "No active OTP request found for this email. Please click 'Send OTP' first."})

        # Check OTP expiration (10 minutes = 600 seconds)
        if time.time() - session_otp_time > 600:
            return JsonResponse({"success": False, "message": "OTP has expired (valid for 10 minutes). Please click 'Send OTP' again."})

        if otp_submitted != session_otp:
            return JsonResponse({"success": False, "message": "Invalid OTP code. Please check your email and enter the correct OTP."})

        if not new_password:
            return JsonResponse({"success": False, "message": "Please enter a new password."})

        if len(new_password) < 6:
            return JsonResponse({"success": False, "message": "Password must be at least 6 characters long."})

        if new_password != confirm_password:
            return JsonResponse({"success": False, "message": "New passwords do not match. Please try again."})

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return JsonResponse({"success": False, "message": "Account not found."})

        # Reset password
        user.set_password(new_password)
        user.save()

        # Clear session OTP data
        request.session.pop("reset_otp", None)
        request.session.pop("reset_email", None)
        request.session.pop("reset_otp_time", None)

        return JsonResponse({
            "success": True,
            "message": "Password changed successfully! You can now log in with your new password.",
            "email": email,
            "username": user.username
        })

    return JsonResponse({"success": False, "message": "Invalid request method."})

