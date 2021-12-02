
import urllib.request
import json
from tqdm import tqdm
import os
from pathlib import Path
import argparse
from src.utils import del_file_if_exists

def extract(args):
    url = "https://api.archives-ouvertes.fr/search/" \
        "?q=*:*&" \
        "wt=json&" \
        "indent=True&" \
        f"fl=docid,abstract_s,{args.lang}_abstract_s&" \
        f"fq=language_s:{args.lang}+submitType_s:file+docType_s:(ART%20OR%20COMM)&" \
        f"start={args.start_idx}&rows={args.num_rows}"  
    
    response = urllib.request.urlopen(url).read().decode()
    data = json.loads(response)

    fpaths = list(Path(args.input_dir).rglob("*.txt"))
    fnames = [os.path.basename(fpath).replace(".txt", "") for fpath in fpaths]

    for i, item in enumerate(tqdm(data["response"]["docs"])):
        docid = str(item["docid"])

        if args.lang + "_abstract_s" not in item:
            continue 

        if docid in fnames:
            all_abstracts = item["abstract_s"]
            main_abstract = item[args.lang + "_abstract_s"][0]

            if len(all_abstracts) <= 1:
                continue 

            all_abstracts = [abstract for abstract in all_abstracts if abstract != main_abstract]
            all_abstracts = [abstract_text.replace("\n", "") for abstract_text in all_abstracts]

            with open(args.other_abstracts_output_path, "a") as fw:
                json.dump(
                    {"id": docid, "abstract": all_abstracts}, fw, ensure_ascii=False
                )
                fw.write('\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--lang",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--input_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--other_abstracts_output_path", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--start_idx",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--num_rows",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--overwrite_output", 
        action="store_true", 
    )

    args = parser.parse_args()

    if args.overwrite_output:
        del_file_if_exists(args.other_abstracts_output_path)  

    extract(args)
