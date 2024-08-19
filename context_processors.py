from .models import Article

def categories_and_websites(request):
    categories = Article.objects.values_list('category', flat=True).distinct()
    websites = Article.objects.values_list('website', flat=True).distinct()
    return {
        'categories': categories,
        'websites': websites,
    }
