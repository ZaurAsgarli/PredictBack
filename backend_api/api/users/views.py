from rest_framework import status, generics, permissions, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Sum, F, Window
from django.db.models.functions import Rank
from .models import User
from .serializers import UserSerializer, SignUpSerializer, LoginSerializer
from security_engine.models import LoginAttempt, SecurityLog
from security_engine.detectors.logging import get_security_logger


class SignUpView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = SignUpSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    """Parse user agent string to extract browser, OS, and device info"""
    if not user_agent_string:
        return {}
    
    result = {
        'browser': None,
        'os': None,
        'device_type': None,
    }
    
    ua = user_agent_string.lower()
    
    # Detect browser
    if 'chrome' in ua and 'edg' not in ua:
        result['browser'] = 'Chrome'
    elif 'firefox' in ua:
        result['browser'] = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        result['browser'] = 'Safari'
    elif 'edg' in ua:
        result['browser'] = 'Edge'
    elif 'opera' in ua:
        result['browser'] = 'Opera'
    
    # Detect OS
    if 'windows' in ua:
        result['os'] = 'Windows'
    elif 'mac' in ua or 'darwin' in ua:
        result['os'] = 'macOS'
    elif 'linux' in ua:
        result['os'] = 'Linux'
    elif 'android' in ua:
        result['os'] = 'Android'
    elif 'ios' in ua or 'iphone' in ua or 'ipad' in ua:
        result['os'] = 'iOS'
    
    # Detect device type
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        result['device_type'] = 'Mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        result['device_type'] = 'Tablet'
    else:
        result['device_type'] = 'Desktop'
    
    return result


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """User login endpoint with comprehensive attempt tracking"""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Extract request details
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    request_path = request.path
    
    # Parse user agent
    ua_info = parse_user_agent(user_agent)
    
    # Get security logger
    security_logger = get_security_logger()
    
    # Check for recent failed attempts (rate limiting)
    recent_failures = LoginAttempt.count_recent_failures(
        email=email,
        ip_address=ip_address,
        hours=1
    )
    
    # Block if too many failed attempts (5 in last hour)
    MAX_FAILED_ATTEMPTS = 5
    if recent_failures >= MAX_FAILED_ATTEMPTS:
        # Create blocked attempt record
        attempt = LoginAttempt.objects.create(
            email=email,
            success=False,
            status='BLOCKED',
            failure_reason='TOO_MANY_ATTEMPTS',
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            browser=ua_info.get('browser'),
            os=ua_info.get('os'),
            device_type=ua_info.get('device_type'),
            is_suspicious=True,
            risk_score=90.0,
            metadata={
                'recent_failures': recent_failures,
                'blocked': True,
            }
        )
        
        # Log to local files
        security_logger.log_login_attempt(
            email=email,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            reason='TOO_MANY_ATTEMPTS',
            blocked=True,
            recent_failures=recent_failures
        )
        
        # Create security log
        SecurityLog.objects.create(
            ip=ip_address,
            event_type='FAILED_LOGIN',
            severity='HIGH',
            message=f'Login blocked: Too many failed attempts for {email}',
            path=request_path,
        )
        
        return Response(
            {
                'error': 'Too many failed login attempts. Please try again later.',
                'retry_after': 3600  # seconds
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Attempt authentication
    user = authenticate(request, username=email, password=password)
    
    if user is None:
        # Failed login attempt
        failure_reason = 'INVALID_CREDENTIALS'
        
        # Check if account exists
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            failure_reason = 'INVALID_CREDENTIALS'  # Don't reveal if account exists
        
        # Calculate risk score based on recent failures
        risk_score = min(50.0 + (recent_failures * 10), 100.0)
        is_suspicious = recent_failures >= 3
        
        # Create failed attempt record
        attempt = LoginAttempt.objects.create(
            email=email,
            success=False,
            status='FAILED',
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            browser=ua_info.get('browser'),
            os=ua_info.get('os'),
            device_type=ua_info.get('device_type'),
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            metadata={
                'recent_failures': recent_failures + 1,
            }
        )
        
        # Log to local files
        security_logger.log_login_attempt(
            email=email,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=failure_reason,
            recent_failures=recent_failures + 1,
            risk_score=risk_score
        )
        
        # Create security log
        SecurityLog.objects.create(
            ip=ip_address,
            event_type='FAILED_LOGIN',
            severity='HIGH' if is_suspicious else 'MEDIUM',
            message=f'Failed login attempt for {email}',
            path=request_path,
        )
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Successful login
    # Check if this IP/user combination is suspicious
    is_suspicious = False
    risk_score = 0.0
    
    # Check for multiple failed attempts from same IP
    ip_failures = LoginAttempt.count_recent_failures(
        ip_address=ip_address,
        hours=24
    )
    if ip_failures > 10:
        is_suspicious = True
        risk_score = 30.0
    
    # Create successful attempt record
    attempt = LoginAttempt.objects.create(
        email=email,
        success=True,
        status='SUCCESS',
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        request_path=request_path,
        browser=ua_info.get('browser'),
        os=ua_info.get('os'),
        device_type=ua_info.get('device_type'),
        is_suspicious=is_suspicious,
        risk_score=risk_score,
        metadata={
            'user_id': user.id,
            'username': user.username,
        }
    )
    
    # Log to local files
    security_logger.log_login_attempt(
        email=email,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
        user_id=user.id
    )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    """Get or update current user profile with enhanced metrics"""
    user = request.user
    
    # Handle PATCH request to update profile
    if request.method == 'PATCH':
        # Allowed fields to update
        allowed_fields = ['username', 'wallet_address', 'first_name', 'last_name']
        updated_fields = []
        
        for field in allowed_fields:
            if field in request.data:
                new_value = request.data[field]
                
                # Validate wallet_address format
                if field == 'wallet_address' and new_value:
                    if not new_value.startswith('0x') or len(new_value) != 42:
                        return Response(
                            {'error': 'Invalid wallet address format. Must be 0x followed by 40 hex characters.'},
                            status=400
                        )
                    # Check uniqueness
                    if User.objects.filter(wallet_address=new_value).exclude(id=user.id).exists():
                        return Response(
                            {'error': 'This wallet address is already in use.'},
                            status=400
                        )
                
                # Validate username
                if field == 'username' and new_value:
                    if len(new_value) < 3:
                        return Response(
                            {'error': 'Username must be at least 3 characters.'},
                            status=400
                        )
                    # Check uniqueness
                    if User.objects.filter(username=new_value).exclude(id=user.id).exists():
                        return Response(
                            {'error': 'This username is already taken.'},
                            status=400
                        )
                
                setattr(user, field, new_value)
                updated_fields.append(field)
        
        if updated_fields:
            user.save(update_fields=updated_fields)
    
    # Calculate metrics (for both GET and PATCH responses)
    # Total volume
    total_volume = user.trades.aggregate(vol=Sum('amount_staked'))['vol'] or 0.0
    user.total_volume = total_volume
    
    # Identify Rank based on total_points
    rank = User.objects.filter(total_points__gt=user.total_points).count() + 1
    user.rank_global = rank
    
    serializer = UserSerializer(user)
    return Response(serializer.data)



class LeaderboardView(views.APIView):
    """
    Returns top 100 users by Total Points.
    Logic: Total Winnings + Current Positions - Invested is abstracted into 'total_points' for MVP speed,
    but we can extend query if needed.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        top_users = User.objects.order_by('-total_points')[:100]
        
        # We can annotate these too if needed in serializer
        data = []
        for i, u in enumerate(top_users):
            u_data = UserSerializer(u).data
            u_data['rank_global'] = i + 1
            data.append(u_data)
        
        response_data = {
            'leaderboard': data,
            'user_rank': None
        }

        if request.user.is_authenticated:
            # Find user rank
            my_rank = User.objects.filter(total_points__gt=request.user.total_points).count() + 1
            response_data['user_rank'] = {
                'rank': my_rank,
                'total_points': request.user.total_points,
                'username': request.user.username
            }

        return Response(response_data)
