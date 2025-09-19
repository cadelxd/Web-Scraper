from django.shortcuts import render
from .forms import SearchForm
from . import utils
import json
import datetime
from urllib.parse import urlparse # Import the urlparse function

def home(request):
    form = SearchForm()
    return render(request, "home.html", {"form": form})

def get_source_name(url):
    """Extracts the domain name from a URL."""
    try:
        domain = urlparse(url).netloc
        # Remove "www." from the domain name for a cleaner look
        return domain.replace('www.', '')
    except Exception:
        return url # Return the original URL if parsing fails

def results(request):
    q = request.GET.get("q", "").strip()
    form = SearchForm(initial={"q": q})
    points = []
    sources = []

    if q:
        points = utils.run_pipeline_for_query(q)
        # Process points to include a clean source name
        for p in points:
            p['source_name'] = get_source_name(p['source'])
            
        sources = list({get_source_name(p["source"]) for p in points})[:20]

    return render(request, "results.html", {
        "form": form,
        "query": q,
        "points": points,
        "sources": sources,
    })