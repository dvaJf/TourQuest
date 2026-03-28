from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .forms import UserCreationForm1
from django.contrib.auth import authenticate, login, logout
from django.views import View
from .models import Tour, TourPoint, UserTour, UserTourPoint, UserProfile, ShopItem, UserPurchase
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

# Константы наград
POINTS_PER_POINT = 10.0   # Монет за точку
POINTS_PER_TOUR = 100.0   # Монет за тур

def get_or_create_profile(user):
    """Получить или создать профиль пользователя"""
    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'balance': 0.0})
    return profile
def index(request):
    """Главная страница со списком туров"""
    # Получаем ID туров, которые пользователь уже прошел
    completed_tour_ids = []
    available_tours = []
    completed_tours = []
    
    profile = None  # ← ДОБАВИТЬ
    if request.user.is_authenticated:
        profile = get_or_create_profile(request.user)  # ← ДОБАВИТЬ
        # Получаем завершенные туры пользователя
        completed_user_tours = UserTour.objects.filter(
            user=request.user,
            status='completed'
        ).select_related('tour')
        completed_tour_ids = list(completed_user_tours.values_list('tour_id', flat=True))
        
        # Разделяем туры на доступные и завершенные
        all_active_tours = Tour.objects.filter(is_active=True)
        for tour in all_active_tours:
            if tour.id in completed_tour_ids:
                # Находим соответствующий UserTour для получения даты завершения
                user_tour = completed_user_tours.filter(tour_id=tour.id).first()
                completed_tours.append({
                    'tour': tour,
                    'completed_at': user_tour.completed_at if user_tour else None
                })
            else:
                available_tours.append(tour)
    else:
        # Для неавторизованных пользователей показываем все туры как доступные
        available_tours = Tour.objects.filter(is_active=True)
    
    completed_tours_count = len(completed_tours)
    balance = 0
    if request.user.is_authenticated:
        profile = get_or_create_profile(request.user)
        balance = profile.balance
    
    return render(request, 'main/main.html', {
        'available_tours': available_tours,
        'completed_tours': completed_tours,
        'completed_tours_count': completed_tours_count,
        'balance': balance,
        'profile': profile,  # ← ДОБАВИТЬ
    })

def tour_detail(request, tour_id):
    """Страница с описанием конкретного тура"""
    tour = get_object_or_404(Tour, id=tour_id, is_active=True)
    points = tour.points.all()

    active_user_tour = None
    if request.user.is_authenticated:
        active_user_tour = UserTour.objects.filter(
            user=request.user,
            tour=tour,
            status='active'
        ).first()

    context = {
        'tour': tour,
        'points': points,
        'points_count': points.count(),
        'active_user_tour': active_user_tour,
    }
    return render(request, 'main/tour_detail.html', context)

@login_required
def start_tour(request, tour_id):
    """Начать тур - создает запись UserTour для пользователя"""
    tour = get_object_or_404(Tour, id=tour_id, is_active=True)

    existing_active = UserTour.objects.filter(
        user=request.user,
        status='active'
    ).first()

    if existing_active:
        messages.warning(request, f'У вас уже есть активный тур "{existing_active.tour.title}". Завершите его перед началом нового.')
        return redirect('active_tour', tour_id=existing_active.tour.id)

    existing_tour = UserTour.objects.filter(
        user=request.user,
        tour=tour
    ).first()

    if existing_tour:
        if existing_tour.status in ['abandoned', 'completed']:
            user_tour = UserTour.objects.create(
                user=request.user,
                tour=tour,
                status='active',
                current_point_order=0
            )
        else:
            user_tour = existing_tour
    else:
        user_tour = UserTour.objects.create(
            user=request.user,
            tour=tour,
            status='active',
            current_point_order=0
        )

    messages.success(request, f'Тур "{tour.title}" начат! Отсканируйте QR-код на первой точке.')
    return redirect('active_tour', tour_id=tour.id)

