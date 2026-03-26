import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.express as px
import plotly.graph_objects as go

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Overview", "Sales Analysis", "Returns Analysis", "Geographic Analysis", "Custom Visualization", "Data"])

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
        ax.plot(monthly_sales_cat.index, monthly_sales_cat[col], linewidth=2, alpha=0.85, label=col)

    ax.set_title('Monthly Sales Trend by Category')
    ax.set_xlabel('Month')
    ax.set_ylabel('Sales')

    # Format x-axis as Year-Month and reduce ticks for readability
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
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

with tab5:
    st.header("Custom Visualization")
    st.markdown("Create custom data visualizations by selecting a chart type and specifying columns.")
    
    # Get numeric and categorical columns
    numeric_columns = filtered.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_columns = filtered.select_dtypes(include=['object']).columns.tolist()
    all_columns = numeric_columns + categorical_columns
    
    col_viz_type, col_spacing = st.columns([2, 1])
    
    with col_viz_type:
        viz_type = st.selectbox(
            "Select Visualization Type",
            options=[
                "Scatter Plot",
                "Line Chart",
                "Bar Chart",
                "Histogram",
                "Box Plot",
                "Violin Plot",
                "Heatmap (Correlation)"
            ],
            help="Choose the type of visualization you want to create"
        )
    
    st.markdown("---")
    
    # Scatter Plot
    if viz_type == "Scatter Plot":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("Select X-axis column", numeric_columns, key="scatter_x")
        with col2:
            y_col = st.selectbox("Select Y-axis column", numeric_columns, key="scatter_y", 
                                index=1 if len(numeric_columns) > 1 else 0)
        
        color_col = st.selectbox("Color by (optional)", options=[None] + categorical_columns, 
                                help="Optionally color points by a categorical variable")
        size_col = st.selectbox("Size by (optional)", options=[None] + numeric_columns,
                               help="Optionally size points by a numeric variable")
        
        if x_col and y_col:
            fig = px.scatter(filtered, x=x_col, y=y_col, color=color_col, size=size_col,
                           title=f"{x_col} vs {y_col}",
                           hover_data={"Order ID": True} if "Order ID" in filtered.columns else {})
            st.plotly_chart(fig, use_container_width=True)
    
    # Line Chart
    elif viz_type == "Line Chart":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("Select X-axis column", all_columns, key="line_x")
        with col2:
            y_col = st.selectbox("Select Y-axis column", numeric_columns, key="line_y")
        
        if x_col and y_col:
            try:
                if x_col in numeric_columns:
                    plot_data = filtered.sort_values(x_col)
                else:
                    plot_data = filtered.sort_values(x_col)
                
                fig = px.line(plot_data, x=x_col, y=y_col,
                            title=f"{y_col} over {x_col}",
                            markers=True)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating line chart: {str(e)}")
    
    # Bar Chart
    elif viz_type == "Bar Chart":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("Select Category column", all_columns, key="bar_x")
        with col2:
            y_col = st.selectbox("Select Value column", numeric_columns, key="bar_y")
        
        if x_col and y_col:
            try:
                bar_data = filtered.groupby(x_col)[y_col].sum().reset_index()
                bar_data = bar_data.sort_values(y_col, ascending=False)
                
                fig = px.bar(bar_data, x=x_col, y=y_col,
                           title=f"{y_col} by {x_col}",
                           color=y_col,
                           color_continuous_scale="Viridis")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating bar chart: {str(e)}")
    
    # Histogram
    elif viz_type == "Histogram":
        col_hist = st.selectbox("Select column for histogram", numeric_columns)
        bins = st.slider("Number of bins", min_value=5, max_value=100, value=20)
        
        if col_hist:
            fig = px.histogram(filtered, x=col_hist, nbins=bins,
                            title=f"Distribution of {col_hist}",
                            color_discrete_sequence=["#636EFA"])
            st.plotly_chart(fig, use_container_width=True)
    
    # Box Plot
    elif viz_type == "Box Plot":
        col1, col2 = st.columns(2)
        with col1:
            y_col = st.selectbox("Select numeric column", numeric_columns, key="box_y")
        with col2:
            x_col = st.selectbox("Group by (optional)", options=[None] + categorical_columns, key="box_x")
        
        if y_col:
            if x_col:
                fig = px.box(filtered, x=x_col, y=y_col,
                           title=f"Distribution of {y_col} by {x_col}")
            else:
                fig = px.box(filtered, y=y_col,
                           title=f"Distribution of {y_col}")
            st.plotly_chart(fig, use_container_width=True)
    
    # Violin Plot
    elif viz_type == "Violin Plot":
        col1, col2 = st.columns(2)
        with col1:
            y_col = st.selectbox("Select numeric column", numeric_columns, key="violin_y")
        with col2:
            x_col = st.selectbox("Group by (optional)", options=[None] + categorical_columns, key="violin_x")
        
        if y_col:
            if x_col:
                fig = px.violin(filtered, x=x_col, y=y_col,
                             title=f"Distribution of {y_col} by {x_col}",
                             box=True, points="outliers")
            else:
                fig = px.violin(filtered, y=y_col,
                             title=f"Distribution of {y_col}",
                             box=True, points="outliers")
            st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap (Correlation)
    elif viz_type == "Heatmap (Correlation)":
        st.write("Select numeric columns to visualize correlation heatmap:")
        selected_cols = st.multiselect("Columns for correlation", 
                                      numeric_columns,
                                      default=numeric_columns[:min(5, len(numeric_columns))])
        
        if len(selected_cols) >= 2:
            corr_data = filtered[selected_cols].corr()
            fig = go.Figure(data=go.Heatmap(z=corr_data.values,
                                           x=corr_data.columns,
                                           y=corr_data.columns,
                                           colorscale="RdBu",
                                           zmid=0,
                                           text=corr_data.values.round(2),
                                           texttemplate='%{text:.2f}',
                                           textfont={"size": 10}))
            fig.update_layout(title="Correlation Heatmap", height=600)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Please select at least 2 columns to create a correlation heatmap.")

with tab6:
    st.header("Data")

    csv = filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download full filtered dataset as CSV",
        data=csv,
        file_name="filtered_dataset.csv",
        mime="text/csv"
    )

    st.subheader("Filtered rows")
    st.write("Showing the filtered dataset based on current sidebar filters and date range")
    st.dataframe(filtered.head(200), use_container_width=True)
    st.markdown("---")
    st.subheader("Dataset summary")
    st.write(filtered.describe(include='all'))
