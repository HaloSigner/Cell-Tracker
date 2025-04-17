import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import date
from pyecharts import options as opts
from pyecharts.charts import Tree
from pyecharts.commons.utils import JsCode
from streamlit_echarts import st_pyecharts

# ------------------ CONFIG ------------------
DATA_FILE = 'tude_data.xlsx'
st.set_page_config(page_title='🧬 Cell Line Tube Manager', layout='wide')

# ------------------ LOAD / SAVE ------------------
def load_data(sheet_name: str = "Default") -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE, sheet_name=sheet_name)
        if "Inuse" not in df.columns:
            df["Inuse"] = "No"
        return df
    else:
        columns = ["Tube ID", "Cell Name", "Passage", "Parent Tube", "Position", "Date", "Tray", "Box", "Lot", "Mycoplasma", "Operator", "Info", "Inuse"]
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

        # Tooltip as HTML
        tooltip = f"""
        <div style='padding: 5px; font-size: 13px; line-height: 1.4'>
            <b>Tube:</b> {tube_id}<br>
            <b>Passage:</b> {passage}<br>
            <b>Date:</b> {pd.to_datetime(row.get("Date", ""), errors='coerce').strftime('%Y-%m-%d') if pd.notna(row.get("Date", "")) else ''}<br>
            <b>Tray:</b> {row.get("Tray", "")}<br>
            <b>Box:</b> {row.get("Box", "")}<br>
            <b>Lot:</b> {row.get("Lot", "")}<br>
            <b>Mycoplasma:</b> {row.get("Mycoplasma", "")}<br>
            <b>Operator:</b> {row.get("Operator", "")}<br>
            <b>Info:</b> {row.get("Info", "")}
        </div>
        """

        # 상태에 따라 색상 조정
        color = "#97C2FC"  # Basic
        if str(row.get("Inuse", "")).lower() == "yes":
            color = "#FF6B6B"  # Use
        elif str(row.get("Inuse", "")).lower() == "no":
            color = "#6BCB77"  # Not use

        nodes[tube_id] = {
            "name": tube_id,
            "value": tooltip,
            "children": [],
            "itemStyle": {"color": color},
            "emphasis": {
                "itemStyle": {
                    "borderColor": "#000000",
                    "borderWidth": 2,
                    "shadowBlur": 10,
                    "shadowColor": "rgba(0, 0, 0, 0.3)"
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
        "itemStyle": {"color": "#4CAF50"}
    }]
    return tree

# ------------------ RENDER CHART ------------------
def render_tree_chart(tree_data: list, title: str = "Cell Lineage Tree"):
    tree = (
        Tree(init_opts=opts.InitOpts(width="1000px", height="650px"))
        .add(
            series_name=title,
            data=tree_data,
            symbol="circle",
            symbol_size=18,
            edge_shape="polyline",
            edge_fork_position="50%",
            initial_tree_depth=-1,
            orient="TB",
            label_opts=opts.LabelOpts(
                position="top",
                vertical_align="middle"
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="item",
                formatter=JsCode("function(params){ return params.data.value; }")
            )
        )
        .set_global_opts(title_opts=opts.TitleOpts(title=title))
    )
    st_pyecharts(tree)

# ------------------ MAIN APP ------------------
st.title('🧬 Cell Line Tube Manager')

sheet_list = pd.ExcelFile(DATA_FILE).sheet_names if os.path.exists(DATA_FILE) else []
selected_sheet = st.selectbox("📑 Select Cell Line Sheet", sheet_list if sheet_list else ["Default"])
tube_df = load_data(sheet_name=selected_sheet)

tab1, tab2, tab3 = st.tabs(["➕ Tube Registration", "📋 Tube List", "🌳 Passage Tree"])

with tab1:
    with st.form("tube_form"):
        col1, col2 = st.columns(2)
        with col1:
            tube_id = st.text_input("Tube ID", placeholder="예: P2_1")
            cell_name = st.text_input("Cell Name", placeholder="예: A549")
            passage = st.number_input("Passage", min_value=0, max_value=100, value=0)
            date_val = st.date_input("Date", value=date.today())
            parent_options = [""] + sorted(tube_df["Tube ID"].dropna().unique().tolist())
            parent_tube = st.selectbox("Parent Tube", parent_options)
        with col2:
            tray = st.text_input("Tray", placeholder="예: Tray-2")
            box = st.text_input("Box", placeholder="예: Box-A1")
            lot = st.text_input("Lot", placeholder="예: L202403")
            myco = st.selectbox("Mycoplasma", ["Yes", "No"])
            operator = st.text_input("Operator", placeholder="예: Chaeyoung")
            position = st.text_input("Position (e.g., A1)", placeholder="예: A1")

        info = st.text_area("Info", placeholder="예: 실험 직전 해동됨")

        submitted = st.form_submit_button("등록하기")
        if submitted:
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
            st.success(f"✅ {tube_id} 등록 완료!")
            st.rerun()


        with st.expander("📦 Box Occupancy Overview"):
            if len(tube_df) > 0:
                box_summary = (
                    tube_df.groupby(["Tray", "Box"])
                    .size()
                    .reset_index(name="Used")
                )
                box_summary["Remaining"] = 100 - box_summary["Used"]  
                st.dataframe(box_summary, use_container_width=True)
            else:
                st.info("등록된 튜브가 없어 박스 정보를 표시할 수 없습니다.")

        with st.expander("🧭 Box Position Map"):
            if len(tube_df) > 0:
                trays = sorted(tube_df["Tray"].dropna().unique().tolist())
                boxes = sorted(tube_df["Box"].dropna().unique().tolist())

                selected_tray = st.selectbox("Tray 선택", trays)
                selected_box = st.selectbox("Box 선택", boxes)

                filtered = tube_df[(tube_df["Tray"] == selected_tray) & (tube_df["Box"] == selected_box)]
                position_map = pd.DataFrame('', index=list("ABCDEFGHIJ"), columns=[str(i) for i in range(1, 11)])

                style_map = pd.DataFrame('', index=position_map.index, columns=position_map.columns)

                for _, row in filtered.iterrows():
                    pos = str(row['Position']).strip().upper()
                    if len(pos) >= 2:
                        row_letter, col_number = pos[0], pos[1:]
                        if row_letter in position_map.index and col_number in position_map.columns:
                            position_map.loc[row_letter, col_number] = row['Tube ID']
                            inuse = str(row.get("Inuse", "")).lower()
                            if inuse == "yes":
                                style_map.loc[row_letter, col_number] = "background-color: #FF9999; font-weight: bold;"  # 빨강
                            else:
                                style_map.loc[row_letter, col_number] = "background-color: #CCFFCC; font-weight: bold;"  # 연두
                
                st.markdown(f"### 📍 {selected_tray} / {selected_box} - Tube Position Map")
                st.dataframe(position_map.style.apply(lambda x: style_map.loc[x.name], axis=1), use_container_width=True)

                st.markdown(
                    """
                    <div style='margin-top: 10px;'>
                        <span style='display:inline-block;width:20px;height:20px;background-color:#FF9999;border:1px solid #999;margin-right:8px;'></span>In Use (Yes)
                        <span style='display:inline-block;width:20px;height:20px;background-color:#CCFFCC;border:1px solid #999;margin-left:20px;margin-right:8px;'></span>Not In Use (No)
                    </div>
                    """, unsafe_allow_html=True
                )
                
            else:
                st.info("등록된 튜브가 없어 박스 정보를 표시할 수 없습니다.")


            


with tab2:
    st.subheader('📋 Registered Tubes')
    st.dataframe(tube_df, use_container_width=True)

    # 선택한 튜브
    selected_tube = st.selectbox("📌 Select Tube to Modify Inuse Status", tube_df["Tube ID"])

    # 현재 상태 확인
    current_status = tube_df.loc[tube_df["Tube ID"] == selected_tube, "Inuse"].values[0]

    # 상태 토글 버튼
    col_inuse, col_not_inuse = st.columns(2)

    with col_inuse:
        if st.button("✅ Mark as Inuse"):
            tube_df.loc[tube_df["Tube ID"] == selected_tube, "Inuse"] = "Yes"
            save_data(tube_df, sheet_name=selected_sheet)
            st.success(f"🔄 {selected_tube} → Inuse 상태로 설정됨")
            st.rerun()

    with col_not_inuse:
        if st.button("🚫 Mark as Not Inuse"):
            tube_df.loc[tube_df["Tube ID"] == selected_tube, "Inuse"] = "No"
            save_data(tube_df, sheet_name=selected_sheet)
            st.info(f"↩️ {selected_tube} → Inuse 상태 해제됨")
            st.rerun()

with tab3:
    st.subheader("🌳 Cell Line Passage Tree")
    if len(tube_df) == 0:
        st.info("튜브 데이터가 없습니다.")
    else:
        tree_data = build_tree(tube_df)
        render_tree_chart(tree_data, title=f"{selected_sheet} Lineage Tree")
