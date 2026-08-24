from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from .models import Ragistration


def index(request):
    return render(request, "index.html")


# ✅ REGISTER API
@api_view(['POST'])
@permission_classes([AllowAny])
def register_data(request):
    data = request.data
    print("DATA:", data)

    try:
        username = data.get('username')
        email = data.get('email')
        mobile = data.get('mobile')
        institute = data.get('institute')

        # ✅ Validation
        if not username or not email:
            return Response(
                {"error": "Username & Email required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ CHECK EMAIL EXISTS
        if Ragistration.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already exists"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ✅ CREATE USER
        user = Ragistration.objects.create(
            username=username,
            email=email,
            mobile=mobile,
            institude=institute
        )

        # ✅ SEND EMAIL
        subject = "Registration Successful 🎉"
        message = f"""
Hello {username},

Your registration has been completed successfully.

Details:
Username: {username}
Email: {email}

Your account is under admin approval.
You will receive login credentials after approval.

Thanks & Regards,
The Celestial Team
        """

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False
        )

        return Response({
            "message": "Registration successful!"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("ERROR:", e)
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }, status=status.HTTP_200_OK)
class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")

            if not refresh_token:
                return Response(
                    {"error": "Refresh token required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "Logged out successfully"},
                status=status.HTTP_205_RESET_CONTENT
            )

        except Exception:
            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST
            )