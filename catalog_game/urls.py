from django.contrib.auth import views as auth
from django.urls import path

from . import views
from django.urls import reverse_lazy

from .forms import EmailLoginForm, EmailPasswordResetForm

app_name = 'catalog_game'

urlpatterns = [
    path('', views.home, name='home'),
    path('pick/', views.pick, name='pick'),

    path('games/', views.GameListView.as_view(), name='catalog'),
    path('games/add/', views.GameCreateView.as_view(), name='game_create'),
    path('games/<int:pk>/', views.GameDetailView.as_view(), name='game_detail'),
    path('games/<int:pk>/edit/', views.GameUpdateView.as_view(), name='game_update'),
    path('games/<int:pk>/delete/', views.GameDeleteView.as_view(), name='game_delete'),

    path('games/<int:pk>/review/', views.ReviewSaveView.as_view(), name='review_save'),
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('reviews/<int:pk>/', views.ReviewDetailView.as_view(), name='review_detail'),
    path('reviews/<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_remove'),

    path('developers/', views.DeveloperListView.as_view(), name='developer_list'),
    path('developers/<int:pk>/', views.DeveloperDetailView.as_view(), name='developer_detail'),
    path('genres/', views.GenreListView.as_view(), name='genre_list'),
    path('genres/<int:pk>/', views.GenreDetailView.as_view(), name='genre_detail'),
    path('platforms/', views.PlatformListView.as_view(), name='platform_list'),
    path('platforms/<int:pk>/', views.PlatformDetailView.as_view(), name='platform_detail'),

    path('games/<int:pk>/wish/', views.wishlist_toggle, name='wishlist_toggle'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/<int:pk>/note/', views.wishlist_note, name='wishlist_note'),
    path('wishlist/<int:pk>/note/delete/', views.wishlist_note_delete, name='wishlist_note_delete'),

    path('profile/', views.profile, name='profile'),
    path('account/delete/', views.account_delete, name='account_delete'),
    path('login/', auth.LoginView.as_view(template_name='catalog_game/login.html',
                                          authentication_form=EmailLoginForm), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
]