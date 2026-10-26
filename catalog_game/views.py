import copy
import re

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Avg, Count, F, Q, Value
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .age import allowed_ratings, user_age
from .forms import (CatalogFilterForm, GameForm, PickForm, ProfileForm, RegisterForm,
                    ReviewForm, UkrainianPasswordChangeForm)
from .models import Developers, Games, Genre, Platform, Reviews, Wishlist


LOGIN_BACKEND = 'catalog_game.backends.EmailBackend'


def rated_games(user):

    return (Games.objects.visible_to(user)
            .select_related('id_dev').prefetch_related('genres')
            .annotate(avg=Avg('reviews__rating'), votes=Count('reviews', distinct=True)))


def visible_count(user, relation='games'):

    return Count(relation, filter=Q(**{f'{relation}__pk__in': Games.objects.visible_to(user).values('pk')}),
                 distinct=True)


def _int(value):
    if isinstance(value, str) and re.fullmatch(r'[0-9]{1,9}', value):
        return int(value)
    return None


def _ids(values):
    return [n for n in (_int(v) for v in values) if n is not None]


def _back(request, fallback):
    nxt = request.POST.get('next', '')
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}):
        return redirect(nxt)
    return redirect(fallback)


def _ages(user):

    return allowed_ratings(user_age(user), Games.AGE_CHOICES)


def can_manage_game(user, game, perm):

    return user.is_authenticated and user.has_perm(perm)



def age_context(request):

    return {'age_limit': user_age(request.user), 'age_is_guest': not request.user.is_authenticated
            or request.user.date_of_birth is None}


def home(request):
    user = request.user
    return render(request, 'catalog_game/home.html', {
        'newest': rated_games(user).order_by(F('release_date').desc(nulls_last=True), 'title')[:8],
        'top': rated_games(user).filter(votes__gt=0).order_by('-avg', '-votes')[:4],
        'genres': Genre.objects.annotate(n=visible_count(user)).filter(n__gt=0).order_by('-n')[:10],
        'total': Games.objects.visible_to(user).count(),
        **age_context(request),
    })


def _pick_results(data, gids, pids, user):
    if gids:
        match = Count('genres', filter=Q(genres__in=gids), distinct=True)
    else:
        match = Value(0)
    qs = rated_games(user).annotate(match=match)
    if gids:
        qs = qs.filter(match__gt=0)
    if pids:
        qs = qs.filter(pk__in=Games.objects.filter(platforms__in=pids).values('pk'))
    if data['max_price'] is not None:
        qs = qs.filter(price__lte=data['max_price'])
    if data['max_size'] is not None:
        qs = qs.filter(file_size_gb__lte=data['max_size'])
    if data['age']:
        qs = qs.filter(age_rating=data['age'])
    if data['min_rating']:
        qs = qs.filter(avg__gte=data['min_rating'])
    return list(qs.order_by('-match', F('avg').desc(nulls_last=True), 'title')[:24])


def pick(request):
    g = request.GET
    ages = _ages(request.user)
    searched = 'go' in g
    sel_genres, sel_platforms = _ids(g.getlist('genre')), _ids(g.getlist('platform'))
    form = PickForm(g if searched else None, ages=ages)
    ctx = {'genres': Genre.objects.all(), 'platforms': Platform.objects.all(), 'ages': ages,
           'f': g, 'sel_genres': sel_genres, 'sel_platforms': sel_platforms,
           'searched': searched, 'errors': {}, **age_context(request)}
    if searched:
        if form.is_valid():
            try:
                ctx['results'] = _pick_results(form.cleaned_data, sel_genres, sel_platforms, request.user)
            except (DatabaseError, ArithmeticError, ValueError):
                ctx['results'] = []
                ctx['search_error'] = True
        else:
            ctx['errors'] = {name: errs[0] for name, errs in form.errors.items()}
    return render(request, 'catalog_game/pick.html', ctx)




