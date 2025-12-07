import streamlit as st
import requests

API_URL = "http://localhost:7860"
# API_URL = "https://mohnish777-enrollmentapi.hf.space/"

st.title("Customer Management UI")

menu = ["View Customers", "Add Customer", "Update Customer", "Delete Customer"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "View Customers":
    st.header("All Customers")
    response = requests.get(f"{API_URL}/customers/")
    if response.status_code == 200:
        customers = response.json()
        if customers:
            import pandas as pd
            df = pd.DataFrame(customers)
            # Search/filter
            search = st.text_input("Search by name, email, or status", "")
            if search:
                df = df[df.apply(lambda row: search.lower() in str(row["name"]).lower() or search.lower() in str(row["email"]).lower() or search.lower() in str(row.get("status", "")).lower(), axis=1)]
            # Column selector
            all_columns = list(df.columns)
            default_cols = [c for c in all_columns if c not in ("reasoning", "address")]
            selected_columns = st.multiselect("Columns to display", all_columns, default=default_cols)
            st.dataframe(df[selected_columns], use_container_width=True, hide_index=True)
            # Download button
            csv = df[selected_columns].to_csv(index=False).encode('utf-8')
            st.download_button("Download as CSV", csv, "customers.csv", "text/csv")
            # Expanders for details
            st.markdown("---")
            st.subheader("Customer Details")
            for idx, row in df.iterrows():
                with st.expander(f"{row['name']} ({row['email']}) - ID: {row['id']}"):
                    for col in all_columns:
                        st.write(f"**{col}:** {row[col]}")
        else:
            st.info("No customers found.")
    else:
        st.error("Failed to fetch customers.")

elif choice == "Add Customer":
    st.header("Add a New Customer")
    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            id = st.number_input("ID", min_value=1, step=1)
            name = st.text_input("Name", placeholder="Enter full name")
            email = st.text_input("Email", placeholder="user@email.com")
        with col2:
            phone = st.text_input("Phone (optional)", placeholder="+1-234-567-8901")
            address = st.text_input("Address (optional)")
            country = st.text_input("Country (optional)")
        st.markdown("---")
        with st.expander("Webinar & Qualification Details (optional)"):
            goal = st.text_input("Goal", placeholder="e.g. Become an AI PM")
            budget = st.selectbox("Budget", options=["", "company", "self"], help="Who is funding?")
            webinar_date_col, join_col, leave_col = st.columns([2,1,1])
            with webinar_date_col:
                webinar_date = st.date_input("Webinar Date")
            with join_col:
                join_time = st.time_input("Join Time")
            with leave_col:
                leave_time = st.time_input("Leave Time")
            import datetime
            webinar_join = datetime.datetime.combine(webinar_date, join_time) if webinar_date and join_time else None
            webinar_leave = datetime.datetime.combine(webinar_date, leave_time) if webinar_date and leave_time else None
            col3, col4, col5 = st.columns(3)
            with col3:
                asked_q = st.checkbox("Asked Questions?", value=False)
            with col4:
                referred = st.checkbox("Referred?", value=False)
            with col5:
                past_touchpoints = st.number_input("Past Touchpoints", min_value=0, step=1)
        st.markdown("---")
        submitted = st.form_submit_button("Add Customer")
        if submitted:
            data = {
                "id": id,
                "name": name,
                "email": email,
                "phone": phone or None,
                "address": address or None,
                "country": country or None,
                "goal": goal or None,
                "budget": budget or None,
                "webinar_join": webinar_join.isoformat() if webinar_join else None,
                "webinar_leave": webinar_leave.isoformat() if webinar_leave else None,
                "asked_q": asked_q,
                "referred": referred,
                "past_touchpoints": past_touchpoints if past_touchpoints else None
            }
            response = requests.post(f"{API_URL}/customers/", json=data)
            if response.status_code == 200:
                st.success("Customer added successfully!")
            else:
                st.error(f"Failed to add customer: {response.text}, response code ={response.status_code}")

elif choice == "Update Customer":
    st.header("Update Customer")
    with st.form("update_customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            id = st.number_input("Customer ID to update", min_value=1, step=1)
            name = st.text_input("New Name", placeholder="Enter full name")
            email = st.text_input("New Email", placeholder="user@email.com")
        with col2:
            phone = st.text_input("New Phone (optional)", placeholder="+1-234-567-8901")
            address = st.text_input("New Address (optional)")
            country = st.text_input("New Country (optional)")
        st.markdown("---")
        with st.expander("Webinar & Qualification Details (optional)"):
            goal = st.text_input("New Goal", placeholder="e.g. Become an AI PM")
            budget = st.selectbox("New Budget", options=["", "company", "self"], help="Who is funding?")
            webinar_date_col, join_col, leave_col = st.columns([2,1,1])
            with webinar_date_col:
                webinar_date = st.date_input("New Webinar Date")
            with join_col:
                join_time = st.time_input("New Join Time")
            with leave_col:
                leave_time = st.time_input("New Leave Time")
            import datetime
            webinar_join = datetime.datetime.combine(webinar_date, join_time) if webinar_date and join_time else None
            webinar_leave = datetime.datetime.combine(webinar_date, leave_time) if webinar_date and leave_time else None
            col3, col4, col5 = st.columns(3)
            with col3:
                asked_q = st.checkbox("Asked Questions?", value=False)
            with col4:
                referred = st.checkbox("Referred?", value=False)
            with col5:
                past_touchpoints = st.number_input("New Past Touchpoints", min_value=0, step=1)
        st.markdown("---")
        submitted = st.form_submit_button("Update Customer", key="update_customer_btn")
        if submitted:
            data = {
                "id": id,
                "name": name,
                "email": email,
                "phone": phone or None,
                "address": address or None,
                "country": country or None,
                "goal": goal or None,
                "budget": budget or None,
                "webinar_join": webinar_join.isoformat() if webinar_join else None,
                "webinar_leave": webinar_leave.isoformat() if webinar_leave else None,
                "asked_q": asked_q,
                "referred": referred,
                "past_touchpoints": past_touchpoints if past_touchpoints else None
            }
            response = requests.put(f"{API_URL}/customers/{id}", json=data)
            if response.status_code == 200:
                st.success("Customer updated successfully!")
            else:
                st.error(f"Failed to update customer: {response.text}")

elif choice == "Delete Customer":
    st.header("Delete Customer")
    delete_id = st.number_input("Customer ID to delete", min_value=1, step=1)
    deletebutton = st.button("Delete Customer")
    if deletebutton:
        response = requests.delete(f"{API_URL}/customers/{delete_id}")
        if response.status_code == 200:
            st.success("Customer deleted successfully!")
        else:
            st.error(f"Failed to delete customer: {response.text}") 