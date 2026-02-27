import io
from collections import Counter

import joblib
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline


def train_model(
    descriptions: list[str], labels: list[str]
) -> tuple[Pipeline, dict[int, str]] | None:
    """Train KMeans model on descriptions. Returns (pipeline, cluster→label mapping) or None."""
    if len(descriptions) < 10:
        return None

    unique_labels = list(set(labels))
    n_clusters = min(len(unique_labels), len(descriptions) // 3, 50)

    if n_clusters < 2:
        return None

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("kmeans", KMeans(n_clusters=n_clusters, random_state=42, n_init=10)),
    ])

    pipeline.fit(descriptions)

    cluster_assignments = pipeline.predict(descriptions)
    cluster_labels: dict[int, list[str]] = {}
    for cluster_id, label in zip(cluster_assignments, labels, strict=True):
        cluster_labels.setdefault(cluster_id, []).append(label)

    label_mapping = {}
    for cluster_id, cat_list in cluster_labels.items():
        counter = Counter(cat_list)
        label_mapping[cluster_id] = counter.most_common(1)[0][0]

    return pipeline, label_mapping


def serialize_model(pipeline: Pipeline) -> bytes:
    buf = io.BytesIO()
    joblib.dump(pipeline, buf)
    return buf.getvalue()


def deserialize_model(blob: bytes) -> Pipeline:
    buf = io.BytesIO(blob)
    return joblib.load(buf)
