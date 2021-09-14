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

def get_ids(input_file, limit):
    id_list = []
    num_processed = 0
    with open(input_file, "r") as f:
        for line in f:
            item = json.loads(line)
            lang_code = lang_to_code[item["language"]]
            title = item["document_title"].replace(" ", "_")
            doc_id = title + "-" + lang_code
            if doc_id not in id_list:
                id_list.append(doc_id)
                num_processed += 1
                if num_processed == limit:
                    break
    return id_list

def create_title_to_rev_dict(mapping_file):
    title_to_revision = dict()

    with open(mapping_file, "r") as f:
        for line in f:
            title, revision_id = line.split("\t")
            title_to_revision[title] = revision_id.rstrip()

    return title_to_revision

def extract(args):
    id_list = get_ids(args.input_file, args.n_docs)
    id_list = list(set(id_list))

    if args.resume:
        print("Resuming download...")
        id_list = remove_processed_from_id_list(
            id_list, args.downloaded_output_log, failed_log=args.failed_output_log
        )

        if not id_list:
            print(f"All documents in {args.input_file} have already been extracted")
            return 

    title_to_revision_id = dict()     
    for mapping_file in os.listdir(args.mapping_dir):
        lang_code = mapping_file.replace(".txt", "")
        mapping_path = os.path.join(args.mapping_dir, mapping_file)
        title_to_revision_id[lang_code] = create_title_to_rev_dict(mapping_path)

    print(f"Extracting {len(id_list)} articles from TyDiQA, using IDs in {args.input_file}")

    num_fails = 0

    for doc_id in tqdm(id_list):
        title, lang = doc_id.rsplit("-", 1)
        pdf_output_path = os.path.join(args.pdf_output_dir, doc_id + ".pdf")
        
        # wikipedia.set_lang(lang)
        # page = wikipedia.page(title=title, auto_suggest=False)
    
        if lang not in title_to_revision_id.keys():
            url = f"https://{lang}.wikipedia.org/w/index.php?title={title}"
        else:
            if title in title_to_revision_id[lang]:
                revision_id = title_to_revision_id[lang][title]
                url = f"https://{lang}.wikipedia.org/w/index.php?title={title}&oldid={revision_id}"
            else:
                print(f"Could not extract article at {title} (lang:{lang})")
                num_fails += 1
                with open(args.failed_output_log, "a") as f:
                    f.write(f"{doc_id}\n")
                continue

        try:
            pdfkit.from_url(
                url, 
                pdf_output_path, 
                options={
                    'quiet': '',
                    'load-error-handling': 'ignore'
                },
            )
        except OSError:
            print(f"Could not extract article at url {url}")

        if os.path.exists(pdf_output_path):
            with open(args.downloaded_output_log, "a") as f:
                f.write(f"{doc_id}\n")
        else:
            num_fails += 1
            with open(args.failed_output_log, "a") as f:
                f.write(f"{doc_id}\n")

    print(f"Extracted PDF for {len(id_list) - num_fails}/{len(id_list)} documents.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--mapping_dir", 
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