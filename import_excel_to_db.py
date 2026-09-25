from pathlib import Path

import pandas as pd
import psycopg2


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = Path(__file__).parent / "data" / "Vendor_and_Product_details.xlsx"

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv("backend/.env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """Convert a value into clean text."""

    if pd.isna(value):
        return ""

    return " ".join(str(value).strip().split())


def normalize_text(value):
    """Create a normalized value for matching."""

    return clean_text(value).lower()


# ============================================================
# LOAD EXCEL
# ============================================================

def load_excel():
    print("Reading Excel file...")

    df = pd.read_excel(DATA_FILE)

    # Clean column names
    df.columns = df.columns.astype(str).str.strip()

    required_columns = [
        "Product",
        "Vendor",
        "Contuct",
        "Mail_id",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Keep only required columns
    df = df[required_columns].copy()

    # Clean values
    for column in required_columns:
        df[column] = df[column].apply(clean_text)

    # Remove rows where Product or Vendor is empty
    df = df[
        (df["Product"] != "")
        & (df["Vendor"] != "")
    ].copy()

    print(f"Excel rows loaded: {len(df)}")

    return df


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect_database():
    print("Connecting to PostgreSQL...")

    connection = psycopg2.connect(**DB_CONFIG)

    print("PostgreSQL connection successful.")

    return connection


# ============================================================
# IMPORT VENDORS
# ============================================================

def import_vendors(cursor, df):
    print("\nImporting vendors...")

    vendor_map = {}

    for _, row in df.iterrows():

        vendor_name = row["Vendor"]
        contact = row["Contuct"]
        mail_id = row["Mail_id"]

        vendor_key = normalize_text(vendor_name)

        # Already processed during this import
        if vendor_key in vendor_map:

            vendor_id = vendor_map[vendor_key]

            # Update missing contact/email if available
            cursor.execute(
                """
                UPDATE vendors
                SET
                    contact = CASE
                        WHEN (contact IS NULL OR TRIM(contact) = '')
                             AND %s <> ''
                        THEN %s
                        ELSE contact
                    END,

                    mail_id = CASE
                        WHEN (mail_id IS NULL OR TRIM(mail_id) = '')
                             AND %s <> ''
                        THEN %s
                        ELSE mail_id
                    END

                WHERE vendor_id = %s
                """,
                (
                    contact,
                    contact,
                    mail_id,
                    mail_id,
                    vendor_id,
                ),
            )

            continue

        # Check whether vendor already exists
        cursor.execute(
            """
            SELECT vendor_id
            FROM vendors
            WHERE LOWER(TRIM(vendor_name)) = %s
            LIMIT 1
            """,
            (vendor_key,),
        )

        existing = cursor.fetchone()

        if existing:

            vendor_id = existing[0]

            # Update missing contact/email
            cursor.execute(
                """
                UPDATE vendors
                SET
                    contact = CASE
                        WHEN (contact IS NULL OR TRIM(contact) = '')
                             AND %s <> ''
                        THEN %s
                        ELSE contact
                    END,

                    mail_id = CASE
                        WHEN (mail_id IS NULL OR TRIM(mail_id) = '')
                             AND %s <> ''
                        THEN %s
                        ELSE mail_id
                    END

                WHERE vendor_id = %s
                """,
                (
                    contact,
                    contact,
                    mail_id,
                    mail_id,
                    vendor_id,
                ),
            )

        else:

            cursor.execute(
                """
                INSERT INTO vendors
                    (vendor_name, contact, mail_id)
                VALUES
                    (%s, %s, %s)
                RETURNING vendor_id
                """,
                (
                    vendor_name,
                    contact,
                    mail_id,
                ),
            )

            vendor_id = cursor.fetchone()[0]

        vendor_map[vendor_key] = vendor_id

    print(f"Unique vendors imported: {len(vendor_map)}")

    return vendor_map


# ============================================================
# IMPORT PRODUCTS
# ============================================================

def import_products(cursor, df):
    print("\nImporting products...")

    product_map = {}

    for product_name in df["Product"]:

        product_key = normalize_text(product_name)

        # Already processed during this import
        if product_key in product_map:
            continue

        # Check database
        cursor.execute(
            """
            SELECT product_id
            FROM products
            WHERE LOWER(TRIM(product_name)) = %s
            LIMIT 1
            """,
            (product_key,),
        )

        existing = cursor.fetchone()

        if existing:

            product_id = existing[0]

        else:

            cursor.execute(
                """
                INSERT INTO products
                    (product_name)
                VALUES
                    (%s)
                RETURNING product_id
                """,
                (product_name,),
            )

            product_id = cursor.fetchone()[0]

        product_map[product_key] = product_id

    print(f"Unique products imported: {len(product_map)}")

    return product_map


# ============================================================
# IMPORT VENDOR-PRODUCT RELATIONSHIPS
# ============================================================

def import_relationships(
    cursor,
    df,
    vendor_map,
    product_map,
):
    print("\nImporting vendor-product relationships...")

    relationship_count = 0

    processed_relationships = set()

    for _, row in df.iterrows():

        vendor_key = normalize_text(row["Vendor"])
        product_key = normalize_text(row["Product"])

        vendor_id = vendor_map[vendor_key]
        product_id = product_map[product_key]

        relationship_key = (
            vendor_id,
            product_id,
        )

        # Avoid duplicate relationship
        if relationship_key in processed_relationships:
            continue

        processed_relationships.add(relationship_key)

        cursor.execute(
            """
            INSERT INTO vendor_products
                (vendor_id, product_id)
            VALUES
                (%s, %s)
            ON CONFLICT (vendor_id, product_id)
            DO NOTHING
            """,
            (
                vendor_id,
                product_id,
            ),
        )

        relationship_count += 1

    print(
        f"Unique vendor-product relationships: "
        f"{relationship_count}"
    )


# ============================================================
# SHOW DATABASE COUNTS
# ============================================================

def show_database_counts(cursor):

    print("\n----------------------------------------")
    print("DATABASE SUMMARY")
    print("----------------------------------------")

    cursor.execute(
        "SELECT COUNT(*) FROM vendors"
    )
    vendor_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM products"
    )
    product_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM vendor_products"
    )
    relationship_count = cursor.fetchone()[0]

    print(f"Vendors       : {vendor_count}")
    print(f"Products      : {product_count}")
    print(f"Relationships : {relationship_count}")

    print("----------------------------------------")


# ============================================================
# MAIN
# ============================================================

def main():

    connection = None

    try:

        # Load Excel
        df = load_excel()

        # Connect database
        connection = connect_database()

        cursor = connection.cursor()

        # Import vendors
        vendor_map = import_vendors(
            cursor,
            df,
        )

        # Import products
        product_map = import_products(
            cursor,
            df,
        )

        # Import relationships
        import_relationships(
            cursor,
            df,
            vendor_map,
            product_map,
        )

        # Commit everything
        connection.commit()

        print("\nData import completed successfully.")

        # Show summary
        show_database_counts(cursor)

        cursor.close()

    except Exception as error:

        if connection:
            connection.rollback()

        print("\nIMPORT FAILED")
        print("----------------------------------------")
        print(error)
        print("----------------------------------------")
        print("All changes have been rolled back.")

    finally:

        if connection:
            connection.close()

            print("\nDatabase connection closed.")


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":
    main()