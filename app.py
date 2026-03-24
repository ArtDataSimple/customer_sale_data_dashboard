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
    options=sorted(orders['Category'].unique()),
    default=sorted(orders['Category'].unique())
)

subcategory_filter = st.sidebar.multiselect(
    "Sub-Category",
    options=sorted(merged['Sub-Category'].unique()),
    default=sorted(merged['Sub-Category'].unique())
)

region_filter = st.sidebar.multiselect(
    "Region",
    options=sorted(merged['Region'].unique()),
    default=sorted(merged['Region'].unique())
)

state_filter = st.sidebar.multiselect(
    "State",
    options=sorted(merged['State'].unique()),
    default=sorted(merged['State'].unique())
)

segment_filter = st.sidebar.multiselect(
    "Segment",
    options=sorted(merged['Segment'].unique()),
    default=sorted(merged['Segment'].unique())
)

ship_mode_filter = st.sidebar.multiselect(
    "Ship Mode",
    options=sorted(merged['Ship Mode'].unique()),
    default=sorted(merged['Ship Mode'].unique())
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
    (merged['Sub-Category'].isin(subcategory_filter)) &
    (merged['Region'].isin(region_filter)) &
    (merged['State'].isin(state_filter)) &
    (merged['Segment'].isin(segment_filter)) &
    (merged['Ship Mode'].isin(ship_mode_filter)) &
    (merged['Order Date'].dt.date >= start_date) &
    (merged['Order Date'].dt.date <= end_date)
]

st.title("Customer Orders & Returns Dashboard")

# Calculate metrics
total_sales = filtered['Sales'].sum()
total_profit = filtered['Profit'].sum()
return_rate = filtered[['Order ID','Returned']].drop_duplicates()['Returned'].mean()
unique_customers = filtered['Customer ID'].nunique()
unique_orders = filtered['Order ID'].nunique()
avg_order_value = total_sales / unique_orders if unique_orders > 0 else 0

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Sales Analysis", "Returns Analysis", "Geographic Analysis"])

with tab1:
    st.header("Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", f"${total_sales/1e6:.2f}M")
    col2.metric("Total Profit", f"${total_profit/1e6:.2f}M")
    col3.metric("Return Rate", f"{return_rate*100:.2f}%")

    col4, col5, col6 = st.columns(3)
    col4.metric("Unique Customers", f"{unique_customers:,}")
    col5.metric("Unique Orders", f"{unique_orders:,}")
    col6.metric("Avg. Order Value", f"${avg_order_value:,.2f}")

    st.subheader("Monthly Sales Trend")
    filtered['YearMonth'] = filtered['Order Date'].dt.to_period('M').dt.to_timestamp()

    # Monthly sales by category (line per category)
    monthly_sales_cat = filtered.groupby(['YearMonth', 'Category'])['Sales'].sum().unstack(fill_value=0)

    # Render category trends with legend via matplotlib for color control
    fig, ax = plt.subplots(figsize=(10, 5))
    for col in monthly_sales_cat.columns:
        ax.plot(monthly_sales_cat.index, monthly_sales_cat[col], marker='o', label=col)

    ax.set_title('Monthly Sales Trend by Category')
    ax.set_xlabel('Month')
    ax.set_ylabel('Sales')

    # Format x-axis as Year-Month
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(plt.matplotlib.dates.MonthLocator(interval=1))
    ax.tick_params(axis='x', rotation=45)
    ax.legend(title='Category', loc='upper left')

    if highlight_q4:
        # highlight Q4 date ranges on the matplotlib chart
        months = pd.to_datetime(monthly_sales_cat.index)
        years = sorted({d.year for d in months})
        for year in years:
            ax.axvspan(pd.Timestamp(f"{year}-10-01"), pd.Timestamp(f"{year}-12-31"), color='orange', alpha=0.15)
        st.caption("Q4 periods (Oct-Dec) are highlighted in the chart below.")

    st.pyplot(fig)
    st.markdown("---")
    st.caption("Monthly sales trend is displayed separately for each category with legend.")

with tab2:
    st.header("Sales Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sales by Category")
        category_sales = filtered.groupby('Category')['Sales'].sum().sort_values(ascending=False)
        st.bar_chart(category_sales)

    with col2:
        st.subheader("Sales by Sub-Category")
        subcategory_sales = filtered.groupby('Sub-Category')['Sales'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(subcategory_sales)

    st.subheader("Profit by Segment")
    segment_profit = filtered.groupby('Segment')['Profit'].sum().sort_values(ascending=False)
    st.bar_chart(segment_profit)

with tab3:
    st.header("Returns Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Return Rate by Category")
        order_level = filtered[['Order ID','Category','Returned']].drop_duplicates()
        return_by_cat = order_level.groupby('Category')['Returned'].mean() * 100
        st.bar_chart(return_by_cat)

    with col2:
        st.subheader("Return Rate by Sub-Category")
        order_level_sub = filtered[['Order ID','Sub-Category','Returned']].drop_duplicates()
        return_by_subcat = order_level_sub.groupby('Sub-Category')['Returned'].mean() * 100
        return_by_subcat = return_by_subcat.sort_values(ascending=False).head(10)
        st.bar_chart(return_by_subcat)

    st.subheader("Returns by Ship Mode")
    order_level_ship = filtered[['Order ID','Ship Mode','Returned']].drop_duplicates()
    return_by_ship = order_level_ship.groupby('Ship Mode')['Returned'].mean() * 100
    st.bar_chart(return_by_ship)

with tab4:
    st.header("Geographic Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sales by Region")
        region_sales = filtered.groupby('Region')['Sales'].sum().sort_values(ascending=False)
        st.bar_chart(region_sales)

    with col2:
        st.subheader("Sales by State")
        state_sales = filtered.groupby('State')['Sales'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(state_sales)

    st.subheader("Top Cities by Orders & AOV")
    city_order = filtered.groupby('City').agg(
        Orders=('Order ID','nunique'),
        TotalSales=('Sales','sum')
    ).reset_index()
    city_order['AOV'] = city_order['TotalSales'] / city_order['Orders']
    city_order = city_order.sort_values('TotalSales', ascending=False).head(20)
    city_order['AOV'] = city_order['AOV'].map('${:,.2f}'.format)
    city_order = city_order.rename(columns={'TotalSales':'Sales'})
    city_order = city_order[['City','Orders','AOV']].reset_index(drop=True)

    st.dataframe(city_order, height=400)
