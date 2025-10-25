from django.shortcuts import render

import json
import hashlib
from collections import Counter
from datetime import datetime, timezone
import re

from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import AnalyzedString

# ---------- Helper: analyze a string ----------
def analyze_string(value: str) -> dict:
    value_str = value  # preserve original (don't strip internal spaces)
    length = len(value_str)
    # Case-insensitive palindrome check (doesn't strip spaces/punctuation; spec: case-insensitive)
    is_palindrome = value_str.lower() == value_str[::-1].lower()
    unique_characters = len(set(value_str))
    word_count = len(value_str.split())
    sha256_hash = hashlib.sha256(value_str.encode('utf-8')).hexdigest()
    character_frequency_map = dict(Counter(value_str))

    return {
        "length": length,
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha256_hash,
        "character_frequency_map": character_frequency_map,
    }

# ---------- Helper: format DB object to response ----------
def model_to_response_obj(obj: AnalyzedString) -> dict:
    try:
        props = obj.get_properties()  # returns dict
    except Exception:
        # fallback if properties not valid JSON
        props = {}
    return {
        "id": obj.sha256_hash,
        "value": obj.value,
        "properties": props,
        "created_at": obj.created_at.astimezone(timezone.utc).isoformat()
    }

# ---------- Helper: parse boolean query param ----------
def parse_bool(s):
    if s is None:
        return None
    s = s.lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    return None

# ---------- Helper: apply filters in memory ----------
def apply_filters(queryset, params):
    results = []
    # load all and filter in Python
    for obj in queryset:
        try:
            props = obj.get_properties()
        except Exception:
            continue
        ok = True
        # is_palindrome filter
        fq = params.get("is_palindrome")
        if fq is not None and props.get("is_palindrome") is not None:
            if props.get("is_palindrome") != fq:
                ok = False
        # min_length
        min_l = params.get("min_length")
        if min_l is not None:
            if props.get("length", 0) < min_l:
                ok = False
        # max_length
        max_l = params.get("max_length")
        if max_l is not None:
            if props.get("length", 0) > max_l:
                ok = False
        # word_count
        wc = params.get("word_count")
        if wc is not None:
            if props.get("word_count") != wc:
                ok = False
        # contains_character
        cc = params.get("contains_character")
        if cc is not None:
            # check if any character equals cc (case-sensitive per stored value)
            if cc not in props.get("character_frequency_map", {}):
                ok = False
        if ok:
            results.append(obj)
    return results

# ---------- Helper: simple natural language parser ----------
def parse_nl_query(q: str):
    q = q.lower()
    parsed = {}
    # single word / single-word -> word_count = 1
    if re.search(r'\bsingle[- ]?word\b', q):
        parsed["word_count"] = 1
    # palindromic / palindrome
    if re.search(r'\bpalindrom(e|ic|al)?\b', q):
        parsed["is_palindrome"] = True
    # strings longer than N characters -> min_length = N+1
    m = re.search(r'longer than (\d+)', q)
    if m:
        parsed["min_length"] = int(m.group(1)) + 1
    # strings with length greater than N (alternative)
    m2 = re.search(r'longer than (\d+) characters', q)
    if m2:
        parsed["min_length"] = int(m2.group(1)) + 1
    # strings containing the letter z / containing the letter x
    m3 = re.search(r'contain(?:ing)? the letter (\w)', q)
    if m3:
        parsed["contains_character"] = m3.group(1)
    # strings containing the letter z (alternative)
    m4 = re.search(r'containing the letter (\w)', q)
    if m4:
        parsed["contains_character"] = m4.group(1)
    # strings containing the letter 'z' without phrase
    m5 = re.search(r'containing the letter (\w)', q)
    if m5:
        parsed["contains_character"] = m5.group(1)
    # strings containing letter X
    m6 = re.search(r'containing the letter\s+([a-zA-Z])', q)
    if m6:
        parsed["contains_character"] = m6.group(1)
    # fallback: cannot parse -> return None
    if not parsed:
        return None
    return parsed

