from django.shortcuts import render

from .models import Produto, SlideCarrossel


def landing(request):
    produtos = Produto.objects.para_cardapio()
    return render(request, "cardapio/landing.html", {"produtos": produtos, "slides": SlideCarrossel.objects.ativos()})
