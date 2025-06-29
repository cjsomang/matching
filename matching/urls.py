from django.urls import path
from . import views

app_name = 'matching'

urlpatterns = [
    path('', views.index, name='index'),
    path('select/', views.select_page, name='select_page'),
    path('select/api/', views.select_api, name='select_api'),
    path('choices/api/', views.choices_api,  name='choices_api'),
    path('result/', views.results_page, name='results_page'),
    path('result/api', views.results_api, name='results_api'),
    # path('contact/api', views.get_contact_api, name='get_contact_api'),
    path('contact/grant/api', views.grant_contact_api, name='grant_contact_api'),
    path('contact/get/api', views.get_granted_contact_api, name='get_granted_contact_api'),
    path('contact/mine/api', views.get_granted_by_me_api, name='get_granted_by_me_api'),

]