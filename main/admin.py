from django.contrib import admin
from .models import Tour, TourPoint, UserTour, UserTourPoint, UserProfile, ShopItem, UserPurchase
from django.utils.html import format_html


class TourPointInline(admin.TabularInline):
    model = TourPoint
    extra = 3
    fields = ['name', 'description', 'facts', 'latitude', 'longitude', 'order', 'qr_code']


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'distance', 'duration', 'rating', 'display_price', 'is_active', 'image']
    list_filter = ['difficulty', 'is_active']
    search_fields = ['title', 'description']
    inlines = [TourPointInline]
    
    def display_price(self, obj):
        if obj.price == 0:
            color = '#28a745'
            text = 'Бесплатно'
        elif obj.price <= 1000:
            color = '#ffc107'
            text = f'{obj.price} ₽'
        else:
            color = '#dc3545'
            text = f'{obj.price} ₽'
        
        return format_html(
            '<span style="color: {}; font-weight: bold; border: 2px solid {}; padding: 2px 8px; border-radius: 12px;">{}</span>',
            color, color, text
        )
    display_price.short_description = 'Цена'


@admin.register(TourPoint)
class TourPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'tour', 'order', 'latitude', 'longitude', 'qr_code']
    list_filter = ['tour']
    search_fields = ['name', 'qr_code', 'description', 'facts']


@admin.register(UserTour)
class UserTourAdmin(admin.ModelAdmin):
    list_display = ['user', 'tour', 'status', 'current_point_order', 'started_at', 'completed_at']
    list_filter = ['status', 'tour']
    search_fields = ['user__username', 'tour__title']
    date_hierarchy = 'started_at'


@admin.register(UserTourPoint)
class UserTourPointAdmin(admin.ModelAdmin):
    list_display = ['user_tour', 'point', 'completed_at']
    list_filter = ['user_tour__tour']
    search_fields = ['user_tour__user__username', 'point__name']
    date_hierarchy = 'completed_at'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance']
    search_fields = ['user__username']


@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(UserPurchase)
class UserPurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'purchased_at']
    list_filter = ['purchased_at']
    search_fields = ['user__username', 'item__name']