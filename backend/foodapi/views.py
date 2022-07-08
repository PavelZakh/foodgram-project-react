from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from djoser.views import UserViewSet
from django.db.models import F, Sum
from django.contrib.auth import get_user_model
from django.http.response import HttpResponse

from .models import (Ingredient, Tag, Recipe, Cart,
                     Favorite, Follow, IngredientsAmount)
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
from .serializers import (TagSerializer, IngredientSerializer,
                          RecipeSerializer, FollowSerializer, ShoppingCartSerializer)
from .pagination import LimitPageNumberPagination
from .filters import RecipeFilter, IngredientFilter

User = get_user_model()


class FixedUserViewSet(UserViewSet):
    pagination_class = LimitPageNumberPagination

    @action(detail=True, permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)
        user = request.user

        if author == user:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя!'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow = Follow.objects.filter(user=user, author=author)
        if follow.exists():
            return Response(
                {'errors': 'Нельзя подписаться на пользователя дважды!'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow = Follow.objects.create(user=user, author=author)
        serializer = FollowSerializer(
            follow,
            context={'request': request},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = Follow.objects.filter(user=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @subscribe.mapping.delete
    def del_subscribe(self, request, id):
        author = get_object_or_404(User, id=id)
        user = request.user

        if user == author:
            return Response(
                {'errors': 'Нельзя отписаться от самого себя!'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow = Follow.objects.filter(user=user, author=author)
        if follow.exists():
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'errors': 'Вы уже отписались'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    pagination_class = LimitPageNumberPagination
    filter_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        if request.method == 'GET':
            return self.add_db_record(request.user, Cart, pk)
        elif request.method == 'DELETE':
            return self.delete_db_record(request.user, Cart, pk)
        return None

    @action(detail=True, methods=['get', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        if request.method == 'GET':
            return self.add_db_record(request.user, Favorite, pk)
        elif request.method == 'DELETE':
            return self.delete_db_record(request.user, Favorite, pk)
        return None

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = IngredientsAmount.objects.filter(
            recipe__in=(user.carts.values('id'))
        ).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit'),
        ).annotate(amount=Sum('amount'))
        filename = f'{user.username}_shopping_list.txt'
        text = f'Список покупок пользователя {user.username}:\n'
        for ingr in ingredients:
            text += f'{ingr["name"]} {ingr["measurement_unit"]} - {ingr["amount"]}\n'
        response = HttpResponse(
            text, content_type='text.txt; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    def delete_db_record(self, user, model, pk):
        record = model.objects.filter(user=user, recipe__id=pk)
        if record.exists():
            record.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Рецепт не найден!'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def add_db_record(self, user, model, pk):
        record = model.objects.filter(user=user, recipe__id=pk)
        if record.exists():
            return Response(
                {'errors': 'Рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = ShoppingCartSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
