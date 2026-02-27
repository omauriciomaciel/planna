import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ml.categorizer import deserialize_model, serialize_model, train_model
from app.repositories.categorization_model import CategorizationModelRepository
from app.repositories.credit_purchase import CreditPurchaseRepository
from app.repositories.transaction import TransactionRepository


class CategorizerService:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        credit_purchase_repo: CreditPurchaseRepository,
        model_repo: CategorizationModelRepository,
    ):
        self.transaction_repo = transaction_repo
        self.credit_purchase_repo = credit_purchase_repo
        self.model_repo = model_repo

    async def train_and_save(self, user_id: uuid.UUID) -> bool:
        descriptions = []
        labels = []

        tx_data = await self.transaction_repo.get_categorized_descriptions(user_id)
        for desc, cat in tx_data:
            descriptions.append(desc)
            labels.append(cat)

        cp_data = await self.credit_purchase_repo.get_categorized_descriptions(user_id)
        for desc, cat in cp_data:
            descriptions.append(desc)
            labels.append(cat)

        result = train_model(descriptions, labels)
        if not result:
            return False

        pipeline, label_mapping = result
        blob = serialize_model(pipeline)

        await self.model_repo.upsert(
            user_id, blob, {str(k): v for k, v in label_mapping.items()}
        )
        return True

    async def predict_category(
        self, user_id: uuid.UUID, description: str
    ) -> str | None:
        model = await self.model_repo.get_for_user(user_id)
        if not model:
            return None

        pipeline = deserialize_model(model.model_blob)
        cluster_id = pipeline.predict([description])[0]
        return model.label_mapping.get(str(cluster_id))


def get_transaction_repository(
    db: AsyncSession = Depends(get_db),
) -> TransactionRepository:
    return TransactionRepository(db)


def get_credit_purchase_repository(
    db: AsyncSession = Depends(get_db),
) -> CreditPurchaseRepository:
    return CreditPurchaseRepository(db)


def get_categorization_model_repository(
    db: AsyncSession = Depends(get_db),
) -> CategorizationModelRepository:
    return CategorizationModelRepository(db)


def get_categorizer_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    credit_purchase_repo: CreditPurchaseRepository = Depends(get_credit_purchase_repository),
    model_repo: CategorizationModelRepository = Depends(get_categorization_model_repository),
) -> CategorizerService:
    return CategorizerService(transaction_repo, credit_purchase_repo, model_repo)
