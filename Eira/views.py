
from http.client import HTTPResponse
from django.shortcuts import render,redirect,HttpResponse
from django.contrib import messages
from .import models
from django.core.mail import send_mail
import base64,io,json,cv2,requests,random
from datetime import timedelta, datetime as dt
import numpy as np
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from deepface import DeepFace
from PIL import Image
from django.utils import timezone
from .models import EmotionLog, ChatHistory
from django.db.models import Count
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import PasswordResetOTP, Register
from functools import wraps
from django.shortcuts import redirect
from .models import Register


def session_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get("user_id")
        if not user_id:
            return redirect("/login/?next=" + request.path)
        try:
            request.user = Register.objects.get(id=user_id)  # assign user to request
        except Register.DoesNotExist:
            request.session.flush()
            return redirect("/login/")
        return view_func(request, *args, **kwargs)
    return wrapper


def index(request):
    return render(request,'index.html')

def register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        gender = request.POST.get("gender")
        password = request.POST.get("password")
        location = request.POST.get("location")

        if models.Register.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("register")

        user = models.Register.objects.create(
            name=name,
            email=email,
            gender=gender,
            password=password,
            location=location,
            email_verified=False
        )

        request.session["email"] = email

        # Send OTP
        send_verification_code(request, user)

        messages.success(request, "OTP sent to your email. Please verify!")
        return redirect("verify_email")

    return render(request, "register.html")

def login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            # Check if user with this email exists
            user = models.Register.objects.get(email=email)

            # Check password separately
            if user.password != password:
                messages.error(request, "Incorrect password!")
                return redirect("login")

            # Block if email not verified
            if not user.email_verified:
                messages.error(request, "Please verify your email first!")
                request.session["email"] = user.email
                return redirect("verify_email")

            request.session["user_id"] = user.id
            return redirect("home")

        except models.Register.DoesNotExist:
            messages.error(request, "User not found!")
            return redirect("login")

    return render(request, "login.html")

@session_login_required
def home(request):
    return render(request,'home.html')


@session_login_required
def Profile(request):

    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('/login/')

    client = Register.objects.filter(id=user_id).first()

    if not client:
        return redirect('/login/')

    # get latest emotion
    last_emotion_log = EmotionLog.objects.filter(user_id=client.id).order_by('-timestamp').first()

    if last_emotion_log:
        raw_emotion = last_emotion_log.emotion.strip().lower()
    else:
        raw_emotion = "normal"

    emotion_mapping = {
        "happy": "normal",
        "excited": "normal",
        "neutral": "normal",
        "normal": "normal",
        "sad": "depressed",
        "depressed": "depressed",
        "angry": "stress",
        "fear": "anxiety",
        "surprise": "anxiety",
        "anxious": "anxiety",
        "stress": "stress",
    }

    mapped_emotion = emotion_mapping.get(raw_emotion, "normal")

    emotion_quotes = {
        "normal": "Keep shining, happiness looks great on you! 🌞",
        "depressed": "Even storms pass, brighter days are ahead. 🌈",
        "stress": "Take a deep breath; calm is strength. 🌿",
        "anxiety": "Focus on one step at a time, you've got this. 💪",
    }

    suggestions = {
        "normal": "Try a short breathing exercise today.",
        "depressed": "Consider talking with a friend or family member.",
        "stress": "Take a short break and relax your mind.",
        "anxiety": "Focus on slow breathing for a few minutes."
    }

    context = {
        'c': client,
        'last_emotion': mapped_emotion.capitalize(),
        'quote': emotion_quotes.get(mapped_emotion),
        'suggestion': suggestions.get(mapped_emotion)
    }

    return render(request, 'profile.html', context)

@session_login_required
def editprofile(request):
    client = request.user  # Already a Register instance

    if request.method == 'POST':
        client.name = request.POST.get('name')
        client.email = request.POST.get('email')
        client.location = request.POST.get('location')
        client.gender = request.POST.get('gender')

        # Update password if provided
        if request.POST.get('password'):
            client.password = request.POST.get('password')

        # Update image if uploaded
        if request.FILES.get('image'):
            # Delete old image if exists
            if client.image:
                client.image.delete(save=False)
            client.image = request.FILES['image']

        # Handle remove image
        if request.POST.get('remove_image') == '1':
            if client.image:
                client.image.delete(save=False)  # remove from storage
            client.image = None  # clear field in DB

        client.save()
        return redirect('profile')

    return render(request, 'editprofile.html', {'c': client})


