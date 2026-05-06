import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- ページ基本設定 ---
st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

# --- データの読み込み関数 ---
@st.cache_data
def load_data():
    # GitHubリポジトリ直下のCSVファイルを読み込みます
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSVファイルの読み込みに失敗しました: {e}")
    st.stop()

# --- サイドバー：評価対象者の選択 ---
st.sidebar.header("評価対象者の選択")
staff_names = df_staff['氏名'].tolist()
selected_name = st.sidebar.selectbox("職員を選んでください", staff_names)

# --- 重要：ここがエラーの修正箇所です ---
# 1. 選択された氏名に一致する行を抽出
staff_matches = df_staff[df_staff['氏名'] == selected_name]

if not staff_matches.empty:
    # .iloc を付けることで、リストから「最初の1行」のデータとして確定させます
    staff_info = staff_matches.iloc
    
    # これで '職員ID' などの文字キーでデータが取り出せるようになります
    staff_id = staff_info['職員ID']
    job_type = staff_info['職種区分']
    qualifications = staff_info['保有資格']
else:
    st.error("職員情報が見つかりません。")
    st.stop()

# 2. 職員IDをキーに「職務分掌マスター」からミッション情報を取得
mission_matches = df_missions[df_missions['職員ID'] == staff_id]

if not mission_matches.empty:
    # ここでも .iloc でデータを確定させます
    mission_info = mission_matches.iloc
    main_mission = mission_info['重要ミッション']
    target_metric = mission_info['主要数値目標']
    target_value = mission_info['目標値']
else:
    main_mission = "未設定"
    target_metric = "未設定"
    target_value = "-"

# --- メイン画面：基本情報の表示 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")

col1, col2 = st.columns(2)
with col1:
    st.subheader("👤 職員プロフィール")
    st.write(f"**職種区分:** {job_type}")
    st.write(f"**保有資格:** {qualifications}")
with col2:
    st.subheader("🎯 今期のミッション")
    st.info(f"**最優先事項:**\n{main_mission}")
    st.write(f"**数値目標:** {target_metric} ({target_value})")

st.divider()

# --- 評価入力セクション ---
st.subheader(f"✅ {job_type}職 評価項目入力")
relevant_criteria = df_criteria[df_criteria['職種区分'] == job_type]

scores = {}
if not relevant_criteria.empty:
    for _, item in relevant_criteria.iterrows():
        # ソース資料[1]に基づいた評価項目名を表示
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning(f"「{job_type}」職用の評価項目が見つかりません。")

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    以下の実データに基づき、職員の能力開発と施設目標達成のための分析レポートを作成してください。

    # 職員プロフィール
    - 氏名：{selected_name}
    - 職種：{job_type}
    - 保有資格：{qualifications}

    # 今期の最優先ミッションと数値目標
    - 重要ミッション：{main_mission}
    - 主要数値目標：{target_metric} ({target_value})

    # 今回の行動評価結果（5点満点）
    {eval_text}

    # レポート構成
    1. 【現状の総評】
    2. 【強みの分析】
    3. 【課題と改善アドバイス】
    4. 【本人へのフィードバックメッセージ】
    """

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner('AIが分析レポートを作成中です...'):
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
    except Exception as e:
        st.error(f"AI分析中にエラーが発生しました。SecretsにAPIキーが設定されているか確認してください。")
