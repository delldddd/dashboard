# dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from st_aggrid.shared import JsCode
import plotly.express as px
import re
from io import BytesIO
from dateutil import parser

st.set_page_config(page_title="UPI Financial Manager", layout="wide", initial_sidebar_state="expanded")

# ---------------------------
# Custom CSS for modern look
# ---------------------------
st.markdown(
    """
    <style>
    .stApp { background: #f6f9fc; font-family: Inter, Arial, sans-serif; }
    .card { background: white; border-radius: 12px; padding: 14px; box-shadow: 0 6px 18px rgba(30,40,60,0.08); }
    .kpi { font-size: 18px; color: #6b7280; }
    .kpi-value { font-size: 22px; font-weight:700; }
    .credit-badge { background: #E6FFFA; color:#065F46; padding: 4px 8px; border-radius: 999px; font-weight:600; }
    .debit-badge { background: #FEF2F2; color:#B91C1C; padding: 4px 8px; border-radius: 999px; font-weight:600; }
    .top-title { font-size:20px; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Helper utilities
# ---------------------------
def read_uploaded_file(uploaded_file):
    """Read uploaded file based on its type"""
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.txt'):
            # Try to read as CSV first, if that fails, read as space/tab separated
            try:
                return pd.read_csv(uploaded_file, sep=None, engine='python')
            except:
                return pd.read_csv(uploaded_file, sep='\t')
        else:
            st.error(f"Unsupported file type: {uploaded_file.name}")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def try_parse_date(x):
    try:
        if pd.isna(x):
            return pd.NaT
        if isinstance(x, (pd.Timestamp, np.datetime64, pd.DatetimeTZDtype)):
            return pd.to_datetime(x)
        s = str(x).strip()
        if s == "":
            return pd.NaT
        # let dateutil handle many formats
        return parser.parse(s, dayfirst=False, fuzzy=True)
    except Exception:
        return pd.NaT

def extract_merchant(text):
    if pd.isna(text):
        return ""
    s = str(text)

    # Enhanced patterns for UPI transactions
    # Pattern 1: UPI-MERCHANT_NAME-@BANK-REF-UPI
    m = re.search(r"UPI[-/]([^-@]+?)(?:-|@|\s|$)", s, re.IGNORECASE)
    if m:
        merchant = m.group(1).strip()
        if merchant.upper() != "UPI" and len(merchant) > 2:
            return merchant

    # Pattern 2: REV-UPI-REF-MERCHANT@BANK-REF-UPI (reversal transactions)
    m_rev = re.search(r"REV-UPI-[^-]+-([^-@]+?)(?:-|@|\s|$)", s, re.IGNORECASE)
    if m_rev:
        merchant = m_rev.group(1).strip()
        if merchant.upper() != "UPI" and len(merchant) > 2:
            return merchant

    # Pattern 3: FT-REF-ACCOUNT - MERCHANT - DESCRIPTION (fund transfers)
    m_ft = re.search(r"FT-[^-]+-[^-]+-\s*([^-]+?)(?:\s*-\s*[^-]*)?$", s, re.IGNORECASE)
    if m_ft:
        merchant = m_ft.group(1).strip()
        if len(merchant) > 2:
            return merchant

    # Pattern 4: Extract merchant from @upi format
    m_atupi = re.search(r"@upi[:\s]*([A-Za-z0-9._-]+)", s, re.IGNORECASE)
    if m_atupi:
        return m_atupi.group(1).strip()

    # Pattern 5: Extract from "to:" or "from:" patterns
    m_to = re.search(r"to:?\s*([A-Za-z0-9 &._@-]{3,})", s, re.IGNORECASE)
    if m_to:
        return m_to.group(1).strip()

    m_from = re.search(r"from:?\s*([A-Za-z0-9 &._@-]{3,})", s, re.IGNORECASE)
    if m_from:
        return m_from.group(1).strip()

    # Fallback: pick first meaningful chunk before comma, pipe, colon, or dash
    parts = re.split(r"[,|:-]", s)
    for part in parts:
        part = part.strip()
        if (part.upper() != "UPI" and part != "" and 
            not re.match(r"^\d+$", part) and  # Skip pure numbers
            len(part) > 2):
            return part[:60]
    
    # Final fallback: return whole text truncated
    return s[:60]

# ---------------------------
# Page layout
# ---------------------------
st.markdown("<div class='top-title'>UPI Financial Manager</div>", unsafe_allow_html=True)
st.write("Upload bank / UPI statements (CSV, XLSX, TXT). Merchant extraction, editable categories, interactive charts and a pro-style UI.")

with st.sidebar:
    st.header("Upload & Filters")
    uploaded = st.file_uploader("Upload CSV / XLSX / TXT", type=["csv", "xlsx", "xls", "txt"])
    st.markdown("---")
    global_search = st.text_input("Search (merchant, category, amount...)")
    date_min = st.date_input("From", value=None)
    date_max = st.date_input("To", value=None)
    st.markdown("---")
    st.write("Display options")
    show_by_category = st.checkbox("Show Category chart", value=True)
    show_time_series = st.checkbox("Show Time series of spend", value=True)
    st.markdown("---")
    st.caption("Tip: You can edit Category directly in the table. Use the download button to export your changes.")

# ---------------------------
# Load data
# ---------------------------
if uploaded is not None:
    try:
        raw = read_uploaded_file(uploaded)
        if raw is None:
            st.stop()
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    st.subheader("Raw preview")
    st.dataframe(raw.head(6), use_container_width=True)

    # Attempt to find typical columns
    cols_lower = [c.lower() for c in raw.columns]

    # Date extraction
    date_col = None
    for c in raw.columns:
        if re.search(r"date|txn date|value date", c, re.IGNORECASE):
            date_col = c
            break

    # Narration/description column detection
    narration_col = None
    for c in raw.columns:
        if re.search(r"narration|description|remarks|particulars|details", c, re.IGNORECASE):
            narration_col = c
            break

    # Amount detection (choose first 'amount' like column or debit/credit columns)
    amount_col = None
    debit_col = None
    credit_col = None
    for c in raw.columns:
        if re.search(r"amount|amt", c, re.IGNORECASE) and amount_col is None:
            amount_col = c
        if re.search(r"debit|withdraw", c, re.IGNORECASE) and debit_col is None:
            debit_col = c
        if re.search(r"credit|deposit", c, re.IGNORECASE) and credit_col is None:
            credit_col = c

    df = raw.copy()

    # Normalize / create Date column
    if date_col:
        df["Date"] = df[date_col].apply(try_parse_date)
    else:
        # try to parse from any column containing date-like strings
        parsed = pd.Series([try_parse_date(x) for x in df.apply(lambda row: " ".join(map(str, row.values)), axis=1)])
        df["Date"] = parsed

    # Merchant column
    if narration_col:
        df["Merchant"] = df[narration_col].apply(extract_merchant)
    else:
        # fallback: try to find meaningful text column
        text_cols = [c for c in df.columns if df[c].dtype == object]
        if text_cols:
            df["Merchant"] = df[text_cols[0]].apply(extract_merchant)
        else:
            df["Merchant"] = ""

    # Amount / Type handling
    if amount_col:
        df["Amount"] = pd.to_numeric(df[amount_col].astype(str).str.replace(',', '').str.replace('INR', '').str.replace('Rs.', ''), errors='coerce').fillna(0)
        # If there are explicit Debit/Credit columns, prefer them
        if debit_col and credit_col:
            df["Debit"] = pd.to_numeric(df[debit_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df["Credit"] = pd.to_numeric(df[credit_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df["Amount"] = df["Credit"].replace(0, np.nan).fillna(df["Debit"])
            # ensure positive
            df["Amount"] = df["Amount"].abs().fillna(0)
            df["Type"] = np.where(df["Credit"] > 0, "Credit", "Debit")
        else:
            # Heuristic: if original amount strings contain '-', treat as Debit
            example_col = raw[amount_col].astype(str).fillna("")
            df["Type"] = np.where(example_col.str.contains(r"-"), "Debit", "Credit")
            df["Amount"] = df["Amount"].abs()
    else:
        # if separate columns exist, try to combine them
        df["Amount"] = 0
        df["Type"] = "Debit"

    # Add Category if missing
    if "Category" not in df.columns:
        df["Category"] = ""

    # Standardize Date string for presentation
    df["Date_display"] = df["Date"].dt.date

    # Basic filtering based on sidebar inputs
    working = df.copy()
    # date filters
    if date_min:
        working = working[working["Date"].dt.date >= date_min]
    if date_max:
        working = working[working["Date"].dt.date <= date_max]

    # search filter
    if global_search:
        s = global_search.lower()
        mask = (
            working["Merchant"].fillna("").str.lower().str.contains(s) |
            working["Category"].fillna("").str.lower().str.contains(s) |
            working["Amount"].astype(str).str.contains(s) |
            working["Date_display"].astype(str).str.contains(s)
        )
        working = working[mask]

    # Reorder columns for display
    display_cols = ["Date_display", "Merchant", "Amount", "Type", "Category"]
    for c in display_cols:
        if c not in working.columns:
            working[c] = ""

    display_df = working[display_cols].rename(columns={"Date_display": "Date"})

    # ---------------------------
    # AG Grid for interactive table
    # ---------------------------
    st.subheader("Transactions")

    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    # make Category editable
    gb.configure_column("Category", editable=True)
    gb.configure_column("Amount", type=["numericColumn"], aggFunc="sum")
    # add single row selection
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        enable_enterprise_modules=False,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        theme="fresh",
        height=400,
    )

    edited = grid_response["data"]

    # show small KPIs
    total_spent = edited.loc[edited["Type"] == "Debit", "Amount"].sum()
    total_credit = edited.loc[edited["Type"] == "Credit", "Amount"].sum()
    balance = total_credit - total_spent

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown("<div class='card'><div class='kpi'>Total Spent</div><div class='kpi-value'>₹ {:,.2f}</div></div>".format(total_spent), unsafe_allow_html=True)
    with k2:
        st.markdown("<div class='card'><div class='kpi'>Total Credit</div><div class='kpi-value'>₹ {:,.2f}</div></div>".format(total_credit), unsafe_allow_html=True)
    with k3:
        st.markdown("<div class='card'><div class='kpi'>Net</div><div class='kpi-value'>₹ {:,.2f}</div></div>".format(balance), unsafe_allow_html=True)

    # ---------------------------
    # Charts (Plotly)
    # ---------------------------
    st.subheader("Insights & Charts")

    col_a, col_b = st.columns((2, 1))

    with col_a:
        if show_time_series:
            # time series: daily sum of debit
            ts = edited.copy()
            ts["Date"] = pd.to_datetime(ts["Date"])
            ts_daily = ts.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
            if not ts_daily.empty:
                fig_ts = px.line(ts_daily, x="Date", y="Amount", title="Daily transaction amount (all types)", markers=True)
                fig_ts.update_layout(margin=dict(t=40, b=10, l=10, r=10))
                st.plotly_chart(fig_ts, use_container_width=True)
            else:
                st.info("No time-series data to plot.")

        # Top merchants bar
        top_merchants = edited.groupby("Merchant")["Amount"].sum().sort_values(ascending=False).head(15).reset_index()
        if not top_merchants.empty:
            fig_bar = px.bar(top_merchants, x="Merchant", y="Amount", title="Top merchants by value",
                             labels={"Amount": "Total Amount"}, hover_data={"Merchant": True, "Amount": True})
            fig_bar.update_layout(xaxis_tickangle=-45, margin=dict(t=40, b=150))
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        if show_by_category:
            cat_sum = edited.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
            if not cat_sum.empty:
                fig_pie = px.pie(cat_sum, values="Amount", names="Category", title="Spend by category", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No category data to show. Edit categories in the table to populate this chart.")

        # Show small table of largest transactions
        st.markdown("**Largest transactions**")
        st.dataframe(edited.sort_values("Amount", ascending=False).head(6).style.format({"Amount": "₹{:,.2f}"}), use_container_width=True)

    # ---------------------------
    # Export edited data
    # ---------------------------
    def to_excel_bytes(df_export: pd.DataFrame):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="transactions")
            writer.save()
        return buffer.getvalue()

    download_format = st.selectbox("Download format", options=["csv", "xlsx"], index=0)
    if download_format == "csv":
        csv_bytes = edited.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download CSV", csv_bytes, file_name="transactions_edited.csv", mime="text/csv")
    else:
        xlsx_bytes = to_excel_bytes(edited)
        st.download_button("⬇ Download XLSX", xlsx_bytes, file_name="transactions_edited.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.success("Loaded and processed file. Edit categories directly in the table, filter, sort and then use the download button.")
else:
    st.info("Upload a bank statement file (CSV / XLSX / TXT) to begin.")