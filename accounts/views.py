from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer


# ============================================================
# LOGIN
# ============================================================

@extend_schema(
    request=inline_serializer(
        name='LoginRequest',
        fields={
            'email': serializers.EmailField(),
            'password': serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name='LoginResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description='Email and password are required'
        ),
        401: OpenApiResponse(
            description='Invalid email or password'
        ),
    },
)
@api_view(['POST'])
def login_view(request):

    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {
                'success': False,
                'message': 'Email and password are required.',
                'data': {},
                'errors': {
                    'authentication': 'Email and password are required.'
                },
                'meta': {}
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(email=email, password=password)

    if user is None:
        return Response(
            {
                'success': False,
                'message': 'Invalid email or password.',
                'data': {},
                'errors': {
                    'authentication': 'Invalid email or password.'
                },
                'meta': {}
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            'success': True,
            'message': 'Login successful.',
            'data': {
                'role': user.role.name if user.role else None,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'errors': None,
            'meta': {}
        },
        status=status.HTTP_200_OK
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

@extend_schema(
    request=inline_serializer(
        name='RefreshTokenRequest',
        fields={
            'refresh': serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name='RefreshTokenResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description='Refresh token is required or invalid'
        ),
    },
)
@api_view(['POST'])
def refresh_token_view(request):

    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response(
            {
                'success': False,
                'message': 'Refresh token is required.',
                'data': {},
                'errors': {
                    'refresh': 'Refresh token is required.'
                },
                'meta': {}
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        refresh = RefreshToken(refresh_token)

        return Response(
            {
                'success': True,
                'message': 'Access token refreshed successfully.',
                'data': {
                    'access': str(refresh.access_token)
                },
                'errors': None,
                'meta': {}
            },
            status=status.HTTP_200_OK
        )

    except TokenError:
        return Response(
            {
                'success': False,
                'message': 'Invalid or expired refresh token.',
                'data': {},
                'errors': {
                    'refresh': 'Invalid or expired refresh token.'
                },
                'meta': {}
            },
            status=status.HTTP_400_BAD_REQUEST
        )
# ============================================================
# PROFILE
# ============================================================

@extend_schema(
    request=inline_serializer(
        name='ProfileUpdateRequest',
        fields={
            'current_password': serializers.CharField(required=False),
            'new_password': serializers.CharField(required=False),
        },
    ),
    responses={
        200: inline_serializer(
            name='ProfileResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
    },
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_view(request):

    user = request.user

    # GET PROFILE
    if request.method == 'GET':
        return Response(
            {
                'success': True,
                'message': 'Profile fetched successfully.',
                'data': {
                    'id': user.id,
                    'role': user.role.name if user.role else None,
                },
                'errors': None,
                'meta': {}
            },
            status=status.HTTP_200_OK
        )

    # PATCH PROFILE / CHANGE PASSWORD
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    if not current_password or not new_password:
        return Response(
            {
                'success': False,
                'message': 'Current password and new password are required.',
                'data': {},
                'errors': {
                    'password': 'Current password and new password are required.'
                },
                'meta': {}
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.check_password(current_password):
        return Response(
            {
                'success': False,
                'message': 'Current password is incorrect.',
                'data': {},
                'errors': {
                    'current_password': 'Current password is incorrect.'
                },
                'meta': {}
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(new_password) < 8:
        return Response(
            {
                'success': False,
                'message': 'New password must be at least 8 characters long.',
                'data': {},
                'errors': {
                    'new_password': 'Password must be at least 8 characters long.'
                },
                'meta': {}
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save()

    return Response(
        {
            'success': True,
            'message': 'Password updated successfully.',
            'data': {
                'id': user.id,
                'role': user.role.name if user.role else None,
            },
            'errors': None,
            'meta': {}
        },
        status=status.HTTP_200_OK
    )