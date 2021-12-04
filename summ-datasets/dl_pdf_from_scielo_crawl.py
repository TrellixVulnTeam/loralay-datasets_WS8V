import json
import os
import argparse
from tqdm import tqdm
from src.utils import (
    del_file_if_exists,
    overwrite_dir_if_exists,
    extract_pdf,
)
import time

def download_pdf_from_crawl(args):
    num_lines = sum(1 for line in open(args.input_file,'r'))
    with open(args.input_file, 'r') as f:
        for line in tqdm(f, total=num_lines):
            item = json.loads(line)
            output_path = os.path.join(args.output_dir, item["id"] + ".pdf") 
            if "pdf_url" in item and item["pdf_url"] is not None:
                if extract_pdf(item["pdf_url"], output_path):
                    with open(args.downloaded_log, "a") as fw:
                        fw.write(item["doi"] + "\n")
                else:
                    with open(args.not_downloaded_log, "a") as fw:
                        fw.write(item["doi"] + "\n")
            else:
                with open(args.not_downloaded_log, "a") as fw:
                    fw.write(item["doi"] + "\n")
                
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--downloaded_log",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--not_downloaded_log",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory and log files."
    )

    args = parser.parse_args()
   
    if os.listdir(args.output_dir):
        if args.overwrite_output_dir:
            overwrite_dir_if_exists(args.output_dir)
            del_file_if_exists(args.downloaded_log)
            del_file_if_exists(args.not_downloaded_log)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )
            
    download_pdf_from_crawl(args)