class GameListView(ListView):

    template_name = 'catalog_game/catalog.html'
    paginate_by = 12
    SORTS = {
        'new': F('release_date').desc(nulls_last=True),
        'old': F('release_date').asc(nulls_last=True),
        'cheap': F('price').asc(nulls_last=True),
        'pricey': F('price').desc(nulls_last=True),
        'rating': F('avg').desc(nulls_last=True),
        'title': F('title').asc(),
    }

    def paginate_queryset(self, queryset, page_size):

        paginator = self.get_paginator(queryset, page_size, orphans=self.get_paginate_orphans(),
                                       allow_empty_first_page=self.get_allow_empty())
        page = paginator.get_page(self.request.GET.get('page'))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_queryset(self):
        g = self.request.GET
        qs = rated_games(self.request.user)
        q = g.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(id_dev__name_dev__icontains=q))
        genre_id, platform_id, dev_id = _int(g.get('genre', '')), _int(g.get('platform', '')), _int(g.get('dev', ''))
        if genre_id is not None:
            qs = qs.filter(pk__in=Games.objects.filter(genres__pk=genre_id).values('pk'))
        if platform_id is not None:
            qs = qs.filter(pk__in=Games.objects.filter(platforms__pk=platform_id).values('pk'))
        if dev_id is not None:
            qs = qs.filter(id_dev=dev_id)
        if g.get('age') in _ages(self.request.user):
            qs = qs.filter(age_rating=g['age'])

        form = CatalogFilterForm(g)
        self.filter_errors = {}
        if form.is_valid():
            pmin, pmax = form.cleaned_data['price_min'], form.cleaned_data['price_max']
            if pmin is not None:
                qs = qs.filter(price__gte=pmin)
            if pmax is not None:
                qs = qs.filter(price__lte=pmax)
        else:

            self.filter_errors = {name: errs[0] for name, errs in form.errors.items()}
            qs = qs.none()
        if g.get('free'):
            qs = qs.filter(price=0)

        self.sort = g.get('sort', 'new')
        order = self.SORTS.get(self.sort, self.SORTS['new'])
        return qs.order_by(order, 'title')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        keep = self.request.GET.copy()
        keep.pop('page', None)
        ctx.update({
            'total': ctx['paginator'].count, 'sort': self.sort, 'keep': keep.urlencode(),
            'genres': Genre.objects.all(), 'platforms': Platform.objects.all(),
            'devs': Developers.objects.all(), 'ages': _ages(self.request.user),
            'f': self.request.GET, 'errors': self.filter_errors,
            **age_context(self.request),
        })
        return ctx


def review_context(request, game, form=None, editing=False):

    reviews = game.reviews.select_related('id_user').order_by('-review_date', '-id_review')
    ctx = {'reviews': reviews, 'form': form, 'mine': None, 'edit_review': False, 'in_wishlist': False,
           'genres': game.genres.all(), 'platforms': game.platforms.all()}
    if request.user.is_authenticated:
        ctx['mine'] = Reviews.objects.filter(id_user=request.user, id_game=game).first()
        ctx['in_wishlist'] = Wishlist.objects.filter(id_user=request.user, id_game=game).exists()

    ctx['edit_review'] = editing and ctx['mine'] is not None
    if form is None:
        ctx['form'] = ReviewForm(instance=ctx['mine'],
                                 author=request.user if request.user.is_authenticated else None, game=game)
    return ctx


