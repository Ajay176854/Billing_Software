import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.config import settings

# Import all models so Base metadata is populated
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.stock_transaction import StockTransaction

# 1. Setup Engines
sqlite_url = "sqlite:///./data/billing.db"
postgres_url = settings.DATABASE_URL

sqlite_engine = create_engine(sqlite_url)
postgres_engine = create_engine(postgres_url)

SqliteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

print(f"Reading from: {sqlite_url}")
print(f"Writing to:   {postgres_url}")

def migrate():
    # 2. Recreate tables in Postgres
    print("Dropping existing tables in Postgres...")
    Base.metadata.drop_all(postgres_engine)
    print("Creating tables in Postgres...")
    Base.metadata.create_all(postgres_engine)

    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()

    try:
        # 3. Iterate over all tables in correct dependency order
        for table in Base.metadata.sorted_tables:
            print(f"Migrating table '{table.name}'...")
            
            # Fetch all data from SQLite using raw SQL so missing schema columns are ignored
            result = sqlite_session.execute(text(f"SELECT * FROM {table.name}"))
            keys = list(result.keys())
            records = result.fetchall()
            
            if not records:
                print(f"  -> No data in '{table.name}', skipping.")
                continue

            # Convert to list of dictionaries
            data_to_insert = [dict(zip(keys, row)) for row in records]
            
            # Insert into Postgres
            postgres_session.execute(table.insert(), data_to_insert)
            
            # Fix Postgres auto-increment sequences!
            if 'id' in keys:
                seq_fix_sql = f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM {table.name};"
                postgres_session.execute(text(seq_fix_sql))
            
            print(f"  -> Migrated {len(data_to_insert)} records.")

        postgres_session.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        postgres_session.rollback()
        print(f"\nMigration failed: {e}")
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    migrate()
