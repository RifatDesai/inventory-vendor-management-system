from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers


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
                'message': serializers.CharField(),
                'access': serializers.CharField(),
                'refresh': serializers.CharField(),
            },
        ),
        400: OpenApiResponse(description='Email and password are required'),
        401: OpenApiResponse(description='Invalid email or password'),
    },
)
@api_view(['POST'])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(email=email, password=password)

    if user is None:
        return Response(
            {'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Login successful',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    })