import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def extract_sentences(src_name: str, dest_name: str) -> None:
    src_path = ROOT / src_name
    dest_path = ROOT / dest_name

    sentences = []
    with src_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            sentences.append(obj.get("sentence", ""))

    dest_path.write_text("\n".join(sentences), encoding="utf-8")


def main() -> None:
    extract_sentences("train_dataset.jsonl", "train_input_prompts.txt")
    extract_sentences("test_dataset.jsonl", "test_input_prompts.txt")


if __name__ == "__main__":
    main()
