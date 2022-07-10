from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from djoser.views import UserViewSet
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.http.response import HttpResponse

from .models import (Ingredient, Tag, Recipe, Cart,
                     Favorite, Follow, IngredientsAmount)
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
from .serializers import (TagSerializer, IngredientSerializer,
                          RecipeSerializer, FollowSerializer,
                          ShoppingCartSerializer)
from .pagination import LimitPageNumberPagination
from .filters import IngredientFilter, RecipeFilter

User = get_user_model()


class FixedUserViewSet(UserViewSet):
    pagination_class = LimitPageNumberPagination

    @action(detail=True, methods=['delete', 'post'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        user = request.user
        follow = Follow.objects.filter(user=user, author=author)
        if request.method == 'POST':

            if author == user:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя!'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
        elif request.method == 'DELETE':
            if user == author:
                return Response(
                    {'errors': 'Нельзя отписаться от самого себя!'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if follow.exists():
                follow.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {'errors': 'Вы уже отписались'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
                    {'errors': 'Нельзя применить данный метод!'},
                    status=status.HTTP_405_METHOD_NOT_ALLOWED,
                )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
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


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    pagination_class = LimitPageNumberPagination
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['delete', 'post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.add_db_record(request.user, Cart, pk)
        elif request.method == 'DELETE':
            return self.delete_db_record(request.user, Cart, pk)
        return None

    @action(detail=True, methods=['delete', 'post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.add_db_record(request.user, Favorite, pk)
        elif request.method == 'DELETE':
            return self.delete_db_record(request.user, Favorite, pk)
        return None

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = self.request.user
        if not user.carts.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        ingredients = IngredientsAmount.objects.filter(
            recipe__carts__user=request.user).values_list(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(ingr_sum=Sum('amount'))
        filename = f'{user.username}_shopping_list.txt'
        text = f'Список покупок пользователя {user.username}:\n'
        for ingr in ingredients:
            text += f'{ingr[0]} {ingr[1]} - {ingr[2]}\n'
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