def logout(request):
  request.session.flush()
  return redirect('index')


def adminlogin(request):
  if request.method=='POST':
    username=request.POST.get('username')
    password=request.POST.get('password')
    ausername="admin"
    apassword="admin"
    try:
      request.session['ausername']=ausername
      if ausername==username:
        if apassword==password: 
          return redirect('adminhome')
        else:
          return HttpResponse('invalid password')
      else:
        return HttpResponse('invalid username')
    except:
      return HttpResponse('admin does not exist')
  else:
     return render(request,'adminlogin.html')


def adminhome(request):
  if 'ausername' not in request.session:
    return redirect('adminlogin')

  from .models import Register, EmotionLog

  total_users  = Register.objects.count()
  total_scans  = EmotionLog.objects.count()

  recent = EmotionLog.objects.select_related('user').order_by('-timestamp')[:10]

  # counts per mental state
  normal     = EmotionLog.objects.filter(emotion__iexact="normal").count()
  stress     = EmotionLog.objects.filter(emotion__iexact="stress").count()
  anxiety    = EmotionLog.objects.filter(emotion__iexact="anxiety").count()
  depression = EmotionLog.objects.filter(emotion__iexact="depression").count() + \
               EmotionLog.objects.filter(emotion__iexact="depressed").count()

  total_emotions = normal + stress + anxiety + depression or 1  # avoid div/0

  context = {
      'total_users':  total_users,
      'total_scans':  total_scans,
      'recent':       recent,
      'normal':       normal,
      'stress':       stress,
      'anxiety':      anxiety,
      'depression':   depression,
      'total_emotions': total_emotions,
  }

  return render(request, 'adminhome.html', context)


def userlist(request):
  users=models.Register.objects.all()
  return render(request,'userlist.html',{'users':users})

  
def deleteuser(request,id):
  users=models.Register.objects.get(id=id)
  users.delete()
  return redirect('userlist')




def get_chat_history(email, limit=10):
    chats = ChatHistory.objects.filter(user__email=email).order_by('-created_at')[:limit]

    history = []
    for chat in reversed(chats):
        history.append({
            "role": chat.role,
            "content": chat.message
        })

    return history



def analyze_sentiment(text):
    text = text.lower()

    if any(word in text for word in ["sad", "depressed", "tired", "lonely"]):
        return "negative"
    elif any(word in text for word in ["happy", "good", "great"]):
        return "positive"
    else:
        return "neutral"
    

    
def chatbot(request):
    # chatbot/ page is a legacy route; the main AI chat runs via /chat/
    if request.method == "GET":
        return render(request, "chatbot.html")
    return JsonResponse({"response": "Use /chat/ endpoint for AI replies."}, status=405)


@session_login_required
def feedback(request):
    client = request.user  # Register instance from session_login_required

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            models.feedback.objects.create(
                user=client.name,
                message=message
            )
            messages.success(request, "Thank you! Your feedback has been submitted ❤️")
        return redirect('home')

    return render(request, 'feedback.html', {'client': client})


def feedbacklist(request):
  users=models.feedback.objects.all()
  return render(request,'feedbacklist.html',{'users':users})


def deletefeedback(request,id):
  users=models.feedback.objects.get(id=id)
  users.delete()
  return redirect('feedbacklist')


