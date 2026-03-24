import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

@st.cache_data
def load_data():
    customers = pd.read_csv("customers.csv")
    orders = pd.read_csv("orders.csv")
    returns = pd.read_csv("returns.csv")

    orders['Order Date'] = pd.to_datetime(orders['Order Date'], format='%m/%d/%y')
    orders['Ship Date'] = pd.to_datetime(orders['Ship Date'], format='%m/%d/%y')
    customers['Postal Code'] = customers['Postal Code'].astype(str)

    merged = orders.merge(customers, on='Customer ID', how='left')

    orders['Returned'] = orders['Order ID'].isin(returns['Order ID']).astype(int)
    merged['Returned'] = merged['Order ID'].isin(returns['Order ID']).astype(int)

    return customers, orders, merged

customers, orders, merged = load_data()

st.sidebar.title("Filters")

category_filter = st.sidebar.multiselect(
    "Category",
    options=orders['Category'].unique(),
    default=orders['Category'].unique()
)

region_filter = st.sidebar.multiselect(
    "Region",
    options=merged['Region'].unique(),
    default=merged['Region'].unique()
)

segment_filter = st.sidebar.multiselect(
    "Segment",
    options=merged['Segment'].unique(),
    default=merged['Segment'].unique()
)

min_date = orders['Order Date'].min().date()
max_date = orders['Order Date'].max().date()

order_date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

highlight_q4 = st.sidebar.checkbox("Highlight Q4 (Oct-Dec)", value=False)

if len(order_date_range) == 2:
    start_date, end_date = order_date_range
else:
    start_date = end_date = order_date_range

filtered = merged[
    (merged['Category'].isin(category_filter)) &
    (merged['Region'].isin(region_filter)) &
    (merged['Segment'].isin(segment_filter)) &
    (merged['Order Date'].dt.date >= start_date) &
    (merged['Order Date'].dt.date <= end_date)
]

st.title("Customer Orders & Returns Dashboard")

total_sales = filtered['Sales'].sum()
total_profit = filtered['Profit'].sum()
return_rate = filtered[['Order ID','Returned']].drop_duplicates()['Returned'].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Sales", f"${total_sales:,.0f}")
col2.metric("Profit", f"${total_profit:,.0f}")
col3.metric("Return Rate", f"{return_rate*100:.2f}%")

st.subheader("Monthly Sales")

filtered['YearMonth'] = filtered['Order Date'].dt.to_period('M').dt.to_timestamp()
monthly = filtered.groupby(['YearMonth','Category'])['Sales'].sum().unstack()

fig, ax = plt.subplots(figsize=(10,5))
for col in monthly.columns:
    ax.plot(monthly.index, monthly[col], label=col)

if highlight_q4:
    for year in monthly.index.year.unique():
        ax.axvspan(pd.Timestamp(f"{year}-10-01"), pd.Timestamp(f"{year}-12-31"), color='orange', alpha=0.2)

ax.legend()
st.pyplot(fig)

st.subheader("Return Rate by Category")
order_level = filtered[['Order ID','Category','Returned']].drop_duplicates()
st.bar_chart(order_level.groupby('Category')['Returned'].mean())

st.subheader("Profit by Segment")
st.bar_chart(filtered.groupby('Segment')['Profit'].sum())
