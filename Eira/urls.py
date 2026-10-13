from django.urls import path
from .import views
urlpatterns=[
    path('',views.index,name='index'),
    path('register/',views.register,name='register'),
    path('login/',views.login,name='login'),
    path('home/',views.home,name='home'),  
    path('profile/',views.Profile,name='profile'),
    path('editprofile/',views.editprofile,name='editprofile'),
    path('logout/',views.logout,name='logout'),
    path('adminlogin/',views.adminlogin,name='adminlogin'),
    path('adminhome/',views.adminhome,name='adminhome'),
    path('userlist/',views.userlist,name='userlist'),
    path('deleteuser/<int:id>/',views.deleteuser,name='deleteuser'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('feedback/', views.feedback, name='feedback'),
    path('deletefeedback/<int:id>/',views.deletefeedback,name='deletefeedback'),
    path('feedbacklist/', views.feedbacklist, name='feedbacklist'),
    path("camera/", views.camera, name="camera"),
    path("analyze-emotion/", views.analyze_emotion, name="analyze_emotion"),
    path("chat/", views.chat, name="chat"), 
    # path('analyze-emotion/', views.analyze_emotion, name='analyze_emotion'),
    path('get-dashboard-data/', views.get_dashboard_data, name='get_dashboard_data'),
    path("verify-email/", views.verify_email, name="verify_email"),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Page View
    path('dashboard/', views.dashboard_view, name='dashboard'),

]

