import requests
from django.views.generic import CreateView, ListView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import translation, timezone
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Song, ScoreLog, SongHistory, SongLater, MonthlyMission, UserMissionProgress, ChatRoom, Message
from accounts.models import CustomUser, PurchasedCatchphrase, Friendship, FriendRequest
from collections import defaultdict
from django.db.models import Avg, Max, Min, Count, Q, F
from django.db.models.functions import TruncMonth
from datetime import timedelta, date
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
import statistics
import random
from datetime import datetime
from decimal import Decimal

User = get_user_model()

def index_view(request):
    user_favorites = []
    recommended_songs = []
    latest_score_logs = []

    MonthlyMission.create_default_missions()
    month_start = timezone.now().date().replace(day=1)
    missions = MonthlyMission.objects.filter(month=month_start)

    if request.user.is_authenticated:
        user_favorites = request.user.favorites.all()[:3]

        favorite_artists = request.user.favorites.values_list('artist_name', flat=True).distinct()
        if favorite_artists:
            recommended_songs = (
                Song.objects
                .filter(artist_name__in=favorite_artists)
                .exclude(id__in=request.user.favorites.values_list('id', flat=True))
                .order_by('?')[:3]
            )

        user_mission_data = []
        for mission in missions:
            progress_obj, _ = UserMissionProgress.objects.get_or_create(
                user=request.user,
                mission=mission
            )
            user_mission_data.append({
                "mission": mission,
                "progress": progress_obj.progress,
                "is_completed": progress_obj.is_completed,
            })
    else:
        user_mission_data = []
    first_favorite = user_favorites[0] if user_favorites else None

    if first_favorite:
        logs = (
            ScoreLog.objects
            .filter(user=request.user, song=first_favorite)
            .order_by('-created_at')[:2]
        )

        grouped = defaultdict(list)
        for log in logs:
            key = (log.song.track_name, log.song.artist_name)
            grouped[key].append(log)

        latest_score_logs = [
            {
                'track_name': k[0],
                'artist_name': k[1],
                'logs': v,
                'song': v[0].song,
            }
            for k, v in grouped.items()
        ]

    context = {
        "user_favorites": user_favorites,
        "latest_score_logs": latest_score_logs,
        "recommended_songs": recommended_songs,
        "user_mission_data": user_mission_data,
    }

    return render(request, "app/index.html", context)

def setting_view(request):
    user = request.user  

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "theme":
            selected_theme = request.POST.get("theme")
            user.theme = selected_theme 
            user.save()
            return redirect("app:setting")
        elif form_type == "language":
            lang_code = request.POST.get("language")
            request.session[settings.LANGUAGE_COOKIE_NAME] = lang_code
            translation.activate(lang_code)
            return redirect(request.path)
        elif form_type == "privacy":
            is_public = request.POST.get("is_public") == "true"
            user.is_public = is_public
            user.save()
            return redirect("app:setting")

    return render(request, "app/setting.html")

# プロフィール

def profile_view_context(user):
    max_score = user.score_logs.aggregate(Max('score'))['score__max'] or 0
    top_score_log = user.score_logs.order_by('-score', '-created_at').first()

    today = date.today()
    start_month = add_months(today.replace(day=1), -11)
    months = [add_months(start_month, i).strftime('%Y-%m') for i in range(12)]

    monthly_stats_qs = (
        user.score_logs
        .filter(created_at__date__gte=start_month)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score'),
            play_count=Count('id')
        )
        .order_by('month')
    )

    month_map = {stat['month'].strftime('%Y-%m'): stat for stat in monthly_stats_qs}

    monthly_stats = []
    for m in months:
        stat = month_map.get(m)
        if stat:
            monthly_stats.append({
                "month": m,
                "avg": float(stat['avg_score']),
                "max": float(stat['max_score']),
                "min": float(stat['min_score']),
                "count": stat['play_count'],
            })
        else:
            monthly_stats.append({
                "month": m,
                "avg": 0,
                "max": 0,
                "min": 0,
                "count": 0,
            })

    diff_data = []
    if len(monthly_stats) >= 2:
        last, prev = monthly_stats[-1], monthly_stats[-2]
        diff_data = [{
            "month": last["month"],
            "diff": last["count"] - prev["count"]
        }]

    radar_data = get_user_radar_data(user)

    monthly_counts_qs = (
        user.score_logs
        .filter(created_at__date__gte=start_month)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
    )
    month_count_map = {item['month'].strftime('%Y-%m'): item['count'] for item in monthly_counts_qs}
    yearly_monthly_counts = [{"month": m, "count": month_count_map.get(m, 0)} for m in months]

    return {
        "user": user,
        "high_score": max_score,
        "top_score_song": top_score_log.song if top_score_log else None,
        "top_score_date": top_score_log.created_at if top_score_log else None,
        "monthly_stats": monthly_stats,
        "diff_data": diff_data,
        "radar_data": radar_data,
        "yearly_monthly_counts": yearly_monthly_counts
    }

