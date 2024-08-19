from django.shortcuts import render
from .models import Article
from django.http import StreamingHttpResponse, JsonResponse
from .tasks import update_url_database_function_with_yield, get_rag_response
import logging
from django.db.models import Q

def search_articles(request):
    query = request.GET.get('q')
    articles = Article.objects.filter(title__icontains=query).order_by('-published') if query else Article.objects.all().order_by('-published')
    return render(request, 'search_results.html', {'articles': articles, 'query': query})

def home(request):
    return render(request, 'home.html')

def summaries(request):
    category = request.GET.get('category')
    website = request.GET.get('website')

    filters = {}
    if category:
        filters['category'] = category
    if website:
        filters['website'] = website

    articles = Article.objects.filter(**filters).order_by('-published')
    
    # Pass the selected filters back to the template to maintain selection state
    return render(request, 'summaries.html', {
        'articles': articles,
        'selected_category': category,
        'selected_website': website,
        'categories': Article.objects.values_list('category', flat=True).distinct(),
        'websites': Article.objects.values_list('website', flat=True).distinct()
    })

def manage(request):
    return render(request, 'manage.html')

def sse_view(request):
    logger = logging.getLogger(__name__)
    def event_stream():
        try:
            for message in update_url_database_function_with_yield():
                logger.info(f"Sending message: {message}")
                yield f"data: {message}\n\n"
        except Exception as e:
            logger.error(f"Error in SSE: {str(e)}")

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response

def category_page(request, category_name):
    articles = Article.objects.filter(category=category_name).order_by('-published')
    return render(request, 'category_page.html', {'articles': articles})

def chat_with_bot(request):
    if request.method == 'POST':
        user_input = request.POST.get('query')
        if user_input:
            response = get_rag_response(user_input)
            return render(request, 'chatbox.html', {'response': response, 'query': user_input})
    return render(request, 'chatbox.html', {'response': "Sorry, I didn't understand that."})

def website_page(request, website_name):
    articles = Article.objects.filter(website=website_name).order_by('-published')
    return render(request, 'website_page.html', {'articles': articles})