@session_login_required
@csrf_exempt
def chat(request):
    """Chat endpoint: combines facial and text emotion for empathetic responses."""
    if request.method != 'POST':
        return JsonResponse({'response': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_message = data.get('message', '')
        facial_emotion = data.get('emotion', '-')
        source = data.get('source', 'text')
        frontend_history = data.get('history', [])  # history from frontend

        # 1️⃣ Text sentiment classification
        sentiment_payload = {
            "model": getattr(settings, "GROQ_MODEL2"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a mental health sentiment classifier. "
                        "Classify the user's text into ONLY one of these labels: "
                        "normal, stress, anxiety, depressed. "
                        "Return only the label."
                    )
                },
                {"role": "user", "content": user_message}
            ],
            "temperature": 0,
            "max_tokens": 5
        }

        headers = {
            "Authorization": f"Bearer {getattr(settings, 'GROQ_API_KEY2')}",
            "Content-Type": "application/json"
        }

        sentiment_resp = requests.post(
            getattr(settings, "GROQ_API_URL2"),
            headers=headers,
            json=sentiment_payload,
            timeout=30
        )
        sentiment_resp.raise_for_status()
        predicted_sentiment = sentiment_resp.json()["choices"][0]["message"]["content"].strip().lower()

        if predicted_sentiment not in ["normal", "stress", "anxiety", "depressed"]:
            if "depress" in predicted_sentiment or "sad" in predicted_sentiment:
                predicted_sentiment = "depressed"
            elif "anx" in predicted_sentiment or "worried" in predicted_sentiment:
                predicted_sentiment = "anxiety"
            elif "stress" in predicted_sentiment or "overwhelmed" in predicted_sentiment:
                predicted_sentiment = "stress"
            else:
                predicted_sentiment = "normal"

        text_emotion = predicted_sentiment

        # 2️⃣ Dominant emotion
        dominant_emotion = facial_emotion if facial_emotion != "-" else text_emotion

        # Safely extract mode string — handles string, dict, empty dict
        if isinstance(source, dict):
            _mode = source.get("type", "text")
        else:
            _mode = str(source)
        if not isinstance(_mode, str) or not _mode.strip():
            _mode = "text"
        _mode = _mode.lower().strip().capitalize()
        EmotionLog.objects.create(
            user=request.user,
            emotion=dominant_emotion,
            mode=_mode  # Text / Voice / Camera
        )

        # 3️⃣ Save user message to DB
        ChatHistory.objects.create(
            user=request.user,
            role="user",
            message=user_message,
            emotion=dominant_emotion,
            sentiment=text_emotion
        )

        # 4️⃣ Build conversation: system prompt + history + current message
        # Emotion adjusts TONE only — never appears as text in the reply
        emotion_guidance = ""
        if dominant_emotion and dominant_emotion != "-":
            tone_map = {
                "stress":    "The user seems stressed. Respond calmly and reassuringly.",
                "anxiety":   "The user seems anxious. Be gentle, grounding, and steady.",
                "depressed": "The user seems low or sad. Be warm, compassionate, and supportive.",
                "normal":    "The user seems okay. Keep the conversation positive and helpful.",
            }
            emotion_guidance = tone_map.get(dominant_emotion.lower(),
                f"The user's emotional state is {dominant_emotion}. Respond empathetically."
            ) + " "

        system_instruction = (
            emotion_guidance +
            "You are a helpful AI mental health assistant. "
            "Respond naturally in plain conversational English. "
            "Do NOT state or repeat the user's emotion label inside your reply. "
            "Do NOT add bracketed notes or analytical summaries. "
            "Remember the conversation context and answer based on previous messages."
        )

        # Use frontend history (already has full session context)
        conversation = [{"role": "system", "content": system_instruction}]
        for h in frontend_history[-10:]:  # last 10 exchanges to stay within token limits
            conversation.append({"role": h["role"], "content": h["content"]})
        conversation.append({"role": "user", "content": user_message})

        # 5️⃣ Call Groq for reply
        chat_payload = {
            "model": getattr(settings, "GROQ_MODEL2"),
            "messages": conversation,
            "temperature": 0.2,
            "max_tokens": 1024
        }

        chat_resp = requests.post(
            getattr(settings, "GROQ_API_URL2"),
            headers=headers,
            json=chat_payload,
            timeout=60
        )
        chat_resp.raise_for_status()
        reply = chat_resp.json()["choices"][0]["message"]["content"].strip()

        # 6️⃣ Save bot reply to DB
        ChatHistory.objects.create(
            user=request.user,
            role="assistant",
            message=reply,
            emotion=dominant_emotion
        )

        return JsonResponse({
            "response": reply,
            "text_emotion": text_emotion,
            "facial_emotion": facial_emotion,
            "dominant_emotion": dominant_emotion,
            "source": source
        })

    except Exception as e:
        return JsonResponse({"response": f"Error: {str(e)}"})

# ==========================================
# 🚀 OPTIMIZATION: PRE-LOAD HIGH-ACCURACY MODEL
# ==========================================
print("[INFO] Loading Accurate AI Model... Please wait...")
try:
    # We use 'ssd' or 'mtcnn' here for better accuracy than 'opencv'
    dummy_img = np.zeros((48, 48, 3), dtype=np.uint8)
    DeepFace.analyze(
        img_path=dummy_img,
        actions=['emotion'],
        enforce_detection=False,
        detector_backend='ssd'  # 'ssd' is much more accurate than 'opencv'
    )
    print("[OK] High-Accuracy Model Loaded!")
