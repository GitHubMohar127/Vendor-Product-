from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rapidfuzz import fuzz

from database import get_connection
from models import SearchRequest
from search import (
    perform_search,
    get_search_suggestions,
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Vendor Product Search API",
    description="API for searching vendors and products",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Convert text into a consistent format.

    Example:
        "  Phenol  " -> "phenol"
        "LEO   CHEMO PLAST" -> "leo chemo plast"
    """

    if value is None:
        return ""

    return " ".join(
        str(value).strip().lower().split()
    )


# ============================================================
# SEARCH REQUEST
# ============================================================

class SearchRequest(BaseModel):
    query: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "success",
        "message": "Vendor Product Search API is running",
    }


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT 1")

        result = cursor.fetchone()

        return {
            "status": "success",
            "database": "connected",
            "result": result[0],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {error}",
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# GET ALL PRODUCTS
# ============================================================

def get_all_products():

    connection = get_connection()
    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT product_id, product_name
            FROM products
            ORDER BY product_name
            """
        )

        return cursor.fetchall()

    finally:

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# GET ALL VENDORS
# ============================================================

def get_all_vendors():

    connection = get_connection()
    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT vendor_id, vendor_name
            FROM vendors
            ORDER BY vendor_name
            """
        )

        return cursor.fetchall()

    finally:

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# EXACT PRODUCT MATCH
# ============================================================

def find_exact_product(query):

    normalized_query = normalize_text(query)

    connection = get_connection()
    cursor = None

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

        return cursor.fetchone()

    finally:

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# EXACT VENDOR MATCH
# ============================================================

def find_exact_vendor(query):

    normalized_query = normalize_text(query)

    connection = get_connection()
    cursor = None

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

        return cursor.fetchone()

    finally:

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# FUZZY PRODUCT MATCH
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
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches


# ============================================================
# FUZZY VENDOR MATCH
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
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches


# ============================================================
# PRODUCT → VENDORS
# ============================================================

def get_product_vendors(product_id):

    connection = get_connection()
    cursor = None

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

        vendors = []

        for row in rows:

            vendors.append(
                {
                    "vendor_id": row[0],
                    "vendor": row[1],
                    "contact": row[2] or "",
                    "mail_id": row[3] or "",
                }
            )

        return vendors

    finally:

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# VENDOR → PRODUCTS
# ============================================================

def get_vendor_products(vendor_id):

    connection = get_connection()
    cursor = None

    try:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # Vendor details
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Products
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Prepare vendor details
        # ----------------------------------------------------

        vendor_details = {}

        if vendor_row:

            vendor_details = {
                "vendor": vendor_row[0],
                "contact": vendor_row[1] or "",
                "mail_id": vendor_row[2] or "",
            }

        # ----------------------------------------------------
        # Prepare products
        # ----------------------------------------------------

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

        if cursor:
            cursor.close()

        connection.close()


# ============================================================
# MAIN SEARCH API
# ============================================================

@app.post("/api/search")
def search(request: SearchRequest):

    query = request.query.strip()

    # --------------------------------------------------------
    # EMPTY QUERY
    # --------------------------------------------------------

    if not query:

        return {
            "type": "no_match",
            "message": "Please enter a product or vendor name.",
        }

    # --------------------------------------------------------
    # EXACT PRODUCT
    # --------------------------------------------------------

    product = find_exact_product(query)

    if product:

        product_id = product[0]
        product_name = product[1]

        vendors = get_product_vendors(
            product_id
        )

        return {
            "type": "product",
            "matched_name": product_name,
            "results": vendors,
        }

    # --------------------------------------------------------
    # EXACT VENDOR
    # --------------------------------------------------------

    vendor = find_exact_vendor(query)

    if vendor:

        vendor_id = vendor[0]
        vendor_name = vendor[1]

        result = get_vendor_products(
            vendor_id
        )

        return {
            "type": "vendor",
            "matched_name": vendor_name,
            "vendor_details": result["vendor_details"],
            "results": result["products"],
        }

    # --------------------------------------------------------
    # FUZZY PRODUCT
    # --------------------------------------------------------

    product_matches = find_matching_products(query)

    if len(product_matches) == 1:

        matched = product_matches[0]

        vendors = get_product_vendors(
            matched["product_id"]
        )

        return {
            "type": "product",
            "matched_name": matched["product_name"],
            "results": vendors,
        }

    # --------------------------------------------------------
    # FUZZY VENDOR
    # --------------------------------------------------------

    vendor_matches = find_matching_vendors(query)

    if len(vendor_matches) == 1:

        matched = vendor_matches[0]

        result = get_vendor_products(
            matched["vendor_id"]
        )

        return {
            "type": "vendor",
            "matched_name": matched["vendor_name"],
            "vendor_details": result["vendor_details"],
            "results": result["products"],
        }

    # --------------------------------------------------------
    # MULTIPLE PRODUCTS
    # --------------------------------------------------------

    if len(product_matches) > 1:

        return {
            "type": "multiple_products",
            "results": product_matches,
        }

    # --------------------------------------------------------
    # MULTIPLE VENDORS
    # --------------------------------------------------------

    if len(vendor_matches) > 1:

        return {
            "type": "multiple_vendors",
            "results": vendor_matches,
        }

    # --------------------------------------------------------
    # NO MATCH
    # --------------------------------------------------------

    return {
        "type": "no_match",
        "message": "No matching product or vendor was found.",
    }


# ============================================================
# AUTOCOMPLETE SUGGESTIONS
# ============================================================

@app.get("/api/suggestions")
def get_suggestions(q: str):

    query = q.strip()

    # --------------------------------------------------------
    # EMPTY QUERY
    # --------------------------------------------------------

    if not query:

        return {
            "products": [],
            "vendors": [],
        }

    connection = get_connection()
    cursor = None

    try:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # PRODUCT SUGGESTIONS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT product_id, product_name
            FROM products
            WHERE product_name ILIKE %s
            ORDER BY product_name
            LIMIT 8
            """,
            (f"%{query}%",),
        )

        product_rows = cursor.fetchall()

        products = [
            {
                "product_id": row[0],
                "product_name": row[1],
            }
            for row in product_rows
        ]

        # ----------------------------------------------------
        # VENDOR SUGGESTIONS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT vendor_id, vendor_name
            FROM vendors
            WHERE vendor_name ILIKE %s
            ORDER BY vendor_name
            LIMIT 8
            """,
            (f"%{query}%",),
        )

        vendor_rows = cursor.fetchall()

        vendors = [
            {
                "vendor_id": row[0],
                "vendor_name": row[1],
            }
            for row in vendor_rows
        ]

        return {
            "products": products,
            "vendors": vendors,
        }

    finally:

        if cursor:
            cursor.close()

        connection.close()