import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import date
from pyecharts import options as opts
from pyecharts.charts import Tree
from pyecharts.commons.utils import JsCode
from streamlit_echarts import st_pyecharts
import plotly.express as px

# ------------------ CONFIG ------------------
DATA_FILE = 'tude_data.xlsx'
st.set_page_config(
    page_title='Cell Line Manager', 
    layout='wide',
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Cell Line Tube Manager - Version 2.0"
    }
)

# ------------------ THEME & STYLING ------------------
# Custom CSS for modern look
# ------------------ THEME & STYLING ------------------
st.markdown("""
<style>
  :root {
    --primary: #6B5B95;
    --secondary: #2EC4B6;
    --danger: #E63946;
    --gray-bg: #F8F9FA;
    --text-color: #343A40;
  }

  /* Main elements */
  .stApp {
    background-color: var(--gray-bg);
    font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-color);
  }

  /* Headings */
  h1 { font-size: 32px; font-weight: 600; margin-bottom: 24px; }
  h2 { font-size: 24px; font-weight: 600; margin: 28px 0 16px; }
  h3 { font-size: 20px; font-weight: 600; margin: 20px 0 12px; }

  /* Card & Container */
  .container, .info-card, .metric-card {
    background-color: #fff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    transition: transform .2s, box-shadow .2s;
  }
  .container:hover, .info-card:hover, .metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
  }

  /* Buttons */
  .stButton > button {
    border-radius: 9999px;
    font-weight: 600;
    letter-spacing: -0.01em;
    padding: 8px 18px;
    color: #fff !important;
    background-color: var(--primary) !important;
    transition: background .2s, transform .2s, box-shadow .2s;
  }
  .stButton > button:hover {
    background-color: var(--primary);
    filter: brightness(0.9);
    transform: translateY(-2px);
  }
  .stButton > button:active {
    background-color: var(--primary);
    transform: scale(0.98);
  }
  /* secondary / danger variants */
  .secondary-button { background-color: var(--secondary) !important; }
  .secondary-button:hover { filter: brightness(0.9); }
  .danger-button { background-color: var(--danger) !important; }
  .danger-button:hover { filter: brightness(0.9); }

  /* Input / Select / Textarea */
  div[data-baseweb="input"],
  div[data-baseweb="select"],
  div[data-baseweb="textarea"] {
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.1);
    background-color: rgba(0,0,0,0.02);
    transition: border-color .2s, box-shadow .2s;
  }
  div[data-baseweb="input"]:focus-within,
  div[data-baseweb="select"]:focus-within,
  div[data-baseweb="textarea"]:focus-within {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(107,91,149,0.2);
  }

  /* Metric cards */
  .metric-card { text-align: center; }
  .metric-value { font-size: 28px; font-weight: bold; }
  .metric-label { font-size: 14px; color: #7f8c8d; }

  /* DataFrame header */
  .stDataFrame th {
    background-color: rgba(0,0,0,0.03);
    font-weight: 500;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.15); }
</style>
""", unsafe_allow_html=True)

# ------------------ LOAD / SAVE ------------------
def load_data(sheet_name: str = "Default") -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE, sheet_name=sheet_name)
        if "Inuse" not in df.columns:
            df["Inuse"] = "No"
        return df
    else:
        columns = ["Tube ID", "Cell Name", "Passage", "Parent Tube", "Position", "Date", 
                  "Tray", "Box", "Lot", "Mycoplasma", "Operator", "Info", "Inuse"]
        return pd.DataFrame(columns=columns)

