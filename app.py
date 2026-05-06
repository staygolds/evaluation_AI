import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

@st.cache_data
def load_data():
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSV読み込み失敗: {e}")
    st.stop()

st.sidebar.header("評価対象者の選択")
selected_name = st.sidebar.selectbox("職員を選んでください", df_staff['氏名'].tolist())

staff_matches = df_staff[df_staff['氏名'] == selected_name]
if not staff_matches.empty:
    selected_staff = staff_matches.iloc[0]
    staff_id = selected_staff['職員ID']
    job_title = selected_staff['職種区分']
    department = selected_staff['所属部署']
    qualifications = selected_staff['保有資格']
else:
    st.stop()

mission_matches = df_missions[df_missions['職員ID'] == staff_id]
if not mission_matches.empty:
    selected_mission = mission_matches.iloc[0]
    main_mission = selected_mission['重要ミッション']
    target_metric = selected_mission['主要数値目標']
    target_value = selected_mission['目標値']
else:
    main_mission, target_metric, target_value = "未設定", "未設定", "-"

st.title(f"📊 AI分析レポート作成: {selected_name} さん")
st.write(f"**役職:** {job_title} | **所属:** {department} | **資格:** {qualifications}")
st.info(f"**今期のミッション:** {main_mission}")

st.divider()

# --- 【名称不一致の自動解消】 ---
# 資料[1]の「初任者」を資料[2]の「新任」に自動で読み替えます
search_dept = "新任" if department == "初任者" else department
relevant_criteria = df_criteria[df_criteria['職種区分'] == search_dept]

scores = {}
if not relevant_criteria.empty:
    st.subheader(f"✅ {search_dept}職 評価項目入力")
    for _, item in relevant_criteria.iterrows():
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning(f"「{department}」に対応する評価項目が見つかりません。CSVの所属部署名を確認してください。")

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    以下のソース資料データに基づき、具体的かつ専門的な評価レポートを作成してください。

    # 職員プロフィール
    - 氏名：{selected_name}
    - 役職：{job_title}
    - 保有資格：{qualifications}

    # 今期の最優先ミッションと数値目標
    - 重要ミッション：{main_mission}
    - 主要数値目標：{target_metric} ({target_value})

    # 行動評価結果（5点満点）
    {eval_text}

    # レポート構成
    1. 【現状の総評】
    2. 【強みの分析】
    3. 【課題と改善アドバイス】
    4. 【本人へのフィードバックメッセージ】
    """

try:
        # 1. APIキーの設定
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        
        # 2. モデル名を標準的な 'gemini-1.5-flash' に変更（latestを外す）
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 3. AI分析の実行
        with st.spinner('AIが分析レポートを作成中です...'):
            # ソース資料のデータをプロンプトに渡します
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
            
    except Exception as e:
        # 文法エラーを防ぐため、この except ブロックを必ず try と同じ高さの字下げで書きます
        st.error(f"AI分析中にエラーが発生しました。詳細: {e}")
