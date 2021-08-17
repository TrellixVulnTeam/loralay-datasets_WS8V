import argparse 
import os 
import shutil
import subprocess
import xml.etree.ElementTree as ET
import urllib.request
import json

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
    if args.resume_download:
        pass
    else:
        url = "https://api.archives-ouvertes.fr/search/" \
            "?q=*:*&" \
            "wt=json&" \
            "indent=True&" \
            f"fl=docid,files_s,{args.lang}_abstract_s&" \
            f"fq=language_s:{args.lang}+submitType_s:file+docType_s:ART" 
    
    print(url)

    response = urllib.request.urlopen(url).read().decode()
    data = json.loads(response)

    for item in data["response"]["docs"]:
        failed_extraction = False 
        if args.lang + "_abstract_s" not in item:
            failed_extraction = True 
        else:
            docid = str(item["docid"])

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
                f.write(docid + "\n")
        else:
            with open(args.downloaded_output_log, "a") as f:
                f.write(docid + "\n")

                

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
        default=5,
    )
    parser.add_argument(
        "--resume_download",
        action="store_true", 
        help="Resume download."
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if args.resume_download and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume_download and --overwrite_output_dir at the same time."
        )

    if os.listdir(args.pdf_output_dir) and not args.resume_download:
        if args.overwrite_output_dir:
            for output_dir in [
                args.pdf_output_dir, args.abstract_output_dir
            ]:
                print(f"Overwriting {output_dir}")
                shutil.rmtree(output_dir)
                os.makedirs(output_dir)

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
            if os.path.isfile(args.downloaded_output_log):
                raise ValueError(
                    f"Output file ({args.downloaded_output_log}) already exists. Use --overwrite_output_dir to overcome."
                )
            if os.path.isfile(args.failed_output_log):
                raise ValueError(
                    f"Output file ({args.failed_output_log}) already exists. Use --overwrite_output_dir to overcome."
                )


    extract(args)


