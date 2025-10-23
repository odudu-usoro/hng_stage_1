from django.urls import path
from . import views

urlpatterns = [
    path('strings/', views.create_string, name='create_string'),  # POST
    path('strings/all/', views.list_strings, name='list_strings'),  # GET all
    path('strings/<str:string_value>/', views.get_string, name='get_string'),  # GET one
    path('strings/<str:string_value>/delete/', views.delete_string, name='delete_string'),  # DELETE
    path('strings/filter-by-natural-language/', views.filter_by_nl, name='filter_by_nl'),  # GET
]
