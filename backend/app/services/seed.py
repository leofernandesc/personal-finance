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
    roots_by_name = {
        category.name.casefold(): category
        for category in db.scalars(
            select(Category).where(Category.user_id == user.id, Category.parent_id.is_(None))
        )
    }
    for kind, category_tree in DEFAULT_CATEGORIES.items():
        for root_name, children in category_tree.items():
            root = roots_by_name.get(root_name.casefold())
            if not root:
                root = Category(user_id=user.id, name=root_name, kind=kind)
                db.add(root)
                db.flush()
                roots_by_name[root_name.casefold()] = root
            elif root.kind != kind and root.kind != "both":
                root.kind = "both"
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
