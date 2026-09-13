PLUGGY_CATEGORY_MAP: dict[str, str] = {
    "Travel": "Viagens",
    "Transportation": "Transporte",
    "Online Services": "Serviços Online",
    "Restaurants": "Restaurantes",
    "Groceries": "Mercado",
    "Health": "Saúde",
    "Education": "Educação",
    "Entertainment": "Entretenimento",
    "Shopping": "Compras",
    "Bills & Utilities": "Contas e Serviços",
    "Transfer": "Transferências",
    "Salary": "Salário",
    "Cash": "Saque",
    "Same person transfer": "Transferência entre contas",
    "Investment": "Investimentos",
    "Insurance": "Seguros",
    "Taxes": "Impostos",
    "Pets": "Pets",
    "Home": "Moradia",
    "Personal Care": "Cuidados Pessoais",
    "Clothing": "Vestuário",
    "Electronics": "Eletrônicos",
    "Subscriptions": "Assinaturas",
    "Other": "Outros",
}


def translate_category(name: str) -> str:
    return PLUGGY_CATEGORY_MAP.get(name, name)
