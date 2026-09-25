import streamlit as st

from product_search import search


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Hindcon-Speciality-Vendor–Product Search System",
    page_icon="🔎",
    layout="wide",
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# HEADER
# ============================================================

st.title("🔎 Hindcon-Speciality Vendor–Product Search System")

st.write(
    "Search for a product to find its associated vendors, "
    "or search for a vendor to find its associated products."
)


# ============================================================
# DISPLAY PREVIOUS CHAT
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"],
            unsafe_allow_html=True,
        )


# ============================================================
# CHAT INPUT
# ============================================================

user_query = st.chat_input(
    "Search product or vendor..."
)


# ============================================================
# PROCESS SEARCH
# ============================================================

if user_query:

    # --------------------------------------------------------
    # Display user message
    # --------------------------------------------------------

    with st.chat_message("user"):

        st.markdown(user_query)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )


    # --------------------------------------------------------
    # Search PostgreSQL
    # --------------------------------------------------------

    try:

        result = search(user_query)

    except Exception as error:

        response = (
            "❌ **Database connection error**\n\n"
            "The application could not connect to "
            "the PostgreSQL database."
        )

        with st.chat_message("assistant"):

            st.markdown(response)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        st.stop()


    # --------------------------------------------------------
    # Prepare response
    # --------------------------------------------------------

    result_type = result.get("type")


    # ========================================================
    # PRODUCT RESULT
    # ========================================================

    if result_type == "product":

        matched_name = result.get(
            "matched_name",
            user_query,
        )

        results = result.get(
            "results",
            [],
        )

        response = (
            f"### 📦 Product: {matched_name}\n\n"
        )

        if results:

            response += "### 🏢 Associated Vendors\n\n"

            response += (
                "| No. | Vendor | Contact | Mail ID |\n"
            )

            response += (
                "|---:|---|---|---|\n"
            )

            for index, vendor_info in enumerate(
                results,
                start=1,
            ):

                vendor = vendor_info.get(
                    "vendor",
                    "",
                )

                contact = vendor_info.get(
                    "contact",
                    "",
                )

                mail_id = vendor_info.get(
                    "mail_id",
                    "",
                )

                response += (
                    f"| {index} | "
                    f"{vendor} | "
                    f"{contact} | "
                    f"{mail_id} |\n"
                )

        else:

            response += (
                "No vendors are associated with "
                "this product."
            )


    # ========================================================
    # VENDOR RESULT
    # ========================================================

    elif result_type == "vendor":

        matched_name = result.get(
            "matched_name",
            user_query,
        )

        vendor_details = result.get(
            "vendor_details",
            {},
        )

        contact = vendor_details.get(
            "contact",
            "",
        )

        mail_id = vendor_details.get(
            "mail_id",
            "",
        )

        results = result.get(
            "results",
            [],
        )

        response = (
            f"### 🏢 Vendor: {matched_name}\n\n"
        )

        response += "### 📞 Contact Details\n\n"

        response += (
            "| Contact | Mail ID |\n"
        )

        response += (
            "|---|---|\n"
        )

        response += (
            f"| {contact} | {mail_id} |\n\n"
        )

        response += "### 📦 Associated Products\n\n"

        if results:

            response += (
                "| No. | Product |\n"
            )

            response += (
                "|---:|---|\n"
            )

            for index, product_info in enumerate(
                results,
                start=1,
            ):

                product_name = product_info.get(
                    "product_name",
                    "",
                )

                response += (
                    f"| {index} | "
                    f"{product_name} |\n"
                )

        else:

            response += (
                "No products are associated with "
                "this vendor."
            )


    # ========================================================
    # MULTIPLE PRODUCT MATCHES
    # ========================================================

    elif result_type == "multiple_products":

        response = (
            "### 🔎 Multiple Products Found\n\n"
            "Please specify which product you mean:\n\n"
        )

        response += (
            "| No. | Product |\n"
        )

        response += (
            "|---:|---|\n"
        )

        for index, product in enumerate(
            result.get("results", []),
            start=1,
        ):

            response += (
                f"| {index} | "
                f"{product['product_name']} |\n"
            )


    # ========================================================
    # MULTIPLE VENDOR MATCHES
    # ========================================================

    elif result_type == "multiple_vendors":

        response = (
            "### 🔎 Multiple Vendors Found\n\n"
            "Please specify which vendor you mean:\n\n"
        )

        response += (
            "| No. | Vendor |\n"
        )

        response += (
            "|---:|---|\n"
        )

        for index, vendor in enumerate(
            result.get("results", []),
            start=1,
        ):

            response += (
                f"| {index} | "
                f"{vendor['vendor_name']} |\n"
            )


    # ========================================================
    # NO MATCH
    # ========================================================

    else:

        response = (
            "❌ **No matching product or vendor "
            "was found.**"
        )


    # ========================================================
    # DISPLAY ASSISTANT RESPONSE
    # ========================================================

    with st.chat_message("assistant"):

        st.markdown(
            response,
            unsafe_allow_html=True,
        )


    # ========================================================
    # SAVE RESPONSE TO CHAT HISTORY
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
        }
    )