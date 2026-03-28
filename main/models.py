from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Tour(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный'),
    ]
    image = models.ImageField(
        upload_to='tours/',
        blank=True,
        null=True,
        verbose_name='Изображение тура'
    )
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='easy')
    distance = models.FloatField(verbose_name='Дистанция (км)')
    duration = models.CharField(max_length=50, verbose_name='Длительность')
    rating = models.FloatField (default=1, verbose_name='Рейтинг 1-5')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Цена (₽)',
                                help_text='0 = бесплатно (зеленый), 1-1000 = желтый, >1000 = красный')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Тур'
        verbose_name_plural = 'Туры'

    def __str__(self):
        return self.title


class TourPoint(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='points')
    name = models.CharField(max_length=200, verbose_name='Название точки')
    description = models.TextField(blank=True, verbose_name='Описание где искать следующую точку')
    facts = models.TextField(blank=True, verbose_name='Интересные факты', 
                            help_text='Интересные факты о точке, которые отобразятся после прохождения')
    latitude = models.FloatField()
    longitude = models.FloatField()
    order = models.IntegerField(default=0)
    qr_code = models.CharField(max_length=100, blank=True, verbose_name='QR код точки',
                               help_text='Уникальный код для сканирования QR')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.tour.title} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = f"point_{self.tour.id}_{self.order}"
        super().save(*args, **kwargs)


class UserTour(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('completed', 'Завершен'),
        ('abandoned', 'Покинут'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tours')
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='user_tours')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_point_order = models.IntegerField(default=0, verbose_name='Текущая точка')
    rewards_given = models.BooleanField(default=False, verbose_name='Награды выданы',
                                        help_text='Были ли уже выданы монеты за этот тур')

    class Meta:
        verbose_name = 'Тур пользователя'
        verbose_name_plural = 'Туры пользователей'
        unique_together = ['user', 'tour', 'started_at']

    def __str__(self):
        return f"{self.user.username} - {self.tour.title} ({self.status})"

    def get_current_point(self):
        """Получить текущую активную точку"""
        return self.tour.points.filter(order=self.current_point_order).first()

    def get_next_point(self):
        """Получить следующую точку"""
        return self.tour.points.filter(order=self.current_point_order + 1).first()

    def complete_current_point(self):
        """Отметить текущую точку как пройденную и перейти к следующей"""
        from django.utils import timezone
        current_point = self.get_current_point()
        if current_point:
            UserTourPoint.objects.get_or_create(
                user_tour=self,
                point=current_point,
                defaults={'completed_at': timezone.now()}
            )

        next_point = self.get_next_point()
        if next_point:
            self.current_point_order += 1
            self.save(update_fields=['current_point_order'])
            return next_point
        else:
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])
            return None


class UserTourPoint(models.Model):
    user_tour = models.ForeignKey(UserTour, on_delete=models.CASCADE, related_name='completed_points')
    point = models.ForeignKey(TourPoint, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Пройденная точка'
        verbose_name_plural = 'Пройденные точки'
        unique_together = ['user_tour', 'point']

    def __str__(self):
        return f"{self.user_tour.user.username} - {self.point.name}"
    
# Модель профиля пользователя для хранения баланса
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    balance = models.IntegerField(default=0, verbose_name='Баланс')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')  # ← ДОБАВИТЬ
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"{self.user.username} - {self.balance} монет"
    
    def add_balance(self, amount):
        """Начислить монеты"""
        self.balance += amount
        self.save()
    
    def subtract_balance(self, amount):
        """Списать монеты"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False


# Модель товара в магазине
class ShopItem(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название товара')
    description = models.TextField(verbose_name='Описание')
    price = models.IntegerField(verbose_name='Цена')
    promo_code = models.TextField(verbose_name='Промокод/Содержимое', 
                                  help_text='Текст который увидит пользователь после покупки (промокод, инструкция и т.д.)')
    image = models.ImageField(upload_to='shop/', blank=True, null=True, verbose_name='Изображение')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Товар в магазине'
        verbose_name_plural = 'Товары в магазине'
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - {self.price} монет"


# Модель покупки пользователя
class UserPurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)
    promo_code_displayed = models.BooleanField(default=False, verbose_name='Промокод показан')
    
    class Meta:
        verbose_name = 'Покупка пользователя'
        verbose_name_plural = 'Покупки пользователей'
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.user.username} купил {self.item.name}"