import json
import os

import tweepy
from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify

from sheets import append_history, get_manga_list, get_recent_history, pick_manga

load_dotenv(override=True)

app = Flask(__name__)
client = Anthropic()

SYSTEM_PROMPT = """あなたは「のりさん」として漫画アフィリエイト投稿を書く専門家です。

【のりさん節の特徴】
- ちょい毒・ちょいユーモア
- 家族ネタ（妻氏・娘氏・推し活）を自然に混ぜる
- 自虐を少し混ぜる
- ロジックで整理する
- 最後に「自戒も込めて」で締める

【投稿ルール】
- 画像は使わない（テキストのみ）
- 台詞引用は1〜2行まで
- 核心ネタバレは避ける
- 「気づき」「あるある」「家族・仕事ネタ」に変換する
- 最後にアフィリンクを自然に添える
- 140〜200字程度

JSONのみを返すこと。余計な説明や ```json ブロックは不要。"""


def _x_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def _build_posts(manga):
    history = get_recent_history(7)
    history_text = "\n".join(
        f"- [{h['date']}] {h['title']}: {h['post']}" for h in history
    ) or "（履歴なし）"

    user_prompt = f"""以下の漫画データで投稿を3案生成してください。

【漫画データ】
タイトル: {manga['title']}
引用: {manga['quote']}
テーマ: {manga['theme']}
アフィリンク: {manga['link']}

【直近の投稿履歴】
{history_text}

履歴を参考に重複しないトーンや切り口で3案作成してください。
履歴の傾向から分析と改善ポイントも記載してください。

以下のJSONのみを返してください：
{{
  "analysis": "直近の投稿傾向の分析（1〜2文）",
  "insights": "改善ポイント（1〜2文）",
  "posts": [
    {{"text": "投稿案1（アフィリンク含む）"}},
    {{"text": "投稿案2（アフィリンク含む）"}},
    {{"text": "投稿案3（アフィリンク含む）"}}
  ]
}}"""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


@app.route("/health")
def health():
    sid = os.environ.get("SPREADSHEET_ID", "NOT SET")
    has_creds = bool(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
    return jsonify({
        "spreadsheet_id": sid,
        "credentials_json_set": has_creds,
        "credentials_json_length": len(os.environ.get("GOOGLE_CREDENTIALS_JSON", "")),
    })


@app.route("/generate", methods=["POST"])
def generate():
    """投稿案を3件生成して返す（X には投稿しない）"""
    manga_list = get_manga_list()
    manga = pick_manga(manga_list)
    result = _build_posts(manga)

    append_history(
        result["posts"][0]["text"],
        manga,
        result.get("analysis", ""),
        result.get("insights", ""),
    )

    return jsonify(result)


@app.route("/post", methods=["POST"])
def post():
    """投稿案を生成し、1案目をXに自動投稿する"""
    manga_list = get_manga_list()
    manga = pick_manga(manga_list)
    result = _build_posts(manga)

    post_text = result["posts"][0]["text"]
    print(f"[POST] 文字数: {len(post_text)}")
    print(f"[POST] テキスト:\n{post_text}")

    try:
        tweet = _x_client().create_tweet(text=post_text)
        tweet_id = tweet.data["id"]
    except tweepy.errors.Forbidden as e:
        print(f"[X 403] {e}")
        api_errors = getattr(e, "api_errors", None)
        api_codes = getattr(e, "api_codes", None)
        return jsonify({
            "error": "X API 403 Forbidden",
            "message": str(e),
            "api_errors": api_errors,
            "api_codes": api_codes,
            "post_text": post_text,
            "char_count": len(post_text),
        }), 403

    append_history(
        post_text,
        manga,
        result.get("analysis", ""),
        result.get("insights", ""),
    )

    result["tweet_id"] = tweet_id
    result["posted_text"] = post_text
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
