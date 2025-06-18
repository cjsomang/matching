from django.urls import path
from . import views

app_name = 'matching'

urlpatterns = [
    path('', views.index, name='index'),
    path('select/', views.select_page, name='select_page'),
    path('select/api/', views.select_api, name='select_api'),
    # path('viewlist/', views.viewlist, name='viewlist'),
]