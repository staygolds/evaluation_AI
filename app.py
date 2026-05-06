Python 3.13.13 (tags/v3.13.13:01104ce, Apr  7 2026, 19:25:48) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
>>> import streamlit as st
... import pandas as pd
... import google.generativeai as genai
... import os
... 
... # --- 設定 ---
... st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")
... 
... # --- データの読み込み ---
... # Googleスプレッドシートから出したCSVを読み込む
... # フォルダ構成：data/m_staff.csv, data/m_missions.csv, data/m_criteria.csv を想定
... @st.cache_data
... def load_data():
...     staff = pd.read_csv('data/m_staff.csv', encoding='utf-8')
...     missions = pd.read_csv('data/m_missions.csv', encoding='utf-8')
...     criteria = pd.read_csv('data/m_criteria.csv', encoding='utf-8')
...     return staff, missions, criteria
... 
... try:
...     df_staff, df_missions, df_criteria = load_data()
... except Exception as e:
...     st.error(f"CSVファイルの読み込みに失敗しました。ファイル名や保存場所を確認してください: {e}")
...     st.stop()
... 
... # --- サイドバー：評価対象者の選択 ---
... st.sidebar.header("評価対象者の選択")
... staff_names = df_staff['氏名'].tolist()
... selected_name = st.sidebar.selectbox("職員を選んでください", staff_names)
... 
... # 選択された職員の詳細データを取得 [1]
... staff_info = df_staff[df_staff['氏名'] == selected_name].iloc
... staff_id = staff_info['職員ID']
... job_type = staff_info['職種区分']
... qualifications = staff_info['保有資格']
... 
# 職務分掌マスターからミッションを取得 [2]
mission_info = df_missions[df_missions['職員ID'] == staff_id].iloc
main_mission = mission_info['重要ミッション']
target_metric = mission_info['主要数値目標']

# --- メイン画面 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")

col1, col2 = st.columns(2)
with col1:
    st.subheader("基本情報")
    st.write(f"**職種区分:** {job_type}")
    st.write(f"**保有資格:** {qualifications}")
with col2:
    st.subheader("今期のミッション")
    st.info(f"**重要ミッション:**\n{main_mission}")
    st.write(f"**目標数値:** {target_metric} ({mission_info['目標値']})")

st.divider()

# --- 評価入力セクション ---
st.subheader(f"✅ {job_type}職 評価項目入力")
# 職種区分に一致する評価項目（20項目）を抽出 [3]
relevant_criteria = df_criteria[df_criteria['職種区分'] == job_type]

scores = {}
if not relevant_criteria.empty:
    for _, item in relevant_criteria.iterrows():
        # スライダーで1〜5点を選択
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning("この職種の評価項目が見つかりません。")

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    # プロンプトの組み立て（ソース資料の情報を統合）
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    以下の実データに基づき、職員の能力開発と施設目標達成のための分析レポートを「具体的かつ厳格に」作成してください。

    # 職員プロフィール
    - 氏名：{selected_name}
    - 職種：{job_type}
    - 保有資格：{qualifications}

    # 今期の最優先ミッションと数値目標
    - 重要ミッション：{main_mission}
    - 主要数値目標：{target_metric} ({mission_info['目標値']})

    # 今回の行動評価結果（5点満点）
    {eval_text}

    # レポート構成
    1. 【現状の総評】
    2. 【強みの分析】（保有資格やミッションへの貢献度を踏まえて）
    3. 【課題と改善アドバイス】（重要ミッション達成に向けた具体的な行動）
    4. 【本人へのフィードバックメッセージ】
    """

    # Gemini API呼び出し
    try:
        # secrets.toml または 環境変数からAPIキーを取得
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner('AIが分析レポートを作成中です...'):
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
    except Exception as e:
