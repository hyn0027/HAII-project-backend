from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
import json
from .models import User


@method_decorator(csrf_exempt, name="dispatch")
class SignupView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            bio = data.get("bio", "")

            # Validate required fields
            if not all([username, email, password]):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Username, email, and password are required",
                    },
                    status=400,
                )

            # Check if user already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse(
                    {"success": False, "message": "Username already exists"}, status=400
                )

            if User.objects.filter(email=email).exists():
                return JsonResponse(
                    {"success": False, "message": "Email already exists"}, status=400
                )

            # Create new user
            user = User(
                username=username,
                email=email,
                bio=bio,
            )
            user.set_password(password)
            user.save()

            # Create session
            session = SessionStore()
            session["user_id"] = user.id
            session["username"] = user.username
            session.save()
            print(
                f"Debug: Created session for user {user.username} with key: {session.session_key}"
            )  # Debug log

            response = JsonResponse(
                {
                    "success": True,
                    "message": "User created successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "bio": user.bio,
                    },
                }
            )
            response.set_cookie(
                "sessionid",
                session.session_key,
                httponly=False,
                samesite="None",
                secure=True,
                max_age=1209600,
            )
            return response

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")

            if not all([username, password]):
                return JsonResponse(
                    {"success": False, "message": "Username and password are required"},
                    status=400,
                )

            try:
                user = User.objects.get(username=username, is_active=True)
            except User.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "Invalid username or password"},
                    status=401,
                )

            if not user.check_password(password):
                return JsonResponse(
                    {"success": False, "message": "Invalid username or password"},
                    status=401,
                )

            # Create session
            session = SessionStore()
            session["user_id"] = user.id
            session["username"] = user.username
            session.save()

            response = JsonResponse(
                {
                    "success": True,
                    "message": "Login successful",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "bio": user.bio,
                    },
                }
            )
            response.set_cookie(
                "sessionid",
                session.session_key,
                httponly=False,
                samesite="None",
                secure=True,
                max_age=1209600,
            )
            return response

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(View):
    def post(self, request):
        try:
            session_key = request.COOKIES.get("sessionid")
            if session_key:
                try:
                    session = Session.objects.get(session_key=session_key)
                    session.delete()
                except Session.DoesNotExist:
                    pass

            response = JsonResponse({"success": True, "message": "Logout successful"})
            response.delete_cookie("sessionid")
            return response

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


def get_user_from_session(request):
    """Helper method to get user from session"""
    session_key = request.COOKIES.get("sessionid")
    print(f"Debug: Session key from cookies: {session_key}")  # Debug log
    print(f"Debug: All cookies: {request.COOKIES}")  # Debug log

    if not session_key:
        print("Debug: No session key found in cookies")  # Debug log
        return None

    try:
        session = Session.objects.get(session_key=session_key)
        session_data = session.get_decoded()
        user_id = session_data.get("user_id")
        print(f"Debug: Found session data: {session_data}")  # Debug log
        if user_id:
            user = User.objects.get(id=user_id, is_active=True)
            print(f"Debug: Found user: {user.username}")  # Debug log
            return user
    except (Session.DoesNotExist, User.DoesNotExist) as e:
        print(f"Debug: Session/User lookup failed: {e}")  # Debug log
        pass
    return None


@method_decorator(csrf_exempt, name="dispatch")
class ProfileView(View):

    def get(self, request):
        """Get current user profile"""
        user = get_user_from_session(request)
        if not user:
            return JsonResponse(
                {"success": False, "message": "Not authenticated"}, status=401
            )

        return JsonResponse(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "bio": user.bio,
                },
            }
        )

    def put(self, request):
        """Update user profile"""
        user = get_user_from_session(request)
        if not user:
            return JsonResponse(
                {"success": False, "message": "Not authenticated"}, status=401
            )

        try:
            data = json.loads(request.body)

            # Update allowed fields
            if "email" in data:
                email = data["email"]
                if email != user.email and User.objects.filter(email=email).exists():
                    return JsonResponse(
                        {"success": False, "message": "Email already exists"},
                        status=400,
                    )
                user.email = email

            if "bio" in data:
                user.bio = data["bio"]

            # Handle password change
            if "current_password" in data and "new_password" in data:
                if not user.check_password(data["current_password"]):
                    return JsonResponse(
                        {"success": False, "message": "Current password is incorrect"},
                        status=400,
                    )
                user.set_password(data["new_password"])

            user.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": "Profile updated successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "bio": user.bio,
                    },
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
