
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="BLN NexGen Edge - Whale Curve Analyzer", layout="wide")

# --- Branding Header ---
st.markdown("""
    <div style="text-align: center;">
        <h1 style="font-size: 48px; margin-bottom: 0;">BLN NexGen Edge</h1>
        <h3 style="font-weight: normal; color: gray; margin-top: 0;">Profitability Intelligence Platform</h3>
    </div>
    <hr style="border: 1px solid lightgray;">
""", unsafe_allow_html=True)

st.title("🐳 Whale Curve Analyzer")
st.markdown("Upload your Sales and Cost data to visualize profitability by Customer, Product, Salesperson, and Region.")

# --- Enhanced Upload Instructions and Sample Tables ---

st.markdown("## Upload Your Data Files")

# SALES DATA SECTION
st.markdown("### Upload Sales Data (.xlsx)")
st.info(
    "Your sales data file must contain these columns:\n\n"
    "- Customer ID\n"
    "- Product ID\n"
    "- Net Sales $\n"
    "- Salesperson\n"
    "- Region\n\n"
    "Each row should represent one transaction or invoice line. "
    "Net Sales $ should reflect revenue after any discounts."
)
sample_sales = pd.DataFrame({
    "Customer ID": ["C001", "C002"],
    "Product ID": ["P101", "P102"],
    "Net Sales $": [12000, 9500],
    "Salesperson": ["Sally", "Jim"],
    "Region": ["North", "West"]
})
st.markdown("**Example Sales Data Format:**")
st.dataframe(sample_sales)

# COST DATA SECTION
st.markdown("### Upload Cost Detail Data (.xlsx)")
st.info(
    "Your cost file must contain:\n\n"
    "- Product ID\n"
    "Plus either:\n"
    "- Standard Total Cost\n"
    "OR\n"
    "- Material Cost, Labor Cost, Overhead Cost, Service Cost\n\n"
    "Note: If 'Standard Total Cost' is provided, it overrides all other cost fields."
)
sample_cost = pd.DataFrame({
    "Product ID": ["P101", "P102"],
    "Standard Total Cost": [7200, None],
    "Material Cost": [None, 3000],
    "Labor Cost": [None, 2000],
    "Overhead Cost": [None, 1500],
    "Service Cost": [None, 1000]
})
st.markdown("**Example Cost Data Format:**")
st.dataframe(sample_cost)


col1, col2 = st.columns(2)

with col1:
    sales_file = st.file_uploader("Upload Sales Data (.xlsx)", type=["xlsx"])
with col2:
    cost_file = st.file_uploader("Upload Cost Detail Data (.xlsx)", type=["xlsx"])

def load_sales_data(uploaded_file):
    try:
        sales = pd.read_excel(uploaded_file)
        required_cols = ['Customer ID', 'Product ID', 'Net Sales $', 'Salesperson', 'Region']
        if not all(col in sales.columns for col in required_cols):
            st.error(f"Missing required columns in Sales Data: {required_cols}")
            return None
        return sales
    except Exception as e:
        st.error(f"Error reading Sales file: {e}")
        return None

def load_cost_data(uploaded_file):
    try:
        cost = pd.read_excel(uploaded_file)
        required_cols = ['Product ID']
        if not all(col in cost.columns for col in required_cols):
            st.error(f"Missing required columns in Cost Data: {required_cols}")
            return None
        return cost
    except Exception as e:
        st.error(f"Error reading Cost file: {e}")
        return None