def get_user_radar_data(user):
    logs = user.score_logs.all()

    if not logs.exists():
        # データがない場合は0で返す
        return {
            "安定ボイス": 0,
            "成長力": 0,
            "挑戦度": 0,
            "継続力": 0,
            "歌い込み量": 0,
        }

    # ① 安定ボイス：標準偏差の逆数（点数の安定性）
    scores = [float(log.score) for log in logs] 
    avg_score = sum(scores) / len(scores)
    variance = sum((s - avg_score)**2 for s in scores) / len(scores)
    stability = max(0, 100 - variance**0.5)  # 標準偏差が小さいほど高評価

    # ② 成長力：過去3か月での平均点差
    now = timezone.now()
    three_months_ago = now - timedelta(days=90)
    recent_logs = logs.filter(created_at__gte=three_months_ago)
    older_logs = logs.filter(created_at__lt=three_months_ago)
    recent_avg = recent_logs.aggregate(avg=Avg('score'))['avg'] or 0
    older_avg = older_logs.aggregate(avg=Avg('score'))['avg'] or 0
    growth = max(0, min(100, (recent_avg - older_avg) + 50))  # 差を0-100に正規化

    # ③ 挑戦度：新曲の割合（過去1か月）
    month_start = now.replace(day=1)
    new_songs = logs.filter(created_at__gte=month_start).values('song').distinct().count()
    total_songs = logs.values('song').distinct().count()
    challenge = int(100 * new_songs / total_songs) if total_songs else 0

    # ④ 継続力：歌った日数 / 今月の日数
    days_played = logs.filter(created_at__gte=month_start).dates('created_at', 'day').count()
    continuity = int(100 * days_played / now.day)

    # ⑤ 歌い込み量：曲数 / 過去最大曲数
    total_songs_played = logs.values('song').distinct().count()
    max_songs = max(total_songs_played, 1)
    practice = min(100, int(100 * total_songs_played / max_songs))

    return {
        "安定ボイス": round(stability, 1),
        "成長力": round(growth, 1),
        "挑戦度": challenge,
        "継続力": continuity,
        "歌い込み量": practice,
    }

def add_months(d, months):
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    return date(year, month, 1)

@login_required
def profile_view(request):
    context = profile_view_context(request.user)
    return render(request, "app/profile.html", context)

@login_required
def friend_profile_view(request, friend_id):
    friend = get_object_or_404(CustomUser, id=friend_id)
    context = profile_view_context(friend)  
    return render(request, "app/profile.html", context)

@login_required
def profile_edit_view(request):
    user = request.user
    max_score = user.score_logs.aggregate(Max('score'))['score__max'] or 0

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        bio = request.POST.get("bio")  
        avatar = request.FILES.get("avatar")  
        catchphrase = request.POST.get("catchphrase")

        if username:
            user.username = username
        if email:
            user.email = email
        user.bio = bio
        if avatar:
            user.avatar = avatar 
        if catchphrase in dict(user.CATCHPHRASE_CHOICES):
            user.catchphrase = catchphrase
        user.save()

        return redirect('app:profile')

    context = {
        "high_score": max_score,
        "user": user,
    }
    return render(request, "app/profile_edit.html", context)