def save_data(df: pd.DataFrame, sheet_name: str = "Default"):
    if os.path.exists(DATA_FILE):
        with pd.ExcelWriter(DATA_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        with pd.ExcelWriter(DATA_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

# ------------------ BUILD TREE ------------------
def build_tree(df: pd.DataFrame) -> list:
    nodes = {}
    parent_map = {}

    df = df.copy()
    df["Tube ID"] = df["Tube ID"].astype(str).str.strip().str.upper()
    df["Parent Tube"] = df["Parent Tube"].astype(str).str.strip().str.upper()
    df["Parent Tube"] = df["Parent Tube"].replace(["NONE", "NAN", ""], np.nan)

    for _, row in df.iterrows():
        tube_id = row["Tube ID"]
        parent_tube = row.get("Parent Tube", np.nan)
        passage = int(row["Passage"])

        # Enhanced tooltip with more detailed styling
        tooltip = f"""
        <div style='padding: 10px; font-size: 13px; line-height: 1.5; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e0e0e0;'>
            <div style='font-weight: bold; font-size: 15px; margin-bottom: 5px; color: #2c3e50; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px;'>
                {tube_id} (P{passage})
            </div>
            <div style='display: grid; grid-template-columns: auto 1fr; gap: 5px;'>
                <div style='color: #7f8c8d;'>Date:</div>
                <div>{pd.to_datetime(row.get("Date", ""), errors='coerce').strftime('%Y-%m-%d') if pd.notna(row.get("Date", "")) else ''}</div>
                
                <div style='color: #7f8c8d;'>Location:</div>
                <div>{row.get("Tray", "")} / {row.get("Box", "")} / {row.get("Position", "")}</div>
                
                <div style='color: #7f8c8d;'>Lot:</div>
                <div>{row.get("Lot", "")}</div>
                
                <div style='color: #7f8c8d;'>Mycoplasma:</div>
                <div>{row.get("Mycoplasma", "")}</div>
                
                <div style='color: #7f8c8d;'>Operator:</div>
                <div>{row.get("Operator", "")}</div>
            </div>
            <div style='margin-top: 5px; border-top: 1px solid #e0e0e0; padding-top: 5px;'>
                <div style='color: #7f8c8d;'>Info:</div>
                <div>{row.get("Info", "")}</div>
            </div>
        </div>
        """

        # 상태에 따라 색상 조정 - 더 세련된 색상
        color = "#3498db"  # Basic blue
        if str(row.get("Inuse", "")).lower() == "yes":
            color = "#e74c3c"  # Use red
        elif str(row.get("Inuse", "")).lower() == "no":
            color = "#2ecc71"  # Not use green

        nodes[tube_id] = {
            "name": tube_id,
            "value": tooltip,
            "children": [],
            "itemStyle": {"color": color, "borderColor": "#ffffff", "borderWidth": 2},
            "emphasis": {
                "itemStyle": {
                    "borderColor": "#34495e",
                    "borderWidth": 3,
                    "shadowBlur": 12,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            }
        }

        if pd.notna(parent_tube):
            parent_map[tube_id] = parent_tube

    for tube_id, parent in parent_map.items():
        if parent in nodes:
            nodes[parent]["children"].append(nodes[tube_id])

    used_as_child = set(parent_map.keys())
    all_ids = set(nodes.keys())
    root_ids = all_ids - used_as_child
    root_nodes = [nodes[tube_id] for tube_id in root_ids]

    tree = [{
        "name": "ROOT",
        "value": "Virtual Root",
        "children": root_nodes,
        "itemStyle": {"color": "#9b59b6", "borderColor": "#ffffff", "borderWidth": 2}
    }]
    return tree

# ------------------ RENDER CHART ------------------
def render_tree_chart(tree_data: list, title: str = "Cell Lineage Tree"):
    tree = (
        Tree(init_opts=opts.InitOpts(width="100%", height="700px", bg_color="#ffffff"))
        .add(
            series_name=title,
            data=tree_data,
            symbol="circle",
            symbol_size=20,
            edge_shape="polyline",
            edge_fork_position="50%",
            initial_tree_depth=-1,
            orient="TB",
            label_opts=opts.LabelOpts(
                position="top",
                vertical_align="middle",
                font_size=14,
                font_family="Arial"
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="item",
                formatter=JsCode("function(params){ return params.data.value; }"),
                border_color="#e0e0e0",
                border_width=1,
                background_color="#ffffff",
                textstyle_opts=opts.TextStyleOpts(
                    font_family="Arial",
                    color="#333333",
                )
            )
            # 문제가 되는 leaves_label_opts 부분 제거
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title=title,
                subtitle="Interactive cell lineage visualization",
                title_textstyle_opts=opts.TextStyleOpts(
                    font_size=18,
                    font_family="Arial",
                    font_weight="bold",
                    color="#34495e"
                ),
                subtitle_textstyle_opts=opts.TextStyleOpts(
                    font_size=12, 
                    color="#7f8c8d"
                )
            ),
            tooltip_opts=opts.TooltipOpts(trigger="item")
        )
    )
    st_pyecharts(tree, height="700px")

# ------------------ DASHBOARD METRICS ------------------
def display_dashboard_metrics(df):
    if len(df) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Tubes</div>
            </div>
            """.format(len(df)), unsafe_allow_html=True)
            
        with col2:
            in_use_count = len(df[df["Inuse"].str.lower() == "yes"])
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value" style="color: #e74c3c;">{}</div>
                <div class="metric-label">In Use</div>
            </div>
            """.format(in_use_count), unsafe_allow_html=True)
            
        with col3:
            available_count = len(df[df["Inuse"].str.lower() == "no"])
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value" style="color: #2ecc71;">{}</div>
                <div class="metric-label">Available</div>
            </div>
            """.format(available_count), unsafe_allow_html=True)
            
        with col4:
            unique_cell_lines = df["Cell Name"].nunique()
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value" style="color: #9b59b6;">{}</div>
                <div class="metric-label">Cell Lines</div>
            </div>
            """.format(unique_cell_lines), unsafe_allow_html=True)

