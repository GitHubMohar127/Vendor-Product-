from pathlib import Path

import psycopg2
from rapidfuzz import fuzz


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

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
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize text for searching.

    Example:
        "  PHENOL  " -> "phenol"
        "Flora Chemicals" -> "flora chemicals"
    """

    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


# ============================================================
# GET ALL PRODUCTS
# ============================================================

def get_all_products():

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT product_id, product_name
            FROM products
            ORDER BY product_name
            """
        )

        rows = cursor.fetchall()

        cursor.close()

        return rows

    finally:
        connection.close()


# ============================================================
# GET ALL VENDORS
# ============================================================

def get_all_vendors():

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT vendor_id, vendor_name
            FROM vendors
            ORDER BY vendor_name
            """
        )

        rows = cursor.fetchall()

        cursor.close()

        return rows

    finally:
        connection.close()


# ============================================================
# FIND EXACT PRODUCT
# ============================================================

def find_exact_product(query):

    normalized_query = normalize_text(query)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT product_id, product_name
            FROM products
            WHERE LOWER(TRIM(product_name)) = %s
            LIMIT 1
            """,
            (normalized_query,),
        )

        result = cursor.fetchone()

        cursor.close()

        return result

    finally:
        connection.close()


# ============================================================
# FIND EXACT VENDOR
# ============================================================

def find_exact_vendor(query):

    normalized_query = normalize_text(query)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT vendor_id, vendor_name
            FROM vendors
            WHERE LOWER(TRIM(vendor_name)) = %s
            LIMIT 1
            """,
            (normalized_query,),
        )

        result = cursor.fetchone()

        cursor.close()

        return result

    finally:
        connection.close()


# ============================================================
# SEARCH PRODUCT FUZZY
# ============================================================

def find_matching_products(query):

    normalized_query = normalize_text(query)

    products = get_all_products()

    matches = []

    for product_id, product_name in products:

        normalized_name = normalize_text(product_name)

        score = fuzz.token_set_ratio(
            normalized_query,
            normalized_name,
        )

        if (
            normalized_query in normalized_name
            or normalized_name in normalized_query
            or score >= 70
        ):
            matches.append(
                {
                    "product_id": product_id,
                    "product_name": product_name,
                    "score": score,
                }
            )

    matches.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return matches


# ============================================================
# SEARCH VENDOR FUZZY
# ============================================================

def find_matching_vendors(query):

    normalized_query = normalize_text(query)

    vendors = get_all_vendors()

    matches = []

    for vendor_id, vendor_name in vendors:

        normalized_name = normalize_text(vendor_name)

        score = fuzz.token_set_ratio(
            normalized_query,
            normalized_name,
        )

        if (
            normalized_query in normalized_name
            or normalized_name in normalized_query
            or score >= 70
        ):
            matches.append(
                {
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "score": score,
                }
            )

    matches.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return matches


# ============================================================
# GET VENDORS FOR A PRODUCT
# ============================================================

def search_product(product_id):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                v.vendor_id,
                v.vendor_name,
                v.contact,
                v.mail_id
            FROM vendor_products vp

            JOIN vendors v
                ON vp.vendor_id = v.vendor_id

            WHERE vp.product_id = %s

            ORDER BY v.vendor_name
            """,
            (product_id,),
        )

        rows = cursor.fetchall()

        cursor.close()

        results = []

        for row in rows:

            results.append(
                {
                    "vendor_id": row[0],
                    "vendor": row[1],
                    "contact": row[2] or "",
                    "mail_id": row[3] or "",
                }
            )

        return results

    finally:
        connection.close()


# ============================================================
# GET PRODUCTS FOR A VENDOR
# ============================================================

def search_vendor(vendor_id):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Vendor contact/email
        cursor.execute(
            """
            SELECT
                vendor_name,
                contact,
                mail_id
            FROM vendors
            WHERE vendor_id = %s
            """,
            (vendor_id,),
        )

        vendor_row = cursor.fetchone()

        # Associated products
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name
            FROM vendor_products vp

            JOIN products p
                ON vp.product_id = p.product_id

            WHERE vp.vendor_id = %s

            ORDER BY p.product_name
            """,
            (vendor_id,),
        )

        product_rows = cursor.fetchall()

        cursor.close()

        vendor_details = {}

        if vendor_row:

            vendor_details = {
                "vendor": vendor_row[0],
                "contact": vendor_row[1] or "",
                "mail_id": vendor_row[2] or "",
            }

        products = []

        for row in product_rows:

            products.append(
                {
                    "product_id": row[0],
                    "product_name": row[1],
                }
            )

        return {
            "vendor_details": vendor_details,
            "products": products,
        }

    finally:
        connection.close()


# ============================================================
# SEARCH FUNCTION
# ============================================================

def search(query):

    query = query.strip()

    if not query:

        return {
            "type": "no_match",
            "message": "Please enter a product or vendor name.",
        }


    # --------------------------------------------------------
    # 1. EXACT PRODUCT
    # --------------------------------------------------------

    product = find_exact_product(query)

    if product:

        product_id = product[0]
        product_name = product[1]

        vendors = search_product(product_id)

        return {
            "type": "product",
            "matched_name": product_name,
            "results": vendors,
        }


    # --------------------------------------------------------
    # 2. EXACT VENDOR
    # --------------------------------------------------------

    vendor = find_exact_vendor(query)

    if vendor:

        vendor_id = vendor[0]
        vendor_name = vendor[1]

        result = search_vendor(vendor_id)

        return {
            "type": "vendor",
            "matched_name": vendor_name,
            "vendor_details": result["vendor_details"],
            "results": result["products"],
        }


    # --------------------------------------------------------
    # 3. PRODUCT FUZZY MATCH
    # --------------------------------------------------------

    product_matches = find_matching_products(query)

    if len(product_matches) == 1:

        matched = product_matches[0]

        vendors = search_product(
            matched["product_id"]
        )

        return {
            "type": "product",
            "matched_name": matched["product_name"],
            "results": vendors,
        }


    # --------------------------------------------------------
    # 4. VENDOR FUZZY MATCH
    # --------------------------------------------------------

    vendor_matches = find_matching_vendors(query)

    if len(vendor_matches) == 1:

        matched = vendor_matches[0]

        result = search_vendor(
            matched["vendor_id"]
        )

        return {
            "type": "vendor",
            "matched_name": matched["vendor_name"],
            "vendor_details": result["vendor_details"],
            "results": result["products"],
        }


    # --------------------------------------------------------
    # 5. MULTIPLE PRODUCT MATCHES
    # --------------------------------------------------------

    if len(product_matches) > 1:

        return {
            "type": "multiple_products",
            "results": product_matches,
        }


    # --------------------------------------------------------
    # 6. MULTIPLE VENDOR MATCHES
    # --------------------------------------------------------

    if len(vendor_matches) > 1:

        return {
            "type": "multiple_vendors",
            "results": vendor_matches,
        }


    # --------------------------------------------------------
    # 7. NO MATCH
    # --------------------------------------------------------

    return {
        "type": "no_match",
        "message": (
            "No matching product or vendor was found."
        ),
    }