if sales_file and cost_file:
    sales_data = load_sales_data(sales_file)
    cost_data = load_cost_data(cost_file)

    if sales_data is not None and cost_data is not None:
        if sales_data.shape[0] > 10000:
            st.warning("⚠️ Your Sales Data file contains more than 10,000 rows. Performance may be slower depending on your system and browser.")
        if cost_data.shape[0] > 10000:
            st.warning("⚠️ Your Cost Detail file contains more than 10,000 rows. Performance may be slower depending on your system and browser.")

        def merge_data(sales, cost):
            merged = pd.merge(sales, cost, on='Product ID', how='left')
            merged.fillna(0, inplace=True)
            merged['Unit Cost'] = np.where(
                merged['Standard Total Cost'] > 0,
                merged['Standard Total Cost'],
                merged['Material Cost'] + merged['Labor Cost'] + merged['Overhead Cost'] + merged['Service Cost']
            )
            merged['Gross Margin $'] = merged['Net Sales $'] - merged['Unit Cost']
            return merged

        def generate_summary(df, group_field):
            total_sales = df['Net Sales $'].sum()
            summary = df.groupby(group_field).agg({
                'Net Sales $': 'sum',
                'Gross Margin $': 'sum'
            }).sort_values('Gross Margin $', ascending=False).reset_index()
            summary['% of Sales'] = 100 * summary['Net Sales $'] / total_sales
            summary['Cumulative Sales $'] = summary['Net Sales $'].cumsum()
            summary['Cumulative Sales %'] = 100 * summary['Cumulative Sales $'] / total_sales
            summary['Margin %'] = 100 * summary['Gross Margin $'] / summary['Net Sales $']
            summary['Cumulative Margin $'] = summary['Gross Margin $'].cumsum()
            summary['Cumulative Profit %'] = 100 * summary['Cumulative Margin $'] / summary['Gross Margin $'].sum()
            return summary

        def get_top_bottom(summary, field, top_n=20):
            top_20 = summary.sort_values(field, ascending=False).head(top_n)
            bottom_20 = summary.sort_values(field, ascending=True).head(top_n)
            return top_20, bottom_20

        def plot_whale_curve(summary, id_column, title):
            fig = px.line(
                summary,
                y="Cumulative Profit %",
                markers=True,
                hover_data={
                    id_column: True,
                    'Net Sales $': ':.2f',
                    'Margin %': ':.1f',
                    'Cumulative Profit %': False,
                },
                labels={"Cumulative Profit %": "Cumulative Profit (%)"},
                title=title
            )
            fig.update_layout(
                xaxis_title="Rank",
                yaxis_title="Cumulative Profit (%)",
                hovermode="closest",
                template="simple_white"
            )
            return fig

        def format_summary(df):
            return df.style.format({
                "Net Sales $": "${:,.2f}",
                "% of Sales": "{:.1f}%",
                "Cumulative Sales $": "${:,.2f}",
                "Cumulative Sales %": "{:.1f}%",
                "Gross Margin $": "${:,.2f}",
                "Margin %": "{:.1f}%",
                "Cumulative Margin $": "${:,.2f}",
                "Cumulative Profit %": "{:.1f}%"
            })

        merged_data = merge_data(sales_data, cost_data)

        for view_name, group_field in {
            "Customer": "Customer ID",
            "Product": "Product ID",
            "Salesperson": "Salesperson",
            "Region": "Region"
        }.items():
            st.header(f"📈 Whale Curve by {view_name}")
            summary = generate_summary(merged_data, group_field)
            fig = plot_whale_curve(summary, group_field, f"Whale Curve: {view_name} Profitability")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"📋 Full {view_name} Profitability Summary")
            st.dataframe(format_summary(summary))

            st.download_button(
                label=f"Download {view_name} Summary as CSV",
                data=summary.to_csv(index=False).encode('utf-8'),
                file_name=f"{view_name.lower()}_profitability_summary.csv",
                mime="text/csv"
            )

            top_sales, _ = get_top_bottom(summary, 'Net Sales $')
            top_margin, bottom_margin = get_top_bottom(summary, 'Margin %')

            st.subheader(f"📋 Top 20 {view_name}s by Net Sales $")
            st.dataframe(format_summary(top_sales))

            st.subheader(f"📋 Top 20 {view_name}s by Margin %")
            st.dataframe(format_summary(top_margin))

            st.subheader(f"📋 Bottom 20 {view_name}s by Margin %")
            st.dataframe(format_summary(bottom_margin))
else:
    st.info("Please upload both Sales and Cost data files to begin.")
