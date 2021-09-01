import argparse 
import time 
import os 
import shutil 
import json 
import pdfkit
from tqdm import tqdm 
from src.utils import remove_processed_from_id_list

lang_to_code = {
    'arabic': 'ar',
    'bengali': 'bn', 
    'english': 'en',
    'finnish': 'fi',
    'indonesian': 'id',
    'japanese': 'ja',
    'korean': 'ko',
    'russian': 'ru',
    'swahili': 'sw',
    'telugu': 'te',
    'thai': 'th',
}

def get_ids_and_url_mapping(input_file, limit):
    id_list = []
    id_to_url = {}
    num_processed = 0
    with open(input_file, "r") as f:
        for line in f:
            item = json.loads(line)
            lang_code = lang_to_code[item["language"]]
            title = item["document_title"].replace(" ", "_")
            doc_id = title + "-" + lang_code
            if doc_id not in id_list:
                id_list.append(doc_id)
                id_to_url[doc_id] = item["document_url"]
                num_processed += 1
                if num_processed == limit:
                    break
    return (id_list, id_to_url)

def extract(args):
    id_list, id_to_url = get_ids_and_url_mapping(args.input_file, args.n_docs)

    if args.resume:
        id_list = remove_processed_from_id_list(
            id_list, args.downloaded_output_log, failed_log=args.failed_output_log
        )

        if not id_list:
            print("Resuming download...")
            print(f"All documents in {args.input_file} have already been extracted")
            return 
            

    print(f"Extracting {len(id_list)} articles from TyDiQA, using IDs in {args.input_file}")

    for doc_id in tqdm(id_list):
        # title, lang = doc_id.rsplit("-", 1)
        pdf_output_path = os.path.join(args.pdf_output_dir, doc_id + ".pdf")

        pdfkit.from_url(id_to_url[doc_id], pdf_output_path, options={'quiet': ''})

        if os.path.exists(pdf_output_path):
            with open(args.downloaded_output_log, "a") as f:
                f.write(f"{doc_id}\n")
        else:
            with open(args.failed_output_log, "a") as f:
                f.write(f"{doc_id}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--pdf_output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--downloaded_output_log",
        type=str,
        default="./downloaded.log"
    )
    parser.add_argument(
        "--failed_output_log",
        type=str,
        default="./failed_to_download.log"
    )
    parser.add_argument(
        "--n_docs",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--resume",
        action="store_true", 
        help="Resume download."
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if args.resume and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume and --overwrite_output_dir at the same time."
        )

    if os.listdir(args.pdf_output_dir) and not args.resume:
        if args.overwrite_output_dir:
            print(f"Overwriting {args.pdf_output_dir}")
            shutil.rmtree(args.pdf_output_dir)
            os.makedirs(args.pdf_output_dir)
            
            if os.path.isfile(args.downloaded_output_log):
                print(f"Overwriting {args.downloaded_output_log}")
                os.remove(args.downloaded_output_log)
            if os.path.isfile(args.failed_output_log):
                print(f"Overwriting {args.failed_output_log}")
                os.remove(args.failed_output_log)
        else:
            raise ValueError(
                f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )

    extract(args)