class GameDetailView(DetailView):
    context_object_name = 'game'
    template_name = 'catalog_game/game_detail.html'

    def get_queryset(self):

        return rated_games(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        game, user = ctx['game'], self.request.user
        ctx.update(review_context(self.request, game, editing=self.request.GET.get('edit_review') == '1'))
        ctx['can_edit'] = can_manage_game(user, game, 'catalog_game.change_games')
        return ctx


class GameCreateView(LoginRequiredMixin, CreateView):
    model = Games
    form_class = GameForm
    template_name = 'catalog_game/game_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Гру «{self.object.title}» додано до каталогу.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['heading'] = 'Додати гру'
        return ctx


class GameAccessMixin(UserPassesTestMixin):

    perm = None

    def test_func(self):
        return can_manage_game(self.request.user, self.get_object(), self.perm)


class GameUpdateView(GameAccessMixin, UpdateView):
    model = Games
    form_class = GameForm
    template_name = 'catalog_game/game_form.html'
    perm = 'catalog_game.change_games'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Зміни збережено.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['heading'] = f'Редагувати: {self.object.title}'
        return ctx


class GameDeleteView(GameAccessMixin, DeleteView):
    model = Games
    template_name = 'catalog_game/game_confirm_delete.html'
    success_url = reverse_lazy('catalog_game:catalog')
    perm = 'catalog_game.delete_games'

    def form_valid(self, form):
        title = self.object.title
        response = super().form_valid(form)
        messages.success(self.request, f'Гру «{title}» видалено.')
        return response




class DeveloperListView(ListView):
    template_name = 'catalog_game/developer_list.html'
    paginate_by = 12

    def get_queryset(self):
        return Developers.objects.annotate(n=visible_count(self.request.user)).order_by('name_dev')


class DeveloperDetailView(DetailView):
    model = Developers
    context_object_name = 'dev'
    template_name = 'catalog_game/developer.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['games'] = rated_games(self.request.user).filter(id_dev=self.object).order_by('title')
        return ctx


class ReferenceListView(ListView):

    template_name = 'catalog_game/reference_list.html'
    heading = ''
    label = ''

    def get_queryset(self):
        return (super().get_queryset().annotate(n=visible_count(self.request.user))
                .order_by(*self.model._meta.ordering))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(heading=self.heading, label=self.label)
        return ctx


class ReferenceDetailView(DetailView):
    template_name = 'catalog_game/reference_detail.html'
    label = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['games'] = rated_games(self.request.user).filter(**{self.lookup: self.object}).order_by('title')
        ctx['label'] = self.label
        ctx['obj_name'] = str(self.object)
        return ctx


class GenreListView(ReferenceListView):
    model, heading, label = Genre, 'Жанри', 'name_genre'


class GenreDetailView(ReferenceDetailView):
    model, label, lookup = Genre, 'Жанр', 'genres'


class PlatformListView(ReferenceListView):
    model, heading, label = Platform, 'Платформи', 'name_platform'


class PlatformDetailView(ReferenceDetailView):
    model, label, lookup = Platform, 'Платформа', 'platforms'


class ReviewListView(PermissionRequiredMixin, ListView):

    permission_required = 'catalog_game.delete_reviews'
    queryset = Reviews.objects.select_related('id_user', 'id_game')
    template_name = 'catalog_game/review_list.html'
    paginate_by = 20


class ReviewDetailView(DetailView):
    context_object_name = 'review'
    template_name = 'catalog_game/review_detail.html'

    def get_queryset(self):

        return (Reviews.objects.select_related('id_user', 'id_game')
                .filter(id_game__in=Games.objects.visible_to(self.request.user).values('pk')))


class ReviewSaveView(LoginRequiredMixin, View):

    http_method_names = ['post']

    def post(self, request, pk):
        game = get_object_or_404(Games.objects.visible_to(request.user), pk=pk)
        mine = Reviews.objects.filter(id_user=request.user, id_game=game).first()
        back = reverse('catalog_game:game_detail', args=[pk]) + '#reviews'

        if mine is not None and request.POST.get('edit') != '1':
            messages.error(request, 'Ви вже залишили відгук на цю гру. Його можна змінити або видалити, але другого не буде.')
            return redirect(back)

        form = ReviewForm(request.POST, instance=mine, author=request.user, game=game)
        if form.is_valid():
            review = form.save(commit=False)
            review.id_user, review.id_game, review.review_date = request.user, game, timezone.now()
            try:
                with transaction.atomic():
                    review.save()
            except IntegrityError:
                messages.error(request, 'Ви вже залишили відгук на цю гру.')
                return redirect(back)
            messages.success(request, 'Ваш відгук оновлено.' if mine else 'Відгук опубліковано.')
            return redirect(back)

        ctx = {'game': game, 'review_failed': True,
               'can_edit': can_manage_game(request.user, game, 'catalog_game.change_games')}
        ctx.update(review_context(request, game, form, editing=mine is not None))
        return render(request, 'catalog_game/game_detail.html', ctx)


class ReviewDeleteView(LoginRequiredMixin, View):

    http_method_names = ['post']

    def post(self, request, pk):
        review = get_object_or_404(Reviews, pk=pk)
        game_id = review.id_game_id
        if review.id_user_id == request.user.pk or request.user.has_perm('catalog_game.delete_reviews'):
            review.delete()
            messages.success(request, 'Відгук видалено.')
        else:
            messages.error(request, 'Ви не можете видалити чужий відгук.')
        return redirect(reverse('catalog_game:game_detail', args=[game_id]) + '#reviews')


@login_required
@require_POST
def wishlist_toggle(request, pk):
    game = get_object_or_404(Games, pk=pk)
    item = Wishlist.objects.filter(id_user=request.user, id_game=game)
    if item.exists():
        item.delete()
        messages.info(request, f'«{game.title}» прибрано з обраного.')
    else:
        if not Games.objects.visible_to(request.user).filter(pk=game.pk).exists():
            raise Http404('Гра недоступна за віком.')
        Wishlist.objects.create(id_user=request.user, id_game=game, added_date=timezone.now())
        messages.success(request, f'«{game.title}» додано до обраного.')
    return _back(request, reverse('catalog_game:game_detail', args=[pk]))


@login_required
def wishlist(request):
    items = (Wishlist.objects.filter(id_user=request.user,
                                     id_game__in=Games.objects.visible_to(request.user).values('pk'))
             .select_related('id_game', 'id_game__id_dev').order_by('-added_date'))
    return render(request, 'catalog_game/wishlist.html', {'items': items})


@login_required
@require_POST
def wishlist_note(request, pk):
    note = request.POST.get('note', '').strip()[:255]
    Wishlist.objects.filter(id_user=request.user, id_game=pk).update(note=note or None)
    messages.success(request, 'Нотатку збережено.' if note else 'Нотатку видалено.')
    return redirect('catalog_game:wishlist')


@login_required
@require_POST
def wishlist_note_delete(request, pk):
    Wishlist.objects.filter(id_user=request.user, id_game=pk).update(note=None)
    messages.success(request, 'Нотатку видалено.')
    return redirect('catalog_game:wishlist')


def register(request):
    if request.user.is_authenticated:
        return redirect('catalog_game:home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save(), backend=LOGIN_BACKEND)
        messages.success(request, 'Ласкаво просимо! Акаунт створено.')
        return redirect('catalog_game:home')
    return render(request, 'catalog_game/register.html', {'form': form})


PROFILE_FORMS = ('profile', 'password')


@login_required
def profile(request):

    form_type = request.POST.get('form_type') if request.method == 'POST' else None
    editing = form_type if form_type in PROFILE_FORMS else request.GET.get('edit')
    if editing not in PROFILE_FORMS:
        editing = None

    profile_form = ProfileForm(request.POST if form_type == 'profile' else None,
                               instance=copy.copy(request.user))
    password_form = UkrainianPasswordChangeForm(request.user, request.POST if form_type == 'password' else None)

    if form_type == 'profile' and profile_form.is_valid():
        profile_form.save()
        messages.success(request, 'Профіль збережено.')
        return redirect('catalog_game:profile')
    if form_type == 'password' and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Пароль успішно змінено.')
        return redirect('catalog_game:profile')

    ratings = _ages(request.user)
    return render(request, 'catalog_game/profile.html', {
        'profile_form': profile_form, 'password_form': password_form, 'editing': editing,
        'age': request.user.age,
        'max_rating': ratings[-1] if ratings else None,
        'age_known': request.user.date_of_birth is not None,
    })


@login_required
@require_POST
def account_delete(request):
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, 'Ваш акаунт видалено.')
    return redirect('catalog_game:home')

