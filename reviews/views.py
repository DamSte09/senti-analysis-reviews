from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from .forms import ReviewForm
from .models import Review
from .tasks import analyze_sentiment

REVIEWS_PER_PAGE = 20
# Upper bound for ids in one polling request
MAX_IDS_PER_REQUEST = 100


def _is_ajax(request):
    # Set by our fetch() calls; plain form submits (no JS) don't send it
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def review_list(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save()
            # Queue the task only after the row is committed, so the worker can see it
            transaction.on_commit(lambda: analyze_sentiment.delay(review.id))
            if _is_ajax(request):
                # Return the rendered card so JS can insert it without a page reload
                html = render_to_string('reviews/_review.html', {'review': review}, request=request)
                return JsonResponse({'html': html}, status=201)
            return redirect('review_list')
        if _is_ajax(request):
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'errors': errors}, status=400)
    else:
        form = ReviewForm()

    page = Paginator(Review.objects.order_by('-pub_date'), REVIEWS_PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'reviews/reviews_list.html', {'form': form, 'page': page})


def reviews_sentiment(request):
    """Batch polling endpoint: GET ?ids=1,2,3

    Returns rendered cards for reviews that are already analysed and the ids
    that are still pending. Ids missing from both lists no longer exist.
    """
    try:
        ids = [int(i) for i in request.GET.get('ids', '').split(',') if i][:MAX_IDS_PER_REQUEST]
    except ValueError:
        return JsonResponse({'error': 'ids must be comma-separated integers'}, status=400)

    ready, pending = {}, []
    for review in Review.objects.filter(id__in=ids):
        if review.sentiment:
            ready[str(review.id)] = render_to_string('reviews/_review.html', {'review': review}, request=request)
        else:
            pending.append(str(review.id))

    return JsonResponse({'ready': ready, 'pending': pending})