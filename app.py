import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from msg_split import split_message, SplitMessageError, count_characters

app = Flask(__name__)
CORS(app)

@app.route("/api/split", methods=["POST"])
def split_html():
    try:
        # 1) Get the source HTML
        if "file" in request.files:
            file = request.files["file"]
            content = file.read()
            source = content.decode("utf-8")
        else:
            with open("source.html", "r", encoding="utf-8") as f:
                source = f.read()

        # 2) Parse max_len
        max_len = int(request.form.get("max_len", 4096))

        # 3) Count total (raw) characters
        total_chars = count_characters(source)

        # 4) Split
        raw_fragments = list(split_message(source, max_len))

        fragments_response = []
        for i, raw_fragment in enumerate(raw_fragments, start=1):
            raw_length = len(raw_fragment)

            # Optionally prettify for display
            soup = BeautifulSoup(raw_fragment, "html.parser")
            prettified = soup.prettify()

            fragments_response.append({
                "filename": f"fragment_{i}.html",
                "content": prettified,
                "raw_length": raw_length
            })

        return jsonify({
            "fragments": fragments_response,
            "totalCharacters": total_chars
        })

    except SplitMessageError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

if __name__ == "__main__":
    # For local development. Gunicorn on Railway will use `web: gunicorn app:app`
    port = int(os.environ.get("PORT", 8002))
    app.run(debug=True, host="0.0.0.0", port=port)