@login_required
def active_tour(request, tour_id):
    """Страница активного тура с картой и кнопкой сканирования QR"""
    tour = get_object_or_404(Tour, id=tour_id, is_active=True)

    user_tour = get_object_or_404(
        UserTour,
        user=request.user,
        tour=tour,
        status='active'
    )

    points = tour.points.all()
    current_point = user_tour.get_current_point()

    completed_point_ids = list(
        user_tour.completed_points.values_list('point_id', flat=True)
    )

    context = {
        'tour': tour,
        'points': points,
        'user_tour': user_tour,
        'current_point': current_point,
        'completed_point_ids': completed_point_ids,
        'points_count': points.count(),
        'completed_count': len(completed_point_ids),
    }
    return render(request, 'main/active_tour.html', context)

@login_required
def point_detail(request, point_id):
    """Страница точки, открывающаяся по QR-коду"""
    point = get_object_or_404(TourPoint, id=point_id)
    tour = point.tour

    user_tour = UserTour.objects.filter(
        user=request.user,
        tour=tour,
        status='active'
    ).first()

    if not user_tour:
        messages.error(request, 'У вас нет активного тура. Сначала начните тур.')
        return redirect('tour_detail', tour_id=tour.id)

    is_current = (user_tour.current_point_order == point.order)

    is_completed = UserTourPoint.objects.filter(
        user_tour=user_tour,
        point=point
    ).exists()

    context = {
        'point': point,
        'tour': tour,
        'user_tour': user_tour,
        'is_current': is_current,
        'is_completed': is_completed,
    }
    return render(request, 'main/point_detail_progress.html', context)

@login_required
def complete_point(request, tour_id, point_id):
    """Закрыть точку - отметить как пройденную и начислить монеты"""
    if request.method != 'POST':
        return redirect('point_detail', point_id=point_id)

    tour = get_object_or_404(Tour, id=tour_id)
    point = get_object_or_404(TourPoint, id=point_id, tour=tour)

    user_tour = get_object_or_404(
        UserTour,
        user=request.user,
        tour=tour,
        status='active'
    )

    if user_tour.current_point_order != point.order:
        messages.error(request, 'Эта точка еще не доступна. Сначала пройдите предыдущие точки.')
        return redirect('point_detail', point_id=point_id)

    has_completed_before = UserTour.objects.filter(
        user=request.user,
        tour=tour,
        status='completed'
    ).exclude(id=user_tour.id).exists()
    if has_completed_before:
        user_tour.rewards_given = True
        user_tour.save(update_fields=['rewards_given'])
    next_point = user_tour.complete_current_point()
    profile = get_or_create_profile(request.user)
    
    if not user_tour.rewards_given:
        profile.balance += POINTS_PER_POINT
        profile.save()
        messages.success(request, f'Точка пройдена! +{POINTS_PER_POINT} монет!')
    else:
        messages.success(request, 'Точка пройдена! (повторное прохождение - баллы не начисляются)')

    if next_point:
        messages.success(request, f'Следующая точка: "{next_point.name}"')
        return redirect('active_tour', tour_id=tour.id)
    else:
        if not user_tour.rewards_given:
            profile.balance += POINTS_PER_TOUR
            profile.save()
            user_tour.rewards_given = True
            user_tour.save(update_fields=['rewards_given'])

        duration = timezone.now() - user_tour.started_at
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        duration_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
        
        request.session['tour_complete'] = {
            'tour_id': tour.id,
            'tour_title': tour.title,
            'points_count': tour.points.count(),
            'distance': tour.distance,
            'duration': duration_str,
            'tour_bonus': POINTS_PER_TOUR if not user_tour.rewards_given else 0,
            'points_bonus': tour.points.count() * POINTS_PER_POINT if not user_tour.rewards_given else 0,
        }
        
        return redirect('tour_complete')

