import json 
import os 
import argparse
import subprocess 
from tqdm import tqdm 
import subprocess
from src.utils import (
    del_file_if_exists,
    overwrite_dir_if_exists,
)

def extract_pdf(download_link, output_path, cookie):
    command = (
        f"curl '{download_link}' -L --output {output_path} "
        "-H 'Connection: keep-alive' "
        "-H 'Cache-Control: max-age=0' "
        "-H 'Upgrade-Insecure-Requests: 1' "
        "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36' "
        "-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9' " 
        "-H 'Referer: http://www.nssd.cn/login.aspx' "
        "-H 'Accept-Language: fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7' " 
        f"-H 'Cookie: {cookie}' "
        "--compressed "
        "--insecure"
    )
    subprocess.call(command, shell=True)

    if os.path.exists(output_path):
        return True 
    return False

def download_pdf_from_crawl(args):
    num_lines = sum(1 for line in open(args.input_file,'r'))
    with open(args.input_file, 'r') as f:
        for line in tqdm(f, total=num_lines):
            item = json.loads(line)
            output_path = os.path.join(args.output_dir, item["id"] + ".pdf") 
            if extract_pdf(item["download_link"], output_path, args.cookie):
                with open(args.downloaded_log, "a") as fw:
                        fw.write(item["id"] + "\n")
            else:
                with open(args.not_downloaded_log, "a") as fw:
                    fw.write(item["id"] + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--cookie",
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