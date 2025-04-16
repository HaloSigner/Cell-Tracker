import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="🧬 Cell Line Manager", layout="wide", initial_sidebar_state='expanded')
st.title("🧬 Cell Line 관리 시스템")

cell_file = "Update_Cell banking_240703.xlsx"
log_file = "usage_log.csv"

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
    "🧬 상태 우수 Cell 추천 및 실험 등록",
    "📝 사용 기록 관리",
    "📈 Cell 사용량 시각화",
    "➕ 새로운 Cell 정보 저장"
])

# 🧬 상태 우수 Cell 추천 및 등록
if menu == "🧬 상태 우수 Cell 추천 및 실험 등록":
    st.subheader("🧬 상태 우수 Cell 추천 및 실험 등록")
    cell_name_selected = st.selectbox("Cell 이름 선택", df[name_col].dropna().unique())
    df_filtered = df[df[name_col] == cell_name_selected].copy()

    df_filtered["Freeze Date"] = pd.to_datetime(df_filtered.get("Freeze Date", pd.NaT), errors="coerce")
    df_filtered["Passage"] = pd.to_numeric(df_filtered.get("Passage", None), errors="coerce")
    df_filtered["Remain vials"] = pd.to_numeric(df_filtered.get("Remain vials", None), errors="coerce")

    cutoff_date = datetime.today() - timedelta(days=365)

    st.markdown("""
    🧮 **스코어 계산 공식**  
    - `-Passage`  
    - `+Remain vials`  
    - `+Freeze Date`
    """)

    df_filtered["Score"] = (
        -df_filtered["Passage"].fillna(999) +
        df_filtered["Remain vials"].fillna(0) +
        df_filtered["Freeze Date"].apply(lambda x: (x - cutoff_date).days if pd.notna(x) else -999)
    )

    top_cells = df_filtered.sort_values("Score", ascending=False).head(5)
    st.dataframe(top_cells[[name_col, "Lot", "Passage", "Freeze Date", "Remain vials", "Score"]], use_container_width=True)

    selected_row_idx = st.selectbox("추천 Cell 선택", options=top_cells.index.tolist())
    selected_row = top_cells.loc[selected_row_idx]

    st.markdown("#### 선택된 Cell 정보")
    st.write(selected_row[[name_col, "Lot", "Passage", "Freeze Date", "Remain vials", "Score"]])

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
            "Used Quantity": 0,
            "Experiment": experiment_name,
            "Type": "Cell"
        }
        log_df = pd.read_csv(log_file) if os.path.exists(log_file) else pd.DataFrame()
        log_df = pd.concat([log_df, pd.DataFrame([entry])], ignore_index=True)
        log_df.to_csv(log_file, index=False)
        st.success("✅ 실험 등록 완료!")

# 📝 사용 기록 관리
elif menu == "📝 사용 기록 관리":
    st.subheader("📂 Cell 사용 기록 관리")
    if os.path.exists(log_file):
        log_df = pd.read_csv(log_file)
        cell_log_df = log_df[log_df["Sheet"].isin(cell_data.keys())]
        for name, group in cell_log_df.groupby("Material"):
            with st.expander(f"{name} ({len(group)}건)"):
                editable = group.reset_index(drop=True)
                idx = st.selectbox("수정할 항목 선택", editable.index.tolist(), key=name)
                user = st.text_input("사용자", editable.loc[idx, "User"], key=f"{name}_user")
                raw_date = pd.to_datetime(editable.loc[idx, "Date"], errors="coerce")
                edit_date = raw_date if not pd.isna(raw_date) else datetime.today()
                date = st.date_input("날짜", edit_date, key=f"{name}_date")
                qty = st.number_input("사용량", float(editable.loc[idx, "Used Quantity"]), key=f"{name}_qty")
                if st.button("🔄 저장", key=f"{name}_edit"):
                    log_df.loc[group.index[idx], ["User", "Date", "Used Quantity"]] = [user, date, qty]
                    log_df.to_csv(log_file, index=False)
                    st.success("✅ 수정 완료")

# 📈 시각화
elif menu == "📈 Cell 사용량 시각화":
    st.subheader("📈 Cell 사용량 시각화")
    if os.path.exists(log_file):
        log_df = pd.read_csv(log_file)
        log_df = log_df[log_df["Sheet"].isin(cell_data.keys())]
        log_df["Date"] = pd.to_datetime(log_df["Date"], errors="coerce")

        chart_df = log_df.groupby("Material")["Used Quantity"].sum().reset_index()
        st.bar_chart(chart_df.set_index("Material"))

        st.markdown("### 📊 타임라인 추이")
        timeline_df = log_df.groupby(["Date", "Material"])["Used Quantity"].sum().reset_index()
        fig = px.line(timeline_df, x="Date", y="Used Quantity", color="Material", markers=True)
        st.plotly_chart(fig, use_container_width=True)

# ➕ 수동 입력
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

        submitted = st.form_submit_button("💾 새 Cell 정보 저장")
        if submitted:
            new_entry = {
                "Tray": tray, "Box": box, "Lot": lot, "Cell name": cell_name,
                "N. of tube": tube, "Date": freeze_date, "Passage": passage, "Name": name,
                "Source": source, "Info (Myco)": info, "freezing condition": freeze_cond,
                "Thaw (date/name)": thaw_info, "additional info": add_info,
                "OncotreeCode": code, "OncotreeSubtype": subtype,
                "OncotreePrimaryDisease": primary, "OncotreeLineage": lineage,
                "Species": species
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            cell_data[selected_sheet] = df
            with pd.ExcelWriter(cell_file, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
                df.to_excel(writer, sheet_name=selected_sheet, index=False)
            st.success("✅ 새 Cell 정보가 저장되었습니다!")
