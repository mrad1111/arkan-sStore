from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.validators import RegexValidator

from .models import Review



class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg ps-5",
                "placeholder": "Username or Email",
                "autocomplete": "username",
                "id": "usernameInput",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg ps-5 pe-5",
                "placeholder": "Password",
                "autocomplete": "current-password",
                "id": "passwordInput",
            }
        )
    )



class RegisterForm(forms.ModelForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg ps-5",
                "placeholder": "Choose a username",
                "autocomplete": "username",
            }
        )
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg ps-5",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }
        )
    )
    phone_number = forms.CharField(
        max_length=10,
        min_length=10,
        validators=[RegexValidator(r"^\d{10}$", "Enter exactly 10 digits.")],
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg ps-5",
                "placeholder": "10-digit mobile number",
                "autocomplete": "tel",
                "inputmode": "numeric",
                "pattern": "[0-9]{10}",
                "oninput": "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10)",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg ps-5",
                "placeholder": "Create a strong password",
                "autocomplete": "new-password",
            }
        )
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone_number",
            "password",
        ]

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number", "")
        if not phone_number.isdigit() or len(phone_number) != 10:
            raise forms.ValidationError("Enter exactly 10 digits.")
        return phone_number



class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Your full name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com"}))
    phone = forms.CharField(
        max_length=10,
        min_length=10,
        validators=[RegexValidator(r"^\d{10}$", "Enter a valid 10-digit phone number.")],
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "10-digit phone number",
                "type": "tel",
                "inputmode": "numeric",
                "pattern": "[0-9]{10}",
                "autocomplete": "tel",
                "data-numeric-only": "true",
            }
        ),
    )
    address = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Street address"}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}))
    payment_method = forms.ChoiceField(
        choices=[("cod", "Cash on Delivery")],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    coupon_code = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter coupon code"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Any delivery notes?"}))


class ContactForm(forms.Form):
    full_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Your full name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com"}))
    subject = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Subject"}))
    message = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Your message"}))


class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review
        fields = [
            "rating",
            "comment",
        ]

        widgets = {
            "rating": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 5,
                }
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Write your review...",
                }
            ),
        }


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg ps-5",
                "placeholder": "name@example.com",
                "autocomplete": "email",
                "id": "emailInput",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Please enter a valid email address.")
        
        users = User.objects.filter(email__iexact=email, is_active=True)
        if not users.exists():
            raise forms.ValidationError("No registered account found with this email address. Please check your email ID or create a new account.")
            
        return email


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg ps-5 pe-5",
                "placeholder": "Enter new password",
                "autocomplete": "new-password",
                "id": "newPasswordInput",
            }
        ),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg ps-5 pe-5",
                "placeholder": "Confirm new password",
                "autocomplete": "new-password",
                "id": "confirmPasswordInput",
            }
        ),
    )