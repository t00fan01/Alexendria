def keyword_similarity(question, text):
    q_words = set(question.lower().split())
    t_words = set(text.lower().split())
    common = q_words.intersection(t_words)
    return len(common) / len(q_words.union(t_words)) if q_words.union(t_words) else 0