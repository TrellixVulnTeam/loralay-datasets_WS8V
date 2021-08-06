
import argparse
import os
import shutil
import subprocess
import re
import json
from tqdm import tqdm
from utils import get_ids


def extract_pdf(arxiv_id, pdf_output_path):
    def matches_first_id_scheme(id):
        p = re.compile("^([a-z\-]*)(\d{7})$")
        m = p.match(id)
        return m
    m = matches_first_id_scheme(arxiv_id)
    if m:
        command = "gsutil cp gs://arxiv-dataset/arxiv/" \
            f"{m.group(1)}/pdf/{m.group(2)[:4]}/{m.group(2)}v1.pdf " \
            f"{pdf_output_path}"
    else:
        p = re.compile("^(\d{4})\.(\d{4,5})$")
        m = p.match(arxiv_id)
        assert m, print(arxiv_id)
        command = "gsutil cp gs://arxiv-dataset/arxiv/" \
            f"arxiv/pdf/{m.group(1)}/{arxiv_id}v1.pdf " \
            f"{pdf_output_path}"

    subprocess.call(command, shell=True)

    if os.path.exists(pdf_output_path):
        return True 
    return False

def extract(args):
    id_list = get_ids(args.input_file, args.n_docs)
    id_list_extracted = []

    for arxiv_id in id_list:
        pdf_output_path = os.path.join(args.pdf_output_dir, arxiv_id + ".pdf")
        pdf_extracted = extract_pdf(arxiv_id, pdf_output_path)
        if pdf_extracted:
            id_list_extracted.append(arxiv_id)
        else:
            print(f"Could not extract PDF file for article {arxiv_id}")

    remaining_ids = id_list_extracted
    with open(args.metadata_file, "r") as f:
        for line in tqdm(f):
            metadata = json.loads(line)
            if metadata["id"] in remaining_ids:
                with open(
                    os.path.join(args.abstract_output_dir, metadata["id"] + ".txt"),
                    "w"
                ) as fw:
                    abstract_words = metadata["abstract"].split()
                    for w in abstract_words:
                        fw.write(w.replace("\n", " ") + "\n")
                remaining_ids.remove(metadata["id"])
                if not remaining_ids:
                    break 

    if remaining_ids:
        for arxiv_id in remaining_ids:
            pdf_output_path = os.path.join(args.pdf_output_dir, arxiv_id + ".pdf")
            print(f"Abstract not found for article {arxiv_id}: deleting {pdf_output_path}")
            os.path.remove(pdf_output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--metadata_file", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--pdf_output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--abstract_output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--n_docs",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if os.listdir(args.pdf_output_dir) or os.listdir(args.abstract_output_dir):
        if args.overwrite_output_dir:
            print(f"Overwriting {args.pdf_output_dir}")
            shutil.rmtree(args.pdf_output_dir)
            os.makedirs(args.pdf_output_dir)
            print(f"Overwriting {args.abstract_output_dir}")
            shutil.rmtree(args.abstract_output_dir)
            os.makedirs(args.abstract_output_dir)
        else:
            if os.listdir(args.pdf_output_dir):
                raise ValueError(
                    f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.listdir(args.abstract_output_dir):
                raise ValueError(
                    f"Output directory ({args.abstract_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )

    extract(args)