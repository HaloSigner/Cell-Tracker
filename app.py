# Cell Line Manager (전체 기능 포함 + 사용자 친화적 UI)
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
import networkx as nx
from pyvis.network import Network


from pyecharts import options as opts
from pyecharts.charts import Tree
from pyecharts.commons.utils import JsCode
from streamlit_echarts import st_pyecharts
import pandas as pd
import os

def build_tree(df_lineage, log_df, name_col):
    nodes = {}
    parent_map = {}

    for _, row in df_lineage.iterrows():
        passage = int(row["Passage"])
        n_tubes = int(row.get("N. of tube", 1))
        parent_label = str(row.get("Parent Tube", "")).strip()
        status = str(row.get("Status", "")).strip().lower()

        for i in range(1, n_tubes + 1):
            label = f"P{passage}_{i}"

            # 로그 정보 확인
            usage_info = log_df[
                (log_df["Passage"] == passage) & 
                (log_df["Used Tube No"] == i)
            ]
            used = not usage_info.empty

            # tooltip
            tooltip = f"""
            <b>Tube:</b> {label}<br>
            Passage: {passage}<br>
            Lot: {row.get("Lot", "")}<br>
            Date: {pd.to_datetime(row.get("Date", ""), errors='coerce').strftime('%Y-%m-%d') if pd.notna(row.get("Date", "")) else ''}<br>
            Remain vials: {row.get("Remain vials", "")}<br>
            Name: {row.get("Name", "")}<br>
            Source: {row.get("Source", "")}<br>
            Status: {status.title()}
            """

            if used:
                user = usage_info["User"].values[0]
                exp = usage_info["Experiment"].values[0]
                date = pd.to_datetime(usage_info["Date"]).strftime("%Y-%m-%d")
                tooltip += f"<br><b>Used by:</b> {user}<br><b>Exp:</b> {exp}<br><b>Date:</b> {date}"

            # ✅ 상태별 색상 지정
            if used:
                color = "#FF6B6B"  # 사용된 튜브 → 빨강
            elif status == "inuse":
                color = "#FFA500"  # Inuse 상태 → 주황
            elif status == "depleted":
                color = "#B0B0B0"  # 고갈 → 회색
            else:
                color = "#97C2FC"  # 기본 (보관 중) → 파랑

            nodes[label] = {
                "name": label,
                "value": tooltip,
                "children": [],
                "itemStyle": {"color": color}
            }

            if parent_label:
                parent_map[label] = parent_label

    # 부모-자식 연결
    tree = []
    for label, node in nodes.items():
        parent_label = parent_map.get(label, "")
        if parent_label and parent_label in nodes:
            nodes[parent_label]["children"].append(node)
        else:
            tree.append(node)

    return tree


st.set_page_config(page_title="🧬 Cell Line Manager", layout="wide", initial_sidebar_state="expanded")
st.title("🧬 Cell Line 관리 시스템")

cell_file = "new_cell_entries.xlsx"
log_file = "usage_log.csv"
new_cell_file = "new_cell_entries.xlsx"

