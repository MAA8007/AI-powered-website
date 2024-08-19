from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('summaries/', views.summaries, name='summaries'),
    path('manage/', views.manage, name='manage'),
    path('category/<str:category_name>/', views.category_page, name='category_page'),
    path('chatbox/', views.chat_with_bot, name='chat_with_bot'),
    path('sse-updates/', views.sse_view, name='sse_view'),
    path('search/', views.search_articles, name='search_articles'),
    path('category/<str:category_name>/', views.category_page, name='category_page'),
    path('website/<str:website_name>/', views.website_page, name='website_page'),
    
]
