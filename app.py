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

        # 3) Count the total (raw) characters in the original HTML
        total_chars = count_characters(source)

        # 4) Split using the raw HTML
        raw_fragments = list(split_message(source, max_len))

        fragments_response = []
        for i, raw_fragment in enumerate(raw_fragments, start=1):
            # This is the exact raw length used by your splitting logic:
            raw_length = len(raw_fragment)

            # Prettify for user-friendly display (optional)
            soup = BeautifulSoup(raw_fragment, "html.parser")
            prettified = soup.prettify()

            fragments_response.append({
                "filename": f"fragment_{i}.html",
                "content": prettified,      # Display version
                "raw_length": raw_length    # Precise length of the raw fragment
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
    app.run(debug=True, host="0.0.0.0", port=8002)
