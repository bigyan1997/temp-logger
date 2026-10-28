from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import ChangePasswordSerializer, LoginSerializer, UserSerializer


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


class CsrfView(APIView):
    """Sets the CSRF cookie so the frontend can send it back on later requests."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'code': 'invalid_credentials', 'message': 'Wrong username or password.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'code': 'wrong_password', 'message': 'Current password is not correct.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(serializer.validated_data['new_password'], user)
        except ValidationError as exc:
            return Response(
                {'code': 'weak_password', 'message': ' '.join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        update_session_auth_hash(request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)