@st.cache_data
def load_all_sheets(path):
    xls = pd.ExcelFile(path)
    return {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

cell_data = load_all_sheets(cell_file)
selected_sheet = st.sidebar.selectbox("📁 시트 선택", list(cell_data.keys()))
df = cell_data[selected_sheet].copy()
df.columns = df.columns.astype(str)
df = df.dropna(subset=[df.columns[0]])
df.index = range(1, len(df)+1)
name_col = next((col for col in df.columns if "cell name" in col.lower()), df.columns[0])

menu = st.sidebar.radio("📋 실행할 기능 선택", [
    "📊 Cell Line 개수 분석", 
    "🧬 상태 우수 Cell 추천 및 실험 등록",
    "📝 사용 기록 관리",
    "📈 Cell 사용량 시각화",
    "➕ 새로운 Cell 정보 저장",
    "🌳 Cell 사용 가계도 보기"
])

# ✅ 상태 우수 Cell 추천 및 실험 등록
if menu == "📊 Cell Line 개수 분석":
    st.subheader("📊 전체 Cell Line 개수 분석")

    # 모든 시트에서 데이터 합치기
    all_cell_df = pd.concat(cell_data.values(), ignore_index=True)
    cell_name_col = next((col for col in all_cell_df.columns if "cell name" in col.lower()), all_cell_df.columns[0])

    # ✅ Cell Line 개수 바플롯
    count_df = all_cell_df[cell_name_col].value_counts().reset_index()
    count_df.columns = ["Cell Line", "Count"]
    fig_count = px.bar(count_df, x="Cell Line", y="Count", text="Count", title="전체 Cell Line 개수")
    st.plotly_chart(fig_count, use_container_width=True)

    # ✅ Source 별 Cell Line 개수도 함께 시각화
    if "Source" in all_cell_df.columns:
        grouped_df = all_cell_df.groupby([cell_name_col, "Source"]).size().reset_index(name="Count")
        fig_grouped = px.bar(grouped_df, x=cell_name_col, y="Count", color="Source", barmode="group",
                             title="Cell Line별 Source 분포", text="Count")
        st.plotly_chart(fig_grouped, use_container_width=True)



    
elif menu == "🧬 상태 우수 Cell 추천 및 실험 등록":
    st.subheader("🧬 상태 우수 Cell 추천 및 실험 등록")

    # ✅ 사용 로그 기본 확인
    if os.path.exists(log_file):
        log_df_init = pd.read_csv(log_file)
        if "Used Tube No" not in log_df_init.columns:
            log_df_init["Used Tube No"] = pd.NA
            log_df_init.to_csv(log_file, index=False)

    # ✅ Cell 이름 선택
    cell_name_selected = st.selectbox("Cell 이름 선택", df[name_col].dropna().unique())
    df_filtered = df[df[name_col] == cell_name_selected].copy()
    df_filtered["Passage"] = pd.to_numeric(df_filtered.get("Passage", None), errors="coerce")
    df_filtered["Remain vials"] = pd.to_numeric(df_filtered.get("Remain vials", None), errors="coerce")
    df_filtered["Score"] = -df_filtered["Passage"].fillna(999) + df_filtered["Remain vials"].fillna(0)

    # ✅ 상위 추천 Cell 5개
    top_cells = df_filtered.sort_values("Score", ascending=False).head(5)
    display_cols = [name_col, "Lot", "Passage", "Remain vials", "Score"]
    if "Source" in top_cells.columns:
        display_cols.insert(1, "Source")
    st.dataframe(top_cells[display_cols], use_container_width=True)

    # ✅ 사용자 선택
    selected_row_idx = st.selectbox("추천 Cell 선택", options=top_cells.index.tolist())
    selected_row = top_cells.loc[selected_row_idx]

    st.markdown("#### 선택된 Cell 정보")
    cols_to_show = [name_col, "Lot", "Passage", "Remain vials", "Score"]
    if "Source" in selected_row.index:
        cols_to_show.append("Source")
    st.write(selected_row[cols_to_show])

    # ✅ 사용 가능한 튜브 필터링 (P2_1 형식)
    passage = int(selected_row.get("Passage", 0))
    n_total = int(selected_row.get("N. of tube", 1))
    all_tubes = [f"P{passage}_{i}" for i in range(1, n_total + 1)]

    log_df = pd.read_csv(log_file) if os.path.exists(log_file) else pd.DataFrame()
    used_tubes = log_df[
        (log_df["Material"] == selected_row[name_col]) &
        (log_df["Lot"] == selected_row.get("Lot", "N/A")) &
        (log_df["Passage"] == passage)
    ]["Used Tube No"].dropna().astype(str).apply(lambda x: f"P{passage}_{int(x)}").tolist()

    available_tubes = sorted(list(set(all_tubes) - set(used_tubes)))

    if not available_tubes:
        st.warning("❗ 사용 가능한 튜브가 없습니다.")
        st.stop()

    tube_id = st.selectbox("사용할 튜브 선택 (예: P2_1)", available_tubes)
    tube_num = int(tube_id.split("_")[1])  # int형 튜브 번호

    # ✅ 실험 정보 입력
    experiment_name = st.text_input("실험 이름")
    experiment_user = st.text_input("담당자")

    if st.button("📌 실험 등록"):
        entry = {
            "Timestamp": datetime.now(),
            "User": experiment_user,
            "Date": datetime.today().date(),
            "Sheet": selected_sheet,
            "Material": selected_row[name_col],
            "Lot": selected_row.get("Lot", "N/A"),
            "Passage": passage,
            "Used Tube No": tube_num,
            "Used Quantity": 1,
            "Experiment": experiment_name,
            "Type": "Cell"
        }

        # ✅ 로그 추가
        log_df = pd.concat([log_df, pd.DataFrame([entry])], ignore_index=True)
        log_df.to_csv(log_file, index=False)

        # ✅ Remain vials 감소 & Status 반영
        try:
            df_sheet = pd.read_excel(new_cell_file, sheet_name=selected_sheet)
            match_idx = df_sheet[
                (df_sheet["Cell name"] == selected_row[name_col]) &
                (df_sheet["Lot"] == selected_row.get("Lot", "N/A")) &
                (df_sheet["Passage"] == passage)
            ].index

            if not match_idx.empty:
                idx = match_idx[0]
                current_remain = df_sheet.loc[idx, "Remain vials"]
                if pd.notna(current_remain):
                    df_sheet.loc[idx, "Remain vials"] = max(0, int(current_remain) - 1)

                new_remain = df_sheet.loc[idx, "Remain vials"]
                df_sheet.loc[idx, "Status"] = "Inuse" if new_remain > 0 else "Depleted"

                with pd.ExcelWriter(new_cell_file, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
                    df_sheet.to_excel(writer, sheet_name=selected_sheet, index=False)

        except Exception as e:
            st.error(f"Remain vials 감소 또는 상태 반영 오류: {e}")

        st.success("✅ 실험 등록 완료! 사용 튜브 기록 및 수량 반영 성공.")
        st.cache_data.clear()
        st.rerun()

# ✅ 사용 기록 관리 + Inuse 해제
elif menu == "📝 사용 기록 관리":
    st.subheader("📂 Cell 사용 기록 관리 및 Inuse 해제")
    if os.path.exists(log_file):
        log_df = pd.read_csv(log_file)
        log_df = log_df[log_df["Sheet"].isin(cell_data.keys())]
        log_df["Date"] = pd.to_datetime(log_df["Date"], errors="coerce")

        # ✅ 전체 로그 표시
        st.markdown("### 📋 전체 사용 기록")
        display_df = log_df.copy()
        display_df.index = range(1, len(display_df)+1)
        st.dataframe(display_df, use_container_width=True)

        st.markdown("### 🛠️ 항목 수정 및 삭제")

        for i, row in log_df.iterrows():
            with st.expander(f"🔎 {row['Material']} | {row['Date'].date()} | {row['User']}"):
                user = st.text_input("사용자", row["User"], key=f"user_{i}")
                date = st.date_input("날짜", pd.to_datetime(row["Date"]), key=f"date_{i}")
                qty = st.number_input("사용량", float(row["Used Quantity"]), key=f"qty_{i}")
                tube_no = st.number_input("사용 튜브 번호", int(row.get("Used Tube No", 1)), key=f"tube_{i}", step=1)

                # ✅ 수정 버튼
                if st.button("💾 수정", key=f"save_{i}"):
                    log_df.loc[i, ["User", "Date", "Used Quantity", "Used Tube No"]] = [user, date, qty, tube_no]
                    log_df.to_csv(log_file, index=False)
                    st.success("✅ 수정 완료")
                    st.rerun()

                # 🗑️ 삭제 버튼
                if st.button("🗑️ 삭제", key=f"delete_{i}"):
                    try:
                        sheet_name = row["Sheet"]
                        df_all_sheets = load_all_sheets(new_cell_file)
                        df_sheet = df_all_sheets.get(sheet_name, pd.DataFrame())

                        match = df_sheet[
                            (df_sheet["Cell name"] == row["Material"]) &
                            (df_sheet["Lot"] == row["Lot"]) &
                            (df_sheet["Passage"] == row["Passage"])
                        ]
                        if not match.empty:
                            idx = match.index[0]

                            # ✅ Remain vials 복구 + 상태 변경
                            current_remain = df_sheet.loc[idx, "Remain vials"]
                            if pd.notna(current_remain):
                                df_sheet.loc[idx, "Remain vials"] = int(current_remain) + 1

                            df_sheet.loc[idx, "Status"] = "Inuse"  # Depleted → Inuse 복구 가능성

                            # ✅ 모든 시트를 다시 저장
                            with pd.ExcelWriter(new_cell_file, mode="w", engine="openpyxl") as writer:
                                for sheet, df_sheet_data in df_all_sheets.items():
                                    if sheet == sheet_name:
                                        df_sheet_data = df_sheet
                                    df_sheet_data.to_excel(writer, sheet_name=sheet, index=False)

                            st.info(f"✅ Inuse 상태 복구 및 Remain vials 증가 완료")
                    except Exception as e:
                        st.error(f"Inuse 상태 해제 오류: {e}")

                    # ✅ 로그 삭제
                    log_df = log_df.drop(i).reset_index(drop=True)
                    log_df.to_csv(log_file, index=False)
                    st.success("🗑️ 사용 기록 삭제 완료")
                    st.cache_data.clear()
                    st.rerun()


elif menu == "📈 Cell Line 시각화":
    st.subheader("📈 Cell 사용 이력 시각화")
    if os.path.exists(log_file):
        log_df = pd.read_csv(log_file)
        log_df = log_df[log_df["Sheet"].isin(cell_data.keys())]
        log_df["Date"] = pd.to_datetime(log_df["Date"], errors="coerce")

        # ✅ Cell별 총 사용 튜브 수 집계
        chart_df = log_df.groupby("Material")["Used Tube No"].count().reset_index()
        chart_df.columns = ["Material", "Tube Uses"]

        st.markdown("### 🔢 Cell별 사용된 튜브 개수")
        st.bar_chart(chart_df.set_index("Material"))

        # ✅ 사용 추이 (타임라인)
        st.markdown("### 📊 타임라인별 튜브 사용 추이")
        timeline_df = log_df.groupby(["Date", "Material"])["Used Tube No"].count().reset_index()
        timeline_df.columns = ["Date", "Material", "Used Tubes"]
        fig = px.line(timeline_df, x="Date", y="Used Tubes", color="Material", markers=True)
        st.plotly_chart(fig, use_container_width=True)

        # ✅ 상세 이벤트 로그 Plotly로 시각화
        st.markdown("### 📅 사용 이력 상세 보기")
        if "Used Tube No" in log_df.columns:
            detail_fig = px.scatter(
                log_df,
                x="Date",
                y="Material",
                color="User",
                symbol="Experiment",
                size_max=10,
                hover_data=["Used Tube No", "Experiment", "User"]
            )
            detail_fig.update_traces(marker=dict(size=12, opacity=0.7))
            st.plotly_chart(detail_fig, use_container_width=True)



elif menu == "➕ 새로운 Cell 정보 저장":
    st.subheader("➕ Cell 정보 직접 입력 및 저장")
    with st.form("cell_input_form"):
        col1, col2 = st.columns(2)
        with col1:
            tray = st.text_input("Tray")
            box = st.text_input("Box")
            lot = st.text_input("Lot")
            cell_name = st.text_input("Cell name")
            tube = st.number_input("N. of tube", min_value=0, step=1)
            freeze_date = st.date_input("Freeze Date")
            passage = st.number_input("Passage", min_value=0, step=1)
            remain_vials = st.number_input("Remain vials", min_value=0, step=1)
            name = st.text_input("Name")
            source = st.text_input("Source")
        with col2:
            info = st.text_input("Info (Myco)")
            freeze_cond = st.text_input("Freezing condition")
            thaw_info = st.text_input("Thaw (date/name)")
            add_info = st.text_input("Additional info")
            code = st.text_input("Oncotree Code")
            subtype = st.text_input("Oncotree Subtype")
            primary = st.text_input("Primary Disease")
            lineage = st.text_input("Lineage")
            species = st.text_input("Species")
            parent_tube = st.text_input("Parent Tube (예: P1_1)", value="")  

        submitted = st.form_submit_button("💾 새 Cell 정보 저장")
        if submitted:
            freeze_score = (pd.to_datetime(freeze_date) - (datetime.today() - timedelta(days=365))).days
            score = -passage + remain_vials + freeze_score

            new_entry = {
                "Tray": tray, "Box": box, "Lot": lot, "Cell name": cell_name,
                "N. of tube": tube, "Date": freeze_date, "Passage": passage,
                "Remain vials": remain_vials, "Score": score,
                "Name": name, "Source": source, "Info (Myco)": info,
                "freezing condition": freeze_cond, "Thaw (date/name)": thaw_info,
                "additional info": add_info, "OncotreeCode": code,
                "OncotreeSubtype": subtype, "OncotreePrimaryDisease": primary,
                "OncotreeLineage": lineage, "Species": species,
                "Status": "",
                "Parent Tube": parent_tube  
            }

            new_df = pd.DataFrame([new_entry])
            sheet_name = cell_name.strip() or "Unknown"
            if os.path.exists(new_cell_file):
                with pd.ExcelWriter(new_cell_file, mode="a", if_sheet_exists="overlay", engine="openpyxl") as writer:
                    try:
                        existing_df = pd.read_excel(new_cell_file, sheet_name=sheet_name)
                        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    except ValueError:
                        combined_df = new_df
                    combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                with pd.ExcelWriter(new_cell_file, engine="openpyxl") as writer:
                    new_df.to_excel(writer, sheet_name=sheet_name, index=False)

            st.success(f"✅ '{sheet_name}' 시트에 새로운 Cell 정보가 저장되었습니다.")
            st.cache_data.clear()
            st.rerun()


elif menu == "🌳 Cell 사용 가계도 보기":
    st.subheader("🌳 Tree 기반 Cell 사용 가계도")
    if os.path.exists(new_cell_file):
        lineage_data = load_all_sheets(new_cell_file)
        all_df = pd.concat(lineage_data.values(), ignore_index=True)
        all_df["Date"] = pd.to_datetime(all_df.get("Date", pd.NaT), errors="coerce")

        cell_name_col = next((col for col in all_df.columns if "cell name" in col.lower()), all_df.columns[0])
        all_df["LineageGroup"] = all_df[cell_name_col].astype(str) + " | " + all_df["Source"].astype(str)
        material_list = all_df["LineageGroup"].dropna().unique().tolist()

        selected_group = st.selectbox("🔬 Cell 이름 + Source 선택", material_list)
        selected_cell_name, selected_source = selected_group.split(" | ")

        df_lineage = all_df[
            (all_df[cell_name_col] == selected_cell_name) & (all_df["Source"] == selected_source)
        ].sort_values("Date").copy()
        df_lineage["Passage"] = pd.to_numeric(df_lineage.get("Passage", 0), errors="coerce").fillna(0).astype(int)

        # 로그 불러오기
        if os.path.exists(log_file):
            log_df = pd.read_csv(log_file)
            log_df = log_df[
                (log_df["Material"] == selected_cell_name) &
                (log_df["Sheet"] == selected_source)
            ]
        else:
            log_df = pd.DataFrame(columns=["Passage", "Used Tube No", "User", "Experiment", "Date"])

        # 트리 데이터 생성
        tree_data = build_tree(df_lineage, log_df, cell_name_col)

        tree_chart = (
            Tree()
            .add(
                series_name="Lineage",
                data=tree_data,
                initial_tree_depth=2,
                orient="LR",
                collapse_interval=2,
                symbol="circle",
                label_opts=opts.LabelOpts(position="right", font_size=10),
            )
            .set_series_opts(
                tooltip=opts.TooltipOpts(
                    formatter=JsCode("function(params){ return params.data.value; }")
                )
                
            )
            .set_global_opts(title_opts=opts.TitleOpts(title="Cell Lineage Tree"))
        )

        # HTML 기반 출력
        st_pyecharts(tree_chart)

        st.markdown("### 📋 전체 Cell 정보")
        st.dataframe(df_lineage, use_container_width=True)
    else:
        st.warning("❗ new_cell_entries.xlsx 파일이 존재하지 않습니다.")