def song_list_view(request):
    query = request.GET.get("q")
    if not query:
        return redirect("/?error=1")

    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "country": "JP",
        "limit": 30,
    }
    response = requests.get(url, params=params)
    data = response.json()
    songs = data.get("results", [])

    # ⭐ previewUrl → Song.id を song 自体に埋める
    for s in songs:
        s["song_id"] = None

        if s.get("previewUrl"):
            song_obj, _ = Song.objects.get_or_create(
                preview_url=s["previewUrl"],
                defaults={
                    "track_name": s["trackName"],
                    "artist_name": s["artistName"],
                    "album_name": s.get("collectionName", ""),
                    "artwork_url": s.get("artworkUrl100", ""),
                    "genre": s.get("primaryGenreName", ""),
                }
            )
            s["song_id"] = song_obj.id

    context = {
        "query": query,
        "songs": songs,
    }
    return render(request, "app/song_list.html", context)

@login_required
def song_detail_view(request):
    preview_url = request.GET.get("preview_url")
    query = request.GET.get("q")  

    if not preview_url:
        return redirect("app:song-list")

    song = Song.objects.filter(preview_url=preview_url).first()
    if not song:
        return redirect("app:song-list")

    SongHistory.objects.create(user=request.user, song=song)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            request.user.favorites.add(song)
        elif action == "remove":
            request.user.favorites.remove(song)

        redirect_url = f"{reverse('app:song-detail')}?preview_url={preview_url}"
        if query:
            redirect_url += f"&q={query}"
        return redirect(redirect_url)

    is_favorite = request.user.favorites.filter(id=song.id).exists()

    context = {
        "song_obj": song,
        "is_favorite": is_favorite,
        "query": query,  
    }
    return render(request, "app/song_detail.html", context)

@login_required
def favorite_view(request):
    user_favorites = request.user.favorites.all()

    query = request.GET.get('q', '').strip()
    if query:
        user_favorites = user_favorites.filter(
            track_name__icontains=query
        ) | user_favorites.filter(
            artist_name__icontains=query
        )

    context = {
        "user_favorites": user_favorites,
        "query": query, 
    }
    return render(request, "app/favorite.html", context)

@login_required
def favorite_detail_view(request, song_id):
    song = get_object_or_404(request.user.favorites, id=song_id)

    if song.lyrics:
        paragraphs = [p for p in song.lyrics.split("\n") if p.strip()]
    else:
        paragraphs = []

    score_logs = (
        ScoreLog.objects
        .filter(user=request.user, song=song)
        .order_by('created_at')
    )
    

    score_data = [
        {
            "date": log.created_at.strftime('%Y-%m-%d'),
            "score": float(log.score),
        }
        for log in score_logs
    ]

    scores = [float(log.score) for log in score_logs]

    aptitude_percent = None
    aptitude_messages = []

    if scores:
        avg_score = statistics.mean(scores)
        aptitude_percent = min(int(avg_score), 100)

        if len(scores) >= 5:
            std_dev = statistics.pstdev(scores)
            penalty = min(std_dev * 2, 10)
            aptitude_percent = max(aptitude_percent - int(penalty), 0)

        if avg_score >= 90:
            absolute_text = "平均90点以上"
        elif avg_score >= 85:
            absolute_text = "平均85点以上"
        else:
            absolute_text = "やや挑戦的な曲"

        all_user_scores = ScoreLog.objects.filter(
            user=request.user
        ).values_list("score", flat=True)

        if all_user_scores.count() >= 3:
            user_avg_score = statistics.mean(map(float, all_user_scores))
            diff = avg_score - user_avg_score

            if diff >= 3:
                relative_text = f"あなたの平均より高得点（+{diff:.1f}点）"
            elif diff >= 0:
                relative_text = "あなたの平均と同程度"
            else:
                relative_text = f"あなたの平均よりやや低め（{diff:.1f}点）"
        else:
            relative_text = None

        if relative_text:
            aptitude_messages.append(f"{absolute_text} — {relative_text}")
        else:
            aptitude_messages.append(absolute_text)

        if len(scores) < 5:
            aptitude_messages.append(f"データ数：{len(scores)}回 (※データ数が少ないため参考値です)")
        else:
            aptitude_messages.append(f"データ数：{len(scores)}回")

    context = {
        "song_obj": song,
        "paragraphs": paragraphs,  
        "is_favorite": True,
        "score_logs": score_logs,
        "score_data": score_data,
        "aptitude_percent": aptitude_percent,
        "aptitude_messages": aptitude_messages,

    }
    return render(request, "app/favorite_detail.html", context)

