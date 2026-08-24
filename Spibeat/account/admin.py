from django.contrib import admin, messages
from .models import Ragistration
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string
import re
import random


# 🔐 SECURE PASSWORD GENERATOR
def generate_password(length=10):
    chars = string.ascii_letters + string.digits 
    return ''.join(secrets.choice(chars) for _ in range(length))


# ✅ CLEAN USERNAME (NO SPACE + SAFE)
def clean_username(username):
    username = username.strip().lower()
    username = username.replace(" ", "")  # remove spaces
    username = re.sub(r'[^a-z0-9]', '', username)  # remove special chars
    return username


# 🔥 UNIQUE USERNAME WITH RANDOM 2-DIGIT
def generate_unique_username(base_username):
    base_username = clean_username(base_username)

    while True:
        random_number = random.randint(10, 99)  # ✅ 2-digit number
        username = f"{base_username}{random_number}"

        if not User.objects.filter(username=username).exists():
            return username


class RagistrationUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'mobile', 'is_approved')
    actions = ['approve_users']

    # ✅ BULK APPROVE
    def approve_users(self, request, queryset):
        success_count = 0

        for obj in queryset:
            if not obj.is_approved:
                created = self.create_user_and_send_email(obj)
                if created:
                    success_count += 1

        if success_count == 0:
            self.message_user(
                request,
                "⚠️ No new users were approved",
                level=messages.WARNING
            )
        else:
            self.message_user(
                request,
                f"✅ {success_count} user(s) approved successfully",
                level=messages.SUCCESS
            )

    approve_users.short_description = "Approve selected users"

    # ✅ AUTO APPROVE ON SAVE
    def save_model(self, request, obj, form, change):
        if obj.is_approved:
            if not User.objects.filter(email=obj.email).exists():
                self.create_user_and_send_email(obj)

        super().save_model(request, obj, form, change)

    # 🔥 MAIN LOGIC
    def create_user_and_send_email(self, obj):
        try:
            # ❌ Avoid duplicate email
            if User.objects.filter(email=obj.email).exists():
                print(f"⚠️ Email already used: {obj.email}")
                return True

            # ✅ CLEAN + UNIQUE USERNAME
            username = generate_unique_username(obj.username)

            # 🔐 PASSWORD
            password = generate_password()

            # 👤 CREATE USER
            user = User.objects.create_user(
                username=username,
                email=obj.email,
                password=password
            )

            print("👤 User created:", user.username)

            # 📩 SEND EMAIL
            send_mail(
                subject="Account Approved 🎉",
                message=f"""
Hello {username},

Your account has been approved successfully!

Username: {username}
Password: {password}

👉 Please login and change your password immediately.

Thanks & Regards,
Celestial Team
                """,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[obj.email],
                fail_silently=False
            )

            print("📩 Email sent")

            # ✅ MARK APPROVED
            obj.is_approved = True
            obj.save()

            return True

        except Exception as e:
            print("❌ Error:", e)
            return False


# ✅ REGISTER ADMIN
admin.site.register(Ragistration, RagistrationUserAdmin)