# ---------- POST /strings/ ----------
#@method_decorator(csrf_exempt, name='dispatch')
@csrf_exempt
def create_string(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # Content-Type check is optional — we parse JSON safely
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    if 'value' not in body:
        return JsonResponse({"detail": 'Missing "value" field.'}, status=400)

    value = body['value']

    if not isinstance(value, str):
        return JsonResponse({"detail": '"value" must be a string.'}, status=422)

    # Normalize exact string as-is (no trimming unless you want)
    # Compute properties
    props = analyze_string(value)
    sha = props["sha256_hash"]

    # Check existence by sha
    existing = AnalyzedString.objects.filter(sha256_hash=sha).first()
    if existing:
        # 409 Conflict — string already exists
        return JsonResponse(model_to_response_obj(existing), status=409)

    # Create DB object
    obj = AnalyzedString(value=value, sha256_hash=sha)
    obj.set_properties(props)
    obj.save()

    resp = model_to_response_obj(obj)
    return JsonResponse(resp, status=201)

# ---------- GET /strings/<string_value> ----------
def get_string(request, string_value):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    # URL path provides the raw string_value (URL-encoded). We'll compute sha and lookup.
    try:
        sha = hashlib.sha256(string_value.encode('utf-8')).hexdigest()
    except Exception:
        return JsonResponse({"detail": "Unable to compute hash for the provided string."}, status=400)

    obj = AnalyzedString.objects.filter(sha256_hash=sha).first()
    if not obj:
        return JsonResponse({"detail": "String not found."}, status=404)

    return JsonResponse(model_to_response_obj(obj), status=200)

# ---------- GET /strings (with filters) ----------
def list_strings(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    # Parse and validate query params
    raw_is_pal = request.GET.get('is_palindrome')
    is_pal = parse_bool(raw_is_pal)
    try:
        min_length = int(request.GET['min_length']) if 'min_length' in request.GET else None
    except ValueError:
        return JsonResponse({"detail": "min_length must be integer."}, status=400)
    try:
        max_length = int(request.GET['max_length']) if 'max_length' in request.GET else None
    except ValueError:
        return JsonResponse({"detail": "max_length must be integer."}, status=400)
    try:
        word_count = int(request.GET['word_count']) if 'word_count' in request.GET else None
    except ValueError:
        return JsonResponse({"detail": "word_count must be integer."}, status=400)

    contains_character = request.GET.get('contains_character')

    # Build param dict for apply_filters
    params = {
        "is_palindrome": is_pal,
        "min_length": min_length,
        "max_length": max_length,
        "word_count": word_count,
        "contains_character": contains_character
    }

    all_objs = AnalyzedString.objects.all().order_by('-created_at')
    filtered_objs = apply_filters(all_objs, params)

    data = [model_to_response_obj(o) for o in filtered_objs]
    return JsonResponse({
        "data": data,
        "count": len(data),
        "filters_applied": {k: v for k, v in params.items() if v is not None}
    }, status=200)

# ---------- GET /strings/filter-by-natural-language ----------
def filter_by_nl(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    query = request.GET.get('query')
    if not query:
        return JsonResponse({"detail": "Missing 'query' param."}, status=400)

    parsed = parse_nl_query(query)
    if parsed is None:
        return JsonResponse({"detail": "Unable to parse natural language query."}, status=400)

    # Build params dict mapped to our filter keys
    params = {}
    if "word_count" in parsed:
        params["word_count"] = parsed["word_count"]
    if "is_palindrome" in parsed:
        params["is_palindrome"] = parsed["is_palindrome"]
    if "min_length" in parsed:
        params["min_length"] = parsed["min_length"]
    if "contains_character" in parsed:
        params["contains_character"] = parsed["contains_character"]

    all_objs = AnalyzedString.objects.all().order_by('-created_at')
    filtered_objs = apply_filters(all_objs, params)
    data = [model_to_response_obj(o) for o in filtered_objs]

    return JsonResponse({
        "data": data,
        "count": len(data),
        "interpreted_query": {
            "original": query,
            "parsed_filters": params
        }
    }, status=200)

# ---------- DELETE /strings/<string_value> ----------
@method_decorator(csrf_exempt, name='dispatch')
def delete_string(request, string_value):
    if request.method != 'DELETE':
        return HttpResponseNotAllowed(['DELETE'])

    sha = hashlib.sha256(string_value.encode('utf-8')).hexdigest()
    obj = AnalyzedString.objects.filter(sha256_hash=sha).first()
    if not obj:
        return JsonResponse({"detail": "String not found."}, status=404)
    obj.delete()
    return HttpResponse(status=204)