# ------------------ BOX VISUALIZATION ------------------
def render_box_position_map(filtered_df, row_letters, col_numbers):
    # Create empty position map
    position_map = pd.DataFrame('', index=row_letters, columns=col_numbers)
    
    # Fill in the tubes
    for _, row in filtered_df.iterrows():
        pos = str(row['Position']).strip().upper()
        if len(pos) >= 2:
            row_letter, col_number = pos[0], pos[1:]
            if row_letter in position_map.index and col_number in position_map.columns:
                position_map.loc[row_letter, col_number] = row['Tube ID']
    
    # Create style function
    def style_cells(val):
        if val == '':
            return 'background-color: #f8f9fa'
        
        tube_info = filtered_df[filtered_df['Tube ID'] == val]
        if not tube_info.empty and str(tube_info['Inuse'].values[0]).lower() == 'yes':
            return 'background-color: rgba(231, 76, 60, 0.7); color: white; font-weight: bold; text-align: center'
        else:
            return 'background-color: rgba(46, 204, 113, 0.7); color: white; font-weight: bold; text-align: center'
    
    # Apply styling
    styled_map = position_map.style.applymap(style_cells)
    
    return styled_map

# ------------------ MAIN APP ------------------
# Sidebar for navigation and app control
with st.sidebar:
    #st.image("", width=100)
    st.title('Cell Line Manager')
    
    if os.path.exists(DATA_FILE):
        sheet_list = pd.ExcelFile(DATA_FILE).sheet_names
        selected_sheet = st.selectbox("📑 Select Cell Line Sheet", sheet_list if sheet_list else ["Default"])
    else:
        selected_sheet = "Default"
        st.info("No data file found. Starting with a new sheet.")
    
    tube_df = load_data(sheet_name=selected_sheet)
    
    st.markdown("---")
    
    # Quick stats in sidebar
    if len(tube_df) > 0:
        st.markdown("### 📊 Quick Stats")
        st.markdown(f"**Total Tubes:** {len(tube_df)}")
        st.markdown(f"**In Use:** {len(tube_df[tube_df['Inuse'].str.lower() == 'yes'])}")
        st.markdown(f"**Available:** {len(tube_df[tube_df['Inuse'].str.lower() == 'no'])}")
    
    st.markdown("---")
    st.markdown("### 📱 Contact")
    st.markdown("For support: kojkos@gmail.com")

# Main content
st.title('Cell Line Tube Manager')
st.markdown("Modern lab management system for organizing and tracking cell line samples")

# Display dashboard metrics
display_dashboard_metrics(tube_df)

tab1, tab2, tab3 = st.tabs([
    "➕ Tube Registration", 
    "📋 Tube Management", 
    "🌳 Lineage Visualization"
])