@login_required
def tour_complete(request):
    data = request.session.get('tour_complete')
    
    if not data:
        last_tour = UserTour.objects.filter(
            user=request.user,
            status='completed'
        ).order_by('-completed_at').first()
        
        if not last_tour:
            return redirect('main')
        
        tour = last_tour.tour
        data = {
            'tour_title': tour.title,
            'points_count': tour.points.count(),
            'distance': tour.distance,
            'duration': '—',
            'tour_bonus': POINTS_PER_TOUR,
            'points_bonus': tour.points.count() * POINTS_PER_POINT,
        }

    if 'tour_complete' in request.session:
        del request.session['tour_complete']
    
    return render(request, 'main/tour_complete.html', data)

@login_required
def scan_qr(request):
    """Страница сканирования QR-кода"""
    user_tour = UserTour.objects.filter(
        user=request.user,
        status='active'
    ).select_related('tour').first()

    if not user_tour:
        messages.error(request, 'У вас нет активного тура. Сначала начните тур.')
        return redirect('main')

    context = {
        'user_tour': user_tour,
        'tour': user_tour.tour,
    }
    return render(request, 'main/scan_qr.html', context)

@login_required
def process_qr_code(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    import json
    data = json.loads(request.body)
    qr_data = data.get('qr_data', '')

    point = TourPoint.objects.filter(qr_code=qr_data).first()

    if not point:
        try:
            point_id = int(qr_data.replace('point_', ''))
            point = TourPoint.objects.filter(id=point_id).first()
        except (ValueError, AttributeError):
            pass

    if not point:
        return JsonResponse({
            'success': False,
            'error': 'QR-код не распознан или точка не найдена'
        })

    user_tour = UserTour.objects.filter(
        user=request.user,
        tour=point.tour,
        status='active'
    ).first()

    if not user_tour:
        return JsonResponse({
            'success': False,
            'error': 'У вас нет активного тура для этой точки'
        })

    return JsonResponse({
        'success': True,
        'redirect_url': f'/point/{point.id}/'
    })

@login_required
def abandon_tour(request, tour_id):
    if request.method != 'POST':
        return redirect('active_tour', tour_id=tour_id)

    tour = get_object_or_404(Tour, id=tour_id)
    user_tour = get_object_or_404(
        UserTour,
        user=request.user,
        tour=tour,
        status='active'
    )

    user_tour.status = 'abandoned'
    user_tour.save()

    messages.info(request, f'Тур "{tour.title}" покинут.')
    return redirect('main')

def sigin(request):
    return render(request, 'main/sigin.html')

def maket(request):
    return render(request, 'main/maket.html')

def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/main/')
        else:
            return render(request, 'main/sigin.html', {
                "error": "неверное имя пользователя или пароль"
            })

    return render(request, 'main/sigin.html')

def user_logout(request):
    logout(request)
    return redirect('/sigin/')

class Register(View):
    template_name = 'main/reg.html'

    def get(self, request):
        form = UserCreationForm1()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserCreationForm1(request.POST)
        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')

            user = authenticate(username=username, password=password)
            login(request, user)

            return redirect('/main/')
        return render(request, self.template_name, {
            "form": form,
            "error": "некорректные данные"
        })
        
@login_required
def user_profile(request):
    profile = get_or_create_profile(request.user)
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, 'Аватар обновлен!')
        return redirect('user_profile')
    completed_tour_ids = UserTour.objects.filter(
        user=request.user,
        status='completed'
    ).values_list('tour_id', flat=True).distinct()
    completed_tours_list = []
    for tour_id in completed_tour_ids:
        last_completed = UserTour.objects.filter(
            user=request.user,
            tour_id=tour_id,
            status='completed'
        ).order_by('-completed_at').first()
        
        if last_completed:
            completed_tours_list.append({
                'tour': last_completed.tour,
                'completed_at': last_completed.completed_at,
                'points_count': last_completed.tour.points.count(),
                'completed_points': last_completed.completed_points.count(),
            })
    
    completed_tours = len(completed_tours_list)
    total_tours = Tour.objects.filter(is_active=True).count()
    completion_percentage = 0
    if total_tours > 0:
        completion_percentage = round((completed_tours / total_tours) * 100)
    active_tour = UserTour.objects.filter(
        user=request.user,
        status='active'
    ).select_related('tour').first()
    total_points = UserTourPoint.objects.filter(
        user_tour__user=request.user
    ).count()
    unlocked_achievements = []
    locked_achievements = []
    
    if completed_tours >= 1:
        unlocked_achievements.append({
            'icon': '',
            'title': 'Первые шаги',
            'description': 'Пройден первый тур',
        })
    else:
        locked_achievements.append({
            'icon': '',
            'title': 'Первые шаги',
            'description': 'Пройдите первый тур',
        })
    
    if completed_tours >= 3:
        unlocked_achievements.append({
            'icon': '',
            'title': 'Исследователь',
            'description': 'Пройдено 3 тура',
        })
    else:
        locked_achievements.append({
            'icon': '',
            'title': 'Исследователь',
            'description': f'Пройдите ещё {3 - completed_tours} тура',
        })
    
    if completed_tours >= 5:
        unlocked_achievements.append({
            'icon': '',
            'title': 'Мастер путешествий',
            'description': 'Пройдено 5 туров',
        })
    else:
        locked_achievements.append({
            'icon': '',
            'title': 'Мастер путешествий',
            'description': f'Пройдите ещё {5 - completed_tours} туров',
        })
    
    if total_points >= 10:
        unlocked_achievements.append({
            'icon': '',
            'title': 'Пункт назначения',
            'description': 'Посещено 10 точек',
        })
    else:
        locked_achievements.append({
            'icon': '',
            'title': 'Пункт назначения',
            'description': f'Посетите ещё {10 - total_points} точек',
        })
    
    if total_points >= 25:
        unlocked_achievements.append({
            'icon': '',
            'title': 'Непоседа',
            'description': 'Посещено 25 точек',
        })
    else:
        locked_achievements.append({
            'icon': '',
            'title': 'Непоседа',
            'description': f'Посетите ещё {25 - total_points} точек',
        })
    
    context = {
        'user': request.user,
        'profile': profile,
        'completed_tours': completed_tours,
        'completed_tours_list': completed_tours_list,
        'active_tour': active_tour,
        'total_points': total_points,
        'unlocked_achievements': unlocked_achievements,
        'locked_achievements': locked_achievements,
        'completion_percentage': completion_percentage,
        'total_tours': total_tours,
    }
    return render(request, 'main/user_profile.html', context)
