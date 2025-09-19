import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from sentence_transformers import SentenceTransformer, util
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

# ---------- Config ----------
SEARCH_RESULTS = 12
MAX_WORKERS = 8
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (compatible; WebScraper/1.0; +https://example.com/bot)"
MIN_PARA_LEN = 200
DEDUP_THRESHOLD = 0.7
EMBED_BATCH_SIZE = 64
# ----------------------------

# Load model once per process (fast model, CPU-friendly)
MODEL_NAME = "all-MiniLM-L6-v2"
try:
    MODEL = SentenceTransformer(MODEL_NAME)
except Exception as e:
    logger.exception("Failed to load sentence-transformers model. Make sure it's installed.")
    MODEL = None


def fetch_search_results(query: str, max_results: int = SEARCH_RESULTS):
    """Return a list of result URLs using DuckDuckGo (no API key)."""
    urls = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                href = r.get("href")
                if href:
                    urls.append(href)
    except Exception as e:
        logger.exception("DuckDuckGo search failed")
    urls = [u for u in urls if u.startswith("http")]
    return urls

def get_webdriver():
    """Configures and returns a headless Chrome WebDriver."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'user-agent={USER_AGENT}')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def scrape_url_selenium(url: str, driver):
    """Scrapes dynamic content using Selenium and returns a list of cleaned paragraphs."""
    try:
        driver.get(url)
        time.sleep(3)  # Wait for page to load dynamic content
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        if not soup.body:
            logger.warning("No body tag found on %s. Skipping this URL.", url)
            return []
            
        for s in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "button", "a"]):
            s.decompose()
            
        paragraphs = []
        # Find all paragraph and list item tags
        content_tags = soup.find_all(['p', 'li'])

        for tag in content_tags:
            text = tag.get_text(strip=True)
            # Filter for text that meets the minimum length
            if len(text) > MIN_PARA_LEN:
                paragraphs.append(clean_text(text))
        
        return paragraphs
    except Exception as e:
        logger.exception("Failed to scrape %s with Selenium: %s", url, e)
        return []

def scrape_urls_multithread(urls, max_workers=MAX_WORKERS):
    """Scrape multiple URLs in parallel using Selenium."""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        drivers = [get_webdriver() for _ in range(max_workers)]
        futures = {ex.submit(scrape_url_selenium, url, drivers[i % max_workers]): url for i, url in enumerate(urls)}
        
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                paragraphs = fut.result()
                if paragraphs:
                    results.append((paragraphs, url))
            except Exception:
                logger.exception("Error scraping %s", url)
        
        for driver in drivers:
            driver.quit()
            
    return results

def clean_text(text: str) -> str:
    """Basic text cleaning."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def collect_paragraphs(scraped_texts):
    paragraphs = []
    for para_list, url in scraped_texts:
        for para in para_list:
            paragraphs.append({"paragraph": clean_text(para), "source": url})
    return paragraphs

def semantic_dedup(para_objs, threshold=DEDUP_THRESHOLD):
    if not para_objs or MODEL is None:
        return []

    paragraphs = [p["paragraph"] for p in para_objs]
    embeddings = MODEL.encode(paragraphs, convert_to_tensor=True, batch_size=EMBED_BATCH_SIZE, show_progress_bar=False)

    keep_indices = []
    kept_embeddings = None
    import torch

    for i, emb in enumerate(embeddings):
        if not keep_indices:
            keep_indices.append(i)
            kept_embeddings = emb.unsqueeze(0)
            continue
        try:
            if kept_embeddings is None:
                keep_indices.append(i)
                kept_embeddings = emb.unsqueeze(0)
                continue
            sims = util.cos_sim(emb.unsqueeze(0), kept_embeddings)[0]
            max_sim = float(torch.max(sims))
            
            if max_sim < threshold:
                keep_indices.append(i)
                kept_embeddings = torch.cat([kept_embeddings, emb.unsqueeze(0)], dim=0)
        except Exception as e:
            logger.error(f"Error during deduplication: {e}")

    deduped = [para_objs[i] for i in keep_indices]
    return deduped

def run_pipeline_for_query(query, use_cache_fn=None, cache_result_fn=None, max_results=SEARCH_RESULTS):
    """
    Full pipeline: search -> scrape -> extract paragraphs -> semantic dedup -> return deduped list of dicts.
    Optional: pass in cache functions (callables) for integration with DB caching outside utils.
    """
    # Try cache
    if use_cache_fn:
        cached = use_cache_fn(query)
        if cached:
            return cached

    urls = fetch_search_results(query, max_results=max_results)
    scraped = scrape_urls_multithread(urls)
    
    para_objs = collect_paragraphs(scraped)
    deduped = semantic_dedup(para_objs)

    result = [{"paragraph": d["paragraph"], "source": d["source"]} for d in deduped]

    if cache_result_fn:
        cache_result_fn(query, result)

    return result