with tab1:
    st.markdown("## Add New Tube")
    
    # Form in a card-like container
    with st.container():
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        
        with st.form("tube_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                tube_id = st.text_input("Tube ID", placeholder="e.g., P2_1")
                cell_name = st.text_input("Cell Name", placeholder="e.g., A549")
                passage = st.number_input("Passage", min_value=0, max_value=100, value=0)
                parent_options = [""] + sorted(tube_df["Tube ID"].dropna().unique().tolist())
                parent_tube = st.selectbox("Parent Tube", parent_options)
            
            with col2:
                date_val = st.date_input("Date", value=date.today())
                tray = st.text_input("Tray", placeholder="e.g., Tray-2")
                box = st.text_input("Box", placeholder="e.g., Box-A1")
                position = st.text_input("Position", placeholder="e.g., A1")
            
            with col3:
                lot = st.text_input("Lot", placeholder="e.g., L202403")
                myco = st.selectbox("Mycoplasma", ["No", "Yes"])
                operator = st.text_input("Operator", placeholder="e.g., Chaeyoung")
                info = st.text_area("Info", placeholder="e.g., Thawed before experiment", height=122)

            submit_col1, submit_col2 = st.columns([3, 1])
            with submit_col2:
                submitted = st.form_submit_button("✅ Register Tube", use_container_width=True)
            
            if submitted:
                if tube_id and cell_name:
                    new_data = {
                        "Tube ID": tube_id,
                        "Cell Name": cell_name,
                        "Passage": passage,
                        "Parent Tube": parent_tube,
                        "Position": position.upper().strip(),
                        "Date": date_val,
                        "Tray": tray,
                        "Box": box,
                        "Lot": lot,
                        "Mycoplasma": myco,
                        "Operator": operator,
                        "Info": info,
                        "Inuse": "No"
                    }
                    tube_df = pd.concat([tube_df, pd.DataFrame([new_data])], ignore_index=True)
                    save_data(tube_df, sheet_name=selected_sheet)
                    st.success(f"✅ Successfully registered tube {tube_id}!")
                    st.rerun()
                else:
                    st.error("Tube ID and Cell Name are required!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Box visualization section
    st.markdown("## 📦 Storage Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### Box Occupancy Summary")
        
        if len(tube_df) > 0:
            box_summary = (
                tube_df.groupby(["Tray", "Box"])
                .size()
                .reset_index(name="Used")
            )
            box_summary["Remaining"] = 100 - box_summary["Used"]
            
            # Add visualization
            if not box_summary.empty:
                fig = px.bar(
                    box_summary, 
                    x="Box", 
                    y=["Used", "Remaining"],
                    color_discrete_map={"Used": "#3498db", "Remaining": "#ecf0f1"},
                    title="Box Capacity Usage",
                    barmode="stack",
                    height=300,
                    labels={"value": "Tubes", "variable": "Status"},
                    facet_col="Tray" if box_summary["Tray"].nunique() > 1 else None
                )
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(box_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No tubes registered yet. Add tubes to see box occupancy.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 🧭 Box Position Map")
        
        if len(tube_df) > 0:
            trays = sorted(tube_df["Tray"].dropna().unique().tolist())
            boxes = sorted(tube_df["Box"].dropna().unique().tolist())
            
            if trays and boxes:
                selected_tray = st.selectbox("Select Tray", trays, key="tray_selector")
                selected_box = st.selectbox("Select Box", boxes, key="box_selector")
                
                filtered = tube_df[(tube_df["Tray"] == selected_tray) & (tube_df["Box"] == selected_box)]
                
                row_letters = list("ABCDEFGHIJ")
                col_numbers = [str(i) for i in range(1, 11)]
                
                st.markdown(f"#### 📍 {selected_tray} / {selected_box}")
                
                styled_map = render_box_position_map(filtered, row_letters, col_numbers)
                st.dataframe(styled_map, use_container_width=True)
                
                # Legend
                st.markdown(
                    """
                    <div style='display: flex; justify-content: center; gap: 20px; margin-top: 10px;'>
                        <div>
                            <span style='display:inline-block; width:20px; height:20px; background-color:rgba(231, 76, 60, 0.7); 
                                  border-radius:4px; margin-right:8px; vertical-align:middle;'></span>
                            <span style='vertical-align:middle;'>In Use</span>
                        </div>
                        <div>
                            <span style='display:inline-block; width:20px; height:20px; background-color:rgba(46, 204, 113, 0.7); 
                                  border-radius:4px; margin-right:8px; vertical-align:middle;'></span>
                            <span style='vertical-align:middle;'>Available</span>
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                st.info("No trays or boxes found in the data.")
        else:
            st.info("No tubes registered yet. Add tubes to view the position map.")
        
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown("## 📋 Tube Management")
    
    # Search and filter section
    with st.container():
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        
        search_col1, search_col2, search_col3 = st.columns(3)
        
        with search_col1:
            search_term = st.text_input("🔍 Search by Tube ID or Cell Name", placeholder="Enter search term...")
        
        with search_col2:
            filter_status = st.selectbox("Filter by Status", ["All", "In Use", "Available"])
        
        with search_col3:
            if len(tube_df) > 0:
                sort_by = st.selectbox("Sort by", ["Tube ID", "Date", "Cell Name", "Passage"])
            else:
                sort_by = "Tube ID"
        
        # Apply filters
        filtered_df = tube_df.copy()
        
        if search_term:
            filtered_df = filtered_df[
                filtered_df["Tube ID"].str.contains(search_term, case=False) | 
                filtered_df["Cell Name"].str.contains(search_term, case=False)
            ]
        
        if filter_status == "In Use":
            filtered_df = filtered_df[filtered_df["Inuse"].str.lower() == "yes"]
        elif filter_status == "Available":
            filtered_df = filtered_df[filtered_df["Inuse"].str.lower() == "no"]
        
        # Apply sorting
        if sort_by == "Date":
            filtered_df = filtered_df.sort_values(by="Date", ascending=False)
        else:
            filtered_df = filtered_df.sort_values(by=sort_by)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display tubes with enhanced styling
    if len(filtered_df) > 0:
        st.markdown(f"### Showing {len(filtered_df)} tubes")
        
        # Function to color rows based on status
        def highlight_rows(row):
            if str(row["Inuse"]).lower() == "yes":
                return ['background-color: rgba(231, 76, 60, 0.1)'] * len(row)
            else:
                return ['background-color: rgba(46, 204, 113, 0.1)'] * len(row)
        
        # Apply styling and display
        styled_df = filtered_df.style.apply(highlight_rows, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Tube status management
        st.markdown("### Update Tube Status")
        
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            selected_tube = st.selectbox("Select Tube to Update", filtered_df["Tube ID"])
            current_status = filtered_df.loc[filtered_df["Tube ID"] == selected_tube, "Inuse"].values[0]
            
            current_status_display = "In Use" if str(current_status).lower() == "yes" else "Available"
            status_color = "status-in-use" if str(current_status).lower() == "yes" else "status-available"
            
            st.markdown(
                f"""
                <div class="status-box {status_color}">
                    Current Status: {current_status_display}
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        with status_col2:
            status_button_col1, status_button_col2 = st.columns(2)
            
            with status_button_col1:
                if st.button("✅ Mark as In Use", key="mark_in_use", use_container_width=True):
                    tube_df.loc[tube_df["Tube ID"] == selected_tube, "Inuse"] = "Yes"
                    save_data(tube_df, sheet_name=selected_sheet)
                    st.success(f"Status updated: {selected_tube} is now In Use")
                    st.rerun()
            
            with status_button_col2:
                if st.button("🔄 Mark as Available", key="mark_available", use_container_width=True):
                    tube_df.loc[tube_df["Tube ID"] == selected_tube, "Inuse"] = "No"
                    save_data(tube_df, sheet_name=selected_sheet)
                    st.success(f"Status updated: {selected_tube} is now Available")
                    st.rerun()
    else:
        st.info("No tubes found matching your filters.")

with tab3:
    st.markdown("## 🌳 Cell Lineage Visualization")
    
    if len(tube_df) == 0:
        st.info("No tube data available. Add tubes to visualize cell lineage.")
    else:
        # Filtering options for visualization
        vis_col1, vis_col2 = st.columns(2)
        
        with vis_col1:
            cell_names = ["All"] + sorted(tube_df["Cell Name"].unique().tolist())
            selected_cell = st.selectbox("Filter by Cell Line", cell_names)
        
        with vis_col2:
            vis_status = st.selectbox("Show by Status", ["All", "In Use Only", "Available Only"])
        
        # Apply filters for visualization
        vis_df = tube_df.copy()
        
        if selected_cell != "All":
            vis_df = vis_df[vis_df["Cell Name"] == selected_cell]
        
        if vis_status == "In Use Only":
            vis_df = vis_df[vis_df["Inuse"].str.lower() == "yes"]
        elif vis_status == "Available Only":
            vis_df = vis_df[vis_df["Inuse"].str.lower() == "no"]
        
        tree_title = f"{selected_sheet} Lineage Tree"
        if selected_cell != "All":
            tree_title += f" - {selected_cell}"
            
        # Build and render the tree
        tree_data = build_tree(vis_df)
        render_tree_chart(tree_data, title=tree_title)
