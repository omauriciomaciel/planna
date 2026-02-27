import io
import uuid
from collections import Counter

import joblib
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categorization_model import CategorizationModel
from app.models.category import Category
from app.models.credit_purchase import CreditPurchase
from app.models.transaction import Transaction


async def collect_training_data(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[list[str], list[str]]:
    """Collect descriptions and their categories for training."""
    descriptions = []
    labels = []

    # From transactions
    result = await db.execute(
        select(Transaction.description, Category.name)
        .join(Category, Transaction.category_id == Category.id)
        .where(Transaction.user_id == user_id, Transaction.category_id.isnot(None))
    )
    for desc, cat in result.all():
        descriptions.append(desc)
        labels.append(cat)

    # From credit purchases
    result = await db.execute(
        select(CreditPurchase.merchant, Category.name)
        .join(Category, CreditPurchase.category_id == Category.id)
        .where(CreditPurchase.user_id == user_id, CreditPurchase.category_id.isnot(None))
    )
    for desc, cat in result.all():
        descriptions.append(desc)
        labels.append(cat)

    return descriptions, labels


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

    # Map clusters to most common label in each cluster
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


async def train_and_save(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Train model for user and save to database. Returns True on success."""
    descriptions, labels = await collect_training_data(db, user_id)
    result = train_model(descriptions, labels)
    if not result:
        return False

    pipeline, label_mapping = result
    blob = serialize_model(pipeline)

    # Upsert model
    existing = await db.execute(
        select(CategorizationModel).where(CategorizationModel.user_id == user_id)
    )
    model = existing.scalar_one_or_none()
    if model:
        model.model_blob = blob
        model.label_mapping = {str(k): v for k, v in label_mapping.items()}
    else:
        model = CategorizationModel(
            user_id=user_id,
            model_blob=blob,
            label_mapping={str(k): v for k, v in label_mapping.items()},
        )
        db.add(model)

    await db.commit()
    return True


async def predict_category(
    db: AsyncSession, user_id: uuid.UUID, description: str
) -> str | None:
    """Predict category for a description. Returns category name or None."""
    result = await db.execute(
        select(CategorizationModel).where(CategorizationModel.user_id == user_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        return None

    pipeline = deserialize_model(model.model_blob)
    cluster_id = pipeline.predict([description])[0]
    return model.label_mapping.get(str(cluster_id))
