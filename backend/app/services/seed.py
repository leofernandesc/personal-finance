from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, User

DEFAULT_CATEGORIES = {
    "expense": {
        "Alimentação": ["Restaurante", "Mercado", "Delivery"],
        "Transporte": ["Combustível", "Aplicativos", "Transporte público"],
        "Moradia": [],
        "Saúde": [],
        "Educação": [],
        "Lazer": [],
        "Compras": [],
        "Assinaturas": [],
        "Impostos": [],
        "Outros": [],
    },
    "income": {
        "Salário": [],
        "Freelance": [],
        "Serviços": [],
        "Investimentos": [],
        "Presentes": [],
        "Outros": [],
    },
}


def seed_categories(db: Session, user: User) -> None:
    existing = {
        name.lower()
        for name in db.scalars(select(Category.name).where(Category.user_id == user.id))
    }
    for kind, roots in DEFAULT_CATEGORIES.items():
        for root_name, children in roots.items():
            if root_name.lower() in existing:
                root = db.scalar(
                    select(Category).where(
                        Category.user_id == user.id,
                        Category.parent_id.is_(None),
                        Category.name.ilike(root_name),
                    )
                )
            else:
                root = Category(user_id=user.id, name=root_name, kind=kind)
                db.add(root)
                db.flush()
                existing.add(root_name.lower())
            if not root:
                continue
            child_names = {
                name.lower()
                for name in db.scalars(
                    select(Category.name).where(
                        Category.user_id == user.id, Category.parent_id == root.id
                    )
                )
            }
            for child_name in children:
                if child_name.lower() not in child_names:
                    db.add(Category(user_id=user.id, parent_id=root.id, name=child_name, kind=kind))