@login_required
def shop(request):
    profile = get_or_create_profile(request.user)
    items = ShopItem.objects.filter(is_active=True)
    
    purchased_item_ids = list(UserPurchase.objects.filter(
        user=request.user
    ).values_list('item_id', flat=True))
    
    return render(request, 'main/shop.html', {
        'balance': profile.balance,
        'items': items,
        'purchased_item_ids': purchased_item_ids,
    })

@login_required
def buy_item(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, is_active=True)
    profile = get_or_create_profile(request.user)
    
    existing = UserPurchase.objects.filter(user=request.user, item=item).first()
    if existing:
        messages.warning(request, 'Вы уже купили этот товар!')
        return redirect('purchase_detail', purchase_id=existing.id)
    
    if profile.balance < item.price:
        messages.error(request, f'Недостаточно монет! Нужно: {item.price}, у вас: {profile.balance}')
        return redirect('shop')
    
    profile.balance -= item.price
    profile.save()
    
    purchase = UserPurchase.objects.create(user=request.user, item=item)
    messages.success(request, f' Куплено: {item.name}! -{item.price} монет')
    return redirect('purchase_detail', purchase_id=purchase.id)

@login_required
def purchase_detail(request, purchase_id):
    purchase = get_object_or_404(UserPurchase, id=purchase_id, user=request.user)
    
    if not purchase.promo_code_displayed:
        purchase.promo_code_displayed = True
        purchase.save()
    
    return render(request, 'main/purchase_detail.html', {
        'purchase': purchase,
        'item': purchase.item,
    })