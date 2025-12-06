from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .models import User, KeywordExplanationPair


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
                known_keywords=[],
            )
            user.set_password(password)
            user.save()

            # Create session using Django's built-in session framework
            request.session["user_id"] = user.id
            request.session["username"] = user.username
            request.session.save()
            print(
                f"Debug: Created session for user {user.username} with key: {request.session.session_key}"
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
                        "known_keywords": user.known_keywords,
                        "all_keyword_explanation_pairs": [
                            {
                                "id": pair.id,
                                "keyword": pair.keyword,
                                "explanation": pair.explanation,
                                "reason": pair.reason,
                            }
                            for pair in user.get_all_keyword_explanation_pairs()
                        ],
                    },
                }
            )
            response.set_cookie(
                "sessionid",
                request.session.session_key,
                httponly=False,
                samesite="Lax",
                secure=False,
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

            # Create session using Django's built-in session framework
            request.session["user_id"] = user.id
            request.session["username"] = user.username
            request.session.save()

            response = JsonResponse(
                {
                    "success": True,
                    "message": "Login successful",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "bio": user.bio,
                        "known_keywords": user.known_keywords,
                        "all_keyword_explanation_pairs": [
                            {
                                "id": pair.id,
                                "keyword": pair.keyword,
                                "explanation": pair.explanation,
                                "reason": pair.reason,
                            }
                            for pair in user.get_all_keyword_explanation_pairs()
                        ],
                    },
                }
            )
            response.set_cookie(
                "sessionid",
                request.session.session_key,
                httponly=False,
                samesite="Lax",
                secure=False,
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
            # Clear the session using Django's built-in method
            if hasattr(request, "session"):
                request.session.flush()  # This deletes the session and session key
                print(f"Debug: Cleared session for logout")  # Debug log

            response = JsonResponse({"success": True, "message": "Logout successful"})
            response.delete_cookie("sessionid", samesite="Lax", secure=False)
            return response

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


def get_user_from_session(request):
    """Helper method to get user from session"""

    # Use Django's built-in session framework
    user_id = request.session.get("user_id")

    if not user_id:
        print("Debug: No user_id found in session")  # Debug log
        return None

    try:
        user = User.objects.get(id=user_id, is_active=True)
        print(f"Debug: Found user: {user.username}")  # Debug log
        return user
    except User.DoesNotExist as e:
        print(f"Debug: User lookup failed: {e}")  # Debug log
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
                    "known_keywords": user.known_keywords,
                    "all_keyword_explanation_pairs": [
                        {
                            "id": pair.id,
                            "keyword": pair.keyword,
                            "explanation": pair.explanation,
                            "reason": pair.reason,
                        }
                        for pair in user.get_all_keyword_explanation_pairs()
                    ],
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

            if "known_keywords" in data:
                known_keywords = data["known_keywords"]
                if not isinstance(known_keywords, list):
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "known_keywords must be a list",
                        },
                        status=400,
                    )
                processed_keywords = []
                for kw in known_keywords:
                    if not isinstance(kw, str):
                        return JsonResponse(
                            {
                                "success": False,
                                "message": "Each keyword must be a string",
                            },
                            status=400,
                        )
                    processed_kw = kw.strip().lower()
                    if processed_kw:
                        processed_keywords.append(processed_kw)
                user.known_keywords = processed_keywords

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
                        "known_keywords": user.known_keywords,
                        "all_keyword_explanation_pairs": [
                            {
                                "id": pair.id,
                                "keyword": pair.keyword,
                                "explanation": pair.explanation,
                                "reason": pair.reason,
                            }
                            for pair in user.get_all_keyword_explanation_pairs()
                        ],
                    },
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ClearUserKeywordHistoryView(View):
    def post(self, request):
        """Clear KeywordExplanationPair history given by the user"""
        user = get_user_from_session(request)
        if not user:
            return JsonResponse(
                {"success": False, "message": "Not authenticated"}, status=401
            )
        try:
            if json.loads(request.body).get("clear_all", False):
                KeywordExplanationPair.objects.filter(user=user).delete()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "All Keyword history cleared successfully",
                    }
                )
            else:
                requested_keywords = json.loads(request.body).get("keywords", [])
                if not isinstance(requested_keywords, list):
                    return JsonResponse(
                        {"success": False, "message": "keywords must be a list"},
                        status=400,
                    )
                for word in requested_keywords:
                    KeywordExplanationPair.objects.filter(
                        user=user, keyword__iexact=word
                    ).delete()
                return JsonResponse(
                    {"success": True, "message": "Keyword history cleared successfully"}
                )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
