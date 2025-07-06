from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'common'

urlpatterns = [
    # path('login/', auth_views.LoginView.as_view(template_name='common/login.html'), name='login'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('guide/', views.guide, name='guide'),
    path('myinfo/', views.myinfo_page, name='myinfo_page'),
    path('myinfo/get/api', views.get_myinfo_api, name='get_myinfo_api'),
    path('myinfo/update/api', views.update_myinfo_api, name='update_myinfo_api'),
    path('myinfo/delete/api', views.delete_myinfo_api, name='delete_myinfo_api'),
]