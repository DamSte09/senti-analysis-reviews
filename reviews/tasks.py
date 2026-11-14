import hashlib

import redis
from celery import shared_task
from celery.signals import worker_ready
from django.conf import settings

from .models import Review


MODEL_NAME = "tabularisai/multilingual-sentiment-analysis"
CACHE_TTL_SECONDS = 60*60*24

redis_client = redis.Redis.from_url(settings.SENTIMENT_CACHE_URL)

_model = None


def get_model():
    global _model
    if _model is None:
        from transformers import pipeline
        print("Model loading...")
        _model = pipeline("text-classification", model=MODEL_NAME)
    return _model


def _cache_key(text):
    digest = hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()
    return f"sentiment:text:{digest}"

@worker_ready.connect
def load_model(sender, **kwargs):
    # Load the model when the worker is ready, so that the first task doesn't have to wait for it
    get_model()

@shared_task(bind=True, max_retries=3, ignore_result=True)
def analyze_sentiment(self, review_id):
    try:
        review = Review.objects.get(id=review_id)
        
    except Review.DoesNotExist:
        # Review was deleted; retrying will not help
        return {"status": "not_found", "review_id": review_id}

    cache_key = _cache_key(review.text)

    try:
        cached = redis_client.get(cache_key)
    except redis.RedisError:
        # Cache is optional - fall back to running the model
        cached = None

    if cached:
        sentiment_label = cached.decode("utf-8")
        status = "cached"
    else:
        try:
            result = get_model()(review.text, truncation=True)[0]
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60)
        sentiment_label = result["label"]
        status = "success"
        try:
            redis_client.set(cache_key, sentiment_label, ex=CACHE_TTL_SECONDS)
        except redis.RedisError:
            pass

    review.sentiment = sentiment_label
    review.save(update_fields=["sentiment"])

    return {
        "status": status,
        "review_id": review_id,
        "review_sentiment": sentiment_label,
    }