@login_required
def favorite_remove_view(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    if request.method == "POST":
        if request.user.favorites.filter(id=song.id).exists():
            request.user.favorites.remove(song)
        
    return redirect('app:favorite') 

@login_required
def save_lyrics(request, song_id):
    song = get_object_or_404(Song, id=song_id)

    if request.method == "POST":
        lyrics_raw = request.POST.get("lyrics", "")
        paragraphs = [f"<p>{line.strip()}</p>" for line in lyrics_raw.split("\n") if line.strip()]
        song.lyrics = "\n".join(paragraphs)
        song.save()

        return redirect('app:favorite-detail', song_id=song.id)

@login_required
def calc_view(request):
    result = None
    recommended_songs = []
    number_of_people = request.POST.get("number_of_people", "")
    total_minutes = request.POST.get("total_minutes", "")

    if request.method == "POST":
        try:
            number_of_people_int = int(number_of_people)
            total_minutes_int = int(total_minutes)
        except ValueError:
            number_of_people_int = 0
            total_minutes_int = 0

        if number_of_people_int > 0 and total_minutes_int > 0:
            minutes_per_person = total_minutes_int // number_of_people_int
            min_songs = minutes_per_person // 5
            max_songs = minutes_per_person // 4

            result = {
                "minutes_per_person": minutes_per_person,
                "min_songs": min_songs,
                "max_songs": max_songs,
            }

            user_favorites = list(request.user.favorites.all())
            if user_favorites:
                recommended_songs = random.sample(
                    user_favorites,
                    min(max_songs, len(user_favorites))
                )

    later_ids = set(
        request.user.later_songs.values_list('song_id', flat=True)
    )

    context = {
        "result": result,
        "number_of_people": number_of_people,
        "total_minutes": total_minutes,
        "recommended_songs": recommended_songs,
        "later_ids": later_ids,
    }

    return render(request, "app/calc.html", context)

@login_required
def quiz_view(request):
    user_favorites = list(request.user.favorites.all())

    if len(user_favorites) < 4:
        return render(request, "app/quiz.html", {
            "error": True,
            "fav_song": None,
            "choices": [],
            "correct": None
        })

    if request.method == "POST":
        fav_song_id = request.session.get("fav_song_id")
        choices_ids = request.session.get("choices_ids", [])

        if not fav_song_id:
            return redirect("app:quiz")

        fav_song = next((s for s in user_favorites if s.id == fav_song_id), None)
        if not fav_song:
            return redirect("app:quiz")

        selected_id = None
        for key, value in request.POST.items():
            if key.startswith("draw_"):
                try:
                    selected_id = int(value)
                except ValueError:
                    selected_id = None
                break

        correct = (selected_id == fav_song.id) if selected_id else False

        if correct:
            month_start = timezone.now().date().replace(day=1)
            mission = MonthlyMission.objects.filter(
                month=month_start,
                title="クイズを3問正解する"
            ).first()

            if mission:
                progress_obj, created = UserMissionProgress.objects.get_or_create(
                    user=request.user,
                    mission=mission
                )

                progress_obj.progress += 1

                if progress_obj.is_completed and not progress_obj.reward_received:
                    request.user.points += 10  
                    request.user.save()
                    progress_obj.reward_received = True  

                progress_obj.save()

        request.session.pop("fav_song_id", None)
        request.session.pop("choices_ids", None)

        return render(request, "app/quiz.html", {
            "fav_song": fav_song,
            "choices": [],  
            "correct": correct,
            "error": False
        })

    fav_song = random.choice(user_favorites)
    other_choices = [s for s in user_favorites if s.id != fav_song.id]
    choices = random.sample(other_choices, 3) + [fav_song]
    random.shuffle(choices)

    request.session["fav_song_id"] = fav_song.id
    request.session["choices_ids"] = [c.id for c in choices]

    context = {
        "fav_song": fav_song,
        "choices": choices,
        "correct": None,
        "error": False
    }
    return render(request, "app/quiz.html", context)

@login_required
def toggle_later(request, song_id):
    if request.method == "POST":
        song = get_object_or_404(Song, id=song_id)
        later, created = SongLater.objects.get_or_create(
            user=request.user,
            song=song
        )
        if not created:
            later.delete()
            status = "removed"
        else:
            status = "added"
        return JsonResponse({"status": status, "song_id": song_id})
    return JsonResponse({"status": "error"}, status=400)

@login_required
def sing_later_view(request):
    user_later_songs = request.user.later_songs.select_related('song').all().values_list('song', flat=True)
    songs = Song.objects.filter(id__in=user_later_songs)

    query = request.GET.get('q', '').strip()
    if query:
        songs = songs.filter(
            track_name__icontains=query
        ) | songs.filter(
            artist_name__icontains=query
        )

    context = {
        "songs": songs,
        "query": query,
    }
    return render(request, "app/sing_later.html", context)

@login_required
def unlock_view(request):
    user = request.user

    purchasable_catchphrases = [
        ('intermediate', '中級者', 50),  
        ('advanced', '上級者', 100),     
    ]
    purchased = user.purchased_catchphrases.values_list('catchphrase', flat=True)

    if request.method == 'POST':
        selected = request.POST.get('catchphrase')
        item = next((x for x in purchasable_catchphrases if x[0] == selected), None)
        if item:
            key, label, cost = item
            if key in purchased:
                messages.info(request, f"{label}は既に購入済みです。")
            elif user.points >= cost:
                user.points -= cost
                user.save()
                PurchasedCatchphrase.objects.create(user=user, catchphrase=key)
                messages.success(request, f"{label}を購入しました！")
            else:
                messages.error(request, f"ポイントが足りません ({cost}pt必要です)。")
        else:
            messages.error(request, "無効な選択です。")
        return redirect('app:unlock')

    context = {
        "user": user,
        "purchasable_catchphrases": purchasable_catchphrases,
        "purchased": purchased,
    }
    return render(request, "app/unlock.html", context)

# フレンド

@login_required
def friends_list_view(request):
    user = request.user
    query = request.GET.get('q', '').strip()

    friends = User.objects.filter(
        id__in=Friendship.objects.filter(user=user).values_list('friend_id', flat=True)
    )

    ranking_users = list(friends) + [user]

    pending_requests = FriendRequest.objects.filter(to_user=user)

    search_results = []
    if query:
        friend_ids = friends.values_list('id', flat=True)
        search_results = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id__in=friend_ids).exclude(id=user.id)

    friends_of_friends_ids = Friendship.objects.filter(
        user__in=friends
    ).values_list('friend_id', flat=True)
    friends_of_friends_ids = set(friends_of_friends_ids) - set(friends.values_list('id', flat=True)) - {user.id}
    recommended_users = User.objects.filter(id__in=list(friends_of_friends_ids)[:3])

    month_start = datetime.now().replace(day=1)
    friend_scores = ScoreLog.objects.filter(
        user__in=ranking_users,
        created_at__gte=month_start
    )

    monthly_play_count_ranking = (
        friend_scores.values('user__id', 'user__username')
        .annotate(count=Count('id'))
        .order_by('-count')[:3]
    )

    monthly_max_score_ranking = (
        friend_scores.values('user__id', 'user__username')
        .annotate(max_score=Max('score'))
        .order_by('-max_score')[:3]
    )

    monthly_min_score_ranking = (
        friend_scores.values('user__id', 'user__username')
        .annotate(min_score=Min('score'))
        .order_by('min_score')[:3]
    )

    context = {
        'friends': friends,
        'pending_requests': pending_requests,
        'search_results': search_results,
        'query': query,
        'recommended_users': recommended_users,
        'monthly_play_count_ranking': monthly_play_count_ranking,
        'monthly_max_score_ranking': monthly_max_score_ranking,
        'monthly_min_score_ranking': monthly_min_score_ranking,
    }

    return render(request, 'app/friends_list.html', context)

