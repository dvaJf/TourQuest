from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path('', views.Register.as_view(), name="reg"),
    path('reg/', views.Register.as_view(), name="reg"),
    path('sigin/', views.sigin, name="sigin"),
    path('login/', views.user_login, name="login"),
    path('logout/', views.user_logout, name="logout"),
    path('make/', views.maket, name="maket"),
    path('main/', views.index, name="main"),
    path('profile/', views.user_profile, name='user_profile'),
    path('tour/<int:tour_id>/', views.tour_detail, name='tour_detail'),
    path('tour/<int:tour_id>/start/', views.start_tour, name='start_tour'),
    path('tour/<int:tour_id>/active/', views.active_tour, name='active_tour'),
    path('tour/<int:tour_id>/abandon/', views.abandon_tour, name='abandon_tour'),
    path('point/<int:point_id>/', views.point_detail, name='point_detail'),
    path('tour/<int:tour_id>/point/<int:point_id>/complete/', views.complete_point, name='complete_point'),
    path('scan-qr/', views.scan_qr, name='scan_qr'),
    path('process-qr/', views.process_qr_code, name='process_qr_code'),
    path('about/', TemplateView.as_view(template_name='main/about.html'), name='about'),
    path('shop/', views.shop, name='shop'),
    path('shop/buy/<int:item_id>/', views.buy_item, name='buy_item'),
    path('purchase/<int:purchase_id>/', views.purchase_detail, name='purchase_detail'),
    path('tour/complete/', views.tour_complete, name='tour_complete'),
]