except Exception as e:
    print(f"[WARN] Model pre-loading failed: {e}")


@session_login_required
def camera(request):
    """Renders the 30-second scan camera page"""
    return render(request, "camera.html")


@session_login_required
@csrf_exempt
def analyze_emotion(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
        img_data = data.get("image")

        if not img_data:
            return JsonResponse({"emotion": "normal"})

        # Decode image
        header, encoded = img_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        open_cv_image = np.array(pil_img)
        img = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

        # DeepFace Analysis
        result = DeepFace.analyze(
            img_path=img,
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="mtcnn"
        )
        if isinstance(result, list):
            result = result[0]

        dominant_emotion = result.get("dominant_emotion", "neutral")

        # Map to your system
        if dominant_emotion in ["happy"]:
            mapped_emotion = "normal"
        elif dominant_emotion in ["sad"]:
            mapped_emotion = "depressed"
        elif dominant_emotion in ["angry", "fear"]:
            mapped_emotion = "stress"
        elif dominant_emotion in ["surprise"]:
            mapped_emotion = "anxiety"
        else:
            mapped_emotion = "normal"


        # 🔥 Save per user (if logged in)
        EmotionLog.objects.create(
            user=request.user,
            emotion=mapped_emotion,
            mode="Camera"
        )
        return JsonResponse({"emotion": mapped_emotion})

    except Exception as e:
        return JsonResponse({"emotion": "normal"})


from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.db.models import Count
from .models import EmotionLog

@csrf_exempt
def get_dashboard_data(request):
    """API that the Dashboard calls to get live stats"""

    user_id = request.session.get('user_id')

    if not user_id:
        return JsonResponse({"error": "Not logged in"}, status=403)

    logs = EmotionLog.objects.filter(user_id=user_id)

    # Total scans
    total_scans = logs.count()

    # Emotion breakdown — sorted by count descending so [0] = most frequent
    emotion_counts = list(
        logs.values('emotion').annotate(count=Count('emotion')).order_by('-count')
    )

    # Recent logs
    recent_logs_qs = logs.order_by('-timestamp')[:10]

    recent_logs = [
        {
            "emotion": log.emotion,
            "timestamp": log.timestamp.isoformat()
        }
        for log in recent_logs_qs
    ]

    return JsonResponse({
        "total": total_scans,
        "breakdown": emotion_counts,
        "recent": recent_logs
    })


def dashboard_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    # Build last-7-days date range (oldest → today)
    today = timezone.now()
    dates = [(today - timedelta(days=i)).date() for i in range(6, -1, -1)]

    # Fetch all logs for this user in that window
    week_start = timezone.make_aware(
        dt.combine(dates[0], dt.min.time())
    )
    logs = EmotionLog.objects.filter(user_id=user_id, timestamp__gte=week_start)

    # Count per emotion per day
    weekly_counts = {
        "normal":   [0] * 7,
        "stress":   [0] * 7,
        "anxiety":  [0] * 7,
        "depressed": [0] * 7,
    }
    for log in logs:
        log_date = log.timestamp.date()
        if log_date in dates:
            idx = dates.index(log_date)
            emotion = log.emotion.strip().lower()
            if emotion in weekly_counts:
                weekly_counts[emotion][idx] += 1

    import json as _json
    context = {
        "weekly_labels": _json.dumps([d.strftime("%d %b") for d in dates]),
        "weekly_normal":   _json.dumps(weekly_counts["normal"]),
        "weekly_stress":   _json.dumps(weekly_counts["stress"]),
        "weekly_anxiety":  _json.dumps(weekly_counts["anxiety"]),
        "weekly_depressed":_json.dumps(weekly_counts["depressed"]),
    }
    return render(request, 'dashboard.html', context)

# ==============================
# SEND OTP FUNCTION
# ==============================
def send_verification_code(request, user):
    code_obj, created = models.EmailVerificationCode.objects.get_or_create(user=user)

    # If code exists but expired -> regenerate
    if not created and code_obj.is_valid():
        pass
    else:
        code_obj.code = ''.join(random.choices('0123456789', k=6))
        code_obj.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        code_obj.save()

    subject = "Verify Your Email"
    message = f"Your verification code is: {code_obj.code}\n\nThis code expires in 15 minutes."

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )


def verify_email(request):
    session_email = request.session.get("email")

    if not session_email:
        messages.error(request, "Session expired. Please register/login again.")
        return redirect("login")

    try:
        user = models.Register.objects.get(email=session_email)
    except models.Register.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("register")

    # If already verified
    if user.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("login")

    if request.method == "POST":
        entered_code = request.POST.get("code", "").strip()

        try:
            code_obj = models.EmailVerificationCode.objects.get(user=user)

            if code_obj.is_valid() and code_obj.code == entered_code:
                user.email_verified = True
                user.save()

                code_obj.delete()

                return redirect('login')
            else:
                return HttpResponse("""
                    <script>
                        alert('Invalid or expired OTP. Please try again.');
                        window.location.reload();
                    </script>
                """)

        except models.EmailVerificationCode.DoesNotExist:
            return HttpResponse("""
                <script>
                    alert('No OTP found. Please reload to resend.');
                    window.location.reload();
                </script>
            """)

    # GET request -> send OTP (resend)
    send_verification_code(request, user)

    return render(request, "verify_email.html", {"email": user.email})



def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = Register.objects.get(email=email)
            
            # Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            
            # Save OTP
            PasswordResetOTP.objects.create(user=user, otp=otp)
            
            # Send OTP via email
            send_mail(
               
    "Important: OTP for Your Password Reset Request",

    f"""
    Hello,

    We received a request to reset the password for your Restaurant.it account.
    Your One-Time Password (OTP) is: {otp}

    This code is valid for the next 10 minutes. 
    If you did not request this, please ignore this email or contact our support team.

    Regards,
    The Restaurant.it Team
    """,

   
    "noreply@restaurant.com",

    
    [email],

    fail_silently=False,

   
    html_message=f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 500px; margin: auto; padding: 25px; border: 1px solid #eee; border-radius: 15px;">
        <div style="text-align: center; border-bottom: 2px solid #f4f4f4; padding-bottom: 15px;">
            <h1 style="color: #d4af37; margin: 0; letter-spacing: 2px;">Mental Health</h1>
        </div>
        
        <div style="padding: 20px 0;">
            <h3 style="color: #333;">Password Reset Request</h3>
            <p style="color: #666; font-size: 15px; line-height: 1.5;">
                Hello there,<br><br>
                We received a request to reset your password. Please use the secure verification code below to proceed:
            </p>
            
            <div style="background-color: #fafafa; border: 1px dashed #d4af37; padding: 20px; text-align: center; margin: 25px 0; border-radius: 10px;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 12px; color: #1a1a1a;">{otp}</span>
            </div>
            
            <p style="color: #ff4d4d; font-size: 13px; font-weight: bold;">
                ⚠️ This code will expire in 10 minutes.
            </p>
        </div>
        
        <div style="background-color: #fff9eb; padding: 15px; border-radius: 8px; border-left: 4px solid #d4af37;">
            <p style="margin: 0; font-size: 12px; color: #8a6d3b;">
                <strong>Security Note:</strong> If you did not make this request, someone might be trying to access your account. Please change your password immediately.
            </p>
        </div>
        
        <div style="text-align: center; padding-top: 25px; border-top: 1px solid #eee; margin-top: 20px; color: #aaa; font-size: 11px;">
            <p>&copy; 2026 Mental Health System. All rights reserved.</p>
        </div>
    </div>
    """
            )
            
            request.session['reset_user_id'] = user.id
            messages.success(request, "OTP sent to your email.")
            return redirect('verify_otp')
        except Register.DoesNotExist:
            messages.error(request, "Email not registered.")
    return render(request, 'forgot_password.html')

def verify_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot_password')

    user =Register.objects.get(id=user_id)

    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        try:
            otp_obj = PasswordResetOTP.objects.filter(user=user, otp=entered_otp).latest('created_at')
            if otp_obj.is_expired():
                messages.error(request, "OTP expired. Request a new one.")
                return redirect('forgot_password')
            return redirect('reset_password')
        except PasswordResetOTP.DoesNotExist:
            messages.error(request, "Invalid OTP.")
    
    return render(request, 'verify_otp.html')

from django.contrib.auth.hashers import make_password

def reset_password(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot_password')
    
    user = Register.objects.get(id=user_id)

    if request.method == "POST":
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')

        user.password = password
        user.save()
        messages.success(request, "Password changed successfully. Login now.")
        return redirect('login')

    return render(request, 'reset_password.html')