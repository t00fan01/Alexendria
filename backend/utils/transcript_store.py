from collections import defaultdict

_fallback_store = defaultdict(list)


def store_chunks(video_id, chunks):
    _fallback_store[video_id] = list(chunks)


def get_chunks(video_id):
    return list(_fallback_store.get(video_id, []))


def clear_chunks(video_id):
    _fallback_store.pop(video_id, None)
