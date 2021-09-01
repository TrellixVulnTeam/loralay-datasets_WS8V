import argparse 
import os 
import shutil
import subprocess
import urllib.request
import json

def get_last_idx(downloaded_log, failed_log):
    """ Get last index processed

    Args:
        downloaded_log (string): Path to log containing IDs of downloaded documents
        failed_log (string): Path to log containing IDs of documents that could 
                             not be downloaded

    Returns:
        int: Last index processed
    """
    with open(downloaded_log, "r") as f:
        lines = f.read().splitlines()
        last_downloaded_idx = lines[-1].split("\t")[0]

    with open(failed_log, "r") as f:
        lines = f.read().splitlines()
        last_failed_idx = lines[-1].split("\t")[0]

    return max(int(last_downloaded_idx), int(last_failed_idx))

def extract_pdf(url, output_path):
    """ Extract PDF based on URL

    Args:
        url (string): link to PDF 
        output_path (string): Path to output PDF file

    Returns:
        bool: True if extraction was successful, False otherwise
    """
    command = f"wget -O {output_path} {url}"
    subprocess.call(command, shell=True)
    
    if os.path.exists(output_path):
        return True
    return False 

def extract(args):
    if args.resume:
        start_idx = get_last_idx(args.downloaded_output_log, args.failed_output_log) + 1
        stop_idx = args.n_docs - start_idx
    else:
        start_idx = 0
        stop_idx = args.n_docs 

    url = "https://api.archives-ouvertes.fr/search/" \
        "?q=*:*&" \
        "wt=json&" \
        "indent=True&" \
        f"fl=docid,files_s,{args.lang}_abstract_s&" \
        f"fq=language_s:{args.lang}+submitType_s:file+docType_s:ART&" \
        f"start={start_idx}&rows={stop_idx}"  
    
    print(url)

    response = urllib.request.urlopen(url).read().decode()
    data = json.loads(response)
    start_idx = int(data["response"]["start"])

    for i, item in enumerate(data["response"]["docs"]):
        failed_extraction = False 
        docid = str(item["docid"])
        if args.lang + "_abstract_s" not in item:
            failed_extraction = True 
        else:
            pdf_output_path = os.path.join(args.pdf_output_dir, docid + ".pdf")        
            abstract_output_path = os.path.join(args.abstract_output_dir, docid + ".txt")

            pdf_url = item["files_s"][0]
            abstract_text = item[args.lang + "_abstract_s"][0]  

            pdf_extracted = extract_pdf(pdf_url, pdf_output_path)

            if abstract_text:
                if pdf_extracted:
                    with open(abstract_output_path, "w") as fw:
                        abstract_words = abstract_text.strip().split()
                        for w in abstract_words:
                            fw.write(w + "\n")
                else:
                    failed_extraction = True
            else:
                failed_extraction = True
                if pdf_extracted: # pdf has been extracted, delete it
                    os.remove(pdf_output_path)

        if failed_extraction:
            with open(args.failed_output_log, "a") as f:
                f.write(str(start_idx + i) + "\t" + docid + "\n")
        else:
            with open(args.downloaded_output_log, "a") as f:
                f.write(str(start_idx + i) + "\t" + docid + "\n")

                

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--lang",
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
        default=30,
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
            for output_dir in [
                args.pdf_output_dir, args.abstract_output_dir
            ]:
                if os.listdir(output_dir):
                    print(f"Overwriting {output_dir}")
                    shutil.rmtree(output_dir)
                    os.makedirs(output_dir)

            if os.path.isfile(args.downloaded_output_log):
                print(f"Overwriting {args.downloaded_output_log}")
                os.remove(args.downloaded_output_log)
            if os.path.isfile(args.failed_output_log):
                print(f"Overwriting {args.failed_output_log}")
                os.remove(args.failed_output_log)
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