@login_required
def send_friend_request_view(request, user_id):
    to_user = get_object_or_404(User, id=user_id)

    if to_user == request.user:
        return redirect('app:friends-list')

    if Friendship.objects.filter(user=request.user, friend=to_user).exists():
        return redirect('app:friends-list')

    FriendRequest.objects.get_or_create(
        from_user=request.user,
        to_user=to_user
    )

    return redirect('app:friends-list')

@login_required
def accept_friend_request_view(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user
    )

    if friend_request.from_user == friend_request.to_user:
        friend_request.delete()
        messages.error(request, "自分自身にフレンド申請はできません。")
        return redirect('app:friends-list')

    if friend_request.from_user != friend_request.to_user:
        Friendship.objects.create(
            user=friend_request.from_user,
            friend=friend_request.to_user
        )
        Friendship.objects.create(
            user=friend_request.to_user,
            friend=friend_request.from_user
        )

    friend_request.delete()
    return redirect('app:friends-list')

@login_required
def reject_friend_request_view(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user
    )
    friend_request.delete()
    return redirect('app:friends-list')

@login_required
def chat_with_user_view(request, user_id):
    friend = get_object_or_404(CustomUser, id=user_id)

    room = ChatRoom.objects.filter(participants=request.user)\
                           .filter(participants=friend)\
                           .first()
    if room is None:
        room = ChatRoom.objects.create(name=f"{request.user.username} & {friend.username}")
        room.participants.add(request.user, friend)

    messages = room.messages.order_by('created_at')
    
    return render(request, 'app/chat_room.html', {
        'room': room,
        'messages': messages,
        'friend': friend
    })

