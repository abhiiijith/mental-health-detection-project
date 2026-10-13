from django.db import models
from django.utils import timezone
import random

# Create your models here.
class Register(models.Model):
    name=models.CharField(max_length=100,null=True,blank=True)
    email=models.EmailField(max_length=30,null=True,blank=True,unique=True)
    password=models.CharField(max_length=8,null=True,blank=True)
    email_verified = models.BooleanField(default=False)
    GENDER_CHOICES=(('M','MALE'),
                    ('F','FEMALE'))
    gender=models.CharField(max_length=1,choices=GENDER_CHOICES,null=True,blank=True)
    LOCATION_CHOICES=(('KSD','KASARGOD'),
                      ('KNR','KANNUR'),
                      ('WYD','WAYANAD'),
                      ('KKD','KOZHIKODE'),
                      ('MLM','MALAPPURAM'),
                      ('PKD','PALAKAD'),
                      ('TSR','THRISSUR'),
                      ('EKM','ERNAKULAM'),
                      ('IDK','IDUKKI'),
                      ('KTM','KOTTAYAM'),
                      ('ALA','ALAPPUZHA'),
                      ('PTA','PATHANAMTHITTA'),
                      ('KLM','KOLLAM'),
                      ('TVM','THIRUVANATHAPURAM'))
    location=models.CharField(max_length=10,choices=LOCATION_CHOICES,null=True,blank=True)
    image = models.FileField(upload_to='profile_pics/', null=True, blank=True)

class feedback(models.Model):
    user=models.CharField(max_length=100,null=True,blank=True)
    message=models.TextField(max_length=100,null=True,blank=True)
    created_at=models.DateField(auto_now_add=True,null=True,blank=True)
    
# emotion_app/models.py
from django.db import models

class camera(models.Model):
    emotion = models.CharField(max_length=50)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.emotion


class EmotionLog(models.Model):
    user = models.ForeignKey(Register, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=50)
    mode = models.CharField(max_length=20, default="Camera")  # Camera / Text / Voice
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.emotion} at {self.timestamp}"
    

class EmailVerificationCode(models.Model):
    user = models.OneToOneField(Register, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices('0123456789', k=6))
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def _str_(self):
        return f"Code {self.code} for {self.user.email}"
    

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(Register, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_expired(self):
        return timezone.now() > self.created_at + datetime.timedelta(minutes=10)  # OTP valid 10 mins



from django.db import models

class ChatHistory(models.Model):
    user = models.ForeignKey(Register, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=10)  # user / assistant
    message = models.TextField()
    emotion = models.CharField(max_length=50, null=True, blank=True)
    sentiment = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.role} - {self.created_at}"