@login_required
def send_message_view(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        image = request.FILES.get("image")

        if text or image:
            Message.objects.create(
                room=room,
                sender=request.user,
                content=text,
                image=image
            )

        friend = room.participants.exclude(id=request.user.id).first()
        return redirect('app:chat-with-user', user_id=friend.id)

    messages = room.messages.order_by('created_at')
    friend = room.participants.exclude(id=request.user.id).first()

    return render(request, 'app/chat_room.html', {
        'room': room,
        'messages': messages,
        'friend': friend
    })

@login_required
def delete_message_view(request, message_id):
    message = get_object_or_404(Message, id=message_id)

    if message.sender != request.user:
        return redirect('app:chat-with-user',
                        user_id=message.room.participants.exclude(id=request.user.id).first().id)

    room = message.room
    message.delete()

    friend = room.participants.exclude(id=request.user.id).first()
    return redirect('app:chat-with-user', user_id=friend.id)

@login_required
def ranking_view(request):
    user = request.user
    song_id = request.GET.get('song_id')

    selected_song = None
    if song_id:
        try:
            selected_song = Song.objects.get(id=song_id)
            if not selected_song.favorited_by.filter(id=user.id).exists():
                selected_song.favorited_by.add(user)
        except Song.DoesNotExist:
            selected_song = None

    friends_ids = set(
        Friendship.objects.filter(user=user).values_list('friend_id', flat=True)
    ) | set(
        Friendship.objects.filter(friend=user).values_list('user_id', flat=True)
    )

    pending_ids = set(
        FriendRequest.objects.filter(from_user=user)
        .values_list('to_user_id', flat=True)
    )

    favorite_songs = (
        Song.objects
        .filter(favorited_by=user)
        .order_by('artist_name', 'track_name')
    )

    songs_by_artist = {}
    for song in favorite_songs:
        songs_by_artist.setdefault(song.artist_name, []).append(song)

    def build_ranking(qs, include_song=True):
        rankings = []
        rank = 1

        for log in qs:
            target_user = log.user

            if not target_user.is_public:
                friend_status = "非公開"
            elif target_user.id == user.id:
                friend_status = "-"
            elif target_user.id in friends_ids:
                friend_status = "済"
            elif target_user.id in pending_ids:
                friend_status = "申請中"
            else:
                friend_status = "申請"

            rankings.append({
                "rank": rank,
                "user": target_user,
                "username": target_user.username if target_user.is_public else "???",
                "score": log.score,
                "song": log.song.track_name if include_song else None,
                "friend_status": friend_status,
            })

            rank += 1
            if rank > 100:
                break

        return rankings

    def get_ranking(karaoke_type):
        if selected_song:
            qs = (
                ScoreLog.objects
                .filter(song=selected_song, karaoke_type=karaoke_type)
                .select_related('user', 'song')
                .order_by('-score', 'created_at')
            )
            return build_ranking(qs, include_song=False)

        qs = (
            ScoreLog.objects
            .filter(karaoke_type=karaoke_type)
            .select_related('user', 'song')
            .order_by('-score', 'created_at')
        )
        return build_ranking(qs)

    dam_ranking = get_ranking('DAM')
    joy_ranking = get_ranking('JOY')

    context = {
        "songs_by_artist": songs_by_artist,
        "selected_song_id": song_id,
        "selected_song": selected_song,
        "dam_ranking": dam_ranking,
        "joy_ranking": joy_ranking,
    }

    return render(request, "app/ranking.html", context)

class ScoreLogCreateView(LoginRequiredMixin, CreateView):
    model = ScoreLog
    fields = ['song', 'key', 'score', 'karaoke_type', 'image']
    template_name = 'app/create_score.html'
    success_url = reverse_lazy('app:score_list')

    def get(self, request, *args, **kwargs):
        song_id = request.GET.get("song_id")
        if song_id:
            try:
                song = Song.objects.get(id=song_id)
                if not song.favorited_by.filter(id=request.user.id).exists():
                    song.favorited_by.add(request.user)
            except Song.DoesNotExist:
                pass

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        songs = Song.objects.filter(favorited_by=self.request.user)
        artists = songs.values_list('artist_name', flat=True).distinct()
        context['artists'] = artists
        context['songs'] = songs
        return context

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['song'].queryset = Song.objects.filter(
            favorited_by=self.request.user
        )

        song_id = self.request.GET.get('song_id')
        if song_id:
            try:
                song = Song.objects.get(id=song_id)
                if song in form.fields['song'].queryset:
                    form.fields['song'].initial = song
            except Song.DoesNotExist:
                pass

        return form
    
    def update_missions(self, score_log):
        user = self.request.user
        month_start = timezone.now().date().replace(day=1)

        mission_update_4 = MonthlyMission.objects.filter(
            month=month_start,
            title="4曲点数更新する"
        ).first()

        if mission_update_4:
            updated_songs_count = ScoreLog.objects.filter(
                user=user,
                created_at__month=month_start.month,
                created_at__year=month_start.year
            ).values('song').distinct().count()

            progress_obj, _ = UserMissionProgress.objects.get_or_create(
                user=user,
                mission=mission_update_4
            )
            progress_obj.progress = updated_songs_count

            if progress_obj.progress >= mission_update_4.goal:
                if progress_obj.is_completed and not progress_obj.reward_received:
                    user.points += mission_update_4.reward_points
                    user.save()
                    progress_obj.reward_received = True

            progress_obj.save()

        mission_90 = MonthlyMission.objects.filter(
            month=month_start,
            title="特定の曲で90点以上を出す"
        ).first()

        if mission_90:
            best_score = ScoreLog.objects.filter(
                user=user,
                created_at__month=month_start.month,
                created_at__year=month_start.year
            ).aggregate(Max('score'))['score__max'] or 0

            progress_obj, _ = UserMissionProgress.objects.get_or_create(
                user=user,
                mission=mission_90
            )
            progress_obj.progress = best_score

            if progress_obj.progress >= mission_90.goal:
                if not progress_obj.reward_received:
                    user.points += mission_90.reward_points
                    user.save()
                    progress_obj.reward_received = True

            progress_obj.save()

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        self.update_missions(form.instance)
        return response

class ScoreLogListView(LoginRequiredMixin, ListView):
    model = ScoreLog
    template_name = 'app/score_list.html'
    context_object_name = 'score_logs_grouped'

    def get_queryset(self):
        logs = ScoreLog.objects.filter(user=self.request.user).order_by('-created_at')

        query = self.request.GET.get('q', '').strip()
        if query:
            logs = logs.filter(
                song__track_name__icontains=query
            ) | logs.filter(
                song__artist_name__icontains=query
            )

        grouped = defaultdict(list)
        for log in logs:
            key = (log.song.track_name, log.song.artist_name)
            grouped[key].append(log)

        return [
            {
                'track_name': k[0],
                'artist_name': k[1],
                'logs': v,
                'song': v[0].song,
            }
            for k, v in grouped.items()
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context 

class ScoreLogDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ScoreLog
    template_name = 'app/delete_score.html'
    success_url = reverse_lazy('app:score_list')  

    def test_func(self):
        score = self.get_object()
        return score.user == self.request.user 

class HistoryListView(LoginRequiredMixin, ListView):
    model = SongHistory
    template_name = "app/history.html"
    context_object_name = "histories"

    def get_queryset(self):
        return SongHistory.objects.filter(user=self.request.user)

